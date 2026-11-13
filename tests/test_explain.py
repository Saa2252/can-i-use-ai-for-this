"""The explanation layer (Phase 3).

Everything here is introspection over the rules the engine already has. The
tests are written to fail if an explanation ever describes something the
rulebook does not do — a chip promising an answer `evaluate` would not give,
a near miss on a rule that actually fired, a "deciding" rule that did not.
"""

from __future__ import annotations

import pytest

from engine.conditions import leaves, matches, specificity
from engine.explain import (
    best_flips,
    deciding_rules,
    flips,
    is_hard_line,
    nearest_stricter,
    safe_route,
    unmet,
)
from engine.models import (
    Activity,
    DataClass,
    DataKind,
    Inputs,
    Status,
    Tool,
    resolve_effective_tier,
)
from engine.rules import evaluate, load_rules
from engine.scenarios import load_scenarios, scenario

VERSION = "v1_6"

#: Severity order, repeated here so a route that claims to improve the
#: answer is checked against the order rather than against itself.
SEVERITY = {
    Status.ALLOWED: 0,
    Status.NEEDS_APPROVAL: 1,
    Status.NOT_PERMITTED: 2,
    Status.PROHIBITED: 3,
}

CHANGEABLE = ["data_class", "tool", "activity", "data_kind"]

CLIENT_CONTRACT = Inputs(
    data_class=DataClass.CONFIDENTIAL,
    data_kind=DataKind.CLIENT_INFO,
    tool=Tool.TIER_C,
    activity=Activity.DRAFTING,
)
PLAIN_DRAFTING = Inputs(
    data_class=DataClass.INTERNAL,
    tool=Tool.TIER_A,
    activity=Activity.DRAFTING,
)


# --------------------------------------------------------------------------
# Reading a `when:` tree
# --------------------------------------------------------------------------


def test_specificity_counts_the_inputs_a_rule_pins_down() -> None:
    assert specificity({}) == 0
    assert specificity({"tool": "A"}) == 1
    assert specificity({"all_of": [{"tool": "A"}, {"data_class": ["Internal"]}]}) == 2


def test_a_leaf_keeps_every_value_it_accepts() -> None:
    (leaf,) = leaves({"data_class": ["Internal", "Confidential"]})
    assert leaf.field == "data_class"
    assert leaf.accepted == ("Internal", "Confidential")


def test_unmet_refuses_to_explain_a_none_of() -> None:
    """A rule that fires on absence fails because something is *present*.

    Naming the condition it "missed" would invert the rule, so these are
    left out of the near-miss search rather than described wrongly.
    """
    assert unmet({"none_of": [{"tool": "A"}]}, {"tool": "A"}) is None


# --------------------------------------------------------------------------
# What decided it
# --------------------------------------------------------------------------


@pytest.mark.parametrize("example", load_scenarios(), ids=lambda s: f"{s.n}")
def test_every_deciding_rule_fired_and_carries_the_verdict_status(example) -> None:
    verdict = evaluate(example.inputs, VERSION)
    deciding = deciding_rules(example.inputs, VERSION)
    assert deciding, f"scenario {example.n} has a verdict with nothing deciding it"
    for rule in deciding:
        assert rule.status is verdict.status
        assert rule.id in verdict.fired_rules


@pytest.mark.parametrize("example", load_scenarios(), ids=lambda s: f"{s.n}")
def test_the_card_leads_with_the_most_specific_deciding_rule(example) -> None:
    """The reason line is the specific sentence, not whichever came first."""
    verdict = evaluate(example.inputs, VERSION)
    deciding = deciding_rules(example.inputs, VERSION)
    assert verdict.reasons[0] == deciding[0].reason


def test_the_general_note_no_longer_leads_a_plain_allowed_answer() -> None:
    """The regression this ordering exists for.

    7.2's "classify the whole interaction" fires on every question, so it led
    the card whenever it happened to sort first — telling a reader who asked
    about Internal data in a Tier A tool nothing about Internal data or Tier A.
    """
    verdict = evaluate(PLAIN_DRAFTING, VERSION)
    assert verdict.reasons[0] == "Internal data is allowed in Tier A and Tier B tools."
    assert any("Classify the whole interaction" in reason for reason in verdict.reasons[1:])


