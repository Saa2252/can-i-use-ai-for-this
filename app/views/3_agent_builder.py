"""The agent permission builder (BUILD_SPEC 9.3).

Switch on what the agent may do and its licence changes: one row per action,
saying whether the agent does it by itself, does it once something is
approved, needs a human each time, or may never do it at all. Every row is
`evaluate` answering a question about the configuration on screen.

The page has no empty state. An agent with nothing switched on is still an
agent and 11.3 has an answer for it, so reading is the first rung of the
ladder and it cannot be switched off: "agents are read-only by default" is
the floor, not a choice a reader has to find.

Everything the impact level depends on is asked out loud. The earlier
version scored three of B.3's five factors and said the other two depended on
what the agent was for; the page now asks what it is for, with B.3's own
cells as the options, so there is nothing left for it to assume.
"""

from __future__ import annotations

import streamlit as st

from app.components.agent import (
    ALLOWANCE_FIELDS,
    ATTACKS,
    CAPABILITIES,
    FACTORS,
    LEVEL_NAMES,
    PRESETS,
    SYSTEMS,
    Config,
    Licence,
    added_by,
    controls,
    factor_levels,
    impact,
    levels_table,
    licence,
    overall,
    rubric,
    stress,
)
from app.components.clause_drawer import render_clause_chips, render_clause_drawer
from app.components.footer import render_footer
from app.components.icons import rule as icon_rule
from app.components.risk import data_class_scale
from app.components.shell import escape, inject_styles, page_header
from app.styles.tokens import TOKENS, style_for
from engine.models import DataClass

VERSION = "v1_6"

OPENED = "cu_agent_opened"
VIEW = "cu_agent_view"
DATA_CLASS = "cu_agent_data"
SYSTEMS_KEY = "cu_agent_systems"
EFFECT = "cu_agent_effect"
AUDIENCE = "cu_agent_audience"
JOB = "cu_agent_job"

#: How a licence row reads. The word comes from the engine; the colour is the
#: nearest verdict tint, so the ladder and the card agree at a glance.
LICENCE_SLUG: dict[Licence, str] = {
    Licence.AUTOMATIC: "allowed",
    Licence.CONDITIONAL: "needs-approval",
    Licence.HUMAN_EACH: "not-permitted",
    Licence.NEVER: "prohibited",
}


# --------------------------------------------------------------------------
# Reading the page back as a configuration
# --------------------------------------------------------------------------


def _config() -> Config:
    allowance = {
        key: {
            field: bool(st.session_state.get(f"cu_allow_{key}_{field}", True)) for field in fields
        }
        for key, fields in ALLOWANCE_FIELDS.items()
    }
    committee = {
        key: bool(st.session_state.get(f"cu_allow_{key}_committee", False))
        for key in ALLOWANCE_FIELDS
    }
    return Config(
        capabilities=tuple(
            capability.key
            for capability in CAPABILITIES
            if capability.fixed or st.session_state.get(f"cu_cap_{capability.key}")
        ),
        data_class=st.session_state.get(DATA_CLASS) or DataClass.CONFIDENTIAL,
        systems=tuple(st.session_state.get(SYSTEMS_KEY) or ()),
        effect=int(st.session_state.get(EFFECT) or 0),
        audience=int(st.session_state.get(AUDIENCE) or 0),
        allowance=allowance,
        committee=committee,
    )


def _load_preset(label: str) -> None:
    """Button callback: a preset replaces the agent rather than adding to it."""
    preset = next(entry for entry in PRESETS if entry.label == label)
    for capability in CAPABILITIES:
        st.session_state[f"cu_cap_{capability.key}"] = capability.key in preset.capabilities
    st.session_state[DATA_CLASS] = preset.data_class
    st.session_state[SYSTEMS_KEY] = list(preset.systems)
    st.session_state[JOB] = preset.job
    st.session_state[EFFECT] = preset.effect
    st.session_state[AUDIENCE] = preset.audience
    # A preset describes an agent, not its paperwork: the conditions start met
    # and the Committee has not yet looked at it.
    for key, fields in ALLOWANCE_FIELDS.items():
        for field in fields:
            st.session_state[f"cu_allow_{key}_{field}"] = True
        st.session_state[f"cu_allow_{key}_committee"] = False


