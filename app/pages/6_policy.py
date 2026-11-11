"""The policy browser (BUILD_SPEC 9.6).

The staff summary first, then the full text with search, clause anchors and
the jurisdiction lens. Clause text is always the parsed file's own words.
"""

from __future__ import annotations

import streamlit as st

from app.components.basis_badges import render_policy_backing
from app.components.footer import render_footer
from app.components.shell import escape, inject_styles, mark_template_fields, page_header
from app.styles.tokens import BASIS_ICONS, BASIS_LABELS
from engine.models import Clause
from engine.policy_parser import load_policy
from engine.rules import JURISDICTION_LENSES, applies_in, basis_for, load_basis

VERSION = "v1_6"
SEARCH_KEY = "cu_policy_search"
LENS_KEY = "cu_policy_lens"


def _matching(clauses: list[Clause], query: str) -> list[Clause]:
    """Clauses whose id or text contains the query, case-insensitively."""
    if not query.strip():
        return clauses
    needle = query.strip().lower()
    return [c for c in clauses if needle in c.id.lower() or needle in c.text.lower()]


def _render_front_matter() -> None:
    """The policy's own header, with its template fields marked as such."""
    fields = load_policy(VERSION).front_matter
    if not fields:
        return

    rows = "".join(
        f"<tr><th>{escape(name)}</th><td>{mark_template_fields(value)}</td></tr>"
        for name, value in fields.items()
    )
    with st.expander("Document details, and what an adopter fills in"):
        st.html(
            '<p class="cu-hint">This is a model policy. The dashed fields are '
            "the ones an organization replaces before adopting it.</p>"
            f'<table class="cu-fields">{rows}</table>'
        )


def _render_staff_summary() -> None:
    summary = load_policy(VERSION).staff_summary
    if summary.is_empty:
        return

    st.markdown("## AI at work, on one page")
    for heading, items, tone in (
        ("Always", summary.always, "allowed"),
        ("Ask first", summary.ask_first, "needs-approval"),
        ("Never", summary.never, "prohibited"),
    ):
        rows = "".join(f"<li>{escape(item)}</li>" for item in items)
        st.html(
            f'<div class="cu-card cu-card--{tone}">'
            f'<p class="cu-status cu-status--compact">{escape(heading)}</p>'
            f'<ul class="cu-list">{rows}</ul></div>'
        )

    if summary.footer:
        st.html(f'<p class="cu-hint">{mark_template_fields(summary.footer)}</p>')


def _render_lens() -> str:
    st.markdown("## The full policy")
    lens = st.segmented_control(
        "Jurisdiction lens",
        options=JURISDICTION_LENSES,
        key=LENS_KEY,
        default="Global",
        width="stretch",
        help=(
            "Highlights which laws and standards apply where. It never changes "
            "a verdict: 1.2 already applies whichever requirement is stricter."
        ),
    )
    return lens or "Global"


def _render_lens_summary(lens: str) -> None:
    entries = [e for e in load_basis() if applies_in(e, lens) and e.clause != "*"]
    if lens == "Global":
        st.html(
            '<p class="cu-hint">Showing every clause. Pick a jurisdiction to see '
            "which ones have a law or standard behind them there.</p>"
        )
        return
    listed = ", ".join(sorted({e.clause for e in entries}))
    st.html(
        f'<p class="cu-hint">Under the {escape(lens)} lens, these clauses have '
        f"a law or standard behind them: {escape(listed)}.</p>"
    )


def _backing_note(clause_id: str, lens: str) -> str:
    """A one-line backing note for a clause, filtered by the lens."""
    entries = [e for e in basis_for([clause_id]) if applies_in(e, lens)]
    if not entries:
        return ""
    bits = []
    for entry in entries:
        icon = BASIS_ICONS[entry.type.value]
        label = BASIS_LABELS[entry.type.value]
        where = f" · {entry.jurisdiction}" if entry.jurisdiction else ""
        bits.append(f"{icon} {label}: {escape(entry.source)}{escape(where)}")
    return f'<p class="cu-meta">{" — ".join(bits)}</p>'


def _render_clauses(lens: str, query: str) -> None:
    policy = load_policy(VERSION)
    clauses = sorted(policy.clauses.values(), key=lambda c: c.sort_key)
    found = _matching(clauses, query)

    if query.strip():
        st.html(
            f'<p class="cu-hint">{len(found)} of {len(clauses)} clauses match '
            f'"{escape(query.strip())}".</p>'
        )

    current_part = object()
    for clause in found:
        if clause.part != current_part:
            current_part = clause.part
            if current_part:
                st.markdown(f"### Part {current_part}")

        where = clause.section_title or ""
        # The anchor makes every clause linkable: #clause-6-3
        anchor = f"clause-{clause.id.replace('.', '-').lower()}"
        st.html(
            f'<div class="cu-clause" id="{anchor}">'
            f'<span class="cu-clause__id">{escape(clause.id)}</span>'
            f'<span class="cu-clause__where">{escape(where)}</span></div>'
        )
        st.markdown(clause.text)
        note = _backing_note(clause.id, lens)
        if note:
            st.html(note)


def main() -> None:
    inject_styles()
    page_header(
        "The policy itself",
        "AIG-POL-001 v1.6, in full. Search it, or see which laws apply where.",
    )

    _render_front_matter()
    _render_staff_summary()
    lens = _render_lens()
    _render_lens_summary(lens)

    query = st.text_input(
        "Search the policy",
        key=SEARCH_KEY,
        placeholder="A clause number, or any words in it",
    )
    _render_clauses(lens, query or "")

    render_policy_backing()
    render_footer(VERSION)


main()
