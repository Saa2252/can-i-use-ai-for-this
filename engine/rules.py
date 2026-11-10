"""The rules engine: `evaluate(inputs, version) -> Verdict`.

Pure Python, no LLM anywhere in the decision path (BUILD_SPEC 1). Rules are
data in `rules_<version>.yaml`; this module only loads them, tests every one
against the inputs, and combines what fired.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

from engine.conditions import matches, validate
from engine.models import (
    ApprovalKind,
    Basis,
    Clause,
    Inputs,
    Rule,
    Status,
    Verdict,
    most_severe,
    resolve_effective_tier,
    strictest_approval,
)
from engine.policy_parser import load_policy

ENGINE_DIR = Path(__file__).resolve().parent

RULES_FILES: dict[str, str] = {
    "v1_0": "rules_v1_0.yaml",
    "v1_5": "rules_v1_5.yaml",
}

#: `clause: "*"` in basis.yaml backs the policy as a whole rather than any one
#: clause, so it is kept off the verdict card and surfaced separately.
WHOLE_POLICY = "*"


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------


@lru_cache(maxsize=8)
def load_rules(version: str = "v1_5") -> tuple[Rule, ...]:
    """Load, validate and cache a ruleset.

    Every `when:` block is validated against the real input fields at load
    time, so a typo fails loudly instead of quietly never matching.
    """
    if version not in RULES_FILES:
        raise KeyError(f"unknown ruleset {version!r}; have {sorted(RULES_FILES)}")

    path = ENGINE_DIR / RULES_FILES[version]
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or []

    known_fields = set(Inputs.model_fields) | {"effective_tier"}
    rules: list[Rule] = []
    seen: set[str] = set()

    for entry in raw:
        rule_id = entry["id"]
        if rule_id in seen:
            raise ValueError(f"{path.name}: duplicate rule id {rule_id!r}")
        seen.add(rule_id)
        rule = Rule(id=rule_id, when=entry["when"], **entry["then"])
        validate(rule.when, known_fields, path=f"{rule_id}.when")
        rules.append(rule)

    return tuple(rules)


@lru_cache(maxsize=1)
def load_basis() -> tuple[Basis, ...]:
    """Load and cache the regulatory crosswalk."""
    path = ENGINE_DIR / "basis.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    return tuple(Basis(**entry) for entry in raw)


# --------------------------------------------------------------------------
# Backing lookup
# --------------------------------------------------------------------------


def _clause_matches(pattern: str, clause_id: str) -> bool:
    if pattern == WHOLE_POLICY:
        return False
    if pattern.endswith(".*"):
        return clause_id.split(".")[0] == pattern[:-2]
    return pattern == clause_id


def basis_for(clause_ids: list[str]) -> list[Basis]:
    """Backing entries for the cited clauses, deduplicated by type and source.

    Two Part C clauses share one OWASP/Singapore entry, so the card shows that
    badge once rather than per clause.
    """
    found: list[Basis] = []
    seen: set[tuple[str, str]] = set()
    for clause_id in clause_ids:
        for entry in load_basis():
            if not _clause_matches(entry.clause, clause_id):
                continue
            key = (entry.type.value, entry.source)
            if key in seen:
                continue
            seen.add(key)
            found.append(entry)
    return found


def policy_basis() -> list[Basis]:
    """Backing for the policy as a whole, for the footer rather than a card."""
    return [entry for entry in load_basis() if entry.clause == WHOLE_POLICY]


# --------------------------------------------------------------------------
# Jurisdiction lens
# --------------------------------------------------------------------------

#: BUILD_SPEC 7: the lens on the policy page. It highlights which laws apply
#: where; it never changes a verdict, because 1.2 already applies whichever
#: requirement is stricter.
JURISDICTION_LENSES: tuple[str, ...] = ("Global", "EU", "US", "India")


def _jurisdiction_tokens(jurisdiction: str | None) -> list[str]:
    """Split a crosswalk jurisdiction into parts: "EU; US-CO" -> EU, US-CO."""
    if not jurisdiction:
        return []
    parts = jurisdiction.replace("/", ";").split(";")
    return [part.strip() for part in parts if part.strip()]


def applies_in(entry: Basis, lens: str) -> bool:
    """Whether a backing entry is in view under `lens`.

    "Global" is the unfiltered view. Under a country lens, an entry matches
    its own jurisdiction and also anything marked Global, since a global
    standard applies there too. "US" matches "US-CO", a state of it.
    """
    if lens == "Global":
        return True
    tokens = _jurisdiction_tokens(entry.jurisdiction)
    if "Global" in tokens:
        return True
    return any(token == lens or token.startswith(f"{lens}-") for token in tokens)


def basis_in_jurisdiction(lens: str) -> list[Basis]:
    """Every backing entry in view under `lens`."""
    return [entry for entry in load_basis() if applies_in(entry, lens)]


def clauses_with_backing_in(lens: str) -> set[str]:
    """The clause ids (and patterns) that have backing under `lens`."""
    return {entry.clause for entry in basis_in_jurisdiction(lens)}


# --------------------------------------------------------------------------
# Clause resolution
# --------------------------------------------------------------------------


def resolve_clauses(clause_ids: list[str], version: str = "v1_5") -> list[Clause]:
    """Clause objects, with text straight from the policy file, in policy order."""
    policy = load_policy(version)
    clauses = [policy.clause(clause_id) for clause_id in clause_ids]
    return sorted(clauses, key=lambda clause: clause.sort_key)


# --------------------------------------------------------------------------
# Evaluation
# --------------------------------------------------------------------------


def evaluate(inputs: Inputs, version: str = "v1_5") -> Verdict:
    """Apply every rule and return the combined verdict.

    All rules are evaluated, every fired rule contributes its clauses, reasons
    and requirements, and the status is the most severe that fired:
    PROHIBITED > NOT_PERMITTED > NEEDS_APPROVAL > ALLOWED.
    """
    ctx = inputs.context(resolve_effective_tier(inputs, version))
    fired = [rule for rule in load_rules(version) if matches(rule.when, ctx)]

    status = most_severe([rule.status for rule in fired])

    # The rules that actually decided the verdict lead the card; the rest give
    # supporting context.
    decisive = [rule for rule in fired if rule.status is status]
    supporting = [rule for rule in fired if rule.status is not status]

    approval_kind = (
        strictest_approval([rule.approval_kind for rule in decisive])
        if status is Status.NEEDS_APPROVAL
        else ApprovalKind.NONE
    )

    reasons = _dedupe(rule.reason for rule in decisive + supporting)
    requirements = _dedupe(
        requirement for rule in decisive + supporting for requirement in rule.requirements
    )
    clause_ids = _dedupe(clause_id for rule in decisive + supporting for clause_id in rule.clauses)
    clause_ids = [clause.id for clause in resolve_clauses(clause_ids, version)]

    try_instead = next(
        (rule.try_instead for rule in decisive if rule.try_instead),
        None,
    )

    return Verdict(
        status=status,
        approval_kind=approval_kind,
        reasons=reasons,
        clauses=clause_ids,
        requirements=requirements,
        try_instead=try_instead,
        basis=basis_for(clause_ids),
        fired_rules=[rule.id for rule in fired],
    )


def _dedupe(values) -> list[str]:
    """Order-preserving deduplication."""
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out
