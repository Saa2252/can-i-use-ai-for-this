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
    "EU AI Act Art. 5, as amended by the Digital Omnibus on AI "
    "(non-consensual intimate imagery and CSAM)",
    "ISO/IEC 27001 access control",
    "GDPR Art. 22",
    "GDPR Arts. 5-6; India DPDP Act 2023 and Rules 2025",
    "EU AI Act Annex III (high-risk); Colorado SB 26-189",
    "EU AI Act Art. 50",
    "OWASP Top 10 for Agentic Applications; Singapore Model AI Governance Framework for Agentic AI",
    "EU AI Act Art. 4 (AI literacy), as amended by the Digital Omnibus",
    "US Revised Guidance on Model Risk Management (Apr 2026); MAS Guidelines "
    "on AI Risk Management (Oct 2026)",
    "ISO/IEC 42001 (AI policy); NIST AI RMF GOVERN",
    "Internal governance choice",
}

#: The dates the crosswalk has been verified on. 2026-10-22 is the build-time
#: seed BUILD_SPEC 7 set; 2026-11-11 is the re-verification against the adopted
#: Digital Omnibus, Colorado SB 26-189 and the amended Article 4. A date not in
#: this set means someone edited a `checked:` line without doing the reading.
VERIFIED_ON = {date(2026, 10, 22), date(2026, 11, 11)}


def test_every_source_is_in_the_seed_crosswalk():
    unexpected = sorted({e.source for e in load_basis()} - ALLOWED_SOURCES)
    assert not unexpected, f"sources outside the BUILD_SPEC 7 crosswalk: {unexpected}"


def test_every_entry_has_a_checked_date():
    assert all(e.checked for e in load_basis())


def test_every_entry_carries_a_date_someone_verified_on():
    """Supersedes the build-time rule that every entry read 2026-10-22.

    That rule held while the crosswalk had never been re-checked. Pinning the
    exact set is stricter than pinning one date: a `checked:` line cannot be
    nudged forward to silence the stale-source tag without adding its date
    here, which is a deliberate act.
    """
    stray = sorted((e.clause, str(e.checked)) for e in load_basis() if e.checked not in VERIFIED_ON)
    assert not stray, f"dates nobody verified on: {stray}"


def test_no_entry_claims_to_have_been_checked_in_the_future():
    today = date.today()
    ahead = sorted((e.clause, str(e.checked)) for e in load_basis() if e.checked > today)
    assert not ahead, f"checked in the future: {ahead}"


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
        # Entries no longer share one date, so name each one's own.
        overdue = sorted({f"{e.clause} (checked {e.checked})" for e in stale})
        warnings.warn(
            f"Law citations over 90 days old, re-check before relying on them: {overdue}",
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
