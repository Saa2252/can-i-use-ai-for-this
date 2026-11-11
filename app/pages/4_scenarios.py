"""The scenario quiz (BUILD_SPEC 9.4).

Ten of the golden scenarios, shuffled, always including 4, 8, 9 and 14 —
the four that show the policy's most interesting lines. Each reveal gives the
clauses and the backing, so a wrong answer teaches the rule.
"""

from __future__ import annotations

import random

import streamlit as st

from app.components.basis_badges import render_basis_row
from app.components.clause_drawer import render_clause_chips, render_clause_drawer
from app.components.footer import render_footer
from app.components.legend import render_verdict_key
from app.components.scenario_text import describe_scenario
from app.components.shell import escape, inject_styles, page_header
from app.styles.tokens import STATUS_STYLES, style_for
from engine.models import Status
from engine.rules import evaluate
from engine.scenarios import QUIZ_LOCKED, Scenario, load_scenarios

VERSION = "v1_6"
QUESTION_COUNT = 10

ORDER_KEY = "cu_quiz_order"
ANSWERS_KEY = "cu_quiz_answers"

#: The four choices offered for every question.
CHOICES: tuple[Status, ...] = (
    Status.ALLOWED,
    Status.NEEDS_APPROVAL,
    Status.NOT_PERMITTED,
    Status.PROHIBITED,
)


def build_quiz(seed: int | None = None) -> list[int]:
    """Ten scenario numbers, shuffled, always including 4, 8, 9 and 14."""
    rng = random.Random(seed)
    everything = [scenario.n for scenario in load_scenarios()]
    locked = list(QUIZ_LOCKED)
    pool = [n for n in everything if n not in locked]
    rng.shuffle(pool)
    chosen = locked + pool[: QUESTION_COUNT - len(locked)]
    rng.shuffle(chosen)
    return chosen


def _ensure_quiz() -> list[int]:
    """One shuffle per session, so a rerun does not reorder the questions."""
    if ORDER_KEY not in st.session_state:
        st.session_state[ORDER_KEY] = build_quiz()
        st.session_state[ANSWERS_KEY] = {}
    return st.session_state[ORDER_KEY]


def _restart() -> None:
    st.session_state[ORDER_KEY] = build_quiz()
    st.session_state[ANSWERS_KEY] = {}


def _answer(number: int) -> None:
    picked = st.session_state.get(f"cu_q_{number}")
    if picked is not None:
        st.session_state[ANSWERS_KEY][number] = picked


def _render_question(position: int, example: Scenario) -> None:
    st.markdown(f"## {position}. {example.title}")
    st.html(f'<p class="cu-hint">{escape(describe_scenario(example))}</p>')

    st.segmented_control(
        "What does the policy say?",
        options=CHOICES,
        format_func=lambda status: STATUS_STYLES[status].word,
        key=f"cu_q_{example.n}",
        on_change=_answer,
        args=(example.n,),
        width="stretch",
        label_visibility="collapsed",
    )

    picked = st.session_state[ANSWERS_KEY].get(example.n)
    if picked is None:
        return

    verdict = evaluate(example.inputs, VERSION)
    correct = picked is verdict.status
    style = style_for(verdict.status)
    mark = "✓ Correct" if correct else "✕ Not quite"

    st.html(
        f'<div class="cu-card cu-card--{style.slug}">'
        f'<p class="cu-status"><span class="cu-status__icon" aria-hidden="true">'
        f"{style.icon}</span><span>{escape(style.word)}</span></p>"
        f'<p class="cu-approval">{escape(mark)}</p>'
        f'<p class="cu-reason">{escape(verdict.reasons[0] if verdict.reasons else "")}</p>'
        f"</div>"
    )
    render_clause_chips(verdict.clauses)
    render_clause_drawer(verdict.clauses, VERSION)
    render_basis_row(verdict.basis)


def _render_score(order: list[int]) -> None:
    """Progress from the first paint, so the page says how long it is.

    This used to render nothing until a question was answered, so the page
    opened on question 1 with no sign that there were ten of them.
    """
    answers = st.session_state[ANSWERS_KEY]
    answered = [n for n in order if n in answers]
    remaining = len(order) - len(answered)

    if not answered:
        st.html(
            f'<p class="cu-hint">{len(order)} questions. Pick an answer and the '
            "clauses behind it open underneath.</p>"
        )
        return

    by_number = {scenario.n: scenario for scenario in load_scenarios()}
    score = sum(1 for n in answered if answers[n] is evaluate(by_number[n].inputs, VERSION).status)

    st.markdown("## Your score")
    tail = f"{remaining} still to answer." if remaining else "All answered."
    st.html(
        f'<p class="cu-score">{score} / {len(answered)}</p><p class="cu-hint">{escape(tail)}</p>'
    )

    if len(answered) == len(order):
        st.html('<p class="cu-label">Share your score</p>')
        st.code(
            f"I scored {score}/{len(order)} on 'Can I use AI for this?', "
            "a quiz built from an AI Acceptable Use Policy (AIG-POL-001 v1.5). "
            "Every answer cites the clause it comes from.",
            language=None,
            wrap_lines=True,
        )

    st.button("Start again", key="cu_quiz_restart", on_click=_restart)


def main() -> None:
    inject_styles()
    page_header(
        "Would you have got these right?",
        "Ten real situations. Each answer shows the clauses behind it.",
    )

    order = _ensure_quiz()
    by_number = {scenario.n: scenario for scenario in load_scenarios()}

    # The four options are the question. Defining them only on the verdict
    # card is no use here, where picking between them is the task.
    render_verdict_key()
    _render_score(order)
    for position, number in enumerate(order, start=1):
        _render_question(position, by_number[number])

    render_footer(VERSION)


main()
