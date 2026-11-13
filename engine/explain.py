"""Why the engine gave the answer it gave.

`evaluate` returns the verdict. This module answers the three questions a
reader asks next, and it answers them by running the same rules again rather
than by anyone writing the answers down:

* which rule actually decided it, so the card can lead with the specific
  sentence instead of a general one that happens to be first;
* what single change would give a different answer;
* what nearly happened, and the condition that stopped it.

Nothing here evaluates a rule differently from `evaluate`. It reads the same
`when:` trees with the same matcher, so an explanation cannot describe a rule
the engine does not actually have (BUILD_SPEC 0.5).
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations, product
from typing import Any

from engine.conditions import COMBINATORS, Condition, leaves, matches, specificity
from engine.models import (
    Inputs,
    Rule,
    Status,
    resolve_effective_tier,
)
from engine.rules import evaluate, load_rules

#: Severity order, repeated from models because this module ranks rules that
#: did *not* fire, which `most_severe` has no view on.
_SEVERITY: dict[Status, int] = {
    Status.ALLOWED: 0,
    Status.NEEDS_APPROVAL: 1,
    Status.NOT_PERMITTED: 2,
    Status.PROHIBITED: 3,
}


# --------------------------------------------------------------------------
# Reading a `when:` tree
# --------------------------------------------------------------------------


def unmet(node: Any, ctx: dict[str, Any]) -> list[Condition] | None:
    """The conditions a non-matching tree fails on, or None if inexplicable.

    `none_of` is deliberately not explained. A rule that fires only when
    something is *absent* fails because something is present, and naming the
    condition it "missed" would invert its meaning. Those rules are left out
    of the near-miss search rather than described wrongly.
    """
    if not isinstance(node, dict):
        return None

    combinator = next((name for name in COMBINATORS if name in node), None)

    if combinator == "none_of":
        return None

    if combinator == "all_of":
        missing: list[Condition] = []
        for branch in node[combinator]:
            if matches(branch, ctx):
                continue
            branch_unmet = unmet(branch, ctx)
            if branch_unmet is None:
                return None
            missing.extend(branch_unmet)
        return missing

    if combinator == "any_of":
        # The nearest branch is the one asking for the least.
        best: list[Condition] | None = None
        for branch in node[combinator]:
            branch_unmet = unmet(branch, ctx)
            if branch_unmet is None:
                continue
            if best is None or len(branch_unmet) < len(best):
                best = branch_unmet
        return best

    return [leaf for leaf in leaves(node) if not _satisfied(leaf, ctx)]


def _satisfied(condition: Condition, ctx: dict[str, Any]) -> bool:
    value = ctx.get(condition.field)
    return any(type(a) is type(value) and a == value for a in condition.accepted)


# --------------------------------------------------------------------------
# What decided it
# --------------------------------------------------------------------------


def deciding_rules(inputs: Inputs, version: str) -> list[Rule]:
    """The rules that fired at the verdict's own status, most specific first.

    These are the rules the answer rests on. The others fired too, and say
    something true, but removing them would not change the answer.
    """
    ctx = inputs.context(resolve_effective_tier(inputs, version))
    status = evaluate(inputs, version).status
    fired = [rule for rule in load_rules(version) if matches(rule.when, ctx)]
    decisive = [rule for rule in fired if rule.status is status]
    return sorted(decisive, key=lambda rule: -specificity(rule.when))


# --------------------------------------------------------------------------
# What would change it
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Flip:
    """A single input change that lands on a different status."""

    field: str
    value: Any
    status: Status

    @property
    def is_relaxation(self) -> bool:
        return False  # set by `flips`, which knows the status it came from


def flips(inputs: Inputs, version: str, fields: list[str]) -> list[Flip]:
    """Every one-field change, among `fields`, that changes the status.

    The caller passes the fields it is actually showing, so the page never
    offers to change something the visitor cannot see. Each candidate is run
    through `evaluate` exactly as a real answer would be: nothing here
    predicts a verdict, it asks for one.
    """
    current = evaluate(inputs, version).status
    found: list[Flip] = []

    for field in fields:
        value = getattr(inputs, field, None)
        if value is None or not isinstance(value, bool | str):
            continue
        for candidate in _alternatives(value):
            try:
                altered = inputs.model_copy(update={field: candidate})
                status = evaluate(altered, version).status
            except Exception:  # noqa: BLE001 - an impossible combination is not a flip
                continue
            if status is not current:
                found.append(Flip(field=field, value=candidate, status=status))

    return found


def _alternatives(value: Any) -> list[Any]:
    """Every other value this input could take."""
    if isinstance(value, bool):
        return [not value]
    if isinstance(value, str):
        return [member for member in type(value) if member != value]
    return []


def best_flips(inputs: Inputs, version: str, fields: list[str], limit: int = 3) -> list[Flip]:
    """The most useful flips: the gentlest change per field, least strict first.

    One chip per field, because three ways to make the same field worse is a
    list of synonyms. Relaxations lead, since a reader who has just been told
    no is looking for the route rather than for more ways to be refused.
    """
    current = _SEVERITY[evaluate(inputs, version).status]

    gentlest: dict[str, Flip] = {}
    for flip in flips(inputs, version, fields):
        best = gentlest.get(flip.field)
        if best is None or _SEVERITY[flip.status] < _SEVERITY[best.status]:
            gentlest[flip.field] = flip

    ordered = sorted(
        gentlest.values(),
        key=lambda flip: (
            0 if _SEVERITY[flip.status] < current else 1,
            abs(_SEVERITY[flip.status] - current) * -1,
        ),
    )
    return ordered[:limit]


# --------------------------------------------------------------------------
# What nearly happened
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class NearMiss:
    """A stricter rule that did not fire, and what stopped it."""

    rule: Rule
    missing: tuple[Condition, ...]


def nearest_stricter(inputs: Inputs, version: str) -> NearMiss | None:
    """The stricter rule that came closest to firing, and the condition it missed.

    "Why is this only Needs approval and not Prohibited?" is the question an
    auditor asks, and a policy that cannot answer it is being trusted rather
    than read. The answer is computed: the rule with the fewest unmet
    conditions among those stricter than the verdict.
    """
    ctx = inputs.context(resolve_effective_tier(inputs, version))
    current = _SEVERITY[evaluate(inputs, version).status]

    candidates: list[NearMiss] = []
    for rule in load_rules(version):
        if _SEVERITY[rule.status] <= current:
            continue
        if matches(rule.when, ctx):
            continue  # it fired; it is not a near miss
        missing = unmet(rule.when, ctx)
        if not missing:
            continue  # inexplicable, or nothing to report
        candidates.append(NearMiss(rule=rule, missing=tuple(missing)))

    if not candidates:
        return None

    return min(
        candidates,
        key=lambda near: (len(near.missing), -_SEVERITY[near.rule.status], near.rule.id),
    )


# --------------------------------------------------------------------------
# The way out
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Change:
    """One input moved to a new value."""

    field: str
    value: Any


@dataclass(frozen=True)
class Route:
    """A set of changes that reaches a gentler answer, and the answer it reaches."""

    changes: tuple[Change, ...]
    status: Status

    @property
    def reaches_allowed(self) -> bool:
        return self.status is Status.ALLOWED


def is_hard_line(inputs: Inputs, version: str) -> bool:
    """Whether the activity itself is prohibited under Section 6.

    The distinction matters, and it is not the same as "the verdict is
    PROHIBITED". Confidential data in a personal account is prohibited and
    has an obvious way out: use a different tool. Emotion recognition is
    prohibited *because of what it is*, and there is nothing to change —
    offering a route there would read as a way around the ban.

    A rule marks the second kind by naming the activity in its `when:` tree
    and citing Section 6. Both facts come from the rule, so no list of
    "real" prohibitions is kept anywhere.
    """
    if evaluate(inputs, version).status is not Status.PROHIBITED:
        return False

    ctx = inputs.context(resolve_effective_tier(inputs, version))
    for rule in load_rules(version):
        if rule.status is not Status.PROHIBITED or not matches(rule.when, ctx):
            continue
        names_activity = any(leaf.field == "activity" for leaf in leaves(rule.when))
        cites_section_6 = any(clause.split(".")[0] == "6" for clause in rule.clauses)
        if names_activity and cites_section_6:
            return True
    return False


#: The activity is the one input a route must never touch. It is what the
#: person is trying to do; a "safe way" that changes it has not found a way
#: to do the thing asked about, it has proposed a different question. The
#: What if… chips still show activity flips, where they are offered as
#: comparisons rather than as advice.
ROUTE_EXCLUDED: frozenset[str] = frozenset({"activity"})

#: How much a change preserves the original question, most preserving first.
#: Putting a control in place (an allowlist, a cap, a human reviewer) leaves
#: the work untouched. Moving to an approved tool leaves the work untouched
#: too. Reclassifying the data, last, means taking the sensitive part out,
#: which is a real answer but a larger one. A field not named here sorts
#: after everything that is.
ROUTE_FIELD_ORDER: tuple[str, ...] = (
    "tool",
    "host",
    "human_review",
    "client_contract_allows",
    "payee_on_allowlist",
    "recipient_on_allowlist",
    "within_caps",
    "agent_action",
    "meeting_type",
    "training_or_finetuning",
    "data_class",
    "data_kind",
)


def _route_rank(field: str) -> int:
    try:
        return ROUTE_FIELD_ORDER.index(field)
    except ValueError:
        return len(ROUTE_FIELD_ORDER)


def safe_route(
    inputs: Inputs,
    version: str,
    fields: list[str],
    max_changes: int = 2,
) -> Route | None:
    """The smallest set of changes that reaches a gentler answer.

    One change is searched before two, so the shortest way out is the one
    offered. Within a size the gentlest answer wins; between two routes to
    the same answer, the one that disturbs the question least wins, by
    `ROUTE_FIELD_ORDER`. Every candidate is run through `evaluate`: the route
    is found, never predicted.

    Returns None when the activity is a Section 6 hard line, when nothing
    useful is changeable, or when no combination of changes helps.
    """
    if is_hard_line(inputs, version):
        return None

    current = _SEVERITY[evaluate(inputs, version).status]
    if current == 0:
        return None

    movable = sorted(
        (
            field
            for field in fields
            if field not in ROUTE_EXCLUDED and _alternatives(getattr(inputs, field, None))
        ),
        key=_route_rank,
    )

    for size in range(1, max_changes + 1):
        best: Route | None = None
        best_key: tuple[int, int] | None = None
        for combination in combinations(movable, size):
            cost = sum(_route_rank(field) for field in combination)
            for values in product(*(_alternatives(getattr(inputs, f)) for f in combination)):
                changes = tuple(
                    Change(field=f, value=v) for f, v in zip(combination, values, strict=True)
                )
                try:
                    altered = inputs.model_copy(
                        update={change.field: change.value for change in changes}
                    )
                    status = evaluate(altered, version).status
                except Exception:  # noqa: BLE001 - an impossible combination is not a route
                    continue
                if _SEVERITY[status] >= current:
                    continue
                key = (_SEVERITY[status], cost)
                if best_key is None or key < best_key:
                    best, best_key = Route(changes=changes, status=status), key
        if best is not None:
            return best
    return None
