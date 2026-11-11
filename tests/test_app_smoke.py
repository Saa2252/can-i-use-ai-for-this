"""AppTest smoke tests for the Check page (BUILD_SPEC 10, Phase 2).

The app is driven through its real entry point, `app/main.py`, so the
`sys.path` bootstrap and `st.navigation` are exercised too.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from app.styles.tokens import APPROVAL_LABELS, STATUS_STYLES
from engine.models import ApprovalKind, Status
from engine.policy_parser import load_policy
from engine.rules import evaluate
from engine.scenarios import load_scenarios, scenario

ENTRYPOINT = str(Path(__file__).resolve().parent.parent / "app" / "main.py")
TIMEOUT = 30


def run_app(**query_params) -> AppTest:
    at = AppTest.from_file(ENTRYPOINT, default_timeout=TIMEOUT)
    for key, value in query_params.items():
        at.query_params[key] = value
    at.run()
    return at


def body(at: AppTest) -> str:
    """Everything the page rendered, with the stylesheet left out.

    The stylesheet is excluded deliberately: it contains numbers like `2.5rem`
    that would let an assertion about a clause id pass off a CSS value.
    """
    return "\n".join(
        [
            *(m.value for m in at.markdown),
            *(h.value for h in at.html if "<style>" not in h.value),
            *(c.value for c in at.code),
        ]
    )


def params_for(inputs) -> dict[str, str]:
    """Every input of a scenario as query parameters, so a link reproduces it."""
    params = {
        "data_class": inputs.data_class.value,
        "tool": inputs.tool.value,
        "activity": inputs.activity.value,
        "data_kind": inputs.data_kind.value,
    }
    for optional in ("host", "agent_action", "meeting_type"):
        value = getattr(inputs, optional)
        if value is not None:
            params[optional] = value.value
    for flag in (
        "human_review",
        "hiring",
        "sexual_or_intimate",
        "recipient_on_allowlist",
        "payee_on_allowlist",
        "within_caps",
        "training_or_finetuning",
        "client_contract_allows",
    ):
        value = getattr(inputs, flag)
        if value is not None:
            params[flag] = "1" if value else "0"
    return params


# --------------------------------------------------------------------------
# It renders at all
# --------------------------------------------------------------------------


def test_app_runs_without_exception():
    at = run_app()
    assert not at.exception


def test_hero_question_is_the_heading():
    at = run_app()
    assert "# Can I use AI for this?" in [m.value for m in at.markdown]


def test_three_main_inputs_are_present():
    at = run_app()
    labels = [w.label for w in at.segmented_control] + [w.label for w in at.selectbox]
    assert any("most sensitive" in label for label in labels)
    assert any("Which tool" in label for label in labels)
    assert any("What are you doing" in label for label in labels)


def test_footer_states_the_privacy_and_advice_disclaimers():
    at = run_app()
    page = body(at)
    assert "Nothing you enter is stored" in page
    assert "Model policy, not legal advice" in page
    # Read from the policy's front matter rather than pinned here, so the
    # assertion cannot pass while the footer shows a date the document dropped.
    checked = load_policy("v1_6").front_matter["Regulatory status checked"]
    assert f"Status checked {checked}" in page


def test_example_chips_are_offered_for_scenarios_2_4_and_8():
    at = run_app()
    keys = {button.key for button in at.button}
    assert {"cu_example_2", "cu_example_4", "cu_example_8"} <= keys


# --------------------------------------------------------------------------
# The verdict reaches the page
# --------------------------------------------------------------------------


def test_default_verdict_renders_a_status_word():
    at = run_app()
    words = {style.word for style in STATUS_STYLES.values()}
    assert any(word in body(at) for word in words)


@pytest.mark.parametrize("number", [2, 4, 8, 12, 20])
def test_query_params_reproduce_a_scenario_verdict(number):
    """BUILD_SPEC 1: every verdict has a URL that reproduces it."""
    example = scenario(number)
    at = run_app(**params_for(example.inputs))
    assert not at.exception

    expected = STATUS_STYLES[example.expect].word
    assert expected in body(at), f"scenario {number} should render {expected!r}"


def test_prohibited_scenario_shows_its_clause_and_offers_no_route():
    at = run_app(data_class="Confidential", tool="C", activity="drafting")
    page = body(at)
    assert STATUS_STYLES[Status.PROHIBITED].word in page
    assert "6.7" in page
    assert "Try instead" not in page


def test_not_permitted_scenario_offers_a_route():
    at = run_app(
        data_class="Internal", tool="self_hosted", host="personal_device", activity="drafting"
    )
    page = body(at)
    assert STATUS_STYLES[Status.NOT_PERMITTED].word in page
    assert "Try instead" in page
    assert "2.3" in page and "B.1.3" in page


def test_needs_approval_scenario_lists_requirements():
    at = run_app(
        data_class="Restricted", tool="A", activity="drafting", data_kind="hr_health_record"
    )
    page = body(at)
    assert STATUS_STYLES[Status.NEEDS_APPROVAL].word in page
    assert "What is required" in page
    assert "8.6" in page


def test_backed_by_badges_appear_for_a_clause_with_backing():
    """BUILD_SPEC 7: tapping a badge shows the source, status and date checked.

    The badge's own label lives on `st.popover`, which AppTest exposes as an
    unlabelled block, so this asserts on the detail the popover reveals.
    """
    at = run_app(data_class="Restricted", tool="A", activity="emotion_recognition")
    page = body(at)
    assert "Backed by" in page
    assert "EU AI Act, Article 5" in page
    assert "Applies to clause 6.1" in page
    assert "In force" in page
    assert "checked 2026-10-22" in page


def test_a_clause_with_no_backing_shows_no_badge_row():
    """8.10 has no crosswalk entry, so nothing should be claimed for it."""
    at = run_app(data_class="Public", tool="C", activity="drafting")
    assert "Backed by" not in body(at)


def test_copy_link_reproduces_the_current_choices():
    at = run_app(data_class="Secrets", tool="A", activity="coding")
    link = "\n".join(c.value for c in at.code)
    assert "data_class=Secrets" in link
    assert "tool=A" in link
    assert "activity=coding" in link


# --------------------------------------------------------------------------
# Interaction
# --------------------------------------------------------------------------


def test_changing_the_tool_changes_the_verdict():
    at = run_app(data_class="Confidential", tool="A", activity="drafting")
    assert STATUS_STYLES[Status.ALLOWED].word in body(at)

    tool = next(w for w in at.segmented_control if "Which tool" in w.label)
    tool.set_value("C").run()
    assert STATUS_STYLES[Status.PROHIBITED].word in body(at)


def test_example_chip_loads_that_scenario():
    at = run_app()
    at.button(key="cu_example_2").click().run()
    assert not at.exception
    assert STATUS_STYLES[Status.PROHIBITED].word in body(at)


def test_conditional_flags_appear_only_when_relevant():
    at = run_app(data_class="Internal", tool="A", activity="drafting")
    assert not [t for t in at.toggle if "overrule" in t.label]

    activity = next(w for w in at.selectbox if "What are you doing" in w.label)
    activity.set_value("decision_about_person").run()
    assert [t for t in at.toggle if "overrule" in t.label]


def test_switching_away_from_agent_drops_the_stale_agent_action():
    """A hidden field must not keep influencing the verdict."""
    at = run_app(data_class="Confidential", tool="A", activity="agent", agent_action="add_payee")
    assert STATUS_STYLES[Status.NOT_PERMITTED].word in body(at)

    activity = next(w for w in at.selectbox if "What are you doing" in w.label)
    activity.set_value("drafting").run()
    page = body(at)
    assert STATUS_STYLES[Status.ALLOWED].word in page
    assert "C.2" not in page


def test_unreadable_query_param_falls_back_instead_of_erroring():
    at = run_app(data_class="NotAClass", tool="banana", activity="drafting")
    assert not at.exception
    assert STATUS_STYLES[Status.ALLOWED].word in body(at)


# --------------------------------------------------------------------------
# Every scenario renders
# --------------------------------------------------------------------------


@pytest.mark.parametrize("example", load_scenarios(), ids=[f"{s.n:02d}" for s in load_scenarios()])
def test_every_scenario_renders_its_expected_status(example):
    """The engine's verdict and the page's verdict must not drift apart."""
    at = run_app(**params_for(example.inputs))
    assert not at.exception

    verdict = evaluate(example.inputs)
    assert verdict.status is example.expect
    page = body(at)
    assert STATUS_STYLES[example.expect].word in page
    if verdict.approval_kind is not ApprovalKind.NONE:
        assert APPROVAL_LABELS[verdict.approval_kind] in page


def test_pattern_backing_reads_as_english_not_a_raw_pattern():
    """`11.*` and `C.*` are how the crosswalk is stored, not what a visitor reads."""
    from app.components.basis_badges import _applies_to

    assert _applies_to("6.1") == "Applies to clause 6.1"
    assert _applies_to("11.*") == "Applies to the clauses in Section 11"
    assert _applies_to("C.*") == "Applies to Part C"
    assert _applies_to("*") == "Applies to the policy as a whole"


def test_agent_verdict_badge_does_not_show_a_raw_pattern():
    at = run_app(
        data_class="Internal",
        tool="A",
        activity="agent",
        agent_action="message_external",
        recipient_on_allowlist="1",
        within_caps="1",
    )
    page = body(at)
    assert "Applies to the clauses in Section 11" in page
    assert "Applies to clause 11.*" not in page


# --------------------------------------------------------------------------
# Demo mode (BUILD_SPEC 10, Phase 5)
# --------------------------------------------------------------------------


def test_demo_mode_preloads_scenario_2():
    at = run_app(demo="1")
    assert not at.exception
    page = body(at)
    assert STATUS_STYLES[Status.PROHIBITED].word in page
    assert "6.7" in page


def test_demo_mode_leaves_the_page_usable_afterwards():
    """It loads once, so a recording can keep clicking without snapping back."""
    at = run_app(demo="1")
    tool = next(w for w in at.segmented_control if "Which tool" in w.label)
    tool.set_value("A").run()
    assert STATUS_STYLES[Status.PROHIBITED].word not in body(at)


def test_without_demo_the_defaults_load():
    at = run_app()
    assert STATUS_STYLES[Status.ALLOWED].word in body(at)


# --- Streamlit chrome -------------------------------------------------- #
#
# Regression guard. `st.navigation(position="top")` renders the page nav
# inside [data-testid="stToolbar"], which is itself inside
# header[data-testid="stHeader"]. Hiding either ancestor to tidy away
# Streamlit's chrome also hides the nav, leaving the deployed app with no
# way to reach five of its six pages — and it does so silently, because the
# header still occupies its 60px and nothing errors. This has already been
# shipped once. Each chrome element must therefore be named individually.

CHROME_ANCESTORS_OF_THE_NAV = ('[data-testid="stToolbar"]', 'header[data-testid="stHeader"]')


def _hide_rule_selectors() -> list[str]:
    """The selectors of every rule in app.css whose body is `display: none`."""
    from app.components.shell import CSS_FILE

    css = CSS_FILE.read_text(encoding="utf-8")
    # Strip comments so a selector mentioned in prose is not mistaken for code.
    without_comments = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)

    selectors: list[str] = []
    for block in re.finditer(r"([^{}]+)\{([^{}]*)\}", without_comments):
        head, declarations = block.group(1), block.group(2)
        if re.search(r"display\s*:\s*none", declarations):
            selectors.extend(part.strip() for part in head.split(",") if part.strip())
    return selectors


@pytest.mark.parametrize("ancestor", CHROME_ANCESTORS_OF_THE_NAV)
def test_css_never_hides_an_ancestor_of_the_page_nav(ancestor: str) -> None:
    hidden = _hide_rule_selectors()
    assert ancestor not in hidden, (
        f"app.css hides {ancestor} outright, which also hides the page nav "
        f"rendered inside it. Name the individual chrome elements instead "
        f"(stMainMenu, stAppDeployButton, stStatusWidget, stDecoration)."
    )


def test_the_nav_compactness_rule_targets_the_top_nav() -> None:
    """The top nav renders stTopNavLink; stSidebarNavLink never matches."""
    from app.components.shell import CSS_FILE

    css = CSS_FILE.read_text(encoding="utf-8")
    without_comments = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)
    assert "stTopNavLink" in without_comments, "nothing styles the top nav links"
