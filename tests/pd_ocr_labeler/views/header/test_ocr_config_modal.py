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


def _wire_apply_selection_inputs(
    modal: OCRConfigModal,
    *,
    detection_value: str = "huggingface",
    recognition_value: str = "huggingface",
    revision_value: str = "",
) -> None:
    """Populate the modal's mock select / input widgets with values.

    ``_apply_selection`` reads the live widget ``.value`` attributes
    rather than going through the app-state model, so tests must wire
    these explicitly before invoking the handler.
    """
    modal._detection_model_select.value = detection_value
    modal._recognition_model_select.value = recognition_value
    modal._hf_revision_input.value = revision_value


class TestApplySelectionSuccessPath:
    """``_apply_selection`` happy path: both commands succeed, dialog closes.

    Pins three load-bearing behaviors:
      1. Successful apply emits a single ``positive`` notification.
      2. Successful apply closes the dialog.
      3. The pin setter is gated by ``new_revision != previous_revision`` —
         a no-op revision skips ``command_set_hf_pinned_revision`` entirely.
    """

    async def test_apply_no_edit_calls_models_setter_and_closes(self, monkeypatch):
        app_state = Mock()
        app_state.hf_pinned_revision = "v1.2.3"
        app_state.command_set_selected_ocr_models = Mock(return_value=True)
        app_state.command_set_hf_pinned_revision = Mock(return_value=True)
        modal = _build_modal_with_mock_widgets(app_state_model=app_state)
        _wire_apply_selection_inputs(
            modal,
            detection_value="huggingface",
            recognition_value="huggingface",
            revision_value="v1.2.3",  # unchanged
        )

        notify_mock = MagicMock()
        monkeypatch.setattr(modal, "_notify", notify_mock)

        await modal._apply_selection()

        # No-op revision: pin setter must NOT be called.
        app_state.command_set_hf_pinned_revision.assert_not_called()
        # Models setter must be called with the as-typed keys.
        app_state.command_set_selected_ocr_models.assert_called_once_with(
            "huggingface", "huggingface"
        )
        notify_mock.assert_called_once_with("OCR models updated", "positive")
        modal._dialog.close.assert_called_once_with()

    async def test_apply_with_revision_edit_calls_pin_setter_then_models(self, monkeypatch):
        app_state = Mock()
        app_state.hf_pinned_revision = "v1.0.0"
        app_state.command_set_selected_ocr_models = Mock(return_value=True)
        app_state.command_set_hf_pinned_revision = Mock(return_value=True)
        modal = _build_modal_with_mock_widgets(app_state_model=app_state)
        _wire_apply_selection_inputs(
            modal,
            detection_value="huggingface",
            recognition_value="huggingface",
            revision_value="v2.0.0",  # changed
        )

        notify_mock = MagicMock()
        monkeypatch.setattr(modal, "_notify", notify_mock)

        await modal._apply_selection()

        app_state.command_set_hf_pinned_revision.assert_called_once_with("v2.0.0")
        app_state.command_set_selected_ocr_models.assert_called_once_with(
            "huggingface", "huggingface"
        )
        notify_mock.assert_called_once_with("OCR models updated", "positive")
        modal._dialog.close.assert_called_once_with()

    async def test_apply_clearing_revision_passes_none_to_pin_setter(self, monkeypatch):
        """Empty new revision when previous was non-empty must reset pin to None."""
        app_state = Mock()
        app_state.hf_pinned_revision = "v1.0.0"
        app_state.command_set_selected_ocr_models = Mock(return_value=True)
        app_state.command_set_hf_pinned_revision = Mock(return_value=True)
        modal = _build_modal_with_mock_widgets(app_state_model=app_state)
        _wire_apply_selection_inputs(
            modal,
            detection_value="huggingface",
            recognition_value="huggingface",
            revision_value="",  # changed -> clear pin
        )

        notify_mock = MagicMock()
        monkeypatch.setattr(modal, "_notify", notify_mock)

        await modal._apply_selection()

        # Critical: empty -> None, not empty -> "".
        app_state.command_set_hf_pinned_revision.assert_called_once_with(None)
        modal._dialog.close.assert_called_once_with()


