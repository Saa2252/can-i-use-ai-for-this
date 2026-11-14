"""What the tool tiers mean, for pages that show the grid or the tool picker.

B.1.2 states the nine Tier A conditions as one semicolon-separated sentence.
That reads badly on a phone, so this module splits that sentence into its
items. Splitting is not paraphrasing: every item is the clause's own words,
sliced out of the parsed policy, so a reworded policy changes this list
instead of leaving a stale copy behind (BUILD_SPEC 0.5).
"""

from __future__ import annotations

import re

import streamlit as st

from app.components.clause_drawer import render_clause
from app.components.grid import ROW_LABELS, TOOL_COLUMNS, cell_status
from app.components.shell import escape
from app.styles.tokens import STATUS_STYLES
from engine.models import DataClass
from engine.policy_parser import load_policy
from engine.rules import resolve_clauses

#: The run-in list in B.1.2 begins after this, and ends at the sentence stop.
_LIST_START = re.compile(r"only with all of:\s*(?P<items>[^.]+)\.", re.IGNORECASE)


def tier_a_conditions(version: str = "v1_6") -> list[str]:
    """The Tier A conditions from B.1.2, one per item, in the policy's words.

    Returns an empty list if B.1.2 no longer has that shape, so a caller can
    fall back to showing the clause whole rather than printing nothing.
    """
    clause = load_policy(version).clauses.get("B.1.2")
    if clause is None:
        return []

    match = _LIST_START.search(clause.text)
    if match is None:
        return []

    items = []
    for raw in match.group("items").split(";"):
        item = raw.strip()
        # The clause writes the final item as "and advance notice ...".
        item = re.sub(r"^and\s+", "", item)
        if item:
            items.append(item)
    return items


#: One line per tier. These are glosses, not policy text: the pages that use
#: them say so, and render the clauses themselves alongside. The Tier C line
#: is the glossary's own sentence, and the Check page's tool help uses it too.
TIER_GLOSS: tuple[tuple[str, str], ...] = (
    ("Tier A", "Assessed and approved. Meets every condition in B.1.2:"),
    ("Tier B", "Vetted, but missing one or more of those conditions."),
    ("Tier C", "Anything not assessed, including personal accounts."),
)

#: The clauses that define the tiers, shown in full on request.
TIER_CLAUSES = ["B.1.1", "B.1.2", "B.1.3"]


def render_tier_key(version: str = "v1_6", label: str = "What Tier A, B and C mean") -> None:
    """The three tiers, with B.1's nine conditions as items rather than prose.

    Used by the Matrix, whose column headings are bare letters, and by the
    Check page, whose tool picker had a tooltip for Tier C only — so the two
    tiers a reader is most likely to be choosing between were unexplained on
    the page most readers land on.
    """
    conditions = tier_a_conditions(version)

    with st.expander(label):
        st.html(
            '<p class="cu-hint">A tool\'s tier is assigned by IT and Security, '
            "not by the person using it. The lines below are a plain-English "
            "gloss; the clause wording is underneath.</p>"
        )
        for tier, gloss in TIER_GLOSS:
            st.html(
                f'<p class="cu-label">{escape(tier)}</p>'
                f'<p class="cu-clause__text">{escape(gloss)}</p>'
            )
            if tier == "Tier A" and conditions:
                items = "".join(f"<li>{escape(c)}</li>" for c in conditions)
                st.html(f'<ul class="cu-list">{items}</ul>')

        if st.checkbox("Show B.1.1 to B.1.3 in full", key=f"cu_tier_clauses_{version}"):
            for clause in resolve_clauses(TIER_CLAUSES, version):
                render_clause(clause)


# --------------------------------------------------------------------------
# The strip
# --------------------------------------------------------------------------

#: The gloss as a sentence, for a card that has no list under it.
_STRIP_GLOSS: dict[str, str] = {
    "Tier A": "Assessed and approved against every condition in B.1.2.",
    "Tier B": "Vetted, but missing one or more of those conditions.",
    "Tier C": "Anything not assessed, including personal accounts.",
}


def tier_strip_rows(version: str = "v1_6") -> list[dict[str, object]]:
    """One row per tier: its names, its gloss, and what may go in.

    "What may go in" is the engine's answer for plain drafting of each data
    class in that tier, which is the 7.1 column read through `evaluate`, so
    the strip cannot disagree with the Matrix or with a verdict.
    """
    rows = []
    for tool, plain, term in TOOL_COLUMNS:
        cells = []
        for data_class in DataClass:
            name = ROW_LABELS[data_class][0]
            status = cell_status(data_class, tool)
            cells.append((name, status))
        rows.append(
            {
                "tool": tool,
                "plain": plain,
                "term": term,
                "gloss": _STRIP_GLOSS[term],
                "cells": cells,
            }
        )
    return rows


def render_tier_strip(version: str = "v1_6") -> None:
    """Tier A, B and C as three cards a first-time reader can take in at once.

    The expander form (`render_tier_key`) keeps the nine conditions and the
    clauses; this puts the three names, one line each, and what may go in,
    on the page itself, because the tier is the word the whole policy turns
    on and it was hidden behind a click.
    """
    cards = []
    for row in tier_strip_rows(version):
        chips = "".join(
            f'<span class="cu-key cu-key--{STATUS_STYLES[status].slug}">'
            f"{escape(STATUS_STYLES[status].icon)} {escape(name)}</span>"
            for name, status in row["cells"]  # type: ignore[union-attr]
        )
        cards.append(
            '<div class="cu-tier">'
            f'<span class="cu-tier__kicker">{escape(str(row["term"]))}</span>'
            f'<strong class="cu-tier__name">{escape(str(row["plain"]))}</strong>'
            f'<p class="cu-tier__gloss">{escape(str(row["gloss"]))}</p>'
            '<span class="cu-tier__label">What may go in</span>'
            f'<div class="cu-tier__chips">{chips}</div>'
            "</div>"
        )
    st.html(
        f'<div class="cu-tiers">{"".join(cards)}</div>'
        '<p class="cu-meta">A tool\'s tier is assigned by IT and Security, not by the '
        "person using it. Each chip is the engine's answer for plain drafting of that "
        "data in that tool, which is the 7.1 grid read through the same rules.</p>"
    )
    conditions = tier_a_conditions(version)
    with st.expander("The Tier A conditions, and B.1.1 to B.1.3 in full"):
        if conditions:
            st.html(
                '<p class="cu-hint">B.1.2 grants Tier A only with all of:</p>'
                '<ul class="cu-list">'
                + "".join(f"<li>{escape(c)}</li>" for c in conditions)
                + "</ul>"
            )
        for clause in resolve_clauses(TIER_CLAUSES, version):
            render_clause(clause)