# --------------------------------------------------------------------------
# Inputs
# --------------------------------------------------------------------------


def _render_presets() -> None:
    st.html('<p class="cu-label">Start from an example</p>')
    with st.container(horizontal=True, gap="small", key="cu_agent_presets"):
        for preset in PRESETS:
            st.button(
                preset.label,
                key=f"cu_preset_{preset.label.replace(' ', '_').lower()}",
                on_click=_load_preset,
                args=(preset.label,),
                help=preset.job,
                width="content",
            )
        st.button(
            "Clear",
            key="cu_preset_clear",
            on_click=_load_preset,
            args=("Support agent",),
            width="content",
            help="Back to the read-only agent this page opens on.",
        )


def _render_job() -> None:
    st.html(f'<p class="cu-next">{escape(st.session_state.get(JOB, ""))}</p>')


def _render_scope() -> None:
    """What the agent handles and what it can reach: visible, never assumed."""
    left, right = st.columns(2, gap="small")
    with left:
        st.selectbox(
            "What data does it handle?",
            options=list(DataClass),
            format_func=lambda value: value.value,
            key=DATA_CLASS,
            help="This sets the Data row of the B.3 rubric below.",
        )
    with right:
        st.multiselect(
            "What can it reach?",
            options=SYSTEMS,
            key=SYSTEMS_KEY,
            help="C.2 requires an allowlist of the systems an agent may read or write.",
        )

    cells = rubric()
    effect_left, audience_right = st.columns(2, gap="small")
    with effect_left:
        st.selectbox(
            "Effect on people",
            options=(0, 1, 2),
            format_func=lambda level: cells["Effect on people"][level],
            key=EFFECT,
        )
    with audience_right:
        st.selectbox(
            "Audience",
            options=(0, 1, 2),
            format_func=lambda level: cells["Audience"][level],
            key=AUDIENCE,
        )
    st.html(
        '<p class="cu-meta">Those two are B.3\'s own wording, taken from the '
        "rubric rather than rephrased.</p>"
    )


def _render_ladder(config: Config) -> None:
    """The permission ladder, in the order 11.3 lists the actions."""
    st.markdown("## What may it do?")
    st.html(
        '<p class="cu-hint">In risk order. Reading is the first rung and stays '
        "on: 11.3 makes agents read-only by default, so it is the floor rather "
        "than a choice.</p>"
    )

    for capability in CAPABILITIES:
        st.toggle(
            capability.label,
            key=f"cu_cap_{capability.key}",
            value=True if capability.fixed else None,
            disabled=capability.fixed,
            help="Read-only by default (11.3)." if capability.fixed else None,
        )
        if config.has(capability.key) and capability.key in ALLOWANCE_FIELDS:
            _render_three_keys(capability.key, capability.label)


def _render_three_keys(key: str, label: str) -> None:
    """The three conditions 11.3 names for an unattended irreversible action."""
    fields = ALLOWANCE_FIELDS[key]
    names = {
        "payee_on_allowlist": "The payee is on the allowlist",
        "recipient_on_allowlist": "The recipient is on the allowlist",
        "within_caps": "Within the caps" if key == "pay" else "Within the rate limit",
    }
    with st.container(key=f"cu_keys_{key}"):
        st.html(f'<p class="cu-meta">Three keys for {escape(label.lower())} (11.3, C.2)</p>')
        for field in fields:
            st.toggle(names[field], key=f"cu_allow_{key}_{field}")
        st.toggle(
            "The Committee has accepted that risk",
            key=f"cu_allow_{key}_committee",
            help="What a one-time use-case approval is (11.3).",
        )


# --------------------------------------------------------------------------
# The licence
# --------------------------------------------------------------------------


