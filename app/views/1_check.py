"""The hero page: "Can I use AI for this?"

Three choices and a verdict, without scrolling first (BUILD_SPEC 1). The
verdict reproduces from its URL, and nothing the visitor enters is stored.
"""

from __future__ import annotations

import streamlit as st

from app.components.footer import render_footer
from app.components.inputs import (
    apply_example,
    missing_prompt,
    missing_required,
    render_inputs,
    seed_from_query_params,
    share_url,
    write_query_params,
)
from app.components.legend import render_data_class_key
from app.components.shell import inject_styles, page_header
from app.components.tiers import render_tier_key
from app.components.verdict_card import render_verdict, render_waiting
from engine.rules import evaluate
from engine.scenarios import scenario

VERSION = "v1_6"

#: BUILD_SPEC 9.1: a "Try an example" chip row for scenarios 2, 4 and 8.
#: Labels are kept short so more than one chip fits a 375px row.
EXAMPLES: tuple[tuple[int, str], ...] = (
    (2, "Client contract"),
    (4, "Naming colleagues"),
    (8, "Agent emails"),
)


#: `?demo=1` preloads this scenario, for a screen recording that opens on a
#: verdict rather than on the defaults (BUILD_SPEC 10, Phase 5).
DEMO_SCENARIO = 2
DEMO_FLAG = "cu_demo_loaded"


def _load_example(number: int) -> None:
    """Button callback: callbacks run before the rerun, so assigning to
    widget-keyed session state here is safe wherever the row is rendered."""
    apply_example(scenario(number).inputs)


def _apply_demo_mode() -> bool:
    """Preload the demo scenario once, before any widget is created.

    It loads a single time per session, so the recording can keep clicking
    afterwards without the page snapping back to the demo.
    """
    if st.query_params.get("demo") != "1":
        return False
    if st.session_state.get(DEMO_FLAG):
        return True
    apply_example(scenario(DEMO_SCENARIO).inputs)
    st.session_state[DEMO_FLAG] = True
    return True


def main() -> None:
    inject_styles()
    page_header(
        "Can I use AI for this?",
        "An answer from the AI Acceptable Use Policy, with the clauses it rests on.",
    )

    demo = _apply_demo_mode()
    if not demo:
        seed_from_query_params()

    st.html('<p class="cu-label">Try an example</p>')
    with st.container(horizontal=True, gap="small"):
        for number, label in EXAMPLES:
            st.button(
                label,
                key=f"cu_example_{number}",
                on_click=_load_example,
                args=(number,),
                help=scenario(number).title,
                width="content",
            )

    inputs, visible = render_inputs()
    if inputs is None:
        render_waiting(missing_prompt(missing_required()))
    else:
        verdict = evaluate(inputs, VERSION)
        render_verdict(verdict, version=VERSION, share_url=share_url(visible))

    # Below the verdict, not above it: the hero has to reach an answer within
    # 375x812 (BUILD_SPEC 1), and this panel costs 40px it does not have. The
    # data-class question carries the same guidance as its own help tooltip.
    render_data_class_key(VERSION)
    render_tier_key(VERSION)

    write_query_params(visible)
    render_footer(VERSION)


main()
