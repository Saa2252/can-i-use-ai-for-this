"""The How-it-works page, and the helpers that compute what it says.

The page's whole claim is that nothing on it is typed in. So the tests
compare what it shows against the files, not against numbers pinned here.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml
from streamlit.testing.v1 import AppTest

from app.components.method import (
    beyond_the_law,
    cited_clause_ids,
    count_test_functions,
    coverage,
    crosswalk,
    describe_pattern,
    figures,
    rule_source,
)
from engine.models import BasisType
from engine.policy_parser import load_policy
from engine.rules import load_basis, load_rules
from engine.scenarios import load_scenarios

ENTRYPOINT = str(Path(__file__).resolve().parent.parent / "app" / "main.py")
PAGE = "views/0_how.py"
TIMEOUT = 40
VERSION = "v1_6"


def open_page() -> AppTest:
    at = AppTest.from_file(ENTRYPOINT, default_timeout=TIMEOUT)
    at.run()
    at.switch_page(PAGE)
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
# Figures
# --------------------------------------------------------------------------


def test_figures_are_read_from_the_files():
    f = figures(VERSION)
    assert f.clauses == len(load_policy(VERSION).clauses)
    assert f.rules == len(load_rules(VERSION))
    assert f.scenarios == len(load_scenarios())
    assert f.basis_entries == len(load_basis())
    assert f.versions == 3
    assert 0 < f.clauses_cited <= f.clauses


def test_cited_clauses_all_exist_in_their_own_policy():
    for version in ("v1_0", "v1_5", "v1_6"):
        policy = load_policy(version)
        assert cited_clause_ids(version) <= set(policy.clauses)


def test_test_function_count_matches_a_grep():
    tests = Path(__file__).resolve().parent
    expected = sum(
        len(re.findall(r"^def test_\w+", p.read_text(encoding="utf-8"), re.MULTILINE))
        for p in tests.glob("*.py")
    )
    assert count_test_functions() == expected > 100


def test_test_function_count_is_zero_without_a_tests_folder(tmp_path):
    assert count_test_functions(tmp_path) == 0


# --------------------------------------------------------------------------
# The sample rule
# --------------------------------------------------------------------------


def test_rule_source_is_the_file_text_and_parses_to_the_same_rule():
    text = rule_source("agent_payment_in_cap_to_allowlisted_payee", VERSION)
    assert text.startswith("- id: agent_payment_in_cap_to_allowlisted_payee\n")
    assert text.count("- id: ") == 1, "the slice ran into the next rule"
    [parsed] = yaml.safe_load(text)
    rule = next(r for r in load_rules(VERSION) if r.id == parsed["id"])
    assert parsed["then"]["clauses"] == rule.clauses
    assert parsed["then"]["status"] == rule.status.value


def test_rule_source_rejects_an_unknown_rule():
    import pytest

    with pytest.raises(KeyError):
        rule_source("no_such_rule", VERSION)


# --------------------------------------------------------------------------
# The crosswalk
# --------------------------------------------------------------------------


def test_crosswalk_holds_every_per_clause_entry_once():
    rows = crosswalk(VERSION)
    expected = [e for e in load_basis() if e.clause != "*"]
    assert len(rows) == len(expected)
    assert {id(r.entry) for r in rows} == {id(e) for e in expected}


def test_crosswalk_is_in_policy_order_with_part_a_first():
    clauses = [r.clause for r in crosswalk(VERSION)]
    heads = [c.split(".")[0] for c in clauses]
    numeric = [h for h in heads if h.isdigit()]
    assert numeric == sorted(numeric, key=int)
    first_letter = next((i for i, h in enumerate(heads) if not h.isdigit()), len(heads))
    assert all(h.isdigit() for h in heads[:first_letter])


def test_describe_pattern_uses_the_policy_section_names():
    assert describe_pattern("6.1", VERSION) == "Prohibited uses"
    assert describe_pattern("11.*", VERSION).startswith("Section 11")
    assert "agents" in describe_pattern("11.*", VERSION).lower()
    assert describe_pattern("*", VERSION) == "The policy as a whole"


def test_beyond_the_law_is_exactly_the_law_plus_our_choice_pairs():
    pairs = set()
    for clause in {e.clause for e in load_basis() if e.clause != "*"}:
        types = {e.type for e in load_basis() if e.clause == clause}
        if {BasisType.LAW, BasisType.OUR_CHOICE} <= types:
            pairs.add(clause)
    assert set(beyond_the_law()) == pairs
    assert "16.1" in pairs, "the README's worked example should still hold"


# --------------------------------------------------------------------------
# Coverage
# --------------------------------------------------------------------------


def test_coverage_accounts_for_every_clause_exactly_once():
    rows = coverage(VERSION)
    assert sum(r.clauses for r in rows) == len(load_policy(VERSION).clauses)
    assert sum(r.cited for r in rows) == len(cited_clause_ids(VERSION))
    assert all(0 <= r.cited <= r.clauses for r in rows)
    assert all(0.0 <= r.share <= 1.0 for r in rows)


def test_coverage_names_the_sections_the_tool_decides_on():
    by_section = {r.section: r for r in coverage(VERSION)}
    assert by_section["6"].title == "Prohibited uses"
    assert by_section["6"].cited > 0
    assert by_section["7"].cited > 0


# --------------------------------------------------------------------------
# The page
# --------------------------------------------------------------------------


def test_page_runs_without_exception():
    assert not open_page().exception


def test_page_shows_the_live_numbers_and_the_crosswalk():
    at = open_page()
    page = body(at)
    f = figures(VERSION)
    assert f'<span class="cu-figure__n">{f.rules}</span>' in page
    assert f'<span class="cu-figure__n">{f.clauses}</span>' in page
    for entry in load_basis():
        if entry.clause != "*":
            assert entry.source.split("\n")[0][:40] in page.replace("&#x27;", "'").replace(
                "&amp;", "&"
            )


def test_page_shows_the_sample_rule_verbatim():
    at = open_page()
    # st.code drops the trailing newline the file has; the words are what matter.
    source = rule_source("agent_payment_in_cap_to_allowlisted_payee", VERSION).rstrip()
    assert source in [c.value.rstrip() for c in at.code]


def test_page_states_the_severity_order_most_severe_first():
    page = body(open_page())
    order = [
        page.index(word) for word in ("Prohibited", "Not permitted", "Needs approval", "Allowed")
    ]
    assert order == sorted(order)