class TestApplySelectionGuards:
    """``_apply_selection`` rejects empty selections without mutating state."""

    async def test_apply_with_empty_detection_warns_and_keeps_dialog_open(self, monkeypatch):
        app_state = Mock()
        app_state.hf_pinned_revision = ""
        app_state.command_set_selected_ocr_models = Mock(return_value=True)
        app_state.command_set_hf_pinned_revision = Mock(return_value=True)
        modal = _build_modal_with_mock_widgets(app_state_model=app_state)
        _wire_apply_selection_inputs(
            modal,
            detection_value="",  # empty -> guard
            recognition_value="huggingface",
            revision_value="",
        )

        notify_mock = MagicMock()
        monkeypatch.setattr(modal, "_notify", notify_mock)

        await modal._apply_selection()

        notify_mock.assert_called_once_with(
            "Select both detection and recognition models first", "warning"
        )
        # No state mutations whatsoever — pin and models setters skipped.
        app_state.command_set_hf_pinned_revision.assert_not_called()
        app_state.command_set_selected_ocr_models.assert_not_called()
        # Dialog remains open.
        modal._dialog.close.assert_not_called()


class TestRescanModelsSuccessPath:
    """``_rescan_models`` happy path: refresh succeeds, options re-sync, modal stays open.

    Pins the load-bearing behaviors of the Rescan Models button:
      1. ``command_refresh_ocr_models`` is invoked exactly once.
      2. Both select widgets' ``.options`` are re-read from app state and
         ``.update()`` is called on each (so the NiceGUI client re-renders).
      3. A positive notification fires.
      4. The dialog is NOT closed — the user typically rescans then picks a
         new model and only closes via Apply or Cancel.
    """

    async def test_rescan_success_refreshes_options_and_notifies(self, monkeypatch):
        app_state = Mock()
        app_state.command_refresh_ocr_models = Mock(return_value=True)
        app_state.ocr_detection_model_options = {"huggingface": "Hugging Face"}
        app_state.ocr_recognition_model_options = {"huggingface": "Hugging Face"}
        app_state.selected_ocr_detection_model_key = "huggingface"
        app_state.selected_ocr_recognition_model_key = "huggingface"
        modal = _build_modal_with_mock_widgets(app_state_model=app_state)

        # Currently-selected values are still valid in the refreshed options.
        modal._detection_model_select.value = "huggingface"
        modal._recognition_model_select.value = "huggingface"

        notify_mock = MagicMock()
        monkeypatch.setattr(modal, "_notify", notify_mock)

        await modal._rescan_models()

        app_state.command_refresh_ocr_models.assert_called_once_with()
        # Options re-bound from app state.
        assert modal._detection_model_select.options == {"huggingface": "Hugging Face"}
        assert modal._recognition_model_select.options == {"huggingface": "Hugging Face"}
        # Both selects redrawn.
        modal._detection_model_select.update.assert_called_once_with()
        modal._recognition_model_select.update.assert_called_once_with()
        # Positive notification only.
        notify_mock.assert_called_once_with("OCR model list refreshed", "positive")
        # Modal stays open.
        modal._dialog.close.assert_not_called()


class TestRescanModelsFailurePath:
    """``_rescan_models`` failure path: refresh returns False, negative notification.

    The select widgets are still re-synced from app state even on failure
    (because the app-state model may have been partially updated), but the
    user-facing notification is negative and the dialog stays open.
    """

    async def test_rescan_failure_emits_negative_notification(self, monkeypatch):
        app_state = Mock()
        app_state.command_refresh_ocr_models = Mock(return_value=False)
        app_state.ocr_detection_model_options = {"huggingface": "Hugging Face"}
        app_state.ocr_recognition_model_options = {"huggingface": "Hugging Face"}
        app_state.selected_ocr_detection_model_key = "huggingface"
        app_state.selected_ocr_recognition_model_key = "huggingface"
        modal = _build_modal_with_mock_widgets(app_state_model=app_state)

        modal._detection_model_select.value = "huggingface"
        modal._recognition_model_select.value = "huggingface"

        notify_mock = MagicMock()
        monkeypatch.setattr(modal, "_notify", notify_mock)

        await modal._rescan_models()

        app_state.command_refresh_ocr_models.assert_called_once_with()
        notify_mock.assert_called_once_with("Failed to refresh OCR model list", "negative")
        modal._dialog.close.assert_not_called()


