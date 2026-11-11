"""Every clause id used anywhere must exist in the parsed policy.

BUILD_SPEC 1 success criteria and BUILD_SPEC 11: a verdict that cites a clause
the policy does not contain is worse than no app.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from engine.policy_parser import load_policy
from engine.rules import ENGINE_DIR, RULES_FILES, WHOLE_POLICY, load_basis
from engine.scenarios import load_scenarios

PROJECT_ROOT = Path(__file__).resolve().parent.parent

#: The version the app serves. The crosswalk and the scenarios back this one.
CURRENT = "v1_6"


def _ruleset_clause_ids(version: str) -> set[str]:
    path = ENGINE_DIR / RULES_FILES[version]
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    return {clause_id for entry in raw for clause_id in entry.get("then", {}).get("clauses", [])}


def _available_rulesets() -> list[str]:
    """v1_0 arrives in Phase 4, so only test the rulesets that exist."""
    return [v for v in RULES_FILES if (ENGINE_DIR / RULES_FILES[v]).exists()]


@pytest.mark.parametrize("version", _available_rulesets())
def test_rule_clauses_exist_in_their_own_policy_version(version):
    """A v1.0 rule is checked against v1.0, not v1.5 (OPEN_QUESTIONS Q1)."""
    policy = load_policy(version)
    missing = sorted(_ruleset_clause_ids(version) - set(policy.clauses))
    assert not missing, f"{RULES_FILES[version]} cites clauses absent from {version}: {missing}"


def test_basis_clauses_exist_in_the_current_policy():
    policy = load_policy(CURRENT)
    missing = []
    for entry in load_basis():
        if entry.clause == WHOLE_POLICY or entry.clause.endswith(".*"):
            continue
        if entry.clause not in policy.clauses:
            missing.append(entry.clause)
    assert not missing, f"basis.yaml cites clauses absent from {CURRENT}: {sorted(set(missing))}"


def test_basis_patterns_match_at_least_one_clause():
    """A pattern that matches nothing is a silent dead entry."""
    policy = load_policy(CURRENT)
    for entry in load_basis():
        if not entry.clause.endswith(".*"):
            continue
        prefix = entry.clause[:-2]
        matched = [cid for cid in policy.clauses if cid.split(".")[0] == prefix]
        assert matched, f"basis.yaml pattern {entry.clause!r} matches no {CURRENT} clause"


def test_scenario_must_cite_clauses_exist_in_the_current_policy():
    policy = load_policy(CURRENT)
    missing = sorted(
        {
            clause_id
            for scenario in load_scenarios()
            for clause_id in scenario.must_cite
            if clause_id not in policy.clauses
        }
    )
    assert not missing, f"scenarios.yaml cites clauses absent from {CURRENT}: {missing}"


@pytest.mark.parametrize("version", _available_rulesets())
def test_no_rule_cites_a_container_section(version):
    """B.1 and C.4 are containers; their sub-clauses are what can be cited.

    Checked against the ruleset's OWN policy version. Checking every ruleset
    against v1.5 worked only while v1.5 was the newest, and conflated two
    different faults: citing a container, and citing a clause that a later
    version introduced. v1.6's HR.6 is a real clause and was failing as a
    container.
    """
    policy = load_policy(version)
    for clause_id in _ruleset_clause_ids(version):
        if clause_id in policy.clauses:
            continue
        pytest.fail(f"{version} cites {clause_id!r}, which is not a citable clause in {version}")


#: Clause ids written as string literals in app code, e.g. "11.3" or "C.6.1".
_CLAUSE_LITERAL = re.compile(
    r'"((?:\d{1,2}\.\d{1,2}|[BC]\.\d{1,2}(?:\.\d{1,2})?|[A-Z]{2,3}\.\d{1,2}))"'
)


def test_clause_ids_written_in_app_code_exist_in_the_current_policy():
    """BUILD_SPEC 11: every clause id in the YAML *and code* must exist.

    The Agent builder cites 11.9 and C.6.1 directly rather than through a
    rule, and the Limits page cites the clauses that closed each gap, so a
    page can cite a clause the policy does not have. Checked against the
    version the app serves, since that is the text those pages render.
    """
    policy = load_policy(CURRENT)
    offenders: dict[str, list[str]] = {}
    for path in sorted((PROJECT_ROOT / "app").rglob("*.py")):
        found = set(_CLAUSE_LITERAL.findall(path.read_text(encoding="utf-8")))
        missing = sorted(cid for cid in found if cid not in policy.clauses)
        if missing:
            offenders[str(path.relative_to(PROJECT_ROOT))] = missing
    assert not offenders, f"app code cites clauses absent from {CURRENT}: {offenders}"


def test_the_app_code_scan_actually_finds_clause_ids():
    """Guard: a regex that matched nothing would make the test above vacuous."""
    builder = (PROJECT_ROOT / "app" / "pages" / "3_agent_builder.py").read_text(encoding="utf-8")
    assert {"11.9", "C.6.1"} <= set(_CLAUSE_LITERAL.findall(builder))


def test_open_questions_file_is_not_empty():
    """BUILD_SPEC 11: OPEN_QUESTIONS.md lists every ambiguity found."""
    text = (PROJECT_ROOT / "OPEN_QUESTIONS.md").read_text(encoding="utf-8")
    assert "## Q1" in text
