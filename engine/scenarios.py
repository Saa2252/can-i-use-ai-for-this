"""The golden scenarios of BUILD_SPEC 6, loaded from `scenarios.yaml`.

One source for three consumers: the tests, the quiz, and the Review page's
"verdict changed" diff.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from engine.models import ApprovalKind, Inputs, Status

SCENARIOS_FILE = Path(__file__).resolve().parent / "scenarios.yaml"

#: BUILD_SPEC 6: the quiz uses a shuffled set of 10 and must always include these.
QUIZ_LOCKED = (4, 8, 9, 14)


class Scenario(BaseModel):
    """One golden scenario and the verdict BUILD_SPEC 6 expects from it."""

    n: int
    title: str
    inputs: Inputs
    expect: Status
    approval_kind: ApprovalKind | None = None
    must_cite: list[str] = Field(default_factory=list)
    quiz_locked: bool = False


@lru_cache(maxsize=1)
def load_scenarios() -> tuple[Scenario, ...]:
    """Load, validate and cache the scenarios."""
    raw = yaml.safe_load(SCENARIOS_FILE.read_text(encoding="utf-8")) or []
    scenarios = tuple(Scenario(**entry) for entry in raw)

    numbers = [scenario.n for scenario in scenarios]
    if len(set(numbers)) != len(numbers):
        raise ValueError("scenarios.yaml: duplicate scenario numbers")

    locked = {scenario.n for scenario in scenarios if scenario.quiz_locked}
    if locked != set(QUIZ_LOCKED):
        raise ValueError(
            f"scenarios.yaml: quiz_locked is {sorted(locked)}, expected {list(QUIZ_LOCKED)}"
        )

    return scenarios


def scenario(n: int) -> Scenario:
    for candidate in load_scenarios():
        if candidate.n == n:
            return candidate
    raise KeyError(f"no scenario {n}")
