"""The green-to-red scale behind the data and tool options.

An option list that is all one colour makes every choice look equivalent,
and these are not: Secrets and Public sit at opposite ends of the policy.
So each option is tinted on a scale, and the scale is *computed from the 7.1
grid* rather than asserted here.

How: hold the activity steady at drafting and run every data class against
every tool through `evaluate`. Count how many counterparts come back
ALLOWED. Public clears all four tiers, Internal three, Confidential two,
Restricted and Secrets none — and between those last two, Restricted can at
least reach "needs approval" while Secrets cannot reach anything. That is
the order, and it is the policy's order, not a designer's.

The colour is then the option's *position* in that order, mapped across the
four verdict tokens. It is a sensitivity scale borrowing the verdict
palette, and it is never a verdict: a red data chip does not mean the answer
is no, it means this is the most restricted thing on the list. The page says
so next to the control, because a colour that looks like an answer and is
not one would be worse than no colour at all.

A self-hosted model is scored as if it ran on organizational infrastructure,
which is the only host that can reach Tier A (B.1.3). Where it actually runs
is asked separately, and the verdict uses the real answer.
"""

from __future__ import annotations

from functools import lru_cache

from engine.models import Activity, DataClass, Host, Inputs, Status, Tool

#: The four verdict tokens, least to most severe. An option's colour is its
#: position on this scale, not a status it was given.
SCALE: tuple[str, ...] = ("allowed", "needs-approval", "not-permitted", "prohibited")

_SEVERITY: dict[Status, int] = {
    Status.ALLOWED: 0,
    Status.NEEDS_APPROVAL: 1,
    Status.NOT_PERMITTED: 2,
    Status.PROHIBITED: 3,
}


def _status(data_class: DataClass, tool: Tool, version: str) -> Status:
    from engine.rules import evaluate

    fields = {"data_class": data_class, "tool": tool, "activity": Activity.DRAFTING}
    if tool is Tool.SELF_HOSTED:
        fields["host"] = Host.ORG_CLOUD
    return evaluate(Inputs(**fields), version).status


def _bucket(position: int, total: int) -> str:
    """Spread `total` ranked options evenly across the four tokens.

    Five data classes over four tokens means one pair shares a colour, and
    it is the two at the open end: Public and Internal are the two the grid
    lets through most widely, so they are the two it costs least to merge.
    """
    if total <= 1:
        return SCALE[0]
    return SCALE[position * len(SCALE) // total]


@lru_cache(maxsize=8)
def _scales(version: str) -> tuple[dict[DataClass, str], dict[Tool, str]]:
    classes = list(DataClass)
    tools = list(Tool)
    grid = {(c, t): _status(c, t, version) for c in classes for t in tools}

    def score(key, counterparts, index: int) -> tuple[int, int, int]:
        statuses = [
            grid[(key, other)] if isinstance(key, DataClass) else grid[(other, key)]
            for other in counterparts
        ]
        allowed = sum(1 for status in statuses if status is Status.ALLOWED)
        best = min(_SEVERITY[status] for status in statuses)
        # Fewest ALLOWED counterparts is most restricted; the best reachable
        # answer separates Restricted from Secrets, which both allow none.
        return (-allowed, best, index)

    ranked_classes = sorted(classes, key=lambda c: score(c, tools, classes.index(c)))
    ranked_tools = sorted(tools, key=lambda t: score(t, classes, tools.index(t)))

    return (
        {c: _bucket(i, len(ranked_classes)) for i, c in enumerate(ranked_classes)},
        {t: _bucket(i, len(ranked_tools)) for i, t in enumerate(ranked_tools)},
    )


def data_class_scale(version: str = "v1_6") -> dict[DataClass, str]:
    """Each data class's place on the sensitivity scale, least sensitive first."""
    return _scales(version)[0]


def tool_scale(version: str = "v1_6") -> dict[Tool, str]:
    """Each tool tier's place on the scale, least restricted first."""
    return _scales(version)[1]


# --------------------------------------------------------------------------
# Painting the options
# --------------------------------------------------------------------------


def option_styles(
    version: str,
    selected_data_class: DataClass | None,
    selected_tool: Tool | None,
) -> str:
    """CSS for the data and tool option buttons, generated for this run.

    Streamlit gives a keyed element the class `st-key-<key>`, which is the
    only hook an option button has. Unselected options carry the scale colour
    as a hairline, so the gradient is readable without any of them shouting;
    the chosen one is filled in the same colour, so selection is a change of
    weight rather than a different hue. No teal: the accent is the app's
    voice, not an answer about risk.
    """
    rules: list[str] = []

    def paint(field: str, value, slug: str, selected: bool) -> None:
        key = f".st-key-cu_opt_{field}_{value.value}"
        if selected:
            rules.append(
                f"{key} .stButton button {{"
                f"  background: var(--{slug}-tint);"
                f"  border: 1px solid var(--{slug});"
                f"  border-left: 6px solid var(--{slug});"
                f"  color: var(--text); font-weight: 600; }}"
            )
        else:
            # The strip carries the scale at full strength and the rest of the
            # button stays quiet, so five options read as a gradient without
            # five coloured rectangles competing with the verdict below.
            rules.append(
                f"{key} .stButton button {{"
                f"  background: var(--surface);"
                f"  border: 1px solid var(--border);"
                f"  border-left: 6px solid var(--{slug});"
                f"  color: var(--muted); }}"
            )
            rules.append(
                f"{key} .stButton button:hover {{"
                f"  background: var(--{slug}-tint);"
                f"  border-color: var(--border-strong);"
                f"  border-left-color: var(--{slug});"
                f"  color: var(--text); }}"
            )

    for data_class, slug in data_class_scale(version).items():
        paint("data_class", data_class, slug, data_class == selected_data_class)
    for tool, slug in tool_scale(version).items():
        paint("tool", tool, slug, tool == selected_tool)

    return "\n".join(rules)
