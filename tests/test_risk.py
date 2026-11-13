"""The green-to-red scale on the data and tool options.

The scale claims to be computed from the 7.1 grid rather than chosen. These
tests hold it to that: the order has to be the order the grid produces, every
option has to land on a real verdict token, and the accent must not reappear
as a selection colour.
"""

from __future__ import annotations

import pytest

from app.components.risk import SCALE, data_class_scale, option_styles, tool_scale
from engine.models import Activity, DataClass, Host, Inputs, Status, Tool
from engine.rules import evaluate

VERSION = "v1_6"


def _allowed_count_for_class(data_class: DataClass) -> int:
    total = 0
    for tool in Tool:
        fields = {"data_class": data_class, "tool": tool, "activity": Activity.DRAFTING}
        if tool is Tool.SELF_HOSTED:
            fields["host"] = Host.ORG_CLOUD
        if evaluate(Inputs(**fields), VERSION).status is Status.ALLOWED:
            total += 1
    return total


def test_every_option_lands_on_a_real_verdict_token():
    for slug in list(data_class_scale(VERSION).values()) + list(tool_scale(VERSION).values()):
        assert slug in SCALE


def test_every_class_and_tier_is_on_the_scale():
    assert set(data_class_scale(VERSION)) == set(DataClass)
    assert set(tool_scale(VERSION)) == set(Tool)


def test_the_order_is_the_one_the_grid_produces():
    """Not a chosen ranking: a class that clears more tiers is never painted
    as more restricted than one that clears fewer."""
    scale = data_class_scale(VERSION)
    for first in DataClass:
        for second in DataClass:
            if _allowed_count_for_class(first) > _allowed_count_for_class(second):
                assert SCALE.index(scale[first]) <= SCALE.index(scale[second]), (
                    f"{first.value} clears more tiers than {second.value} "
                    f"but is painted more restricted"
                )


@pytest.mark.parametrize(
    "lighter,heavier",
    [
        (DataClass.PUBLIC, DataClass.CONFIDENTIAL),
        (DataClass.CONFIDENTIAL, DataClass.RESTRICTED),
        (DataClass.RESTRICTED, DataClass.SECRETS),
    ],
)
def test_the_scale_runs_from_public_to_secrets(lighter, heavier):
    scale = data_class_scale(VERSION)
    assert SCALE.index(scale[lighter]) < SCALE.index(scale[heavier])


def test_secrets_is_the_far_end_and_tier_c_is_the_far_end_of_the_tools():
    assert data_class_scale(VERSION)[DataClass.SECRETS] == SCALE[-1]
    assert tool_scale(VERSION)[Tool.TIER_C] == SCALE[-1]
    assert tool_scale(VERSION)[Tool.TIER_A] == SCALE[0]


def test_an_approved_tier_is_never_painted_worse_than_an_unassessed_one():
    scale = tool_scale(VERSION)
    assert SCALE.index(scale[Tool.TIER_A]) < SCALE.index(scale[Tool.TIER_B])
    assert SCALE.index(scale[Tool.TIER_B]) < SCALE.index(scale[Tool.TIER_C])


def test_selection_is_never_the_accent():
    """Phase 5 took teal off the options: selection is the option's own place
    on the scale, filled in, so a chosen chip cannot read as an answer."""
    css = option_styles(VERSION, DataClass.CONFIDENTIAL, Tool.TIER_C)
    assert "--accent" not in css
    assert "#0F5E66" not in css


def test_the_selected_option_is_filled_in_its_own_colour():
    css = option_styles(VERSION, DataClass.SECRETS, Tool.TIER_A)
    secrets = next(
        rule
        for rule in css.split("\n")
        if "cu_opt_data_class_Secrets" in rule and ":hover" not in rule
    )
    assert "var(--prohibited-tint)" in secrets
    assert "var(--prohibited)" in secrets


def test_an_unselected_option_keeps_its_colour_to_the_edge():
    """The strip carries the scale; filling five options would drown the card."""
    css = option_styles(VERSION, DataClass.PUBLIC, Tool.TIER_A)
    secrets = next(
        rule
        for rule in css.split("\n")
        if "cu_opt_data_class_Secrets" in rule and ":hover" not in rule
    )
    assert "border-left: 6px solid var(--prohibited)" in secrets
    assert "background: var(--surface)" in secrets
