"""The golden scenarios of BUILD_SPEC 6.

If an expected result conflicts with the policy text, the rule is wrong or the
policy is ambiguous: log it in OPEN_QUESTIONS.md. Never edit a scenario to make
a test pass (BUILD_SPEC 6).
"""

from __future__ import annotations

import re

import pytest

from engine.explain import deciding_rules
from engine.models import ApprovalKind, Inputs, Status
from engine.policy_parser import load_policy
from engine.rules import evaluate, load_rules
from engine.scenarios import load_scenarios

SCENARIOS = load_scenarios()
IDS = [f"{s.n:02d}-{s.title[:40]}" for s in SCENARIOS]


@pytest.mark.parametrize("scenario", SCENARIOS, ids=IDS)
def test_golden_scenario_status(scenario):
    verdict = evaluate(scenario.inputs)
    assert verdict.status is scenario.expect, (
        f"scenario {scenario.n} ({scenario.title}): expected {scenario.expect.value}, "
        f"got {verdict.status.value} from rules {verdict.fired_rules}"
    )


@pytest.mark.parametrize("scenario", SCENARIOS, ids=IDS)
def test_golden_scenario_cites_required_clauses(scenario):
    verdict = evaluate(scenario.inputs)
    missing = [c for c in scenario.must_cite if c not in verdict.clauses]
    assert not missing, (
        f"scenario {scenario.n} ({scenario.title}): missing {missing}; cited {verdict.clauses}"
    )


@pytest.mark.parametrize(
    "scenario",
    [s for s in SCENARIOS if s.approval_kind is not None],
    ids=[f"{s.n:02d}" for s in SCENARIOS if s.approval_kind is not None],
)
def test_golden_scenario_approval_kind(scenario):
    """OPEN_QUESTIONS Q3: one-time use-case approval vs approval per action."""
    verdict = evaluate(scenario.inputs)
    assert verdict.approval_kind is scenario.approval_kind, (
        f"scenario {scenario.n} ({scenario.title}): expected "
        f"{scenario.approval_kind.value}, got {verdict.approval_kind.value}"
    )


# --------------------------------------------------------------------------
# Invariants that hold for every verdict
# --------------------------------------------------------------------------


@pytest.mark.parametrize("scenario", SCENARIOS, ids=IDS)
def test_not_permitted_offers_a_route_and_prohibited_does_not(scenario):
    """BUILD_SPEC 5: NOT_PERMITTED has a compliant route; PROHIBITED has none."""
    verdict = evaluate(scenario.inputs)
    if verdict.status is Status.NOT_PERMITTED:
        assert verdict.try_instead, f"scenario {scenario.n} needs try_instead"
    if verdict.status is Status.PROHIBITED:
        assert verdict.try_instead is None, (
            f"scenario {scenario.n} is PROHIBITED under Section 6, which has no "
            f"route and no exceptions (18.1), but offers: {verdict.try_instead}"
        )


@pytest.mark.parametrize("scenario", SCENARIOS, ids=IDS)
def test_every_verdict_has_a_reason_and_a_clause(scenario):
    verdict = evaluate(scenario.inputs)
    assert verdict.reasons
    assert verdict.clauses


@pytest.mark.parametrize("scenario", SCENARIOS, ids=IDS)
def test_approval_kind_is_none_unless_approval_is_needed(scenario):
    verdict = evaluate(scenario.inputs)
    if verdict.status is not Status.NEEDS_APPROVAL:
        assert verdict.approval_kind is ApprovalKind.NONE


@pytest.mark.parametrize("scenario", SCENARIOS, ids=IDS)
def test_needs_approval_lists_what_is_required(scenario):
    verdict = evaluate(scenario.inputs)
    if verdict.status is Status.NEEDS_APPROVAL:
        assert verdict.requirements, "BUILD_SPEC 5: NEEDS_APPROVAL lists what is required"


# --------------------------------------------------------------------------
# Precedence and the engine's own contract
# --------------------------------------------------------------------------


def test_precedence_prohibited_beats_needs_approval():
    """Scenario 13 fires both 6.1 (prohibited) and 8.6 (needs approval)."""
    verdict = evaluate(
        Inputs(
            data_class="Restricted",
            tool="A",
            activity="emotion_recognition",
            data_kind="sensitive_personal",
        )
    )
    assert verdict.status is Status.PROHIBITED
    assert "6.1" in verdict.clauses
    assert "8.6" in verdict.clauses, "every fired rule still contributes its clauses"


def test_all_rules_are_evaluated_not_just_the_first_match():
    verdict = evaluate(
        Inputs(
            data_class="Restricted",
            tool="A",
            activity="decision_about_person",
            human_review=False,
            hiring=True,
            data_kind="sensitive_personal",
        )
    )
    assert verdict.status is Status.PROHIBITED
    for clause_id in ("6.6", "8.1", "8.6", "HR.1", "7.4"):
        assert clause_id in verdict.clauses


def test_in_cap_payment_and_out_of_cap_payment_differ_only_in_approval_kind():
    base = {
        "data_class": "Confidential",
        "tool": "A",
        "activity": "agent",
        "agent_action": "pay",
        "payee_on_allowlist": True,
    }
    in_cap = evaluate(Inputs(**base, within_caps=True))
    out_of_cap = evaluate(Inputs(**base, within_caps=False))
    assert in_cap.status is out_of_cap.status is Status.NEEDS_APPROVAL
    assert in_cap.approval_kind is ApprovalKind.ONE_TIME_USE_CASE
    assert out_of_cap.approval_kind is ApprovalKind.PER_ACTION


