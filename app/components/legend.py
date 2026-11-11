"""Keys to the app's own vocabulary.

The app asks a reader to choose between four verdicts and five data classes
and then answers in the same words. Those words are defined on the verdict
card, which is no help on the Quiz, where choosing between them is the task.

Nothing here is new wording. The verdict lines are the same subtitles the
cards use, so a key cannot drift from a card, and the data-class text is the
policy's own clauses.
"""

from __future__ import annotations

import streamlit as st

from app.components.clause_drawer import render_clause
from app.components.shell import escape
from app.styles.tokens import STATUS_STYLES
from engine.models import Status
from engine.rules import resolve_clauses

#: In order of severity, which is the order the engine resolves them in.
VERDICTS: tuple[Status, ...] = (
    Status.ALLOWED,
    Status.NEEDS_APPROVAL,
    Status.NOT_PERMITTED,
    Status.PROHIBITED,
)

#: 7.4 defines Restricted outright. 7.5 and 7.6 say how the other classes are
#: decided, and both point outside this policy, which the key says plainly.
DATA_CLASS_CLAUSES = ["7.4", "7.5", "7.6"]


def render_verdict_key(label: str = "What the four answers mean") -> None:
    """The four verdicts, in the words the verdict cards use."""
    with st.expander(label):
        st.html(
            '<p class="cu-hint">The difference between the middle two is the '
            "whole point: one is blocked as you described it but has a lawful "
            "route, the other has no route at all.</p>"
        )
        for status in VERDICTS:
            style = STATUS_STYLES[status]
            st.html(
                f'<div class="cu-clause">'
                f'<span class="cu-clause__id">{escape(style.icon)} '
                f"{escape(style.word)}</span></div>"
                f'<p class="cu-clause__text">{escape(style.subtitle)}</p>'
            )


def render_data_class_key(
    version: str = "v1_5",
    label: str = "What the five data classes mean",
) -> None:
    """Where each class is defined, including the parts that are not here."""
    with st.expander(label):
        st.html(
            '<p class="cu-hint">Classify the whole interaction, and the highest '
            "class present decides the tool. 7.4 defines Restricted. Public, "
            "Internal and Confidential are set by the organization's own Data "
            "Classification Standard, which this policy points to rather than "
            "restates, so an adopter maps them to their own scheme.</p>"
        )
        for clause in resolve_clauses(DATA_CLASS_CLAUSES, version):
            render_clause(clause)
