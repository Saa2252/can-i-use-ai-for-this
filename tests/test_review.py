"""The v1.0 ruleset and the Review page (Phase 4)."""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from engine.models import (
    Activity,
    ApprovalKind,
    DataClass,
    EffectiveTier,
    Host,
    Inputs,
    Status,
    Tool,
    resolve_effective_tier,
)
from engine.policy_parser import load_policy
from engine.review import changed_verdicts, compare, compare_all
from engine.rules import evaluate, load_rules
from engine.scenarios import scenario

ENTRYPOINT = str(Path(__file__).resolve().parent.parent / "app" / "main.py")


def open_review() -> AppTest:
    at = AppTest.from_file(ENTRYPOINT, default_timeout=60)
    at.run()
    at.switch_page("pages/5_review.py")
    at.run()
    return at


def body(at: AppTest) -> str:
    return "\n".join(
        [
            *(m.value for m in at.markdown),
            *(h.value for h in at.html if "<style>" not in h.value),
            *(c.value for c in at.code),
        ]
    )


# --------------------------------------------------------------------------
# The v1.0 ruleset
# --------------------------------------------------------------------------


def test_v1_0_ruleset_loads():
    rules = load_rules("v1_0")
    assert len(rules) > 20
    assert len(rules) == len({rule.id for rule in rules})


def test_every_v1_0_clause_is_a_real_v1_0_clause():
    """Guards the numbering trap: v1.0's 7.3 is not v1.5's 7.3."""
    policy = load_policy("v1_0")
    for rule in load_rules("v1_0"):
        for clause_id in rule.clauses:
            assert clause_id in policy.clauses, f"{rule.id} cites {clause_id}, absent from v1.0"


def test_v1_0_cites_no_part_b_or_c_clause():
    for rule in load_rules("v1_0"):
        for clause_id in rule.clauses:
            assert not clause_id.startswith(("B.", "C.")), (
                f"{rule.id} cites {clause_id}, but v1.0 has no Parts B or C"
            )


def test_v1_0_sensitive_data_cites_7_3_not_7_4():
    """v1.0's 7.3 is the special-category clause; its 7.4 is client data."""
    verdict = evaluate(
        Inputs(
            data_class=DataClass.RESTRICTED,
            tool=Tool.TIER_A,
            activity=Activity.DRAFTING,
            data_kind="hr_health_record",
        ),
        "v1_0",
    )
    assert "7.3" in verdict.clauses
    assert "7.5" not in verdict.clauses, "v1.0 has no clause on ordinary personal data"


def test_v1_0_has_no_whole_interaction_classification_clause():
    """v1.5's 7.2 was inserted; under v1.0 that number means something else."""
    verdict = evaluate(
        Inputs(data_class=DataClass.INTERNAL, tool=Tool.TIER_A, activity=Activity.DRAFTING),
        "v1_0",
    )
    assert "7.2" not in verdict.clauses


# --------------------------------------------------------------------------
# Version-dependent tier resolution
# --------------------------------------------------------------------------


@pytest.mark.parametrize("host", [Host.ORG_CLOUD, Host.MANAGED_LAPTOP, Host.PERSONAL_DEVICE])
def test_v1_0_treats_every_self_hosted_model_as_tier_c(host):
    """v1.0's only Tier A test (7.5) is vendor-contract shaped."""
    inputs = Inputs(
        data_class=DataClass.INTERNAL,
        tool=Tool.SELF_HOSTED,
        host=host,
        activity=Activity.DRAFTING,
    )
    assert resolve_effective_tier(inputs, "v1_0") is EffectiveTier.C


def test_v1_5_tiers_a_self_hosted_model_by_its_host():
    base = {
        "data_class": DataClass.INTERNAL,
        "tool": Tool.SELF_HOSTED,
        "activity": Activity.DRAFTING,
    }
    assert resolve_effective_tier(Inputs(**base, host=Host.ORG_CLOUD), "v1_5") is EffectiveTier.A
    assert (
        resolve_effective_tier(Inputs(**base, host=Host.MANAGED_LAPTOP), "v1_5") is EffectiveTier.B
    )
    assert (
        resolve_effective_tier(Inputs(**base, host=Host.PERSONAL_DEVICE), "v1_5")
        is EffectiveTier.PERSONAL_SELFHOSTED
    )


# --------------------------------------------------------------------------
# The four verdicts that changed
# --------------------------------------------------------------------------


def test_exactly_the_expected_scenarios_changed():
    changed = {change.scenario.n for change in changed_verdicts()}
    assert changed == {9, 11, 19, 20}


def test_off_allowlist_message_tightened_to_per_action():
    """v1.0 offered a pre-approved scope for any agent action; v1.5 does not."""
    change = compare(scenario(9))
    assert change.before.approval_kind is ApprovalKind.ONE_TIME_USE_CASE
    assert change.after.approval_kind is ApprovalKind.PER_ACTION
    assert not change.status_changed


