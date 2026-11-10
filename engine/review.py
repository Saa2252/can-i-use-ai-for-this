"""Comparing one policy version's verdicts against another's.

The Review page's "scenarios whose verdict changed" list is computed here
from the two rulesets, never written by hand, so it cannot go stale when a
rule changes.
"""

from __future__ import annotations

from pydantic import BaseModel

from engine.models import Verdict
from engine.rules import evaluate
from engine.scenarios import Scenario, load_scenarios

BASELINE = "v1_0"
CURRENT = "v1_5"


class VerdictChange(BaseModel):
    """One scenario run through both rulesets."""

    scenario: Scenario
    before: Verdict
    after: Verdict

    @property
    def status_changed(self) -> bool:
        return self.before.status is not self.after.status

    @property
    def approval_changed(self) -> bool:
        return self.before.approval_kind is not self.after.approval_kind

    @property
    def changed(self) -> bool:
        """A change the visitor would notice in the answer itself."""
        return self.status_changed or self.approval_changed

    @property
    def added_clauses(self) -> list[str]:
        return [c for c in self.after.clauses if c not in self.before.clauses]

    @property
    def dropped_clauses(self) -> list[str]:
        return [c for c in self.before.clauses if c not in self.after.clauses]

    @property
    def citations_changed(self) -> bool:
        return bool(self.added_clauses or self.dropped_clauses)


def compare(scenario: Scenario, before: str = BASELINE, after: str = CURRENT) -> VerdictChange:
    return VerdictChange(
        scenario=scenario,
        before=evaluate(scenario.inputs, before),
        after=evaluate(scenario.inputs, after),
    )


def compare_all(before: str = BASELINE, after: str = CURRENT) -> list[VerdictChange]:
    """Every scenario, run through both rulesets."""
    return [compare(scenario, before, after) for scenario in load_scenarios()]


def changed_verdicts(before: str = BASELINE, after: str = CURRENT) -> list[VerdictChange]:
    """Only the scenarios whose answer changed between the two versions."""
    return [change for change in compare_all(before, after) if change.changed]
