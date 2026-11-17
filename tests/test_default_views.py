"""Each page's default view, and the trail that joins them.

The pass that added these made four long pages open on their main thing and
put the rest under tabs, and gave every page one card naming the next one.
These tests keep that shape, not the words on it.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from app.components.trail import TRAIL, next_page

ENTRYPOINT = str(Path(__file__).resolve().parent.parent / "app" / "main.py")
TIMEOUT = 40

PAGES = {
    "check": None,
    "how": "views/0_how.py",
    "matrix": "views/2_matrix.py",
    "agents": "views/3_agent_builder.py",
    "quiz": "views/4_scenarios.py",
    "policy": "views/6_policy.py",
    "limits": "views/7_limits.py",
}


def open_page(name: str) -> AppTest:
    at = AppTest.from_file(ENTRYPOINT, default_timeout=TIMEOUT)
    at.run()
    if PAGES[name]:
        at.switch_page(PAGES[name])
        at.run()
    return at


def next_cards(at: AppTest) -> list[str]:
    return [h.value for h in at.html if 'class="cu-next-page"' in h.value]


# --------------------------------------------------------------------------
# The trail
# --------------------------------------------------------------------------


def test_the_trail_lists_every_page_once_and_wraps():
    slugs = [slug for slug, _t, _b in TRAIL]
    assert sorted(slugs) == sorted(PAGES), "every page is on the trail, once"
    assert next_page("limits")[0] == "check"
    assert next_page("check")[0] == "agents"


@pytest.mark.parametrize("name", list(PAGES))
def test_every_page_ends_with_one_card_pointing_at_the_next(name: str):
    at = open_page(name)
    assert not at.exception
    [card] = next_cards(at)
    slug, title, blurb = next_page(name)
    href = re.search(r'href="([^"]+)"', card).group(1)
    assert href == ("./" if slug == "check" else slug)
    assert title in card and blurb in card


# --------------------------------------------------------------------------
# Default views
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "first", "count"),
    [
        ("how", "A rule, as written", 5),
        ("agents", "Required controls", 3),
        ("policy", "On one page", 2),
    ],
)
def test_the_long_pages_open_on_their_main_thing_and_tab_the_rest(name, first, count):
    at = open_page(name)
    labels = [tab.label for tab in at.tabs]
    assert len(labels) == count
    assert labels[0] == first


def test_the_check_page_answers_before_its_three_tabs():
    at = open_page("check")
    assert [tab.label for tab in at.tabs] == ["Why this answer", "What if", "Share"]
    assert len([e for e in at.expander if "five data classes" in e.label]) == 1


def test_the_stakes_sit_inside_the_card_not_under_it():
    at = open_page("check")
    at.button(key="cu_example_2").click().run()
    # Scenario 2 is loaded behind a guess; answer it to reach the card.
    picks = [b for b in at.button if b.key and b.key.startswith("cu_guess_")]
    at = picks[0].click().run()
    cards = [h.value for h in at.html if 'class="cu-card cu-card--' in h.value]
    assert any("Why it matters" in card and "Do this next" in card for card in cards)


def test_surprise_me_loads_a_scenario_the_cards_do_not_show():
    at = open_page("check")
    numbered = re.compile(r"cu_example_(\d+)$")
    shown = {int(m.group(1)) for b in at.button if (m := numbered.match(b.key or ""))}
    at = at.button(key="cu_example_random").click().run()
    assert not at.exception
    picked = at.session_state["_cu_guess_for"]
    assert picked not in shown
