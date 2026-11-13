"""The four gates, and where a question stopped.

The trail is not allowed to be a second opinion. Everything here checks that
it agrees with `evaluate`: the gate that failed is the gate whose status is
the verdict's, the stricter gates passed, the gentler ones were not reached,
and no gate cites a clause the verdict does not.
"""

from __future__ import annotations

import pytest

from engine.gates import _ORDER, GateState, gates
from engine.models import Status
from engine.rules import evaluate
from engine.scenarios import load_scenarios

VERSION = "v1_6"

SCENARIOS = [(s.n, s) for s in load_scenarios()]
IDS = [f"scenario-{n}" for n, _ in SCENARIOS]

SEVERITY = {
    Status.ALLOWED: 0,
    Status.NEEDS_APPROVAL: 1,
    Status.NOT_PERMITTED: 2,
    Status.PROHIBITED: 3,
}


@pytest.mark.parametrize("number,example", SCENARIOS, ids=IDS)
def test_the_trail_is_the_policys_four_sections_in_order(number, example):
    trail = gates(example.inputs, VERSION)
    assert [gate.section for gate in trail] == ["6", "7", "8", "9"]
    assert [gate.status for gate in trail] == [status for status, *_ in _ORDER]


@pytest.mark.parametrize("number,example", SCENARIOS, ids=IDS)
def test_exactly_one_gate_stops_the_question(number, example):
    """Unless nothing stopped it: an allowed answer reaches the last gate."""
    verdict = evaluate(example.inputs, VERSION)
    trail = gates(example.inputs, VERSION)
    failed = [gate for gate in trail if gate.state is GateState.FAILED]

    if verdict.status is Status.ALLOWED:
        assert not failed
        assert all(gate.state is GateState.PASSED for gate in trail)
    else:
        assert len(failed) == 1
        assert failed[0].status is verdict.status


@pytest.mark.parametrize("number,example", SCENARIOS, ids=IDS)
def test_stricter_gates_passed_and_gentler_ones_were_never_reached(number, example):
    verdict = evaluate(example.inputs, VERSION)
    for gate in gates(example.inputs, VERSION):
        if SEVERITY[gate.status] > SEVERITY[verdict.status]:
            assert gate.state is GateState.PASSED, gate.name
        elif SEVERITY[gate.status] < SEVERITY[verdict.status]:
            assert gate.state is GateState.NOT_REACHED, gate.name


@pytest.mark.parametrize("number,example", SCENARIOS, ids=IDS)
def test_no_gate_cites_a_clause_the_verdict_does_not(number, example):
    verdict = evaluate(example.inputs, VERSION)
    for gate in gates(example.inputs, VERSION):
        assert set(gate.clauses) <= set(verdict.clauses), gate.name


@pytest.mark.parametrize("number,example", SCENARIOS, ids=IDS)
def test_a_gate_leads_with_its_own_sections_clauses(number, example):
    """A Section 9 gate headed by 7.1 is a true clause at the wrong gate."""
    for gate in gates(example.inputs, VERSION):
        own = [cid for cid in gate.clauses if cid.split(".")[0] == gate.section]
        if own:
            assert gate.clauses[0] in own, f"{gate.name} leads with {gate.clauses[0]}"


@pytest.mark.parametrize("number,example", SCENARIOS, ids=IDS)
def test_a_gate_that_was_not_reached_explains_nothing(number, example):
    """Rules do fire at the allowed floor for a prohibited question. Reporting
    them under a gate the answer never got to would be inventing a step."""
    for gate in gates(example.inputs, VERSION):
        if gate.state is GateState.NOT_REACHED:
            assert not gate.clauses
            assert gate.reason is None


def test_the_failed_gate_carries_the_reason_the_card_leads_with():
    """The trail and the card are the same rule seen twice, not two sources."""
    example = next(
        s for s in load_scenarios() if evaluate(s.inputs, VERSION).status is not Status.ALLOWED
    )
    verdict = evaluate(example.inputs, VERSION)
    failed = next(g for g in gates(example.inputs, VERSION) if g.state is GateState.FAILED)
    assert failed.reason == verdict.reasons[0]


def test_the_clause_limit_is_respected():
    allowed = next(
        s for s in load_scenarios() if evaluate(s.inputs, VERSION).status is Status.ALLOWED
    )
    for gate in gates(allowed.inputs, VERSION, limit=2):
        assert len(gate.clauses) <= 2
