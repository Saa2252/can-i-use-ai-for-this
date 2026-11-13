"""The Check page's inputs, and their two-way sync with `st.query_params`.

Order is Data -> Tool -> Activity (BUILD_SPEC 9.1), with the conditional flags
shown only when they can change the answer (BUILD_SPEC 5).

Sync works by seeding `st.session_state` from the URL *before* the widgets are
created. A widget's `default=` loses to a seeded session value, so seeding is
the only way a shared link reproduces its verdict.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

import streamlit as st

from app.components.shell import escape
from engine.models import (
    Activity,
    AgentAction,
    DataClass,
    DataKind,
    Host,
    Inputs,
    MeetingType,
    Tool,
)

SEEDED_FLAG = "_cu_seeded"


# --------------------------------------------------------------------------
# Field registry
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Field:
    """One input, its query-parameter name and how it round-trips."""

    key: str
    enum: type[StrEnum] | None
    default: Any


FIELDS: tuple[Field, ...] = (
    Field("data_class", DataClass, DataClass.INTERNAL),
    Field("data_kind", DataKind, DataKind.NONE),
    Field("tool", Tool, Tool.TIER_A),
    Field("host", Host, Host.ORG_CLOUD),
    Field("activity", Activity, Activity.DRAFTING),
    Field("human_review", None, True),
    Field("hiring", None, False),
    Field("training_or_finetuning", None, False),
    Field("client_contract_allows", None, False),
    Field("sexual_or_intimate", None, False),
    Field("agent_action", AgentAction, AgentAction.READ),
    Field("recipient_on_allowlist", None, True),
    Field("payee_on_allowlist", None, True),
    Field("within_caps", None, True),
    Field("meeting_type", MeetingType, MeetingType.ORDINARY),
)

BY_KEY = {field.key: field for field in FIELDS}

#: Every query parameter that carries an answer, so a caller can tell a shared
#: verdict link from a bare visit and decide what to open on.
INPUT_KEYS: frozenset[str] = frozenset(field.key for field in FIELDS)

#: The three inputs the engine cannot answer without. They are not guaranteed
#: to hold a value: `st.segmented_control` clears itself when its chosen chip
#: is clicked again, so a visitor can empty an answer at any time.
REQUIRED_KEYS: tuple[str, ...] = ("data_class", "tool", "activity")

#: How each required input is named when it is the one still missing.
REQUIRED_LABELS: dict[str, str] = {
    "data_class": "a data class",
    "tool": "a tool",
    "activity": "an activity",
}


def missing_required() -> list[str]:
    """The required inputs with no value right now, in the order they are asked."""
    return [key for key in REQUIRED_KEYS if st.session_state.get(key) is None]


def missing_prompt(missing: list[str]) -> str:
    """The sentence shown in place of a verdict, named for what is unset."""
    names = [REQUIRED_LABELS[key] for key in missing]
    if not names:
        return "Pick an answer above to see the verdict."
    if len(names) > 1:
        names = [", ".join(names[:-1]) + " and " + names[-1]]
    return f"Pick {names[0]} to see the answer."


# --------------------------------------------------------------------------
# Labels
# --------------------------------------------------------------------------

#: Plain English first, the policy's own term after it, because the term is
#: what the clauses, the Matrix and a colleague will say. The term cannot be
#: set in smaller grey type: a segmented control renders its label through a
#: markdown container that strips colour directives, so `:gray[...]` comes
#: out as plain text. The separator carries the distinction instead.
#:
#: Only the classes this policy defines are glossed. 7.4 defines Restricted
#: outright and 6.3 names what a secret is, so those glosses are the clause's
#: own examples. Public and Internal are set by the organization's external
#: Data Classification Standard (7.5), so inventing examples for them here
#: would be this app writing policy (BUILD_SPEC 0.1). They stay bare, and the
#: key below the form says where they come from.
DATA_CLASS_LABELS = {
    DataClass.PUBLIC: "Public",
    DataClass.INTERNAL: "Internal",
    DataClass.CONFIDENTIAL: "Client or HR information · Confidential",
    DataClass.RESTRICTED: "Health, ID or payment data · Restricted",
    DataClass.SECRETS: "Passwords & keys · Secrets",
}

#: Worked examples drawn from 7.4, 7.5 and B.2.3, so the control teaches
#: the classification rather than assuming the visitor knows it.
DATA_KIND_LABELS = {
    DataKind.NONE: "Nothing personal, and no client information",
    DataKind.ORDINARY_PERSONAL: "A colleague's name or work email (7.5)",
    DataKind.SENSITIVE_PERSONAL: "Sensitive personal data: health, biometric, ID (7.4)",
    DataKind.HR_HEALTH_RECORD: "An HR record with health data, e.g. sick leave (7.5)",
    DataKind.CLIENT_INFO: "A client's name or non-public client info (B.2.3)",
}

#: Same pattern, from B.1.1 to B.1.3: assessed and approved, vetted with gaps,
#: not assessed at all, and a model the organization runs itself.
TOOL_LABELS = {
    Tool.TIER_A: "Company-approved AI · Tier A",
    Tool.TIER_B: "Vetted, with gaps · Tier B",
    Tool.TIER_C: "Personal or free AI · Tier C",
    Tool.SELF_HOSTED: "A model we run ourselves · Self-hosted",
}

HOST_LABELS = {
    Host.ORG_CLOUD: "Our servers or our cloud tenancy",
    Host.MANAGED_LAPTOP: "A managed company laptop",
    Host.PERSONAL_DEVICE: "A personal or unmanaged device",
}

ACTIVITY_LABELS = {
    Activity.DRAFTING: "Drafting, summarizing or research",
    Activity.CODING: "Coding help",
    Activity.DECISION_ABOUT_PERSON: "A decision about a person",
    Activity.CHATBOT: "Customer- or public-facing chatbot",
    Activity.PUBLISHING: "Publishing AI content externally",
    Activity.SYNTHETIC_MEDIA: "Synthetic media of a real person",
    Activity.MONITORING_EMPLOYEES: "Monitoring or evaluating employees",
    Activity.EMOTION_RECOGNITION: "Emotion recognition (staff or students)",
    Activity.FATIGUE_DETECTION: "Fatigue or safety detection",
    Activity.SAFETY_CRITICAL: "Safety-critical or clinical operations",
    Activity.CONNECTING_SYSTEMS: "Connecting AI to an internal system",
    Activity.NOTETAKER: "An AI meeting notetaker",
    Activity.AGENT: "An AI agent that takes actions",
}

AGENT_ACTION_LABELS = {
    AgentAction.READ: "Read only",
    AgentAction.WRITE: "Write or change records",
    AgentAction.PAY: "Make a payment",
    AgentAction.DELETE: "Delete something",
    AgentAction.MESSAGE_EXTERNAL: "Send a message outside the org",
    AgentAction.PRODUCTION_CHANGE: "Change a production system",
    AgentAction.ADD_PAYEE: "Add a payee to its own allowlist",
    AgentAction.ADD_RECIPIENT: "Add a recipient to its own allowlist",
}

MEETING_TYPE_LABELS = {
    MeetingType.ORDINARY: "An ordinary meeting",
    MeetingType.LEGAL_COUNSEL: "A meeting with legal counsel",
    MeetingType.HR_CASEWORK: "HR disciplinary, grievance or medical",
    MeetingType.BOARD_EXEC: "A board executive session",
    MeetingType.UNDISCLOSED_DEAL: "A meeting about an undisclosed transaction",
}


# --------------------------------------------------------------------------
# Query-parameter sync
# --------------------------------------------------------------------------


def _decode(field: Field, raw: str) -> Any | None:
    """Turn one query-parameter string into a value, or None if unusable."""
    if field.enum is not None:
        try:
            return field.enum(raw)
        except ValueError:
            return None
    lowered = raw.strip().lower()
    if lowered in {"1", "true", "yes"}:
        return True
    if lowered in {"0", "false", "no"}:
        return False
    return None


def _encode(value: Any) -> str:
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, StrEnum):
        return value.value
    return str(value)


def seed_from_query_params() -> None:
    """Seed widget state from the URL, once per session.

    An unreadable or unknown value falls back to the field's default rather
    than erroring, so a hand-edited link still renders something.
    """
    if st.session_state.get(SEEDED_FLAG):
        return
    params = st.query_params
    for field in FIELDS:
        value = None
        if field.key in params:
            value = _decode(field, params[field.key])
        st.session_state[field.key] = field.default if value is None else value
    st.session_state[SEEDED_FLAG] = True


def write_query_params(visible_keys: list[str]) -> None:
    """Write the visible inputs back to the URL.

    Only what is on screen is written, so a shared link carries the question
    that was actually asked and nothing stale behind it.
    """
    st.query_params.from_dict(
        {
            key: _encode(st.session_state[key])
            for key in visible_keys
            if st.session_state[key] is not None
        }
    )


def share_url(visible_keys: list[str]) -> str:
    """A URL that reproduces this verdict."""
    query = "&".join(
        f"{key}={_encode(st.session_state[key])}"
        for key in visible_keys
        if st.session_state[key] is not None
    )
    try:
        base = (st.context.url or "").split("?")[0]
    except Exception:  # noqa: BLE001 - no browser context, e.g. under AppTest
        base = ""
    return f"{base}?{query}" if base else f"?{query}"


def apply_example(example_inputs: Inputs) -> None:
    """Load a scenario into the widgets. Call before any widget is created."""
    for field in FIELDS:
        value = getattr(example_inputs, field.key)
        st.session_state[field.key] = field.default if value is None else value
    st.session_state[SEEDED_FLAG] = True


# --------------------------------------------------------------------------
# The sentence
# --------------------------------------------------------------------------

#: Which slot of the sentence is open, if any. Nothing is open on arrival,
#: so the page opens on its answer rather than on a list of options.
OPEN_SLOT = "_cu_open_slot"

#: Each activity as a verb phrase, and the preposition that carries the data
#: after it. "I want to {verb} {preposition} {data} using {tool}." The
#: preposition is per activity because English does not have one that fits
#: drafting, deciding and connecting a system all at once.
ACTIVITY_SENTENCE: dict[Activity, tuple[str, str]] = {
    Activity.DRAFTING: ("draft or summarize", ""),
    Activity.CODING: ("write or review code", "with"),
    Activity.DECISION_ABOUT_PERSON: ("make a decision about a person", "from"),
    Activity.CHATBOT: ("run a customer-facing chatbot", "on"),
    Activity.PUBLISHING: ("publish AI content externally", "from"),
    Activity.SYNTHETIC_MEDIA: ("create synthetic media of a real person", "from"),
    Activity.MONITORING_EMPLOYEES: ("monitor or evaluate employees", "from"),
    Activity.EMOTION_RECOGNITION: ("detect emotion in staff or students", "from"),
    Activity.FATIGUE_DETECTION: ("detect fatigue for safety", "from"),
    Activity.SAFETY_CRITICAL: ("run a safety-critical or clinical process", "on"),
    Activity.CONNECTING_SYSTEMS: ("connect AI to an internal system", "holding"),
    Activity.NOTETAKER: ("take AI meeting notes", "covering"),
    Activity.AGENT: ("let an AI agent take actions", "on"),
}

#: The data classes as the sentence says them. The policy's own term is on
#: the option in the picker, not in the sentence, where it would turn a
#: readable line into a classification exercise.
DATA_SENTENCE: dict[DataClass, str] = {
    DataClass.PUBLIC: "public information",
    DataClass.INTERNAL: "internal information",
    DataClass.CONFIDENTIAL: "client or HR information",
    DataClass.RESTRICTED: "health, ID or payment data",
    DataClass.SECRETS: "passwords or keys",
}

TOOL_SENTENCE: dict[Tool, str] = {
    Tool.TIER_A: "a company-approved tool",
    Tool.TIER_B: "a vetted tool with gaps",
    Tool.TIER_C: "a personal or free AI account",
    Tool.SELF_HOSTED: "a model we run ourselves",
}

#: The three slots, in sentence order: the session key, the enum, the label
#: the picker gets, and the map from value to the words used on an option.
SLOTS: tuple[tuple[str, type[StrEnum], str, dict], ...] = (
    ("activity", Activity, "What do you want to do?", ACTIVITY_LABELS),
    ("data_class", DataClass, "What is the most sensitive thing involved?", DATA_CLASS_LABELS),
    ("tool", Tool, "Which tool?", TOOL_LABELS),
)

#: The classification notes whose own wording becomes the help under the data
#: options. Taking the sentences from the rules means the guidance under the
#: picker and the note on the verdict card cannot drift apart, and that the
#: app is quoting the rulebook rather than describing it.
DATA_HELP_RULES: tuple[str, ...] = (
    "note_client_information",
    "note_sensitive_personal_data",
    "note_hr_health_record",
    "note_ordinary_personal_data",
)


def open_slot() -> str | None:
    return st.session_state.get(OPEN_SLOT)


def _toggle_slot(name: str) -> None:
    st.session_state[OPEN_SLOT] = None if st.session_state.get(OPEN_SLOT) == name else name


def _choose(field: str, value: Any) -> None:
    """Pick an option. The picker stays open, so several can be tried in turn
    while the verdict below (or the bar at the foot of a phone) keeps up."""
    st.session_state[field] = value


def close_slots() -> None:
    st.session_state[OPEN_SLOT] = None


def sentence_parts() -> tuple[str, str, str, str]:
    """The four pieces of the sentence: verb, preposition, data, tool."""
    activity = st.session_state.get("activity")
    data_class = st.session_state.get("data_class")
    tool = st.session_state.get("tool")
    verb, preposition = ACTIVITY_SENTENCE.get(activity, ("do something", "with"))
    return (
        verb if activity is not None else "…",
        preposition,
        DATA_SENTENCE.get(data_class, "…"),
        TOOL_SENTENCE.get(tool, "…"),
    )


def render_sentence() -> None:
    """The question as one sentence, each answer a chip that opens its options.

    Each connecting word is bound to the chip it introduces, in a container
    of its own, so a narrow screen breaks the line between phrases rather
    than between "using" and the tool it belongs to. At 375px the sentence
    becomes three lines that still read downwards as one.
    """
    verb, preposition, data, tool = sentence_parts()

    parts = (
        ("I want to", verb, "cu_slot_activity", "Change what you are doing"),
        (preposition, data, "cu_slot_data_class", "Change the data involved"),
        ("using", tool, "cu_slot_tool", "Change the tool"),
    )

    with st.container(horizontal=True, gap="small", vertical_alignment="center", key="cu_sentence"):
        for lead, label, key, tip in parts:
            with st.container(
                horizontal=True,
                gap="small",
                vertical_alignment="center",
                width="content",
                key=f"cu_said_{key}",
            ):
                if lead:
                    st.html(f'<span class="cu-say">{escape(lead)}</span>', width="content")
                st.button(
                    label,
                    key=key,
                    on_click=_toggle_slot,
                    args=(key.removeprefix("cu_slot_"),),
                    help=tip,
                )

    if open_slot() is None:
        st.html('<p class="cu-hint">Tap any underlined part to change it.</p>')


def render_picker(version: str) -> None:
    """The options for whichever slot is open."""
    opened = open_slot()
    if opened is None:
        return

    field, enum, label, labels = next(slot for slot in SLOTS if slot[0] == opened)
    chosen = st.session_state.get(field)

    st.html(f'<p class="cu-label">{escape(label)}</p>')
    with st.container(horizontal=True, gap="small", key=f"cu_picker_{field}"):
        for value in enum:
            st.button(
                labels[value],
                key=f"cu_opt_{field}_{value.value}",
                on_click=_choose,
                args=(field, value),
                type="tertiary" if value == chosen else "secondary",
            )

    if field in {"data_class", "tool"}:
        st.html(
            '<p class="cu-meta">Colour here is how restricted the option is under '
            "the 7.1 grid, not the answer. The answer is below.</p>"
        )
    if field == "data_class":
        _render_data_help(version)


def _render_data_help(version: str) -> None:
    """What counts as what, in the rules' own words.

    This is the question the picker used to ask outright. Four worked cases
    answer it better than a dropdown did, and they are the text of the four
    classification notes, so nothing here is written twice.
    """
    from engine.rules import load_rules

    by_id = {rule.id: rule for rule in load_rules(version)}
    rows = []
    for rule_id in DATA_HELP_RULES:
        rule = by_id.get(rule_id)
        if rule is None:
            continue
        cites = escape(", ".join(rule.clauses))
        rows.append(f'<li>{escape(rule.reason)} <span class="cu-cite">{cites}</span></li>')
    if rows:
        st.html(
            '<p class="cu-label">Which one is it?</p>'
            f'<ul class="cu-list cu-list--help">{"".join(rows)}</ul>'
        )


# --------------------------------------------------------------------------
# More detail
# --------------------------------------------------------------------------


def render_question(version: str = "v1_6") -> None:
    """The sentence, and the options for whichever part of it is open.

    Split from the detail questions so the page can put the verdict between
    them: the answer belongs directly under the sentence that produced it,
    and the further questions belong under the answer.
    """
    render_sentence()
    render_picker(version)


def render_detail() -> tuple[Inputs | None, list[str], list[str]]:
    """More detail, and the inputs the page has ended up with.

    Returns the parsed `Inputs`, the keys that make it up (which is what a
    shared link carries), and the keys that have a control on screen right
    now (which is what the card may offer to change). Those two differ:
    `data_kind` travels with a scenario and with a link, and is no longer
    asked, so it must never be offered as a change nobody can make.
    """
    included: list[str] = ["data_class", "data_kind", "tool", "activity"]
    changeable: list[str] = ["data_class", "tool", "activity"]

    detail = _detail_fields()
    if detail:
        label, keys = detail
        with st.expander(label, expanded=_detail_opens_itself()):
            st.html(
                '<p class="cu-hint">These are the further questions this '
                "combination actually turns on. Nothing else is asked.</p>"
            )
            shown = _render_detail(keys)
        included.extend(shown)
        changeable.extend(shown)

    included = list(dict.fromkeys(included))
    changeable = list(dict.fromkeys(changeable))
    return _build_inputs(included), included, changeable


def _detail_fields() -> tuple[str, list[str]] | None:
    """Which further questions this activity and tool actually turn on."""
    activity = st.session_state.get("activity")
    tool = st.session_state.get("tool")
    data_class = st.session_state.get("data_class")

    keys: list[str] = []
    if tool is Tool.SELF_HOSTED:
        keys.append("host")
    if activity is Activity.DECISION_ABOUT_PERSON:
        keys += ["human_review", "hiring"]
    if activity is Activity.SYNTHETIC_MEDIA:
        keys.append("sexual_or_intimate")
    if activity is Activity.NOTETAKER:
        keys.append("meeting_type")
    if activity is Activity.AGENT:
        keys.append("agent_action")
    # 6.8 and 7.6 are about client data, and B.2.3 puts client information in
    # Confidential. The question used to hang off the data-kind dropdown that
    # Phase 5 removed, so it hangs off the class that dropdown stood for.
    if data_class in {DataClass.CONFIDENTIAL, DataClass.RESTRICTED}:
        keys.append("training_or_finetuning")
    if not keys:
        return None
    return "More detail", keys


def _detail_opens_itself() -> bool:
    """Open it when a hidden answer would otherwise decide the verdict.

    A toggle has a safe default and can wait behind a summary. A choice of
    host, meeting or agent action does not: leaving one folded away would
    answer a question the visitor has not seen.
    """
    activity = st.session_state.get("activity")
    return st.session_state.get("tool") is Tool.SELF_HOSTED or activity in {
        Activity.NOTETAKER,
        Activity.AGENT,
    }


def _render_detail(keys: list[str]) -> list[str]:
    """Render the detail questions and return the keys actually shown."""
    shown: list[str] = []

    if "host" in keys:
        shown.append("host")
        st.selectbox(
            "Where does the model run?",
            options=list(Host),
            format_func=HOST_LABELS.get,
            key="host",
            help="Only our own servers or cloud tenancy can reach Tier A (B.1.3).",
        )

    if "human_review" in keys:
        shown += ["human_review", "hiring"]
        st.toggle(
            "A human reviews it and can overrule the AI",
            key="human_review",
            help="Without meaningful human review this is prohibited under 6.6.",
        )
        st.toggle("It is hiring, promotion, performance or termination", key="hiring")

    if "sexual_or_intimate" in keys:
        shown.append("sexual_or_intimate")
        st.toggle("The imagery is sexual or intimate", key="sexual_or_intimate")

    if "meeting_type" in keys:
        shown.append("meeting_type")
        st.selectbox(
            "What kind of meeting?",
            options=list(MeetingType),
            format_func=MEETING_TYPE_LABELS.get,
            key="meeting_type",
        )

    if "agent_action" in keys:
        shown.append("agent_action")
        st.selectbox(
            "What will the agent do?",
            options=list(AgentAction),
            format_func=AGENT_ACTION_LABELS.get,
            key="agent_action",
        )
        shown += _render_agent_flags()

    if "training_or_finetuning" in keys:
        shown.append("training_or_finetuning")
        st.toggle(
            "It will be used to train or fine-tune a model",
            key="training_or_finetuning",
        )
        if st.session_state["training_or_finetuning"]:
            shown.append("client_contract_allows")
            st.toggle(
                "The client contract allows it",
                key="client_contract_allows",
                help="If the contract is silent, the answer is no (7.6).",
            )

    return shown


def _render_agent_flags() -> list[str]:
    shown: list[str] = []
    action = st.session_state["agent_action"]

    if action is AgentAction.PAY:
        shown += ["payee_on_allowlist", "within_caps"]
        st.toggle("The payee is on the allowlist", key="payee_on_allowlist")
        st.toggle("The payment is within the per-action and daily caps", key="within_caps")

    if action is AgentAction.MESSAGE_EXTERNAL:
        shown += ["recipient_on_allowlist", "within_caps"]
        st.toggle("The recipient is on the allowlist", key="recipient_on_allowlist")
        st.toggle("It is within the rate limit", key="within_caps")

    return shown


def _build_inputs(included: list[str]) -> Inputs | None:
    """Build `Inputs` from the included fields only, or None if one is missing.

    A field that is not included contributes nothing, so switching away from
    "agent" cannot leave a stale `agent_action` behind to influence the
    verdict.

    A required field can still be None: a scenario or a link can be seeded
    with one missing, and session state is writable from a test. Returning
    None keeps that in the UI layer, where it is a question not yet answered,
    rather than letting it reach the engine as an invalid one.
    """
    values: dict[str, Any] = {key: st.session_state.get(key) for key in included}
    if any(values.get(key) is None for key in REQUIRED_KEYS):
        return None
    return Inputs(**values)
