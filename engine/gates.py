"""The four gates a question passes through, and where it stopped.

A verdict says what the answer is. It does not say how far the question got
before something stopped it, which is the thing a reader actually wants to
see: *this* was fine, *this* was fine, and then it failed here.

The policy already has those gates. They are its own sections, and they are
ordered by severity, which is why this module needs no table of its own:

    Section 6   prohibited uses          PROHIBITED
    Section 7   data rules and the 7.1 grid   NOT_PERMITTED
    Section 8   uses that need approval  NEEDS_APPROVAL
    Section 9   human oversight of outputs    ALLOWED

`evaluate` already resolves the status as the most severe thing that fired.
So the gate a question stopped at is the gate whose status *is* the verdict's,
every stricter gate was passed, and every gentler one was never reached.
Nothing here re-decides anything: it reads the rules that fired and sorts
them into the sections they already cite.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from engine.conditions import matches, specificity
from engine.models import Inputs, Rule, Status, resolve_effective_tier
from engine.rules import evaluate, load_rules, resolve_clauses


class GateState(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    #: A stricter gate already decided the answer, so this one was never
    #: asked. Saying so is more honest than showing it as passed.
    NOT_REACHED = "not_reached"


@dataclass(frozen=True)
class Gate:
    """One gate, and what happened at it."""

    status: Status
    name: str
    section: str
    question: str
    state: GateState
    clauses: tuple[str, ...] = ()
    reason: str | None = None

    @property
    def is_stop(self) -> bool:
        """Whether this is the gate the question stopped at."""
        return self.state is GateState.FAILED


#: Severity order, lowest gate last. `most_severe` already encodes the same
#: order for statuses; this is the reading order of the trail.
_ORDER: tuple[tuple[Status, str, str, str], ...] = (
    (
        Status.PROHIBITED,
        "Hard line",
        "6",
        "Is this one of the uses the policy rules out entirely?",
    ),
    (
        Status.NOT_PERMITTED,
        "Data and tool",
        "7",
        "May this class of data go into this tier of tool?",
    ),
    (
        Status.NEEDS_APPROVAL,
        "Approval",
        "8",
        "Does this have to be approved and registered before it starts?",
    ),
    (
        Status.ALLOWED,
        "Output checks",
        "9",
        "What you still carry responsibility for afterwards.",
    ),
)

_SEVERITY: dict[Status, int] = {
    Status.ALLOWED: 0,
    Status.NEEDS_APPROVAL: 1,
    Status.NOT_PERMITTED: 2,
    Status.PROHIBITED: 3,
}


def _state(gate_status: Status, verdict_status: Status) -> GateState:
    if gate_status is verdict_status:
        # The gentlest gate is the one nothing stopped at: reaching Section 9
        # with nothing above it having fired is the pass, not the failure.
        return GateState.PASSED if gate_status is Status.ALLOWED else GateState.FAILED
    if _SEVERITY[gate_status] > _SEVERITY[verdict_status]:
        return GateState.PASSED
    return GateState.NOT_REACHED


def _leading(rules: list[Rule]) -> Rule | None:
    """The rule at a gate that names the most inputs, as `evaluate` orders them."""
    if not rules:
        return None
    return sorted(rules, key=lambda rule: -specificity(rule.when))[0]


def gates(inputs: Inputs, version: str, limit: int = 3) -> list[Gate]:
    """The four gates for this question, in reading order.

    `limit` caps how many clauses a single gate shows, because the Section 9
    gate collects every note that fired and a trail is not a drawer.
    """
    verdict = evaluate(inputs, version)
    ctx = inputs.context(resolve_effective_tier(inputs, version))
    fired = [rule for rule in load_rules(version) if matches(rule.when, ctx)]

    trail: list[Gate] = []
    for status, name, section, question in _ORDER:
        state = _state(status, verdict.status)
        at_gate = [rule for rule in fired if rule.status is status]

        clauses: tuple[str, ...] = ()
        reason: str | None = None
        if state is not GateState.NOT_REACHED and at_gate:
            lead = _leading(at_gate)
            assert lead is not None
            reason = lead.reason
            ids = [cid for rule in at_gate for cid in rule.clauses]
            ordered = [clause.id for clause in resolve_clauses(_dedupe(ids), version)]
            # The gate is a section, so that section's own clauses lead. A
            # Section 9 gate headed by 7.1 is citing a true clause at the
            # wrong gate, which reads as a mistake even when it is not.
            ordered.sort(key=lambda cid: 0 if cid.split(".")[0] == section else 1)
            clauses = tuple(ordered[:limit])

        trail.append(
            Gate(
                status=status,
                name=name,
                section=section,
                question=question,
                state=state,
                clauses=clauses,
                reason=reason,
            )
        )
    return trail


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out
