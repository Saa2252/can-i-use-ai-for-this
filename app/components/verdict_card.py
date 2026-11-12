"""The verdict card (BUILD_SPEC 8).

Status line, one-sentence reason, clause chips, "Backed by" badges,
requirements or try-instead, and Copy link.
"""

from __future__ import annotations

import streamlit as st

from app.components.basis_badges import render_basis_row
from app.components.clause_drawer import render_clause_chips, render_clause_drawer
from app.components.shell import escape
from app.styles.tokens import APPROVAL_LABELS, style_for
from engine.models import ApprovalKind, Status, Verdict


def render_waiting(prompt: str) -> None:
    """The card shown when a required answer has been cleared.

    A segmented control deselects when its chosen chip is clicked again, so a
    visitor can empty an answer the engine needs. Before this, that reached
    pydantic as None and Streamlit printed a ValidationError traceback to
    someone who had done nothing wrong.
    """
    st.html(
        '<div class="cu-card cu-card--waiting">'
        '<p class="cu-status">'
        '<span class="cu-status__icon" aria-hidden="true">?</span>'
        f"<span>{escape(prompt)}</span></p>"
        '<p class="cu-subtitle">Clicking a chosen chip again clears it. '
        "Pick one and the answer comes straight back.</p>"
        "</div>"
    )


def render_verdict(
    verdict: Verdict,
    *,
    version: str = "v1_5",
    share_url: str | None = None,
) -> None:
    """Render one verdict, top to bottom."""
    style = style_for(verdict.status)

    approval = ""
    if verdict.approval_kind is not ApprovalKind.NONE:
        approval = f'<p class="cu-approval">{escape(APPROVAL_LABELS[verdict.approval_kind])}</p>'

    headline = verdict.reasons[0] if verdict.reasons else ""

    st.html(
        f'<div class="cu-card cu-card--{style.slug}">'
        f'<p class="cu-status">'
        f'<span class="cu-status__icon" aria-hidden="true">{style.icon}</span>'
        f"<span>{escape(style.word)}</span></p>"
        f'<p class="cu-subtitle">{escape(style.subtitle)}</p>'
        f"{approval}"
        f'<p class="cu-reason">{escape(headline)}</p>'
        f"</div>"
    )

    if verdict.status is Status.NOT_PERMITTED and verdict.try_instead:
        st.html(
            '<p class="cu-label">Try instead</p>'
            f'<p class="cu-route">{escape(verdict.try_instead)}</p>'
        )

    if verdict.status is Status.NEEDS_APPROVAL and verdict.requirements:
        _render_list("What is required", verdict.requirements)

    _render_supporting_reasons(verdict)

    render_clause_chips(verdict.clauses)
    render_clause_drawer(verdict.clauses, version)
    render_basis_row(verdict.basis)

    if share_url:
        st.html('<p class="cu-label">Copy link</p>')
        st.code(share_url, language=None, wrap_lines=True)


def render_compact_verdict(verdict: Verdict, *, heading: str) -> None:
    """A short card for side-by-side comparison, without the drawer or badges."""
    style = style_for(verdict.status)
    approval = ""
    if verdict.approval_kind is not ApprovalKind.NONE:
        approval = f'<p class="cu-approval">{escape(APPROVAL_LABELS[verdict.approval_kind])}</p>'
    chips = "".join(f'<li class="cu-chip">{escape(cid)}</li>' for cid in verdict.clauses)
    st.html(
        f'<div class="cu-card cu-card--{style.slug}">'
        f'<p class="cu-label">{escape(heading)}</p>'
        f'<p class="cu-status cu-status--compact">'
        f'<span class="cu-status__icon" aria-hidden="true">{style.icon}</span>'
        f"<span>{escape(style.word)}</span></p>"
        f"{approval}"
        f'<p class="cu-reason">{escape(verdict.reasons[0] if verdict.reasons else "")}</p>'
        f'<ul class="cu-chips">{chips}</ul>'
        f"</div>"
    )


def _render_supporting_reasons(verdict: Verdict) -> None:
    """Everything else that fired, after the decisive reason."""
    rest = verdict.reasons[1:]
    if not rest:
        return
    _render_list("Also applies", rest)


def _render_list(label: str, items: list[str]) -> None:
    rows = "".join(f"<li>{escape(item)}</li>" for item in items)
    st.html(f'<p class="cu-label">{escape(label)}</p><ul class="cu-list">{rows}</ul>')
