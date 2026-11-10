"""The backing layer may only use the BUILD_SPEC 7 seed crosswalk.

BUILD_SPEC 0.4: never invent law. Anything that looks missing belongs in
OPEN_QUESTIONS.md, not in the app.
"""

from __future__ import annotations

import warnings
from datetime import date

import pytest

from engine.models import BasisType
from engine.rules import basis_for, load_basis, policy_basis

#: Exactly the sources named in the BUILD_SPEC 7 table, plus the wording of the
#: `6.1` entry in the section's own YAML example, which differs from its table
#: row ("EU AI Act Art. 5"). Adding anything here needs a BUILD_SPEC change.
ALLOWED_SOURCES = {
    "EU AI Act, Article 5",
    "EU AI Act Art. 5, as amended by the 2026 AI omnibus "
    "(non-consensual intimate imagery and CSAM)",
    "ISO/IEC 27001 access control",
    "GDPR Art. 22",
    "GDPR Arts. 5-6; India DPDP Act 2023 and Rules 2025",
    "EU AI Act Annex III (high-risk); Colorado SB 26-189",
    "EU AI Act Art. 50",
    "OWASP Top 10 for Agentic Applications; Singapore Model AI Governance Framework for Agentic AI",
    "EU AI Act Art. 4 (AI literacy)",
    "US Revised Guidance on Model Risk Management (Apr 2026); MAS Guidelines "
    "on AI Risk Management (Oct 2026)",
    "ISO/IEC 42001 (AI policy); NIST AI RMF GOVERN",
    "Internal governance choice",
}

CHECKED_ON = date(2026, 10, 22)


def test_every_source_is_in_the_seed_crosswalk():
    unexpected = sorted({e.source for e in load_basis()} - ALLOWED_SOURCES)
    assert not unexpected, f"sources outside the BUILD_SPEC 7 crosswalk: {unexpected}"


def test_every_entry_has_a_checked_date():
    assert all(e.checked for e in load_basis())


def test_every_entry_is_checked_on_the_date_build_spec_sets():
    """BUILD_SPEC 7: mark every entry checked 2026-10-22."""
    wrong = [(e.clause, e.checked) for e in load_basis() if e.checked != CHECKED_ON]
    assert not wrong, f"entries not checked {CHECKED_ON}: {wrong}"


def test_the_crosswalk_is_covered():
    """Each row of the BUILD_SPEC 7 table is present."""
    clauses = {e.clause for e in load_basis()}
    for expected in (
        "6.1",
        "6.2",
        "6.3",
        "6.6",
        "7.3",
        "8.1",
        "HR.1",
        "10.1",
        "11.*",
        "C.*",
        "16.1",
        "FS.1",
        "*",
        "15.1",
        "17.2",
        "B.4",
        "C.2",
    ):
        assert expected in clauses, f"crosswalk row {expected!r} is missing"


def test_6_3_carries_both_types_the_crosswalk_gives_it():
    """The table row reads "standard + our_choice", so it is two entries."""
    types = {e.type for e in load_basis() if e.clause == "6.3"}
    assert types == {BasisType.STANDARD, BasisType.OUR_CHOICE}


def test_law_entries_that_need_a_recheck_warn_rather_than_fail():
    """BUILD_SPEC 1: a test that warns rather than fails."""
    today = date.today()
    stale = [e for e in load_basis() if e.type is BasisType.LAW and e.is_stale(today)]
    if stale:
        warnings.warn(
            "Law citations need re-checking (over 90 days since "
            f"{CHECKED_ON}): {sorted({e.clause for e in stale})}",
            stacklevel=1,
        )
    assert True


# --------------------------------------------------------------------------
# Lookup behaviour
# --------------------------------------------------------------------------


def test_prefix_patterns_match_part_c_and_section_11():
    assert any(e.clause == "11.*" for e in basis_for(["11.3"]))
    assert any(e.clause == "C.*" for e in basis_for(["C.4.1"]))


def test_prefix_pattern_does_not_over_match():
    """`11.*` must not back clause 1.1 or 10.1 by accident."""
    sources = {e.clause for e in basis_for(["1.1"])}
    assert "11.*" not in sources


def test_shared_source_is_listed_once_per_verdict():
    """11.3 and C.2 share the OWASP/Singapore entry; the card shows it once."""
    entries = basis_for(["11.3", "C.2"])
    owasp = [e for e in entries if e.source.startswith("OWASP")]
    assert len(owasp) == 1


def test_whole_policy_entry_is_kept_off_the_card():
    assert not basis_for(["6.1", "11.3", "C.2"]) or all(
        e.clause != "*" for e in basis_for(["6.1", "11.3", "C.2"])
    )
    assert [e.clause for e in policy_basis()] == ["*"]


def test_clause_with_no_backing_returns_nothing():
    assert basis_for(["8.10"]) == []


@pytest.mark.parametrize(
    "clause_id,expected_type",
    [("6.1", BasisType.LAW), ("B.4", BasisType.OUR_CHOICE)],
)
def test_badge_type_is_what_the_crosswalk_says(clause_id, expected_type):
    assert any(e.type is expected_type for e in basis_for([clause_id]))
