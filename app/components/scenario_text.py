"""Turning a scenario's inputs into a readable question.

Kept out of the quiz page so it can be tested across every scenario rather
than whichever ten a shuffle happens to draw. Every condition that changes a
verdict has to appear here, or two scenarios become the same question with
two different right answers.
"""

from __future__ import annotations

from app.components.inputs import ACTIVITY_LABELS
from engine.models import AgentAction, DataKind, Inputs, MeetingType
from engine.scenarios import Scenario

DATA_KIND_PHRASES = {
    DataKind.ORDINARY_PERSONAL: "names a colleague",
    DataKind.SENSITIVE_PERSONAL: "sensitive personal data",
    DataKind.HR_HEALTH_RECORD: "an HR record with health data",
    DataKind.CLIENT_INFO: "names a client",
}

AGENT_ACTION_PHRASES = {
    AgentAction.READ: "only read",
    AgentAction.WRITE: "write or change records",
    AgentAction.PAY: "make a payment",
    AgentAction.DELETE: "delete something",
    AgentAction.MESSAGE_EXTERNAL: "send a message outside the organization",
    AgentAction.PRODUCTION_CHANGE: "change a production system",
    AgentAction.ADD_PAYEE: "add a payee to its own allowlist",
    AgentAction.ADD_RECIPIENT: "add a recipient to its own allowlist",
}

MEETING_PHRASES = {
    MeetingType.ORDINARY: "an ordinary meeting",
    MeetingType.LEGAL_COUNSEL: "a meeting with legal counsel",
    MeetingType.HR_CASEWORK: "an HR disciplinary or medical discussion",
    MeetingType.BOARD_EXEC: "a board executive session",
    MeetingType.UNDISCLOSED_DEAL: "a meeting about an undisclosed transaction",
}

TIER_PHRASES = {"A": "Tier A", "B": "Tier B", "C": "Tier C"}


def tool_phrase(inputs: Inputs) -> str:
    if inputs.host is not None:
        return f"self-hosted ({inputs.host.value.replace('_', ' ')})"
    return TIER_PHRASES.get(inputs.tool.value, inputs.tool.value)


def describe_scenario(example: Scenario) -> str:
    """The inputs in words, so the question is answerable without guessing."""
    inputs = example.inputs
    parts = [
        ACTIVITY_LABELS[inputs.activity],
        f"{inputs.data_class.value} data",
        f"in a {tool_phrase(inputs)} tool",
    ]

    if inputs.data_kind is not DataKind.NONE:
        parts.append(DATA_KIND_PHRASES[inputs.data_kind])
    if inputs.agent_action is not None:
        parts.append(f"the agent will {AGENT_ACTION_PHRASES[inputs.agent_action]}")
    if inputs.recipient_on_allowlist is not None:
        parts.append(
            "recipient is on the allowlist"
            if inputs.recipient_on_allowlist
            else "recipient is not on the allowlist"
        )
    if inputs.payee_on_allowlist is not None:
        parts.append(
            "payee is on the allowlist"
            if inputs.payee_on_allowlist
            else "payee is not on the allowlist"
        )
    if inputs.within_caps is not None:
        parts.append(
            "within the caps and rate limit"
            if inputs.within_caps
            else "outside the caps and rate limit"
        )
    if inputs.meeting_type is not None:
        parts.append(MEETING_PHRASES[inputs.meeting_type])
    if inputs.human_review is not None:
        parts.append("a human reviews it" if inputs.human_review else "no human review")
    if inputs.hiring:
        parts.append("a hiring decision")
    if inputs.sexual_or_intimate:
        parts.append("sexual or intimate imagery")
    if inputs.training_or_finetuning:
        parts.append("used to train or fine-tune a model")
    if inputs.client_contract_allows is not None:
        parts.append(
            "the client contract allows it"
            if inputs.client_contract_allows
            else "the client contract does not allow it"
        )
    return " · ".join(parts)