def _render_licence(config: Config, expert: bool) -> None:
    status = overall(config)
    style = style_for(status)
    st.html(
        f'<div class="cu-card cu-card--{style.slug}">'
        f'<p class="cu-status"><span class="cu-status__icon cu-status__icon--svg '
        f'cu-icon cu-icon--{style.slug}"></span>'
        f"<span>{escape(style.word)}</span></p>"
        f'<p class="cu-subtitle">{escape(style.subtitle)}</p></div>'
    )

    rows = licence(config)
    html = []
    for row in rows:
        slug = LICENCE_SLUG[row.licence]
        chips = (
            "".join(f'<span class="cu-gate__clause">{escape(c)}</span>' for c in row.clauses)
            if expert
            else ""
        )
        html.append(
            f'<li class="cu-licence cu-licence--{slug}">'
            f'<span class="cu-licence__mark cu-icon cu-icon--{slug}"></span>'
            f'<span class="cu-licence__body">'
            f'<span class="cu-licence__head">{escape(row.label)}'
            f'<span class="cu-licence__state">{escape(row.licence.value)}</span></span>'
            f"{f'<span class="cu-licence__note">{escape(row.note)}</span>' if row.note else ''}"
            f'<span class="cu-gate__clauses">{chips}</span>'
            f"</span></li>"
        )
    st.html(
        '<p class="cu-label">Agent licence</p>'
        f'<ul class="cu-licence-list">{"".join(html)}</ul>'
        '<p class="cu-meta">Each row is the engine answering for this agent, not a '
        "table kept beside the rules.</p>"
    )


# --------------------------------------------------------------------------
# Controls and the impact meter
# --------------------------------------------------------------------------


def _render_controls(config: Config, expert: bool) -> None:
    every = controls(config)
    credited: dict[str, str] = {}
    for capability in CAPABILITIES:
        if capability.fixed or not config.has(capability.key):
            continue
        for control in added_by(config, capability.key):
            credited.setdefault(control, capability.label)

    st.html(f'<p class="cu-label">Required controls <span class="cu-count">{len(every)}</span></p>')
    rows = []
    for control, clauses in every:
        because = credited.get(control)
        chips = (
            "".join(f'<span class="cu-gate__clause">{escape(c)}</span>' for c in clauses)
            if expert
            else ""
        )
        why = (
            f'<span class="cu-control__why">+ added because you allowed '
            f"{escape(because.lower())}</span>"
            if because
            else ""
        )
        rows.append(
            f'<li class="{"cu-control cu-control--new" if because else "cu-control"}">'
            f"{escape(control)}{why}"
            f'<span class="cu-gate__clauses">{chips}</span>'
            f"</li>"
        )
    st.html(f'<ul class="cu-list cu-controls">{"".join(rows)}</ul>')


def _render_impact(config: Config) -> None:
    """All five B.3 factors, as bars, with the highest marked."""
    levels = factor_levels(config)
    level, driver = impact(config)
    cells = rubric()
    table = levels_table()
    name = LEVEL_NAMES[level]

    bars = []
    for factor in FACTORS:
        value = levels[factor]
        steps = "".join(
            f'<span class="cu-bar__step{" cu-bar__step--on" if index <= value else ""}'
            f'{" cu-bar__step--peak" if factor == driver and index == value else ""}">'
            f"</span>"
            for index in range(3)
        )
        bars.append(
            f'<li class="cu-bar{" cu-bar--driver" if factor == driver else ""}">'
            f'<span class="cu-bar__name">{escape(factor)}</span>'
            f'<span class="cu-bar__track">{steps}</span>'
            f'<span class="cu-bar__cell">{escape(cells[factor][value])}</span>'
            f"</li>"
        )

    assessment, approver, review = table[name]
    st.html(
        f'<p class="cu-label">Impact level (B.3) '
        f'<span class="cu-count cu-count--{name.lower()}">{escape(name)}</span></p>'
        f'<ul class="cu-bars">{"".join(bars)}</ul>'
        f'<p class="cu-hint">The highest factor sets the level. Here that is '
        f"<strong>{escape(driver.lower())}</strong>: "
        f"{escape(cells[driver][level].lower())}.</p>"
        f'<table class="cu-fields"><tbody>'
        f"<tr><th>Assessment</th><td>{escape(assessment)}</td></tr>"
        f"<tr><th>Default approver</th><td>{escape(approver)}</td></tr>"
        f"<tr><th>Review cycle</th><td>{escape(review)}</td></tr>"
        f"</tbody></table>"
        f'<p class="cu-meta">Read from B.3\'s own tables, not restated here.</p>'
    )