@pytest.mark.parametrize("example", load_scenarios(), ids=lambda s: f"{s.n}")
def test_decisive_clauses_are_a_subset_of_all_clauses(example) -> None:
    verdict = evaluate(example.inputs, VERSION)
    assert set(verdict.decisive_clauses) <= set(verdict.clauses)
    assert verdict.decisive_clauses, f"scenario {example.n} cites nothing as decisive"


# --------------------------------------------------------------------------
# What would change it
# --------------------------------------------------------------------------


@pytest.mark.parametrize("example", load_scenarios(), ids=lambda s: f"{s.n}")
def test_every_offered_flip_really_does_flip(example) -> None:
    """A chip may not promise an answer the engine would not give."""
    current = evaluate(example.inputs, VERSION).status
    for flip in best_flips(example.inputs, VERSION, CHANGEABLE):
        altered = example.inputs.model_copy(update={flip.field: flip.value})
        actual = evaluate(altered, VERSION).status
        assert actual is flip.status, f"{flip.field}={flip.value} claims {flip.status}"
        assert actual is not current, "a flip that changes nothing is not a flip"


def test_flips_change_exactly_one_field() -> None:
    for flip in flips(CLIENT_CONTRACT, VERSION, CHANGEABLE):
        altered = CLIENT_CONTRACT.model_copy(update={flip.field: flip.value})
        differences = [
            name
            for name in type(CLIENT_CONTRACT).model_fields
            if getattr(altered, name) != getattr(CLIENT_CONTRACT, name)
        ]
        assert differences == [flip.field]


def test_best_flips_offers_one_chip_per_field_and_leads_with_the_way_out() -> None:
    found = best_flips(CLIENT_CONTRACT, VERSION, CHANGEABLE)
    assert found, "a prohibited answer with no way out teaches nothing"
    assert len({flip.field for flip in found}) == len(found), "two chips for one field"
    assert found[0].status is Status.ALLOWED


def test_best_flips_never_offers_a_field_that_is_not_on_screen() -> None:
    found = best_flips(CLIENT_CONTRACT, VERSION, ["tool"])
    assert {flip.field for flip in found} == {"tool"}


# --------------------------------------------------------------------------
# What nearly happened
# --------------------------------------------------------------------------


def test_nothing_is_stricter_than_prohibited() -> None:
    assert evaluate(CLIENT_CONTRACT, VERSION).status is Status.PROHIBITED
    assert nearest_stricter(CLIENT_CONTRACT, VERSION) is None


@pytest.mark.parametrize("example", load_scenarios(), ids=lambda s: f"{s.n}")
def test_a_near_miss_is_stricter_and_really_did_not_fire(example) -> None:
    verdict = evaluate(example.inputs, VERSION)
    near = nearest_stricter(example.inputs, VERSION)
    if near is None:
        return
    assert near.rule.id not in verdict.fired_rules, "a rule that fired is not a near miss"
    assert near.missing, "a near miss with nothing missing is just a rule that fired"


@pytest.mark.parametrize("example", load_scenarios(), ids=lambda s: f"{s.n}")
def test_the_conditions_a_near_miss_names_are_really_unmet(example) -> None:
    """Each named condition must be one the inputs actually fail."""
    near = nearest_stricter(example.inputs, VERSION)
    if near is None:
        return
    ctx = example.inputs.context(resolve_effective_tier(example.inputs, VERSION))
    for condition in near.missing:
        value = ctx.get(condition.field)
        assert not any(type(a) is type(value) and a == value for a in condition.accepted), (
            f"{condition.field} already satisfies the rule"
        )


def test_a_near_miss_names_a_rule_that_exists_in_this_version() -> None:
    ids = {rule.id for rule in load_rules(VERSION)}
    near = nearest_stricter(PLAIN_DRAFTING, VERSION)
    assert near is not None
    assert near.rule.id in ids


# --------------------------------------------------------------------------
# The way out (Phase 5)
# --------------------------------------------------------------------------

ROUTE_FIELDS = [
    "data_class",
    "tool",
    "activity",
    "host",
    "agent_action",
    "meeting_type",
    "human_review",
    "payee_on_allowlist",
    "recipient_on_allowlist",
    "within_caps",
    "client_contract_allows",
    "training_or_finetuning",
]


