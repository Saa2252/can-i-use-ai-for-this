"""AppTest smoke tests for the Check page (BUILD_SPEC 10, Phase 2).

The app is driven through its real entry point, `app/main.py`, so the
`sys.path` bootstrap and `st.navigation` are exercised too.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from app.components.shell import escape
from app.styles.tokens import APPROVAL_LABELS, STATUS_STYLES
from engine.models import ApprovalKind, Status, Tool
from engine.policy_parser import load_policy
from engine.rules import evaluate, load_rules
from engine.scenarios import load_scenarios, scenario

#: The four answers the guess buttons offer, in severity order.
CHOICES = (Status.ALLOWED, Status.NEEDS_APPROVAL, Status.NOT_PERMITTED, Status.PROHIBITED)

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


def open_slot(at: AppTest, field: str) -> AppTest:
    """Tap the part of the sentence that holds `field`, revealing its options."""
    return at.button(key=f"cu_slot_{field}").click().run()


def choose(at: AppTest, field: str, value: str) -> AppTest:
    """Open a slot and pick one of its options, as a visitor would."""
    if not [b for b in at.button if b.key == f"cu_opt_{field}_{value}"]:
        at = open_slot(at, field)
    return at.button(key=f"cu_opt_{field}_{value}").click().run()


def load_example(at: AppTest, number: int, guess: str | None = None) -> AppTest:
    """Tap an example card and get past the guess it asks for."""
    at = at.button(key=f"cu_example_{number}").click().run()
    key = f"cu_guess_{guess}" if guess else "cu_guess_skip"
    return at.button(key=key).click().run()


# --------------------------------------------------------------------------
# It renders at all
# --------------------------------------------------------------------------


def test_app_runs_without_exception():
    at = run_app()
    assert not at.exception


def test_hero_question_is_the_heading():
    at = run_app()
    assert "# Can I use AI for this?" in [m.value for m in at.markdown]


def test_the_question_is_one_sentence_with_three_changeable_parts():
    """Phase 5 replaced the form with a sentence. The three answers the engine
    cannot do without are the three chips in it."""
    at = run_app()
    keys = {button.key for button in at.button}
    assert {"cu_slot_activity", "cu_slot_data_class", "cu_slot_tool"} <= keys

    sentence = body(at)
    assert "I want to" in sentence
    assert "using" in sentence


def test_a_slot_opens_its_options_and_nothing_else():
    at = open_slot(run_app(), "tool")
    opened = {b.key for b in at.button if b.key and b.key.startswith("cu_opt_")}
    assert opened == {f"cu_opt_tool_{tool.value}" for tool in Tool}


def test_the_page_opens_with_no_slot_open():
    """The sentence is the answer's question, not a list of menus: a visitor
    arrives at a verdict, and opens a part only when they want to change it."""
    at = run_app()
    assert not [b for b in at.button if b.key and b.key.startswith("cu_opt_")]


def test_footer_states_the_privacy_and_advice_disclaimers():
    at = run_app()
    page = body(at)
    assert "Nothing you enter is stored" in page
    assert "Model policy, not legal advice" in page
    # Read from the policy's front matter rather than pinned here, so the
    # assertion cannot pass while the footer shows a date the document dropped.
    checked = load_policy("v1_6").front_matter["Regulatory status checked"]
    assert f"Status checked {checked}" in page


#: Phase 2 replaced three chips with six, chosen so that each lands in a
#: different part of the policy: a tool question, a decision about a person,
#: an agent, a prohibited practice, confidentiality, and a secret.
EXAMPLE_SCENARIOS = (2, 5, 8, 13, 19, 12)


def test_an_example_chip_is_offered_for_each_of_the_six_scenarios():
    at = run_app()
    keys = {button.key for button in at.button}
    assert {f"cu_example_{n}" for n in EXAMPLE_SCENARIOS} <= keys


def test_the_example_chips_do_not_all_give_the_same_answer():
    """Six examples that land on one verdict teach that the answer is always
    no. They have to disagree with each other to be worth tapping."""
    statuses = {evaluate(scenario(n).inputs, "v1_6").status for n in EXAMPLE_SCENARIOS}
    assert len(statuses) > 1, f"all six examples are {statuses}"


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

    at = choose(at, "tool", "C")
    assert STATUS_STYLES[Status.PROHIBITED].word in body(at)


def test_example_card_loads_that_scenario():
    at = load_example(run_app(), 2)
    assert not at.exception
    assert STATUS_STYLES[Status.PROHIBITED].word in body(at)


def test_conditional_flags_appear_only_when_relevant():
    at = run_app(data_class="Internal", tool="A", activity="drafting")
    assert not [t for t in at.toggle if "overrule" in t.label]

    at = choose(at, "activity", "decision_about_person")
    assert [t for t in at.toggle if "overrule" in t.label]


def test_switching_away_from_agent_drops_the_stale_agent_action():
    """A hidden field must not keep influencing the verdict."""
    at = run_app(data_class="Confidential", tool="A", activity="agent", agent_action="add_payee")
    assert STATUS_STYLES[Status.NOT_PERMITTED].word in body(at)

    at = choose(at, "activity", "drafting")
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
    at = choose(run_app(demo="1"), "tool", "A")
    assert STATUS_STYLES[Status.PROHIBITED].word not in body(at)


def test_a_bare_visit_opens_on_an_answer_not_on_empty_defaults():
    """BUILD_SPEC 1, tightened in Phase 2: a visitor who arrives with nothing
    in the URL gets a loaded situation and its verdict, not four blank
    questions and a safe-looking default."""
    at = run_app()
    opening = evaluate(scenario(2).inputs, "v1_6")
    assert opening.status is Status.PROHIBITED, "the opening example should be worth seeing"
    assert STATUS_STYLES[opening.status].word in body(at)


def test_a_shared_link_still_beats_the_opening_example():
    """Opening on an example must never overwrite an answer someone sent."""
    allowed = next(
        s for s in load_scenarios() if evaluate(s.inputs, "v1_6").status is Status.ALLOWED
    )
    at = run_app(**params_for(allowed.inputs))
    assert STATUS_STYLES[Status.ALLOWED].word in body(at)


def test_the_answer_sits_directly_under_the_sentence():
    """Phase 5: the verdict is the next thing after the line that produced it,
    and the further questions come after the answer, not before it."""
    at = run_app()
    rendered = [h.value for h in at.html if "<style>" not in h.value]
    sentence = next(i for i, value in enumerate(rendered) if "I want to" in value)
    verdict = next(i for i, value in enumerate(rendered) if "cu-status" in value)
    assert sentence < verdict

    detail = [e for e in at.expander if e.label == "More detail"]
    assert detail, "the client-contract example turns on training and fine-tuning"


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


# --------------------------------------------------------------------------
# No visitor ever sees a traceback (Phase 1)
# --------------------------------------------------------------------------

#: Every registered page, by the script path `st.navigation` knows it by.
#: Read from `app/main.py` so a page added later is covered without an edit
#: here — a test that lists pages by hand stops testing the ones you forget.
ALL_PAGES: list[str] = re.findall(
    r'st\.Page\(\s*"([^"]+)"',
    (Path(__file__).resolve().parent.parent / "app" / "main.py").read_text(encoding="utf-8"),
)


def test_every_registered_page_is_discovered() -> None:
    """Guards the regex above: if it silently matched nothing, so would the
    parametrized test below, and an empty sweep passes."""
    assert len(ALL_PAGES) == 7, ALL_PAGES


@pytest.mark.parametrize("page", ALL_PAGES)
def test_every_page_loads_clean_with_no_query_params(page: str) -> None:
    """A visitor arriving at a bare URL sees the page, never a traceback."""
    at = AppTest.from_file(ENTRYPOINT, default_timeout=TIMEOUT)
    at.run()
    at.switch_page(page)
    at.run()
    assert not at.exception, f"{page} raised: {[e.message for e in at.exception]}"


#: Clicking the chosen chip of an `st.segmented_control` again deselects it,
#: setting the session value to None. Both of the Check page's segmented
#: controls back a field pydantic requires.
CLEARABLE = {"data_class": "a data class", "tool": "a tool"}


@pytest.mark.parametrize("key,name", sorted(CLEARABLE.items()))
def test_clearing_a_required_input_asks_instead_of_crashing(key: str, name: str) -> None:
    at = run_app()
    assert not at.exception

    at.session_state[key] = None
    at.run()

    assert not at.exception, (
        f"clearing {key} raised {[e.message for e in at.exception]}. A visitor "
        f"deselects a chip by clicking it; that must never reach pydantic."
    )
    assert f"Pick {name} to see the answer" in body(at)


def test_the_prompt_names_every_cleared_input() -> None:
    at = run_app()
    at.session_state["data_class"] = None
    at.session_state["tool"] = None
    at.run()

    assert not at.exception
    assert "Pick a data class and a tool to see the answer" in body(at)


def test_a_cleared_input_is_left_out_of_the_share_link() -> None:
    """A link carrying `tool=None` would decode to the default on arrival,
    which silently answers a question the sender never answered."""
    at = run_app()
    at.session_state["tool"] = None
    at.run()

    assert "tool" not in at.query_params
    assert at.query_params.get("data_class") is not None


def test_no_pages_directory_sits_beside_the_entry_script() -> None:
    """A `pages/` folder next to the entry script silently disables it.

    Streamlit sets `PagesManager.uses_pages_directory` from whether that
    folder exists, and when it does, the script runner calls `_mpa_v1(...)`
    *in lieu of* the main script. The sys.path bootstrap at the top of
    `app/main.py` never runs, and every page's `import app...` raises
    ModuleNotFoundError.

    It hides well: the first visitor to the root runs main.py as the v1 home
    page, which calls `st.navigation` and flips the process to v2 for good.
    Only a deep link opened as the first request after a cold start fails —
    and then keeps failing for everyone until someone loads the root.
    """
    beside = Path(ENTRYPOINT).resolve().parent / "pages"
    assert not beside.exists(), (
        f"{beside} exists. Streamlit will run that folder's scripts instead "
        f"of app/main.py on a cold start, skipping the sys.path bootstrap. "
        f"The page scripts live in views/ for this reason."
    )


@pytest.mark.parametrize("page", ALL_PAGES)
def test_every_registered_page_script_exists(page: str) -> None:
    """Catches a rename that updated the folder but not the registration."""
    script = Path(ENTRYPOINT).resolve().parent / page
    assert script.is_file(), f"app/main.py registers {page}, which is not on disk"


# --------------------------------------------------------------------------
# The verdict card explains itself (Phase 3)
# --------------------------------------------------------------------------


def test_the_chip_row_is_the_clauses_that_decided_it() -> None:
    """Seven chips of equal weight hide the one doing the work."""
    at = run_app(**params_for(scenario(2).inputs))
    verdict = evaluate(scenario(2).inputs, "v1_6")
    page = body(at)

    assert "What decided it" in page
    assert len(verdict.decisive_clauses) < len(verdict.clauses), (
        "this scenario is a poor test if everything is decisive"
    )
    # The drawer's heading is an expander label, which `body` does not collect.
    assert any(f"All {len(verdict.clauses)} clauses in full" in e.label for e in at.expander)
    assert f"{len(verdict.clauses) - len(verdict.decisive_clauses)} more clauses" in page


def test_what_if_chips_offer_a_way_out_of_a_prohibited_answer() -> None:
    at = run_app(**params_for(scenario(2).inputs))
    page = body(at)
    assert "What if" in page
    # Scenario 2 is the client contract in a personal account: both the data
    # class and the tool are one change away from an answer that is not no.
    assert STATUS_STYLES[Status.ALLOWED].word in page


def test_the_card_does_not_ask_why_it_is_not_stricter_than_prohibited() -> None:
    at = run_app(**params_for(scenario(2).inputs))
    assert evaluate(scenario(2).inputs, "v1_6").status is Status.PROHIBITED
    assert not any("Why is this not" in e.label for e in at.expander)


def test_an_allowed_answer_says_what_would_have_made_it_stricter() -> None:
    at = run_app(data_class="Internal", data_kind="none", tool="A", activity="drafting")
    assert any("Why is this not" in e.label for e in at.expander), (
        "an answer with stricter rules above it should say what they wanted"
    )


# --------------------------------------------------------------------------
# Phase 5: the sentence, the trail, the route, the guess
# --------------------------------------------------------------------------


def test_the_data_question_is_gone_and_its_examples_are_under_the_options() -> None:
    """Phase 5 removed "Does it involve personal or client information?". The
    worked cases it carried move under the data options, in the rules' own
    words, so nothing the policy says was lost with the dropdown."""
    at = run_app()
    labels = [w.label for w in at.selectbox]
    assert not any("personal or client information" in label for label in labels)

    at = open_slot(at, "data_class")
    page = body(at)
    for rule_id in ("note_client_information", "note_sensitive_personal_data"):
        rule = next(r for r in load_rules("v1_6") if r.id == rule_id)
        # The page escapes its own HTML, so the apostrophes differ.
        assert escape(rule.reason) in page


def test_the_data_kind_still_travels_with_a_scenario_even_though_nobody_asks() -> None:
    """Removing the question must not change a single verdict. The value
    still arrives from a link or an example and still reaches the engine."""
    at = run_app(**params_for(scenario(2).inputs))
    expected = evaluate(scenario(2).inputs, "v1_6")
    page = body(at)
    assert STATUS_STYLES[expected.status].word in page
    for clause in expected.decisive_clauses:
        assert clause in page
    assert at.query_params.get("data_kind") == "client_info"


def test_a_change_nobody_can_make_is_never_offered() -> None:
    """`data_kind` is carried, not asked, so it must not appear as a what-if:
    a chip proposing a change with no control behind it is a dead end."""
    at = run_app(**params_for(scenario(2).inputs))
    assert "it involved" not in body(at)


def test_the_card_says_what_is_at_stake_and_what_to_do_next() -> None:
    at = run_app(**params_for(scenario(2).inputs))
    verdict = evaluate(scenario(2).inputs, "v1_6")
    page = body(at)
    assert "Why it matters" in page
    assert verdict.why_it_matters in page
    assert "Do this next" in page
    assert verdict.next_step in page


def test_the_trail_shows_four_gates_and_names_the_one_that_stopped_it() -> None:
    at = run_app(**params_for(scenario(2).inputs))
    page = body(at)
    assert "How it got here" in page
    for name in ("Hard line", "Data and tool", "Approval", "Output checks"):
        assert name in page
    assert "failed" in page
    assert "not reached" in page


def test_a_blocked_answer_offers_the_smallest_change_that_fixes_it() -> None:
    at = run_app(**params_for(scenario(2).inputs))
    assert "Show me the safe way" in body(at)

    at = at.button(key="cu_safe_way").click().run()
    assert not at.exception
    assert STATUS_STYLES[Status.ALLOWED].word in body(at)
    assert at.query_params["tool"] == "A"


def test_a_hard_line_is_told_plainly_and_offered_nothing() -> None:
    """Scenario 13 is emotion recognition: Section 6 rules out the activity,
    so a row of "it would be allowed if…" chips would read as a workaround."""
    at = run_app(**params_for(scenario(13).inputs))
    page = body(at)
    assert "No route: this is a hard line." in page
    assert "What if" not in page
    assert not [b for b in at.button if b.key == "cu_safe_way"]


def test_an_allowed_answer_is_offered_no_route_at_all() -> None:
    at = run_app(data_class="Public", tool="A", activity="drafting")
    assert STATUS_STYLES[Status.ALLOWED].word in body(at)
    assert "Show me the safe way" not in body(at)


def test_tapping_an_example_asks_before_it_tells() -> None:
    at = run_app().button(key="cu_example_19").click().run()
    page = body(at)
    assert "Guess first" in page
    assert scenario(19).title in page
    # The answer is not on screen yet, and neither is the sentence.
    assert "I want to" not in page
    assert {f"cu_guess_{status.value}" for status in CHOICES} <= {b.key for b in at.button}


def test_the_guess_is_marked_without_any_statistics() -> None:
    at = run_app().button(key="cu_example_19").click().run()
    at = at.button(key="cu_guess_PROHIBITED").click().run()

    page = body(at)
    assert evaluate(scenario(19).inputs, "v1_6").status is Status.NEEDS_APPROVAL
    assert "Not quite" in page
    assert "You said Prohibited" in page
    assert "%" not in page


def test_a_right_guess_says_so() -> None:
    at = run_app().button(key="cu_example_13").click().run()
    at = at.button(key="cu_guess_PROHIBITED").click().run()
    assert "You had it" in body(at)


def test_the_loaded_example_is_marked_and_the_others_are_not() -> None:
    at = load_example(run_app(), 19)
    marked = [
        b.label for b in at.button if b.key and b.key.startswith("cu_example_") and "✓" in b.label
    ]
    assert marked == ["Legal meeting ✓"]


def test_no_card_is_marked_while_a_guess_is_pending() -> None:
    """The question on screen is a different scenario from the one loaded."""
    at = run_app().button(key="cu_example_19").click().run()
    assert not [
        b for b in at.button if b.key and b.key.startswith("cu_example_") and "✓" in b.label
    ]


def test_the_answer_is_repeated_at_the_foot_of_a_narrow_screen() -> None:
    """The picker fills a phone, which is when the answer is most wanted."""
    at = run_app(**params_for(scenario(2).inputs))
    sticky = [h.value for h in at.html if "cu-sticky" in h.value and "<style>" not in h.value]
    assert sticky, "no pinned answer was rendered"
    assert STATUS_STYLES[Status.PROHIBITED].word in sticky[0]


def test_more_detail_is_absent_when_nothing_turns_on_it() -> None:
    """The row appears only when this combination has a further question. An
    empty "More detail" invites a visitor to look for something not there."""
    at = run_app(data_class="Internal", tool="A", activity="drafting")
    assert not [e for e in at.expander if e.label == "More detail"]

    at = run_app(**params_for(scenario(19).inputs))
    assert [e for e in at.expander if e.label == "More detail"]
