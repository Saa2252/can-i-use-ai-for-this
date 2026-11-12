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
