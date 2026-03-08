"""Shared NiceGUI button style helpers.

These helpers centralize reusable style patterns so individual views can apply
consistent button appearance without duplicating class/prop strings.
"""

from __future__ import annotations

from enum import Enum
from typing import Any


class ButtonVariant(str, Enum):
    """Supported shared button style variants."""

    DEFAULT = "default"
    DELETE = "delete"
    TOGGLE = "toggle"


def _coerce_variant(variant: ButtonVariant | str) -> ButtonVariant:
    """Normalize variant values while preserving backward compatibility."""
    if isinstance(variant, ButtonVariant):
        return variant

    normalized = str(variant or "").strip().lower()
    if normalized in {"", "default", "blue"}:
        return ButtonVariant.DEFAULT
    if normalized == "delete":
        return ButtonVariant.DELETE
    if normalized == "red":
        return ButtonVariant.DELETE
    if normalized == "toggle":
        return ButtonVariant.TOGGLE
    return ButtonVariant.DEFAULT


def style_word_icon_button(
    button: Any,
    *,
    variant: ButtonVariant | str = ButtonVariant.DEFAULT,
) -> Any:
    """Apply consistent styling to icon-only word edit buttons."""
    resolved_variant = _coerce_variant(variant)
    button.props("size=xs unelevated round")
    if resolved_variant == ButtonVariant.DELETE:
        button.props("color=negative text-color=white")
    else:
        button.props("color=primary text-color=white")
    return button


def style_word_text_button(
    button: Any,
    *,
    variant: ButtonVariant | str = ButtonVariant.DEFAULT,
    active: bool = False,
    compact: bool = False,
) -> Any:
    """Apply consistent styling to text-based word edit buttons."""
    resolved_variant = _coerce_variant(variant)
    if compact:
        button.props("size=xs unelevated")
    else:
        button.props("size=xs dense")

    if resolved_variant == ButtonVariant.TOGGLE:
        if active:
            button.props("color=primary text-color=white")
        else:
            button.props("color=grey-5 text-color=black")
    elif resolved_variant == ButtonVariant.DELETE:
        button.props("color=negative text-color=white")
    elif active:
        button.props("color=primary text-color=white")
    else:
        button.props("color=primary text-color=white")
    return button


def style_action_button(
    button: Any,
    *,
    variant: ButtonVariant | str = ButtonVariant.DEFAULT,
    size: str = "sm",
) -> Any:
    """Apply shared styling to icon+text action buttons.

    Intended for larger action rows (e.g., Merge/Delete/Refine controls).
    """
    resolved_variant = _coerce_variant(variant)
    button.props(f"size={size} unelevated")
    if resolved_variant == ButtonVariant.DELETE:
        button.props("color=negative text-color=white")
    else:
        button.props("color=primary text-color=white")
    return button