def test_agent_adding_its_own_payee_became_not_permitted():
    change = compare(scenario(11))
    assert change.before.status is Status.NEEDS_APPROVAL
    assert change.after.status is Status.NOT_PERMITTED
    assert "C.2" in change.after.clauses


def test_notetaker_in_a_legal_meeting_was_allowed_under_v1_0():
    """v1.0 is not silent here: 8.10 permits everything else."""
    change = compare(scenario(19))
    assert change.before.status is Status.ALLOWED
    assert "8.10" in change.before.clauses
    assert change.after.status is Status.NEEDS_APPROVAL
    assert "B.6.3" in change.after.clauses


def test_self_hosted_on_a_personal_device_softened_and_gained_a_route():
    change = compare(scenario(20))
    assert change.before.status is Status.PROHIBITED
    assert change.after.status is Status.NOT_PERMITTED
    assert change.before.try_instead is None
    assert change.after.try_instead, "v1.5 gives this a compliant route"


def test_unchanged_scenarios_really_are_unchanged():
    for change in compare_all():
        if change.scenario.n not in {9, 11, 19, 20}:
            assert not change.changed, f"scenario {change.scenario.n} changed unexpectedly"


def test_citations_changed_even_where_the_verdict_did_not():
    """Scenario 4 keeps its answer but gains 7.5, which v1.0 lacked."""
    change = compare(scenario(4))
    assert not change.changed
    assert change.citations_changed
    assert "7.5" in change.added_clauses


# --------------------------------------------------------------------------
# Changelog parsing
# --------------------------------------------------------------------------


def test_all_five_changelogs_are_parsed():
    changelogs = load_policy("v1_5").changelogs
    assert list(changelogs) == ["1.5", "1.4", "1.3", "1.2", "1.1"]
    assert all(table.headers == ["Area", "Change"] for table in changelogs.values())
    assert sum(len(table.rows) for table in changelogs.values()) == 28


def test_v1_5_changelog_records_the_second_exception():
    row = load_policy("v1_5").changelogs["1.5"].rows[0]
    assert row[0] == "External messages"
    assert "second narrow exception" in row[1]


def test_v1_0_has_no_changelogs():
    assert load_policy("v1_0").changelogs == {}


def test_changelogs_contribute_no_clauses():
    policy = load_policy("v1_5")
    assert "1.5" not in policy.clauses


# --------------------------------------------------------------------------
# The Review page
# --------------------------------------------------------------------------


def test_review_page_runs():
    assert not open_review().exception


def test_review_page_lists_the_changed_scenarios():
    page = body(open_review())
    assert "Scenarios whose verdict changed" in page
    assert "4 of 21 scenarios" in page
    for title in (
        "Agent emails an address not on the list",
        "Agent adds a new payee to its own allowlist",
        "Notetaker in a meeting with legal counsel",
        "Open-weight model on a personal laptop, with internal docs",
    ):
        assert title in page


def test_review_page_shows_both_versions_for_a_scenario():
    at = open_review()
    at.selectbox(key="cu_review_scenario").set_value(20).run()
    page = body(at)
    assert "Under v1.0" in page
    assert "Under v1.5" in page
    assert "Prohibited" in page and "Not permitted" in page


def test_review_page_renders_the_changelog_cards():
    page = body(open_review())
    assert "How the policy changed" in page
    assert "second narrow exception" in page
    assert "The R1 to R9 labels are removed" in page


def test_review_page_covers_the_four_disputed_points():
    """Titles are expander labels, which AppTest exposes separately from text."""
    at = open_review()
    assert "Where it could have gone the other way" in body(at)
    labels = {expander.label for expander in at.expander}
    for title in (
        "Fatigue detection",
        "The absolute ban on secrets",
        "Platform labelling",
        "The R1 to R9 codes",
    ):
        assert title in labels


def test_changelog_expanders_count_changes_grammatically():
    labels = {expander.label for expander in open_review().expander}
    assert "Version 1.5 — 1 change" in labels
    assert "Version 1.4 — 4 changes" in labels


def test_disputed_points_give_both_readings_and_say_what_the_record_is():
    page = body(open_review())
    assert page.count("One reading") == 4
    assert page.count("The other") == 4
    assert page.count("How it was settled") == 4
    assert "no transcript of the review itself" in page


def test_disputed_points_only_cite_real_clauses():
    import app.pages  # noqa: F401

    source = (Path(__file__).resolve().parent.parent / "app" / "pages" / "5_review.py").read_text(
        encoding="utf-8"
    )
    policy = load_policy("v1_5")
    import re

    for clause_id in re.findall(r'"(\d{1,2}\.\d{1,2}|[BC]\.\d{1,2}(?:\.\d{1,2})?)"', source):
        assert clause_id in policy.clauses