class TestRescanModelsOptionDisappearance:
    """When a previously-selected option vanishes after rescan, fall back to
    the app-state's currently-selected key rather than leaving a dangling value.

    This pins the recovery behavior of the
    ``if value not in options: value = selected_key`` guards on lines 153-159
    and 165-171.  Without this fallback the select widget would briefly show
    a value that's no longer in its options list, causing NiceGUI to render
    a blank/inconsistent select.
    """

    async def test_rescan_recovers_when_selected_value_disappears(self, monkeypatch):
        app_state = Mock()
        app_state.command_refresh_ocr_models = Mock(return_value=True)
        # After rescan, "old-model" is no longer offered.  App state has
        # already been updated to a fallback selection.
        app_state.ocr_detection_model_options = {"huggingface": "Hugging Face"}
        app_state.ocr_recognition_model_options = {"huggingface": "Hugging Face"}
        app_state.selected_ocr_detection_model_key = "huggingface"
        app_state.selected_ocr_recognition_model_key = "huggingface"
        modal = _build_modal_with_mock_widgets(app_state_model=app_state)

        # User had previously picked a model that's now gone.
        modal._detection_model_select.value = "old-detection-model"
        modal._recognition_model_select.value = "old-recognition-model"

        notify_mock = MagicMock()
        monkeypatch.setattr(modal, "_notify", notify_mock)

        await modal._rescan_models()

        # Both selects fall back to the app-state's selected key.
        assert modal._detection_model_select.value == "huggingface"
        assert modal._recognition_model_select.value == "huggingface"
        notify_mock.assert_called_once_with("OCR model list refreshed", "positive")


class TestRescanModelsWithoutBuiltSelects:
    """Defensive: ``_rescan_models`` tolerates unbuilt select widgets.

    If the modal hasn't been built yet (or has been partially torn down),
    the select widget attributes can be ``None``.  The handler must skip
    the option-resync block without raising and still emit the appropriate
    notification.
    """

    async def test_rescan_skips_resync_when_selects_are_none(self, monkeypatch):
        app_state = Mock()
        app_state.command_refresh_ocr_models = Mock(return_value=True)
        modal = _build_modal_with_mock_widgets(app_state_model=app_state)
        modal._detection_model_select = None
        modal._recognition_model_select = None

        notify_mock = MagicMock()
        monkeypatch.setattr(modal, "_notify", notify_mock)

        # Must not raise.
        await modal._rescan_models()

        app_state.command_refresh_ocr_models.assert_called_once_with()
        notify_mock.assert_called_once_with("OCR model list refreshed", "positive")


class TestApplySelectionPartialCommit:
    """Characterize the partial-commit failure documented in iter-33 review.

    When the HF pin setter succeeds but ``command_set_selected_ocr_models``
    fails, the current implementation has *already committed* the pin
    change before discovering the failure — leaving the modal in a
    half-applied state: the pin is persisted, but the user-visible models
    are not, and the dialog stays open with a negative notification.

    This is documented as iter-33 finding 4.1.  This test pins the
    *current* behavior so any future fix to make the apply atomic
    (rollback the pin, or pre-validate the model keys before committing
    the pin) deliberately fails this test, forcing the test to be updated
    in lockstep with the production fix.
    """

    async def test_models_failure_after_pin_commit_leaves_pin_committed(self, monkeypatch):
        app_state = Mock()
        app_state.hf_pinned_revision = "v1.0.0"
        app_state.command_set_hf_pinned_revision = Mock(return_value=True)
        # Models setter fails — simulating either a bad key or a
        # post-rescan disappearance of the previously-valid option.
        app_state.command_set_selected_ocr_models = Mock(return_value=False)
        modal = _build_modal_with_mock_widgets(app_state_model=app_state)
        _wire_apply_selection_inputs(
            modal,
            detection_value="huggingface",
            recognition_value="huggingface",
            revision_value="v2.0.0",  # pin changes
        )

        notify_mock = MagicMock()
        monkeypatch.setattr(modal, "_notify", notify_mock)

        await modal._apply_selection()

        # Pin was committed BEFORE the models setter failed.  This is the
        # partial-commit hazard.
        app_state.command_set_hf_pinned_revision.assert_called_once_with("v2.0.0")
        app_state.command_set_selected_ocr_models.assert_called_once()
        # Negative notification fires.
        notify_mock.assert_called_once_with("Failed to apply OCR models", "negative")
        # Dialog stays open so the user can correct the selection.
        modal._dialog.close.assert_not_called()