def test_agent_cannot_widen_its_own_allowlist():
    for action in ("add_payee", "add_recipient"):
        verdict = evaluate(
            Inputs(data_class="Confidential", tool="A", activity="agent", agent_action=action)
        )
        assert verdict.status is Status.NOT_PERMITTED
        assert verdict.try_instead == "a human adds it, and it is logged"


def test_read_only_agent_is_allowed():
    verdict = evaluate(
        Inputs(data_class="Internal", tool="A", activity="agent", agent_action="read")
    )
    assert verdict.status is Status.ALLOWED


def test_self_hosted_host_changes_the_effective_tier():
    """B.1.3 and 2.3: only org infrastructure reaches Tier A."""
    confidential = {"data_class": "Confidential", "tool": "self_hosted", "activity": "drafting"}
    assert evaluate(Inputs(**confidential, host="org_cloud")).status is Status.ALLOWED
    assert evaluate(Inputs(**confidential, host="managed_laptop")).status is Status.NOT_PERMITTED
    assert evaluate(Inputs(**confidential, host="personal_device")).status is Status.NOT_PERMITTED


def test_secrets_are_prohibited_in_every_tier():
    for tool in ("A", "B", "C"):
        verdict = evaluate(Inputs(data_class="Secrets", tool=tool, activity="coding"))
        assert verdict.status is Status.PROHIBITED
        assert "6.3" in verdict.clauses


def test_client_training_without_contract_permission_is_prohibited():
    verdict = evaluate(
        Inputs(
            data_class="Confidential",
            tool="A",
            activity="drafting",
            data_kind="client_info",
            training_or_finetuning=True,
            client_contract_allows=False,
        )
    )
    assert verdict.status is Status.PROHIBITED
    assert "6.8" in verdict.clauses


def test_ruleset_loads_with_unique_ids_and_valid_conditions():
    rules = load_rules("v1_5")
    assert len(rules) == len({rule.id for rule in rules})
    assert len(rules) > 30


# --------------------------------------------------------------------------
# Stakes and the next move (Phase 5)
# --------------------------------------------------------------------------

#: A clause id as it appears inside a sentence. Either a lettered id (C.2,
#: B.1.3, HR.1) or a numeric one with at least one dot (7.1, 11.3). A bare
#: number is deliberately not one, so "Section 7" and "20 working days" are
#: prose rather than citations.
CLAUSE_IN_PROSE = re.compile(r"\b([A-Z]{1,3}\.\d+(?:\.\d+)*|\d+\.\d+(?:\.\d+)*)\b")


@pytest.mark.parametrize("rule", load_rules("v1_6"), ids=lambda r: r.id)
def test_every_v1_6_rule_says_what_is_at_stake_and_what_to_do(rule):
    assert rule.why_it_matters, f"{rule.id} has no why_it_matters"
    assert rule.next_step, f"{rule.id} has no next_step"


@pytest.mark.parametrize("rule", load_rules("v1_6"), ids=lambda r: r.id)
def test_the_stake_and_the_next_step_are_each_one_sentence(rule):
    """Two sentences in a card field is a paragraph, and a paragraph on a
    verdict card is not read."""
    for field in (rule.why_it_matters, rule.next_step):
        assert field.rstrip().endswith("."), field
        assert field.count(". ") == 0, f"{rule.id}: more than one sentence — {field}"


@pytest.mark.parametrize("rule", load_rules("v1_6"), ids=lambda r: r.id)
def test_every_clause_cited_in_prose_exists_in_the_policy(rule):
    """The stake and the next step cite clauses in their own text, which is
    not checked by `resolve_clauses`. An invented id would read as real."""
    known = set(load_policy("v1_6").clauses)
    for field in (rule.why_it_matters, rule.next_step):
        for cited in CLAUSE_IN_PROSE.findall(field):
            assert cited in known, f"{rule.id} cites {cited}, which v1.6 does not have"


@pytest.mark.parametrize("rule", load_rules("v1_6"), ids=lambda r: r.id)
def test_the_next_step_cites_at_least_one_clause(rule):
    assert CLAUSE_IN_PROSE.findall(rule.next_step), f"{rule.id}: {rule.next_step}"


def test_an_approval_next_step_names_the_route_and_its_b4_target():
    """BUILD_SPEC: a verdict that says "get it approved" and stops has told
    someone nothing they can act on."""
    targets = {row[1] for row in load_policy("v1_6").table("B.4").rows}
    approvals = [
        rule
        for rule in load_rules("v1_6")
        if rule.status is Status.NEEDS_APPROVAL and "intake form" in rule.next_step
    ]
    assert approvals, "no rule routes anyone to the intake form"
    for rule in approvals:
        assert any(target in rule.next_step for target in targets), rule.next_step
        assert "B.4" in rule.next_step, rule.next_step


def test_the_verdict_carries_the_leading_rules_stake_and_next_step():
    """One voice: the card must not explain one rule's answer with another
    rule's consequences."""
    for example in load_scenarios():
        verdict = evaluate(example.inputs, "v1_6")
        leading = next(
            rule
            for rule in deciding_rules(example.inputs, "v1_6")
            if rule.reason == verdict.reasons[0]
        )
        assert verdict.why_it_matters == leading.why_it_matters
        assert verdict.next_step == leading.next_step


def test_older_rulesets_load_without_the_new_fields():
    """v1.0 and v1.5 are historical and are not rewritten to suit the card."""
    for version in ("v1_0", "v1_5"):
        assert all(rule.why_it_matters is None for rule in load_rules(version))
        assert all(rule.next_step is None for rule in load_rules(version))
