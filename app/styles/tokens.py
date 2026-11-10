"""Design tokens from BUILD_SPEC 8.

This module is the single source of the token *values*; `app.css` holds every
rule and refers to them through CSS custom properties, so there is one
stylesheet and one place where a colour is defined.

A note on contrast. Measured against white surface:

    ALLOWED        #1E7B4A   4.6:1   AA for body text
    NEEDS_APPROVAL #B26B00   4.2:1   AA for large text only
    NOT_PERMITTED  #9A4A12   5.9:1   AA for body text
    PROHIBITED     #B42318   6.6:1   AA for body text
    accent teal    #0F5E66   7.5:1   AA for body text
    muted          #5B6573   5.7:1   AA for body text (on #FAFAF7)

Amber clears AA for large text but not for 16px body text, so a status colour
is only ever used for the large status line, icons, borders and tinted
backgrounds. Body copy always uses `--text` or `--muted`. Chips put dark text
on a tinted background rather than coloured text on white.
"""

from __future__ import annotations

from dataclasses import dataclass

from engine.models import ApprovalKind, Status

# --------------------------------------------------------------------------
# Palette and scale
# --------------------------------------------------------------------------

TOKENS: dict[str, str] = {
    # surfaces and type
    "bg": "#FAFAF7",
    "surface": "#FFFFFF",
    "text": "#1C2430",
    "muted": "#5B6573",
    "accent": "#0F5E66",
    "border": "#E3E3DC",
    "border-strong": "#CFCFC6",
    # verdicts
    "allowed": "#1E7B4A",
    "needs-approval": "#B26B00",
    "not-permitted": "#9A4A12",
    "prohibited": "#B42318",
    # verdict tints, for card headers and chips
    "allowed-tint": "#EAF4EE",
    "needs-approval-tint": "#FBF1E1",
    "not-permitted-tint": "#F8EDE4",
    "prohibited-tint": "#FBEBE9",
    # layout
    "measure": "720px",
    "radius": "10px",
    "radius-sm": "6px",
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
