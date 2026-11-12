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
# Widgets
# --------------------------------------------------------------------------


def render_inputs() -> tuple[Inputs | None, list[str]]:
    """Render the inputs and return the parsed `Inputs` plus the visible keys.

    `Inputs` is None when a required answer has been cleared. The caller asks
    for it rather than evaluating, because there is no question to answer yet.
    """
    visible: list[str] = ["data_class", "data_kind", "tool", "activity"]

    st.segmented_control(
        "What is the most sensitive thing in the whole interaction?",
        options=list(DataClass),
        format_func=DATA_CLASS_LABELS.get,
        key="data_class",
        width="stretch",
        help=(
            "Classify the prompt, anything the tool can see, and any attachment. "
            "The highest class present decides the tool (7.2)."
        ),
    )
    st.selectbox(
        "Does it involve personal or client information?",
        options=list(DataKind),
        format_func=DATA_KIND_LABELS.get,
        key="data_kind",
    )

    st.segmented_control(
        "Which tool?",
        options=list(Tool),
        format_func=TOOL_LABELS.get,
        key="tool",
        width="stretch",
        help="Tier C means anything not assessed, including personal accounts.",
    )

    if st.session_state["tool"] is Tool.SELF_HOSTED:
        visible.append("host")
        st.selectbox(
            "Where does the model run?",
            options=list(Host),
            format_func=HOST_LABELS.get,
            key="host",
            help="Only our own servers or cloud tenancy can reach Tier A (B.1.3).",
        )

    st.selectbox(
        "What are you doing with it?",
        options=list(Activity),
        format_func=ACTIVITY_LABELS.get,
        key="activity",
    )

    visible.extend(_render_conditional_flags())
    # `within_caps` is asked by two different agent actions, so de-duplicate
    # before it reaches the URL.
    visible = list(dict.fromkeys(visible))
    return _build_inputs(visible), visible


def _render_conditional_flags() -> list[str]:
    """The flags that are shown only when they can change the answer."""
    shown: list[str] = []
    activity = st.session_state["activity"]
    data_kind = st.session_state["data_kind"]

    if activity is Activity.DECISION_ABOUT_PERSON:
        shown += ["human_review", "hiring"]
        st.toggle(
            "A human reviews it and can overrule the AI",
            key="human_review",
            help="Without meaningful human review this is prohibited under 6.6.",
        )
        st.toggle("It is hiring, promotion, performance or termination", key="hiring")

    if activity is Activity.SYNTHETIC_MEDIA:
        shown.append("sexual_or_intimate")
        st.toggle("The imagery is sexual or intimate", key="sexual_or_intimate")

    if activity is Activity.NOTETAKER:
        shown.append("meeting_type")
        st.selectbox(
            "What kind of meeting?",
            options=list(MeetingType),
            format_func=MEETING_TYPE_LABELS.get,
            key="meeting_type",
        )

    if activity is Activity.AGENT:
        shown.append("agent_action")
        st.selectbox(
            "What will the agent do?",
            options=list(AgentAction),
            format_func=AGENT_ACTION_LABELS.get,
            key="agent_action",
        )
        shown += _render_agent_flags()

    if data_kind is DataKind.CLIENT_INFO:
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


def _build_inputs(visible: list[str]) -> Inputs | None:
    """Build `Inputs` from the visible fields only, or None if one is missing.

    A hidden field contributes nothing, so switching away from "agent" cannot
    leave a stale `agent_action` behind to influence the verdict.

    A cleared segmented control leaves a required field as None, which pydantic
    rejects. Returning None here keeps that in the UI layer, where it is a
    question not yet answered, rather than letting it reach the engine as an
    invalid one.
    """
    values: dict[str, Any] = {}
    for key in visible:
        values[key] = st.session_state[key]
    if any(values.get(key) is None for key in REQUIRED_KEYS):
        return None
    return Inputs(**values)
