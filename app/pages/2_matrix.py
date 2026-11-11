"""The data class x tool tier grid (BUILD_SPEC 9.2).

Every cell is computed by the rules engine, not transcribed from the policy,
so the grid cannot drift from the verdicts the Check page gives. A test
asserts the generated grid still agrees with the parsed 7.1 table.
"""

from __future__ import annotations

import streamlit as st

from app.components.clause_drawer import render_clause
from app.components.footer import render_footer
from app.components.shell import escape, inject_styles, page_header
from app.components.tiers import TIER_CLAUSES, TIER_GLOSS, tier_a_conditions
from app.components.verdict_card import render_verdict
from app.styles.tokens import style_for
from engine.models import Activity, DataClass, Inputs, Tool
from engine.policy_parser import load_policy
from engine.rules import evaluate, resolve_clauses

VERSION = "v1_6"
SELECTED = "cu_matrix_cell"

GRID_TIERS: tuple[Tool, ...] = (Tool.TIER_A, Tool.TIER_B, Tool.TIER_C)

TIER_HEADINGS = {Tool.TIER_A: "Tier A", Tool.TIER_B: "Tier B", Tool.TIER_C: "Tier C"}

#: A cell is about 80px wide on a phone, so the longest of the policy's own
#: words is abbreviated on the button. The detail panel quotes it in full.
SHORT_WORDS = {"Approved use case only": "Approval"}


#: Illustrative examples, not policy text. They show what each cell looks like
#: in practice; several are the golden scenarios of BUILD_SPEC 6.
EXAMPLES: dict[tuple[DataClass, Tool], str] = {
    (DataClass.PUBLIC, Tool.TIER_A): "Summarising your own published press release.",
    (DataClass.PUBLIC, Tool.TIER_B): "The same press release in a vetted Tier B tool.",
    (DataClass.PUBLIC, Tool.TIER_C): "Summarising a public news article in personal ChatGPT.",
    (DataClass.INTERNAL, Tool.TIER_A): "Drafting an internal memo in the approved tool.",
    (DataClass.INTERNAL, Tool.TIER_B): "Tidying an internal process note in a Tier B tool.",
    (DataClass.INTERNAL, Tool.TIER_C): "Pasting the internal org chart into a personal account.",
    (DataClass.CONFIDENTIAL, Tool.TIER_A): "Drafting a client deliverable in the approved tool.",
    (DataClass.CONFIDENTIAL, Tool.TIER_B): "A document naming a client, in a Tier B tool.",
    (DataClass.CONFIDENTIAL, Tool.TIER_C): "Pasting a client contract into personal ChatGPT.",
    (DataClass.RESTRICTED, Tool.TIER_A): "Uploading sick-leave notes for a summary.",
    (DataClass.RESTRICTED, Tool.TIER_B): "Health data in a vetted but not Tier A tool.",
    (DataClass.RESTRICTED, Tool.TIER_C): "Health data in a personal AI account.",
    (DataClass.SECRETS, Tool.TIER_A): "Pasting an API key into the approved tool to debug.",
    (DataClass.SECRETS, Tool.TIER_B): "An API key in a Tier B tool.",
    (DataClass.SECRETS, Tool.TIER_C): "An API key in a personal AI account.",
}


def cell_inputs(data_class: DataClass, tool: Tool) -> Inputs:
    """The neutral question each cell asks: this data, this tool, plain drafting."""
    return Inputs(data_class=data_class, tool=tool, activity=Activity.DRAFTING)


def _select(data_class: DataClass, tool: Tool) -> None:
    st.session_state[SELECTED] = (data_class.value, tool.value)


def policy_word(data_class: DataClass, tool: Tool) -> str:
    """The policy's own word for this cell of the 7.1 table."""
    table = load_policy(VERSION).table("7.1")
    words = {row[0]: row[1:] for row in table.rows}
    return words.get(data_class.value, ("", "", ""))[GRID_TIERS.index(tool)]


def _render_grid() -> None:
    # The key puts `.st-key-cu_matrix` on the wrapper, which is what stops the
    # columns stacking at phone width (see app.css).
    with st.container(key="cu_matrix"):
        header = st.columns([1.25, 1, 1, 1], gap="small")
        header[0].html('<p class="cu-grid-head">Data</p>')
        for index, tool in enumerate(GRID_TIERS, start=1):
            header[index].html(f'<p class="cu-grid-head">{escape(TIER_HEADINGS[tool])}</p>')

        for data_class in DataClass:
            row = st.columns([1.25, 1, 1, 1], gap="small")
            row[0].html(f'<p class="cu-grid-row">{escape(data_class.value)}</p>')
            for index, tool in enumerate(GRID_TIERS, start=1):
                verdict = evaluate(cell_inputs(data_class, tool), VERSION)
                style = style_for(verdict.status)
                word = policy_word(data_class, tool)
                row[index].button(
                    f"{style.icon} {SHORT_WORDS.get(word, word)}",
                    key=f"cu_cell_{data_class.value}_{tool.value}",
                    on_click=_select,
                    args=(data_class, tool),
                    help=f"7.1 says: {word}. {style.word}. {EXAMPLES[(data_class, tool)]}",
                    width="stretch",
                )


def _render_selection() -> None:
    chosen = st.session_state.get(SELECTED)
    if not chosen:
        st.html('<p class="cu-hint">Tap any cell for the rule behind it, and an example.</p>')
        return

    data_class, tool = DataClass(chosen[0]), Tool(chosen[1])
    st.markdown(f"## {data_class.value} data in a {TIER_HEADINGS[tool]} tool")
    st.html(
        f'<p class="cu-hint">7.1 says: <strong>{escape(policy_word(data_class, tool))}'
        f"</strong></p>"
        f'<p class="cu-route">{escape(EXAMPLES[(data_class, tool)])}</p>'
    )
    render_verdict(evaluate(cell_inputs(data_class, tool), VERSION), version=VERSION)


def _render_tier_key() -> None:
    """What the three column headings mean.

    The grid's headings are bare letters, which say nothing to a reader who
    has not read Part B. B.1.2's nine Tier A conditions are shown as a list
    rather than as its own run-in sentence, which is unreadable on a phone;
    the wording is still the clause's, and the full clauses are one more tap
    away rather than dumped into the panel.
    """
    conditions = tier_a_conditions(VERSION)

    with st.expander("What Tier A, B and C mean"):
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

        if st.checkbox("Show B.1.1 to B.1.3 in full", key="cu_matrix_tier_clauses"):
            for clause in resolve_clauses(TIER_CLAUSES, VERSION):
                render_clause(clause)


def main() -> None:
    inject_styles()
    page_header(
        "Which tools may hold which data",
        "The 7.1 grid. Every cell is worked out by the same rules the Check page uses.",
    )
    _render_tier_key()
    _render_grid()
    _render_selection()
    render_footer(VERSION)


main()
