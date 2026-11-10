"""`scenarios.yaml` must match the BUILD_SPEC 6 table row for row.

This is the guard against the failure mode BUILD_SPEC 6 warns about: a scenario
quietly edited until it passes. The expectations are read back out of
BUILD_SPEC.md itself, so drifting from the spec fails here rather than silently
changing what the app claims.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from engine.models import ApprovalKind, DataClass, Host, Status, Tool
from engine.scenarios import QUIZ_LOCKED, load_scenarios

BUILD_SPEC = Path(__file__).resolve().parent.parent / "BUILD_SPEC.md"

#: How the BUILD_SPEC 6 "Tool" column maps onto `tool` + `host`.
TOOL_COLUMN = {
    "A": (Tool.TIER_A, None),
    "B": (Tool.TIER_B, None),
    "C": (Tool.TIER_C, None),
    "Self-hosted, personal device": (Tool.SELF_HOSTED, Host.PERSONAL_DEVICE),
}

#: How the parenthetical in the "Expected" column maps onto `approval_kind`.
APPROVAL_SUFFIX = {
    "one-time": ApprovalKind.ONE_TIME_USE_CASE,
    "per message": ApprovalKind.PER_ACTION,
}


class SpecRow:
    __slots__ = ("approval_kind", "data_class", "expect", "host", "must_cite", "n", "title", "tool")


def _parse_build_spec_table() -> list[SpecRow]:
    """Pull the 21 golden scenarios out of the BUILD_SPEC 6 markdown table."""
    text = BUILD_SPEC.read_text(encoding="utf-8")
    section = text.split("## 6. Golden scenarios")[1].split("## 7.")[0]

    rows: list[SpecRow] = []
    for line in section.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != 6 or not cells[0].isdigit():
            continue

        number, title, data, tool, expected, cited = cells
        row = SpecRow()
        row.n = int(number)
        row.title = title
        row.data_class = DataClass(data)
        row.tool, row.host = TOOL_COLUMN[tool]

        match = re.match(r"^([A-Z_]+)(?:\s*\((.+)\))?$", expected)
        assert match, f"cannot read the Expected cell for scenario {number}: {expected!r}"
        row.expect = Status(match.group(1))
        row.approval_kind = APPROVAL_SUFFIX[match.group(2)] if match.group(2) else None
        row.must_cite = [c.strip() for c in cited.split(",")]
        rows.append(row)

    return rows


SPEC_ROWS = _parse_build_spec_table()
BY_NUMBER = {scenario.n: scenario for scenario in load_scenarios()}
IDS = [f"{row.n:02d}" for row in SPEC_ROWS]


def test_build_spec_table_was_read():
    """A parser that silently found nothing would make every test below vacuous."""
    assert len(SPEC_ROWS) == 21
    assert [row.n for row in SPEC_ROWS] == list(range(1, 22))


def test_scenarios_yaml_has_exactly_the_spec_rows():
    assert sorted(BY_NUMBER) == [row.n for row in SPEC_ROWS]


@pytest.mark.parametrize("row", SPEC_ROWS, ids=IDS)
def test_scenario_matches_the_spec_row(row):
    scenario = BY_NUMBER[row.n]
    assert scenario.title == row.title
    assert scenario.inputs.data_class is row.data_class
    assert scenario.inputs.tool is row.tool
    assert scenario.inputs.host is row.host
    assert scenario.expect is row.expect
    assert set(scenario.must_cite) == set(row.must_cite)


@pytest.mark.parametrize("row", SPEC_ROWS, ids=IDS)
def test_approval_kind_matches_the_spec_row(row):
    """Only rows the spec annotates are pinned; the rest may stay unspecified."""
    scenario = BY_NUMBER[row.n]
    if row.approval_kind is not None:
        assert scenario.approval_kind is row.approval_kind


def test_quiz_locked_scenarios_are_the_four_the_spec_names():
    """BUILD_SPEC 6: the quiz must always include 4, 8, 9 and 14."""
    locked = sorted(s.n for s in load_scenarios() if s.quiz_locked)
    assert locked == sorted(QUIZ_LOCKED) == [4, 8, 9, 14]
