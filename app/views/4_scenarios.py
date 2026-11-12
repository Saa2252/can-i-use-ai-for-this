"""The scenario quiz (BUILD_SPEC 9.4).

Ten of the golden scenarios, shuffled, always including 4, 8, 9 and 14 —
the four that show the policy's most interesting lines. Each reveal gives the
clauses and the backing, so a wrong answer teaches the rule.

One question at a time. Ten at once is a wall of text in which no single
question is the thing you are doing, and the answer to question 7 is visible
while you are still on question 2.

The question itself is the scenario's title, which is how a colleague would
actually put it. The input breakdown — data class, tier, flags — moves into
the reveal, because naming the class and the tier up front turns the question
into a lookup in the Matrix rather than an exercise in classifying.
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
AT_KEY = "cu_quiz_at"

#: A score arriving in the URL is someone else's result, not this session's.
SHARED_SCORE = "score"

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
        st.session_state[AT_KEY] = 0
    return st.session_state[ORDER_KEY]


def _restart() -> None:
    st.session_state[ORDER_KEY] = build_quiz()
    st.session_state[ANSWERS_KEY] = {}
    st.session_state[AT_KEY] = 0


def _advance() -> None:
    order = st.session_state[ORDER_KEY]
    st.session_state[AT_KEY] = min(st.session_state[AT_KEY] + 1, len(order))


def _back() -> None:
    st.session_state[AT_KEY] = max(st.session_state[AT_KEY] - 1, 0)


def _answer(number: int) -> None:
    picked = st.session_state.get(f"cu_q_{number}")
    if picked is not None:
        st.session_state[ANSWERS_KEY][number] = picked


def _by_number() -> dict[int, Scenario]:
    return {scenario.n: scenario for scenario in load_scenarios()}


def _score(order: list[int]) -> tuple[int, int]:
    """Correct answers, and how many have been answered at all."""
    answers = st.session_state[ANSWERS_KEY]
    by_number = _by_number()
    answered = [n for n in order if n in answers]
    correct = sum(
        1 for n in answered if answers[n] is evaluate(by_number[n].inputs, VERSION).status
    )
    return correct, len(answered)


def _render_progress(order: list[int]) -> None:
    """Where you are, how far there is to go, and how you are doing."""
    position = min(st.session_state[AT_KEY], len(order) - 1)
    correct, answered = _score(order)

    tail = f" · {correct} right so far" if answered else ""
    st.progress(
        (position + 1) / len(order),
        text=f"Question {position + 1} of {len(order)}{tail}",
    )


def _render_reveal(example: Scenario, picked: Status) -> None:
    """The answer, why, and the inputs that produced it."""
    verdict = evaluate(example.inputs, VERSION)
    style = style_for(verdict.status)
    mark = "✓ Correct" if picked is verdict.status else "✕ Not quite"

    st.html(
        f'<div class="cu-card cu-card--{style.slug}">'
        f'<p class="cu-status"><span class="cu-status__icon" aria-hidden="true">'
        f"{style.icon}</span><span>{escape(style.word)}</span></p>"
        f'<p class="cu-approval">{escape(mark)}</p>'
        f'<p class="cu-reason">{escape(verdict.reasons[0] if verdict.reasons else "")}</p>'
        f"</div>"
        f'<p class="cu-label">What you were being asked</p>'
        f'<p class="cu-hint">{escape(describe_scenario(example))}</p>'
    )
    render_clause_chips(verdict.clauses)
    render_clause_drawer(verdict.clauses, VERSION)
    render_basis_row(verdict.basis)


def _render_question(position: int, example: Scenario, last: bool) -> None:
    st.markdown(f"## {position}. {example.title}")

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
        st.html('<p class="cu-hint">Pick one. The clauses open as soon as you do.</p>')
    else:
        _render_reveal(example, picked)

    with st.container(horizontal=True, gap="small"):
        if position > 1:
            st.button("Back", key="cu_quiz_back", on_click=_back, width="content")
        if picked is not None:
            st.button(
                "See your score" if last else "Next question",
                key="cu_quiz_next",
                on_click=_advance,
                type="primary",
                width="content",
            )


def _share_text(correct: int, total: int) -> str:
    return (
        f"I scored {correct}/{total} on 'Can I use AI for this?', a quiz built "
        f"from an AI Acceptable Use Policy (AIG-POL-001 {VERSION.replace('v1_', 'v1.')}). "
        "Every answer cites the clause it comes from."
    )


def _share_link(correct: int, total: int) -> str:
    try:
        base = (st.context.url or "").split("?")[0]
    except Exception:  # noqa: BLE001 - no browser context, e.g. under AppTest
        base = ""
    return f"{base}?{SHARED_SCORE}={correct}&of={total}"


def _render_final(order: list[int]) -> None:
    correct, _answered = _score(order)
    total = len(order)

    st.markdown("## Your score")
    st.html(f'<p class="cu-score">{correct} / {total}</p>')
    st.progress(correct / total, text=f"{correct} of {total} right")

    st.html('<p class="cu-label">Share it</p>')
    st.code(_share_text(correct, total), language=None, wrap_lines=True)
    st.code(_share_link(correct, total), language=None, wrap_lines=True)

    st.button("Start again", key="cu_quiz_restart", on_click=_restart, type="primary")


def _render_shared_score(total: int) -> None:
    """A score that arrived in the URL belongs to whoever sent the link."""
    raw = st.query_params.get(SHARED_SCORE)
    if raw is None or st.session_state[ANSWERS_KEY]:
        return
    try:
        theirs = int(raw)
    except ValueError:
        return
    if not 0 <= theirs <= total:
        return
    st.html(
        f'<p class="cu-hint">Someone scored <strong>{theirs}/{total}</strong> and '
        "sent you this. The ten questions below are shuffled, so yours will not "
        "be the same ten.</p>"
    )


def main() -> None:
    inject_styles()
    page_header(
        "Would you have got these right?",
        "Ten real situations. Each answer shows the clauses behind it.",
    )

    order = _ensure_quiz()
    by_number = _by_number()

    # The four options are the question. Defining them only on the verdict
    # card is no use here, where picking between them is the task.
    render_verdict_key()
    _render_shared_score(len(order))

    position = st.session_state[AT_KEY]
    if position >= len(order):
        _render_final(order)
    else:
        _render_progress(order)
        _render_question(
            position + 1,
            by_number[order[position]],
            last=position == len(order) - 1,
        )

    render_footer(VERSION)


main()
