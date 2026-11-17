"""Design tokens from BUILD_SPEC 8.

This module is the single source of the token *values*; `app.css` holds every
rule and refers to them through CSS custom properties, so there is one
stylesheet and one place where a colour is defined.

The look is an editorial one: white paper, near-black ink, hairline rules,
square corners and one midnight accent. Nothing warm, nothing rounded.

A note on contrast. Measured against white surface:

    ALLOWED        #1D6B47   6.3:1   AA for body text
    NEEDS_APPROVAL #A26100   4.6:1   AA for body text, used at large sizes
    NOT_PERMITTED  #8C4519   7.0:1   AA for body text
    PROHIBITED     #A3221A   7.3:1   AA for body text
    accent midnight #1C2B44 13.9:1   AA for body text
    muted          #5E636B   6.1:1   AA for body text

A status colour is only ever used for the large status line, icons, borders
and tinted backgrounds. Body copy always uses `--text` or `--muted`. Chips put
dark text on a tinted background rather than coloured text on white.
"""

from __future__ import annotations

from dataclasses import dataclass

from engine.models import ApprovalKind, Status

# --------------------------------------------------------------------------
# Palette and scale
# --------------------------------------------------------------------------

TOKENS: dict[str, str] = {
    # surfaces and type
    "bg": "#FFFFFF",
    "surface": "#FFFFFF",
    "text": "#0F1114",
    "muted": "#5E636B",
    "accent": "#1C2B44",
    "border": "#E8E6E1",
    "border-strong": "#C9C6BF",
    # verdicts
    "allowed": "#1D6B47",
    "needs-approval": "#A26100",
    "not-permitted": "#8C4519",
    "prohibited": "#A3221A",
    # verdict tints, for card headers and chips
    "allowed-tint": "#EFF4F1",
    "needs-approval-tint": "#F8F2E6",
    "not-permitted-tint": "#F6EFE9",
    "prohibited-tint": "#F8EDEB",
    # a quiet wash for bands and hovers
    "wash": "#F6F5F2",
    # layout
    "measure": "720px",
    "radius": "3px",
    "radius-sm": "2px",
    "gutter": "16px",
}


def css_variables() -> str:
    """The `:root` block that `app.css` refers to."""
    declarations = "\n".join(f"  --{name}: {value};" for name, value in TOKENS.items())
    return f":root {{\n{declarations}\n}}"


# --------------------------------------------------------------------------
# Verdict presentation
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class StatusStyle:
    """How one verdict reads.

    BUILD_SPEC 8, "Never color alone": every verdict carries an icon, a word
    and a colour, so the status survives greyscale and colour blindness.
    """

    icon: str
    word: str
    slug: str
    subtitle: str


STATUS_STYLES: dict[Status, StatusStyle] = {
    Status.ALLOWED: StatusStyle(
        icon="✓",
        word="Allowed",
        slug="allowed",
        subtitle="Go ahead, and check the output before you rely on it.",
    ),
    Status.NEEDS_APPROVAL: StatusStyle(
        icon="!",
        word="Needs approval",
        slug="needs-approval",
        subtitle="Permitted, once it has been approved and registered.",
    ),
    Status.NOT_PERMITTED: StatusStyle(
        icon="⊘",
        word="Not permitted",
        slug="not-permitted",
        subtitle="Blocked as described, but there is a compliant route.",
    ),
    Status.PROHIBITED: StatusStyle(
        icon="✕",
        word="Prohibited",
        slug="prohibited",
        subtitle="A hard line in Section 6. No approval route, and no exceptions.",
    ),
}

APPROVAL_LABELS: dict[ApprovalKind, str] = {
    ApprovalKind.NONE: "",
    ApprovalKind.ONE_TIME_USE_CASE: "one-time use-case approval",
    ApprovalKind.PER_ACTION: "human approval for each action",
}

#: BUILD_SPEC 7: law, standard or our own choice.
BASIS_ICONS: dict[str, str] = {
    "law": "⚖️",
    "standard": "📘",
    "our_choice": "🏢",
}

BASIS_LABELS: dict[str, str] = {
    "law": "Law",
    "standard": "Standard",
    "our_choice": "Our choice",
}


def style_for(status: Status) -> StatusStyle:
    return STATUS_STYLES[status]
