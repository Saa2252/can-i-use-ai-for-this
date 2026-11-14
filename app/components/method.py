"""What the How-it-works page says about the engine, computed from the engine.

Every number on that page is read from the policy, the rules and the
crosswalk at render time, so the page cannot claim 46 rules after a 47th is
added. Nothing here is typed in by hand except the words around the numbers.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from engine.models import Basis, BasisType, Clause
from engine.policy_parser import load_policy
from engine.rules import ENGINE_DIR, RULES_FILES, load_basis, load_rules
from engine.scenarios import load_scenarios

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

#: The whole-policy entry in the crosswalk, kept off per-clause tables.
WHOLE_POLICY = "*"


# --------------------------------------------------------------------------
# Numbers
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Figures:
    """The credibility numbers, each with where it comes from."""

    clauses: int
    rules: int
    clauses_cited: int
    scenarios: int
    versions: int
    basis_entries: int
    sources: int
    test_functions: int


def cited_clause_ids(version: str) -> set[str]:
    """Every clause id at least one rule in `version` cites."""
    return {clause_id for rule in load_rules(version) for clause_id in rule.clauses}


def count_test_functions(root: Path = PROJECT_ROOT) -> int:
    """How many `def test_...` the suite defines, read from the files.

    Parametrised tests expand to several cases each, so this undercounts
    what pytest runs. It is the number that can be read without running
    anything, which is the honest one to show.
    """
    tests = root / "tests"
    if not tests.is_dir():
        return 0
    pattern = re.compile(r"^def test_\w+", re.MULTILINE)
    return sum(
        len(pattern.findall(path.read_text(encoding="utf-8"))) for path in tests.glob("*.py")
    )


def figures(version: str = "v1_6") -> Figures:
    policy = load_policy(version)
    basis = load_basis()
    return Figures(
        clauses=len(policy.clauses),
        rules=len(load_rules(version)),
        clauses_cited=len(cited_clause_ids(version)),
        scenarios=len(load_scenarios()),
        versions=len(RULES_FILES),
        basis_entries=len(basis),
        sources=len({entry.source for entry in basis if entry.type != BasisType.OUR_CHOICE}),
        test_functions=count_test_functions(),
    )


# --------------------------------------------------------------------------
# A rule, verbatim
# --------------------------------------------------------------------------


def rule_source(rule_id: str, version: str = "v1_6") -> str:
    """The YAML block for one rule, exactly as the file has it.

    Sliced from the file rather than re-serialised, so the page shows the
    rule as its author wrote it, comments and key order included.
    """
    text = (ENGINE_DIR / RULES_FILES[version]).read_text(encoding="utf-8")
    start = text.find(f"- id: {rule_id}\n")
    if start < 0:
        raise KeyError(f"no rule {rule_id!r} in {RULES_FILES[version]}")
    rest = text[start + 1 :]
    match = re.search(r"\n(?=- id: |# |\Z)", rest)
    end = start + 1 + (match.start() if match else len(rest))
    return text[start:end].rstrip() + "\n"


# --------------------------------------------------------------------------
# The crosswalk
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class CrosswalkRow:
    clause: str
    where: str
    entry: Basis


def describe_pattern(pattern: str, version: str = "v1_6") -> str:
    """Where a crosswalk entry points, in the policy's own section names."""
    policy = load_policy(version)
    if pattern == WHOLE_POLICY:
        return "The policy as a whole"
    if pattern.endswith(".*"):
        prefix = pattern[:-2]
        for clause in policy.clauses.values():
            if clause.section == prefix and clause.section_title:
                return f"Section {prefix} · {clause.section_title}"
            if clause.part == prefix:
                return f"Part {prefix}, every clause"
        return f"Section {prefix}"
    clause = policy.clauses.get(pattern)
    if clause is None:
        return pattern
    return clause.section_title or pattern


def _pattern_sort_key(pattern: str) -> tuple[int, tuple[int | str, ...]]:
    probe = pattern[:-2] if pattern.endswith(".*") else pattern
    head = probe.split(".")[0]
    group = {"B": 1, "C": 2}.get(head, 0 if head.isdigit() else 3)
    parts: list[int | str] = [int(p) if p.isdigit() else p for p in probe.split(".")]
    return group, tuple(parts)


def crosswalk(version: str = "v1_6") -> list[CrosswalkRow]:
    """Every per-clause backing entry, in policy order."""
    rows = [
        CrosswalkRow(
            clause=entry.clause, where=describe_pattern(entry.clause, version), entry=entry
        )
        for entry in load_basis()
        if entry.clause != WHOLE_POLICY
    ]
    type_order = {BasisType.LAW: 0, BasisType.STANDARD: 1, BasisType.OUR_CHOICE: 2}
    return sorted(rows, key=lambda row: (_pattern_sort_key(row.clause), type_order[row.entry.type]))


def whole_policy_basis() -> list[Basis]:
    return [entry for entry in load_basis() if entry.clause == WHOLE_POLICY]


def beyond_the_law() -> list[str]:
    """Clauses the crosswalk marks as both a legal duty and our own choice.

    That pairing is the crosswalk saying the policy asks for more than the
    law does on the same point. 16.1 is the worked example: yearly training
    survived the omnibus only in weakened form, so the clause now outruns it.
    """
    by_clause: dict[str, set[BasisType]] = {}
    for entry in load_basis():
        if entry.clause != WHOLE_POLICY:
            by_clause.setdefault(entry.clause, set()).add(entry.type)
    return sorted(
        (
            clause
            for clause, types in by_clause.items()
            if {BasisType.LAW, BasisType.OUR_CHOICE} <= types
        ),
        key=_pattern_sort_key,
    )


def basis_counts() -> Counter[BasisType]:
    return Counter(entry.type for entry in load_basis())


# --------------------------------------------------------------------------
# Coverage
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class SectionCoverage:
    section: str
    title: str
    part: str
    clauses: int
    cited: int

    @property
    def share(self) -> float:
        return self.cited / self.clauses if self.clauses else 0.0


def coverage(version: str = "v1_6") -> list[SectionCoverage]:
    """Per section: how many clauses there are, and how many a rule cites.

    A clause no rule cites is not a gap in the rules by itself. Sections on
    roles, procurement and metrics describe process, not a decision taken at
    a desk, and the tool only answers the second kind of question.
    """
    policy = load_policy(version)
    cited = cited_clause_ids(version)
    buckets: dict[str, list[Clause]] = {}
    for clause in policy.clauses.values():
        key = clause.section or clause.id.split(".")[0]
        buckets.setdefault(key, []).append(clause)

    rows = []
    for section, clauses in buckets.items():
        first = min(clauses, key=lambda clause: clause.sort_key)
        rows.append(
            SectionCoverage(
                section=section,
                title=first.section_title or section,
                part=first.part or "",
                clauses=len(clauses),
                cited=sum(clause.id in cited for clause in clauses),
            )
        )
    # By section id, not by first clause: Part D's clause ids are sector codes
    # (FS, HR, ED...), which would put Education before Financial services.
    return sorted(rows, key=lambda row: _pattern_sort_key(row.section))
