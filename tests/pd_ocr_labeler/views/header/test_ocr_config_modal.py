"""Unit tests for OCRConfigModal handler-level behavior.

These complement the browser-level tests in
``tests/browser/test_ocr_config_modal.py`` by exercising the modal's
``_open`` / ``_close`` handlers directly in-process, without a NiceGUI
runtime.

The HF-revision Cancel-revert *result* (after Cancel + re-open the
input is back to the persisted value) is already covered at the
browser level by
``test_ocr_config_hf_revision_edit_reverts_on_cancel``.  This file
pins the *mechanism* of that revert: the revert is driven by the
next ``_open`` call, not by ``_close`` — ``_close`` only closes the
dialog and leaves the input value in its dirty state.  Restructuring
the revert to fire on close (e.g. moving the reset into ``_cancel``)
would still pass the existing browser test, but would silently break
the user-facing contract of "your typed value persists between
Cancel and the very next manual modal-open".  These tests fail in
that scenario.
"""

from __future__ import annotations

from unittest.mock import MagicMock, Mock

import pytest

from pd_ocr_labeler.views.header.ocr_config_modal import OCRConfigModal


def _build_modal_with_mock_widgets(
    app_state_model: Mock | None = None,
    project_state_model: Mock | None = None,
) -> OCRConfigModal:
    """Construct an ``OCRConfigModal`` and attach mock widget stand-ins.

    Bypasses ``build()`` (which requires a NiceGUI runtime).  Each
    widget mock has ``.value``, ``.options``, ``.update``, and (for the
    dialog) ``.open`` / ``.close`` so the async handlers can interact
    with them as if they were real widgets.
    """

    app_state = app_state_model or Mock()
    project_state = project_state_model or Mock()
    modal = OCRConfigModal(
        app_state_model=app_state,
        project_state_model=project_state,
    )

    modal._dialog = MagicMock()
    modal._detection_model_select = MagicMock()
    modal._recognition_model_select = MagicMock()
    modal._hf_revision_input = MagicMock()
    return modal


class TestOpenResetsHfRevisionInput:
    """``_open`` must reset the HF revision input from app state."""

    async def test_open_resets_hf_input_from_app_state(self):
        app_state = Mock()
        app_state.hf_pinned_revision = "v1.2.3"
        modal = _build_modal_with_mock_widgets(app_state_model=app_state)

        modal._hf_revision_input.value = "stale-user-typed-value"

        await modal._open()

        assert modal._hf_revision_input.value == "v1.2.3"
        modal._hf_revision_input.update.assert_called_once_with()
        modal._dialog.open.assert_called_once_with()

    async def test_open_normalizes_none_revision_to_empty_string(self):
        app_state = Mock()
        app_state.hf_pinned_revision = None
        modal = _build_modal_with_mock_widgets(app_state_model=app_state)

        modal._hf_revision_input.value = "leftover-from-previous-open"

        await modal._open()

        assert modal._hf_revision_input.value == ""


class TestCloseDoesNotResetHfInput:
    """``_close`` only closes the dialog — it does NOT reset the input.

    This is the load-bearing assertion that pins the revert
    *mechanism* in place.  If the implementation is later refactored
    to clear / reset the HF input value inside ``_close``, the
    user-facing "your typed value sticks across the close" contract
    breaks even though the surface-level browser test
    (``test_ocr_config_hf_revision_edit_reverts_on_cancel``) would
    still pass.
    """

    async def test_close_does_not_mutate_hf_input_value(self):
        app_state = Mock()
        app_state.hf_pinned_revision = "v1.2.3"
        modal = _build_modal_with_mock_widgets(app_state_model=app_state)

        modal._hf_revision_input.value = "user-typed-dirty-value"

        await modal._close()

        # The dirty value persists — only the dialog closed.
        assert modal._hf_revision_input.value == "user-typed-dirty-value"
        modal._dialog.close.assert_called_once_with()

    async def test_close_does_not_call_app_state_revision_setter(self):
        """``_close`` must not touch app state at all."""

        app_state = Mock()
        app_state.hf_pinned_revision = "v1.2.3"
        modal = _build_modal_with_mock_widgets(app_state_model=app_state)

        modal._hf_revision_input.value = "user-typed-dirty-value"

        await modal._close()

        # No write paths into the app-state model should fire on close.
        app_state.command_set_hf_pinned_revision.assert_not_called()
        app_state.command_refresh_ocr_models.assert_not_called()
        app_state.command_set_selected_ocr_models.assert_not_called()


class TestRevertSequenceIsOpenDriven:
    """Composes the open/cancel/open sequence end-to-end.

    Iter 14's browser test asserts the *result* of the full sequence
    (after ``_open`` -> dirty -> ``_close`` -> ``_open`` the input is
    back to the persisted value).  This test additionally pins the
    intermediate state: between ``_close`` and the next ``_open`` the
    input value is still dirty.  That's what makes this a
    *mechanism* test rather than just a redundant unit-level mirror
    of the browser test.
    """

    async def test_full_open_dirty_close_reopen_revert_cycle(self):
        app_state = Mock()
        app_state.hf_pinned_revision = "v1.2.3"
        modal = _build_modal_with_mock_widgets(app_state_model=app_state)

        # 1. Initial open hydrates input from app state.
        await modal._open()
        assert modal._hf_revision_input.value == "v1.2.3"

        # 2. User types a dirty value.
        modal._hf_revision_input.value = "user-typed-dirty-value"

        # 3. Cancel/close — dirty value still persists in memory.
        await modal._close()
        assert modal._hf_revision_input.value == "user-typed-dirty-value", (
            "Revert must not happen on close; otherwise the user's typed "
            "value would be lost mid-session before they re-open the modal."
        )

        # 4. Next open re-hydrates from app state — revert lands here.
        await modal._open()
        assert modal._hf_revision_input.value == "v1.2.3"


class TestOpenWithoutHfInput:
    """Defensive: ``_open`` tolerates an unbuilt HF input field."""

    async def test_open_skips_hf_input_when_none(self):
        app_state = Mock()
        app_state.hf_pinned_revision = "v1.2.3"
        modal = _build_modal_with_mock_widgets(app_state_model=app_state)
        modal._hf_revision_input = None

        # Must not raise.
        await modal._open()

        modal._dialog.open.assert_called_once_with()


@pytest.mark.parametrize(
    "persisted_revision",
    ["", "v1.0.0", "abc123def456", None],
)
async def test_open_propagates_various_persisted_revisions(persisted_revision):
    """``_open`` faithfully echoes the persisted value (with None -> '')."""
    app_state = Mock()
    app_state.hf_pinned_revision = persisted_revision
    modal = _build_modal_with_mock_widgets(app_state_model=app_state)

    modal._hf_revision_input.value = "scratch-value"

    await modal._open()

    expected = persisted_revision or ""
    assert modal._hf_revision_input.value == expected
