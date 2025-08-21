"""Compatibility layer for previous import path.

The original implementation has been moved to `state.app_state.AppState`.
Keep this file minimal to avoid code drift.
"""

from .state import AppState  # noqa: F401

__all__ = ["AppState"]
