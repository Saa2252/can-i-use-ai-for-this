"""The "Backed by" row (BUILD_SPEC 7).

The policy decides the verdict. These badges only explain why the rule exists,
and a verdict never changes with jurisdiction, because 1.2 already applies the
stricter rule.
"""

from __future__ import annotations

from datetime import date

import streamlit as st

from app.components.shell import escape
from app.styles.tokens import BASIS_ICONS, BASIS_LABELS
from engine.models import Basis
from engine.rules import policy_basis


def render_basis_row(entries: list[Basis], *, today: date | None = None) -> None:
    """A row of tappable badges, one per distinct backing entry."""
    if not entries:
        return

    today = today or date.today()
    st.html('<p class="cu-label">Backed by</p>')

    with st.container(horizontal=True, gap="small"):
        for index, entry in enumerate(entries):
            icon = BASIS_ICONS[entry.type.value]
            label = BASIS_LABELS[entry.type.value]
            stale = entry.is_stale(today)
            with st.popover(
                f"{icon} {label}",
                help=f"Why {entry.clause} exists",
            ):
                _render_detail(entry, stale=stale, index=index)


def _applies_to(clause: str) -> str:
    """Describe a crosswalk entry's reach without showing the raw pattern."""
    if clause == "*":
        return "Applies to the policy as a whole"
    if clause.endswith(".*"):
        prefix = clause[:-2]
        if prefix in {"B", "C", "D"}:
            return f"Applies to Part {prefix}"
        return f"Applies to the clauses in Section {prefix}"
    return f"Applies to clause {clause}"


def _render_detail(entry: Basis, *, stale: bool, index: int) -> None:
    recheck = '<span class="cu-recheck">needs re-check</span>' if stale else ""
    st.html(
        f'<p class="cu-source"><strong>{escape(entry.source)}</strong>{recheck}</p>'
        f'<p class="cu-meta">'
        f"{escape(_applies_to(entry.clause))}"
        f"{' · ' + escape(entry.jurisdiction) if entry.jurisdiction else ''}"
        f"{' · ' + escape(entry.status) if entry.status else ''}"
        f" · checked {entry.checked.isoformat()}"
        f"</p>" + (f'<p class="cu-meta">{escape(entry.note)}</p>' if entry.note else "")
    )


def render_policy_backing() -> None:
    """Backing for the policy as a whole, for an about or footer area."""
    for entry in policy_basis():
        icon = BASIS_ICONS[entry.type.value]
        st.html(
            f'<p class="cu-meta">{icon} The policy as a whole follows {escape(entry.source)}.</p>'
        )
