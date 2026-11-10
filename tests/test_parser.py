"""Parser tests, including the checks named in BUILD_SPEC 4."""

from __future__ import annotations

import re

import pytest

from engine.policy_parser import load_policy

R_CODE_RE = re.compile(r"\bR[1-9]\b")


@pytest.fixture(scope="module")
def v1_5():
    return load_policy("v1_5")


@pytest.fixture(scope="module")
def v1_0():
    return load_policy("v1_0")


# --------------------------------------------------------------------------
# Known clause texts, byte for byte against the policy file
# --------------------------------------------------------------------------


def test_short_clause_text_is_exact(v1_5):
    assert v1_5.clause("6.2").text == (
        "Creating or altering sexual or intimate imagery of a real person, "
        "or any child sexual abuse material."
    )


def test_clause_2_3_is_exact(v1_5):
    assert v1_5.clause("2.3").text == (
        "On personal devices, AI may be used with non-public work data only "
        "through approved apps running in a managed work profile. Otherwise, "
        "personal devices may be used with public information only."
    )


def test_v1_5_amended_11_3_carries_both_exceptions(v1_5):
    text = v1_5.clause("11.3").text
    assert "with two exceptions" in text
    assert "(a) payments within the per-action and daily caps" in text
    assert "(b) messages sent outside the organization" in text
    assert "never widen them" in text


def test_clause_with_bullets_keeps_its_list(v1_5):
    text = v1_5.clause("10.2").text
    assert text.startswith("Where local law is stricter, it applies.")
    assert "- Realistic synthetic images, audio and video are always labelled" in text


def test_clause_body_stops_before_the_next_paragraph(v1_5):
    """B.1.3 keeps its bullets but not the paragraph that follows them."""
    text = v1_5.clause("B.1.3").text
    assert "- A licence that permits the intended commercial use." in text
    assert "Those are the only hosts eligible for Tier A." in text
    assert "Self-hosting removes vendor risk" not in text


def test_part_d_annex_clauses_are_parsed(v1_5):
    assert v1_5.clause("HR.1").part == "D"
    assert "anti-bias testing before and after deployment" in v1_5.clause("HR.1").text
    assert v1_5.clause("ED.4").text.startswith("Tools used by minors")


# --------------------------------------------------------------------------
# Tables
# --------------------------------------------------------------------------


def test_7_1_table_is_5_by_3(v1_5):
    table = v1_5.table("7.1")
    assert table.shape == (5, 3)
    assert table.headers == ["Data class", "Tier A", "Tier B", "Tier C"]
    assert [row[0] for row in table.rows] == [
        "Public",
        "Internal",
        "Confidential",
        "Restricted",
        "Secrets",
    ]
    assert table.rows[3][1] == "Approved use case only"
    assert table.rows[4] == ["Secrets", "Never", "Never", "Never"]


def test_c_2_table_has_6_rows(v1_5):
    table = v1_5.table("C.2")
    assert len(table.rows) == 6
    assert [row[0] for row in table.rows] == [
        "Spend",
        "Rate",
        "Recipients",
        "Data scope",
        "Tools",
        "Irreversible actions",
    ]


def test_c_2_rows_carry_the_v1_5_amendments(v1_5):
    rows = {row[0]: row[1] for row in v1_5.table("C.2").rows}
    assert "is never done by an agent" in rows["Recipients"]
    assert "any external message outside the recipient allowance" in rows["Irreversible actions"]


def test_section_4_defines_irreversible_action(v1_5):
    definitions = {row[0]: row[1] for row in v1_5.table("4").rows}
    assert "Irreversible action" in definitions
    assert (
        "even where a refund or chargeback might later be possible"
        in definitions["Irreversible action"]
    )


def test_b_3_risk_rubric_is_parsed(v1_5):
    rubric = v1_5.table("B.3", 0)
    assert rubric.headers == ["Factor", "Low", "Medium", "High"]
    assert len(rubric.rows) == 5
    levels = v1_5.table("B.3", 1)
    assert [row[0] for row in levels.rows] == ["Low", "Medium", "High"]


def test_b_4_service_targets_are_parsed(v1_5):
    targets = {row[0]: row[1] for row in v1_5.table("B.4").rows}
    assert targets["Triage of any request"] == "2 working days"
    assert len(targets) == 3


# --------------------------------------------------------------------------
# Leaf sections vs containers
# --------------------------------------------------------------------------


@pytest.mark.parametrize("clause_id", ["B.3", "B.4", "B.8", "B.9", "B.10", "C.2", "C.3"])
def test_leaf_sections_are_citable(v1_5, clause_id):
    assert v1_5.clause(clause_id).text


@pytest.mark.parametrize(
    "container,child",
    [("B.1", "B.1.3"), ("B.6", "B.6.5"), ("C.1", "C.1.2"), ("C.4", "C.4.2")],
)
def test_container_sections_expose_sub_clauses(v1_5, container, child):
    assert child in v1_5.clauses
    assert container not in v1_5.clauses


# --------------------------------------------------------------------------
# BUILD_SPEC 4: the R-code check
# --------------------------------------------------------------------------


def test_no_clause_text_in_v1_5_contains_r_codes(v1_5):
    """Scoped to clause text, per OPEN_QUESTIONS Q2.

    The string survives once in the v1.4 changelog table, which is version
    history rather than clause text and is what the Review page is built from.
    """
    offenders = {
        clause.id: R_CODE_RE.findall(clause.text)
        for clause in v1_5.clauses.values()
        if R_CODE_RE.search(clause.text)
    }
    assert offenders == {}


def test_v1_0_still_uses_r_codes(v1_0):
    """The guard above would pass trivially if the parser returned nothing."""
    assert any(R_CODE_RE.search(clause.text) for clause in v1_0.clauses.values())


# --------------------------------------------------------------------------
# The two document shapes
# --------------------------------------------------------------------------


def test_v1_0_has_no_part_b_or_c_clauses(v1_0):
    """OPEN_QUESTIONS Q1: v1.0 predates the Part A-D restructure."""
    assert not [cid for cid in v1_0.clauses if cid.startswith(("B.", "C."))]
    assert "7.1" in v1_0.clauses
    assert "FS.1" in v1_0.clauses


def test_v1_0_annex_clauses_are_found(v1_0):
    assert v1_0.clause("HR.1").part == "D"
    assert v1_0.clause("FS.6").text.startswith("Concentration on single AI")


def test_v1_0_has_no_notetaker_rules(v1_0):
    """Underpins OPEN_QUESTIONS Q1: v1.0 is silent, not merely different."""
    assert "8.11" not in v1_0.clauses
    assert not any("notetaker" in clause.text.lower() for clause in v1_0.clauses.values())


def test_staff_summary_present_in_v1_5_and_absent_in_v1_0(v1_5, v1_0):
    summary = v1_5.staff_summary
    assert not summary.is_empty
    assert len(summary.always) == 6
    assert len(summary.ask_first) == 7
    assert len(summary.never) == 5
    assert summary.always[0] == "Use approved AI tools with your work account."
    assert v1_0.staff_summary.is_empty


def test_bold_prose_is_not_mistaken_for_a_clause(v1_5):
    """The staff summary's `**Always**` and v1.0's `**Version:**` must not parse."""
    for not_a_clause in ("Always", "Ask first", "Never", "Version:", "Policy ID:"):
        assert not_a_clause not in v1_5.clauses


def test_changelog_sections_contribute_no_clauses(v1_5):
    sections = {clause.section_title for clause in v1_5.clauses.values()}
    assert not any(title.startswith("Changes in version") for title in sections if title)
