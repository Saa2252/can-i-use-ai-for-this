"""The clause drawer: clause id plus the exact policy text, expanding on tap.

The text is rendered as markdown rather than escaped HTML so the policy's own
bullets and tables read properly. It is still the file's own words, sliced by
the parser and never rewritten (BUILD_SPEC 0.5).
"""

from __future__ import annotations

import streamlit as st

from app.components.shell import escape
from engine.models import Clause
from engine.rules import resolve_clauses


def render_clause_chips(clause_ids: list[str]) -> None:
    """The visible citation row."""
    if not clause_ids:
        return
    chips = "".join(f'<li class="cu-chip">{escape(cid)}</li>' for cid in clause_ids)
    st.html(f'<p class="cu-label">Clauses</p><ul class="cu-chips">{chips}</ul>')


def render_clause_drawer(
    clause_ids: list[str],
    version: str = "v1_5",
    *,
    label: str | None = None,
    expanded: bool = False,
) -> None:
    """An expander holding each cited clause's exact text."""
    if not clause_ids:
        return
    clauses = resolve_clauses(clause_ids, version)
    heading = label or f"Read the {len(clauses)} clause{'s' if len(clauses) != 1 else ''} in full"
    with st.expander(heading, expanded=expanded):
        for clause in clauses:
            render_clause(clause)


def render_clause(clause: Clause) -> None:
    """One clause: its id, where it sits, and its text verbatim."""
    where = _where(clause)
    st.html(
        f'<div class="cu-clause"><span class="cu-clause__id">{escape(clause.id)}</span>'
        f'<span class="cu-clause__where">{escape(where)}</span></div>'
    )
    st.markdown(clause.text)


def _where(clause: Clause) -> str:
    parts = []
    if clause.part:
        parts.append(f"Part {clause.part}")
    if clause.section_title:
        parts.append(clause.section_title)
    return " · ".join(parts)
