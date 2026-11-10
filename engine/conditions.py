"""The `when:` matcher.

A condition is a declarative tree, never a Python expression, so the rules
stay data a non-programmer can review and there is no `eval()` in the
decision path (BUILD_SPEC 1, "Deterministic").

Grammar
-------
A node is either:

* a **mapping** of input field -> accepted value or list of values. Every key
  must match for the node to match. An empty mapping matches everything,
  which is how an always-applied note rule is written.
* exactly one **combinator**: ``all_of``, ``any_of`` or ``none_of``, holding a
  non-empty list of nodes.
"""

from __future__ import annotations

from typing import Any

COMBINATORS = ("all_of", "any_of", "none_of")


class RuleError(ValueError):
    """A malformed `when:` block. Raised at load time, not during evaluation."""


def matches(node: Any, ctx: dict[str, Any], *, path: str = "when") -> bool:
    """True when `node` matches the flattened input `ctx`."""
    if not isinstance(node, dict):
        raise RuleError(f"{path}: expected a mapping, got {type(node).__name__}")

    present = [name for name in COMBINATORS if name in node]
    if present:
        if len(node) != 1:
            raise RuleError(f"{path}: a combinator must be the only key, got {sorted(node)}")
        name = present[0]
        branches = node[name]
        if not isinstance(branches, list) or not branches:
            raise RuleError(f"{path}.{name}: expected a non-empty list of conditions")
        results = (
            matches(branch, ctx, path=f"{path}.{name}[{i}]") for i, branch in enumerate(branches)
        )
        if name == "all_of":
            return all(results)
        if name == "any_of":
            return any(results)
        return not any(results)

    for field, accepted in node.items():
        if field not in ctx:
            raise RuleError(f"{path}: unknown input field {field!r}")
        allowed = accepted if isinstance(accepted, list) else [accepted]
        if not _contains(allowed, ctx[field]):
            return False
    return True


def _contains(allowed: list[Any], value: Any) -> bool:
    """Membership that does not let True == 1 or False == 0 slip through."""
    return any(type(a) is type(value) and a == value for a in allowed)


def validate(node: Any, known_fields: set[str], *, path: str = "when") -> None:
    """Walk a `when:` block and raise RuleError on anything malformed.

    Called once per rule at load time, so a typo in a field name fails fast
    instead of silently never matching. Unlike `matches`, this visits every
    branch and every key rather than short-circuiting.
    """
    if not isinstance(node, dict):
        raise RuleError(f"{path}: expected a mapping, got {type(node).__name__}")

    present = [name for name in COMBINATORS if name in node]
    if present:
        if len(node) != 1:
            raise RuleError(f"{path}: a combinator must be the only key, got {sorted(node)}")
        name = present[0]
        branches = node[name]
        if not isinstance(branches, list) or not branches:
            raise RuleError(f"{path}.{name}: expected a non-empty list of conditions")
        for i, branch in enumerate(branches):
            validate(branch, known_fields, path=f"{path}.{name}[{i}]")
        return

    for field, accepted in node.items():
        if field not in known_fields:
            raise RuleError(
                f"{path}: unknown input field {field!r} (known: {', '.join(sorted(known_fields))})"
            )
        if isinstance(accepted, list) and not accepted:
            raise RuleError(f"{path}.{field}: empty list of accepted values")
