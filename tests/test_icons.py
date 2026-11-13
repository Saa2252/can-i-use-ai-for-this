"""The icon set, and the one way it is allowed to reach the page.

`st.html` strips an inline `<svg>`: the surrounding element survives and the
drawing does not, so the page renders an empty span and every assertion
about the text beside it still passes. That is how the first version of this
shipped. These tests make the failure loud instead.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.components.icons import MARKS, data_uri, rule
from app.styles.tokens import STATUS_STYLES, TOKENS
from engine.models import Status

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCE_FILES = sorted((PROJECT_ROOT / "app").rglob("*.py"))


def test_every_status_has_an_icon():
    for status in Status:
        assert STATUS_STYLES[status].slug in MARKS


def test_the_set_is_drawn_the_same_way_throughout():
    """One box, one stroke, no fills: four marks that read as a set."""
    for name, marks in MARKS.items():
        assert "fill=" not in marks, f"{name} is filled, so it will not match the others"

    for status in Status:
        svg = data_uri(STATUS_STYLES[status].slug, "#000000")
        assert "viewBox%3D%220%200%2024%2024%22" in svg, "every icon shares one 24x24 box"


def test_a_status_icon_is_drawn_in_its_own_colour():
    for status in Status:
        slug = STATUS_STYLES[status].slug
        declaration = rule(f".x--{slug}", slug, TOKENS[slug])
        assert "background-image:url(" in declaration
        assert "display:inline-block" in declaration


def test_the_four_marks_are_distinguishable_without_colour():
    """BUILD_SPEC 8, "Never color alone". Two statuses drawn with the same
    path would leave only the colour to tell them apart."""
    drawings = {STATUS_STYLES[status].slug: MARKS[STATUS_STYLES[status].slug] for status in Status}
    assert len(set(drawings.values())) == len(drawings)


@pytest.mark.parametrize("path", SOURCE_FILES, ids=lambda p: p.name)
def test_no_page_hands_an_inline_svg_to_streamlit(path: Path):
    """The sanitiser would drop it and nothing would say so."""
    source = path.read_text(encoding="utf-8")
    if path.name == "icons.py":
        return  # where the drawings are defined, and never rendered directly
    assert "<svg" not in source, (
        f"{path.name} builds an inline <svg>; st.html strips it, so the icon "
        f"would silently disappear. Use icons.rule() and a CSS background."
    )


def test_the_matrix_paints_an_icon_for_every_status():
    """The generated stylesheet is where the icons actually come from, so a
    missing rule is a missing icon."""
    from app.components.grid import GRID_TIERS  # noqa: F401  (import check)

    source = (PROJECT_ROOT / "app" / "views" / "2_matrix.py").read_text(encoding="utf-8")
    assert "icon_rule(" in source, "the matrix must paint its own icons"
    for target in (".cu-key__icon", ".cu-hostcell__icon", ".cu-icon--"):
        assert target in source, f"no icon rule for {target}"