def _fields_for(inputs) -> list[str]:
    return [name for name in ROUTE_FIELDS if getattr(inputs, name, None) is not None]


@pytest.mark.parametrize("example", load_scenarios(), ids=lambda s: f"{s.n}")
def test_a_route_really_reaches_the_answer_it_promises(example):
    """The button cannot offer a verdict the engine would refuse to give."""
    route = safe_route(example.inputs, VERSION, _fields_for(example.inputs))
    if route is None:
        return
    altered = example.inputs.model_copy(
        update={change.field: change.value for change in route.changes}
    )
    assert evaluate(altered, VERSION).status is route.status


@pytest.mark.parametrize("example", load_scenarios(), ids=lambda s: f"{s.n}")
def test_a_route_is_always_an_improvement(example):
    route = safe_route(example.inputs, VERSION, _fields_for(example.inputs))
    if route is None:
        return
    current = evaluate(example.inputs, VERSION).status
    assert SEVERITY[route.status] < SEVERITY[current]


@pytest.mark.parametrize("example", load_scenarios(), ids=lambda s: f"{s.n}")
def test_a_route_never_changes_what_you_are_trying_to_do(example):
    """Changing the activity is not a safer way to do the thing asked about,
    it is a different question."""
    route = safe_route(example.inputs, VERSION, _fields_for(example.inputs))
    if route is None:
        return
    assert all(change.field != "activity" for change in route.changes)


@pytest.mark.parametrize("example", load_scenarios(), ids=lambda s: f"{s.n}")
def test_a_route_is_at_most_two_changes_and_prefers_one(example):
    fields = _fields_for(example.inputs)
    route = safe_route(example.inputs, VERSION, fields)
    if route is None:
        return
    assert 1 <= len(route.changes) <= 2
    if len(route.changes) == 2:
        one_change = safe_route(example.inputs, VERSION, fields, max_changes=1)
        assert one_change is None, "a one-change route existed and was passed over"


@pytest.mark.parametrize("example", load_scenarios(), ids=lambda s: f"{s.n}")
def test_a_hard_line_is_offered_no_route_at_all(example):
    if is_hard_line(example.inputs, VERSION):
        assert safe_route(example.inputs, VERSION, _fields_for(example.inputs)) is None


@pytest.mark.parametrize("example", load_scenarios(), ids=lambda s: f"{s.n}")
def test_a_hard_line_is_an_activity_prohibited_by_section_6(example):
    """Computed from the rule that fired, not from a list kept somewhere."""
    verdict = evaluate(example.inputs, VERSION)
    ctx = example.inputs.context(resolve_effective_tier(example.inputs, VERSION))
    expected = verdict.status is Status.PROHIBITED and any(
        matches(rule.when, ctx)
        and rule.status is Status.PROHIBITED
        and any(leaf.field == "activity" for leaf in leaves(rule.when))
        and any(clause.startswith("6.") for clause in rule.clauses)
        for rule in load_rules(VERSION)
    )
    assert is_hard_line(example.inputs, VERSION) is expected


def test_a_tool_question_is_not_a_hard_line():
    """Confidential data in a personal account is prohibited and has an
    obvious way out. Treating it like emotion recognition would hide that."""
    client_contract = scenario(2)
    assert evaluate(client_contract.inputs, VERSION).status is Status.PROHIBITED
    assert not is_hard_line(client_contract.inputs, VERSION)
    route = safe_route(client_contract.inputs, VERSION, _fields_for(client_contract.inputs))
    assert route is not None
    assert [change.field for change in route.changes] == ["tool"]


def test_emotion_recognition_is_a_hard_line():
    emotion = scenario(13)
    assert is_hard_line(emotion.inputs, VERSION)
    assert safe_route(emotion.inputs, VERSION, _fields_for(emotion.inputs)) is None


def test_an_allowed_answer_is_offered_no_route():
    allowed = next(
        s for s in load_scenarios() if evaluate(s.inputs, VERSION).status is Status.ALLOWED
    )
    assert safe_route(allowed.inputs, VERSION, _fields_for(allowed.inputs)) is None
