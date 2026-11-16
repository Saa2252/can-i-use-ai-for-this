"""The trail: one card at the foot of every page, pointing at the next.

Eight pages is a lot to be dropped into. A visitor who came out of interest
has no reason to open the navigation, so each page ends by naming the one to
read next, in an order that goes from trying the thing to reading how it is
built. The last page points back to the first.
"""

from __future__ import annotations

import streamlit as st

from app.components.shell import escape

#: (url slug, title, one line on why to go there). The Check page is the
#: root, so its slug is empty and its link is `./`.
TRAIL: tuple[tuple[str, str, str], ...] = (
    ("check", "Check", "Ask the question in a sentence and read the verdict."),
    ("quiz", "Quiz", "Ten real situations. Would you have got them right?"),
    ("matrix", "Matrix", "Which tools may hold which data, on one grid."),
    ("agents", "Agents", "Switch on what an agent may do and watch its licence change."),
    ("changes", "Changes", "The verdicts that flipped between versions of the policy."),
    ("how", "How it works", "Rules as data, every verdict citing its clause."),
    ("policy", "Policy", "The policy itself, searchable, with the law behind each clause."),
    ("limits", "Limits", "What this does not cover, and what stays open."),
)


def next_page(current: str) -> tuple[str, str, str]:
    """The entry after `current`, wrapping round to the first."""
    slugs = [slug for slug, _title, _blurb in TRAIL]
    return TRAIL[(slugs.index(current) + 1) % len(TRAIL)]


def render_next(current: str) -> None:
    slug, title, blurb = next_page(current)
    href = "./" if slug == "check" else slug
    st.html(
        f'<a class="cu-next-page" href="{href}" target="_self">'
        '<span class="cu-next-page__kicker">Keep going</span>'
        f'<span class="cu-next-page__title">{escape(title)}</span>'
        f'<span class="cu-next-page__blurb">{escape(blurb)}</span>'
        "</a>"
    )