# --------------------------------------------------------------------------
# Stress test
# --------------------------------------------------------------------------


def _render_stress(config: Config, expert: bool) -> None:
    st.markdown("## Try to break it")
    st.html(
        '<p class="cu-hint">Five things that get tried on agents. Each answer is '
        "worked out from the agent above as it stands now.</p>"
    )

    for attack in ATTACKS:
        outcome = stress(config, attack)
        slug = "allowed" if outcome.blocked else "prohibited"
        chips = (
            "".join(f'<span class="cu-gate__clause">{escape(c)}</span>' for c in outcome.clauses)
            if expert
            else ""
        )
        st.html(
            f'<div class="cu-attack cu-attack--{slug}">'
            f'<p class="cu-attack__what">{escape(attack.label)}</p>'
            f'<p class="cu-attack__verdict">'
            f'<span class="cu-icon cu-icon--{slug}"></span>'
            f"<strong>{'Blocked' if outcome.blocked else 'Not blocked'}</strong> "
            f"&middot; {escape(outcome.control)}</p>"
            f'<span class="cu-gate__clauses">{chips}</span>'
            f"</div>"
        )


# --------------------------------------------------------------------------
# Page
# --------------------------------------------------------------------------


def _icon_styles() -> str:
    """The four status icons, painted as CSS because st.html strips an SVG."""
    return "".join(
        icon_rule(f".cu-icon--{slug}", slug, TOKENS[slug], size=20)
        for slug in ("allowed", "needs-approval", "not-permitted", "prohibited")
    )


def _render_data_risk(config: Config) -> None:
    """Where the chosen class sits on the 7.1 scale, in the Matrix's colours.

    The same computed scale the grid uses, and the same caveat: the colour is
    how restricted the data is, not an answer about this agent.
    """
    slug = data_class_scale(VERSION)[config.data_class]
    st.html(
        f'<span class="cu-key cu-key--{slug}"><span class="cu-key__icon '
        f'cu-icon cu-icon--{slug}"></span>{escape(config.data_class.value)}</span>'
        '<span class="cu-meta"> how restricted this data is under 7.1, not the '
        "answer for this agent</span>"
    )


def main() -> None:
    inject_styles()
    page_header(
        "What controls does this agent need?",
        "Switch on what it may do, and its licence changes as you go.",
    )

    if not st.session_state.get(OPENED):
        st.session_state[OPENED] = True
        _load_preset("Support agent")

    view = st.radio(
        "View",
        options=("Plain", "Expert"),
        horizontal=True,
        key=VIEW,
        label_visibility="collapsed",
        help="Expert attaches the clause behind each control and each outcome.",
    )
    expert = view == "Expert"

    _render_presets()
    _render_job()
    _render_scope()

    config = _config()
    st.html(
        "<style>"
        + _icon_styles()
        # Like the Matrix, this page puts a ladder beside a licence and does
        # not fit the reading measure. Widened only where there is room.
        + "@media (min-width: 1000px){.block-container{max-width:1080px;}}"
        + "</style>"
    )
    _render_data_risk(config)

    left, right = st.columns([1, 1.15], gap="medium")
    with left:
        _render_ladder(config)
    with right:
        _render_licence(_config(), expert)
        _render_impact(_config())

    _render_controls(_config(), expert)
    _render_stress(_config(), expert)

    if expert:
        every = sorted({clause for _c, clauses in controls(_config()) for clause in clauses})
        render_clause_chips(every, label="Every clause behind this agent")
        render_clause_drawer(every, VERSION)

    render_footer(VERSION)


main()
