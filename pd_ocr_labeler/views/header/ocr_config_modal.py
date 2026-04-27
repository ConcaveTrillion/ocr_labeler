from __future__ import annotations

from nicegui import events, ui

from ...viewmodels.app.app_state_view_model import AppStateViewModel
from ...viewmodels.project.project_state_view_model import ProjectStateViewModel
from ..shared.button_styles import style_action_button
from ..shared.view_helpers import NotificationMixin


class OCRConfigModal(NotificationMixin):
    """Modal for configuring OCR model selection from trainer outputs."""

    def __init__(
        self,
        app_state_model: AppStateViewModel,
        project_state_model: ProjectStateViewModel,
    ):
        self.app_state_model = app_state_model
        self._app_state_view_model = app_state_model
        self.project_state_model = project_state_model
        self._notified_error_keys: set[str] = set()
        self._dialog: ui.dialog | None = None
        self._model_select: ui.select | None = None
        self._trigger_button: ui.button | None = None

    def build(self) -> ui.button:
        """Build the modal and return its trigger button."""
        with (
            ui.dialog() as self._dialog,
            ui.card().classes("min-w-[36rem] max-w-[90vw]"),
        ):
            ui.label("OCR Configuration").classes("text-lg font-bold")
            ui.label(
                "Select built-in OCR or a fine-tuned model pair produced by pd-ocr-trainer."
            ).classes("text-sm text-gray-500")

            self._model_select = ui.select(
                label="OCR model",
                options=self.app_state_model.ocr_model_options,
                value=self.app_state_model.selected_ocr_model_key,
                with_input=True,
            ).classes("w-full")

            self._bind_from_safe(
                self._model_select,
                "options",
                self.app_state_model,
                "ocr_model_options",
                key="ocr-model-options-binding",
                message="OCR model list may not refresh automatically",
            )

            with ui.row().classes("w-full justify-between pt-2"):
                ui.button("Rescan Models", on_click=self._rescan_models).props("flat")
                with ui.row().classes("gap-2"):
                    ui.button("Cancel", on_click=self._close).props("flat")
                    ui.button("Apply", on_click=self._apply_selection)

        self._trigger_button = ui.button(icon="tune", on_click=self._open)
        style_action_button(self._trigger_button, size="md")
        self._bind_disabled_from_safe(
            self._trigger_button,
            self.project_state_model,
            "is_controls_disabled",
            key="ocr-config-trigger-disabled-binding",
            message="OCR config button may not reflect disabled state",
        )
        return self._trigger_button

    async def _open(
        self,
        _event: events.ClickEventArguments | None = None,
    ) -> None:
        self.app_state_model.command_refresh_ocr_models()
        if self._model_select is not None:
            self._model_select.options = self.app_state_model.ocr_model_options
            self._model_select.value = self.app_state_model.selected_ocr_model_key
            self._model_select.update()
        if self._dialog is not None:
            self._dialog.open()

    async def _close(
        self,
        _event: events.ClickEventArguments | None = None,
    ) -> None:
        if self._dialog is not None:
            self._dialog.close()

    async def _rescan_models(
        self,
        _event: events.ClickEventArguments | None = None,
    ) -> None:
        success = self.app_state_model.command_refresh_ocr_models()
        if self._model_select is not None:
            self._model_select.options = self.app_state_model.ocr_model_options
            if self._model_select.value not in self.app_state_model.ocr_model_options:
                self._model_select.value = self.app_state_model.selected_ocr_model_key
            self._model_select.update()

        if success:
            self._notify("OCR model list refreshed", "positive")
        else:
            self._notify("Failed to refresh OCR model list", "negative")

    async def _apply_selection(
        self,
        _event: events.ClickEventArguments | None = None,
    ) -> None:
        if self._model_select is None:
            return
        selected_key = str(self._model_select.value or "").strip()
        if not selected_key:
            self._notify("Select an OCR model first", "warning")
            return

        success = self.app_state_model.command_set_selected_ocr_model(selected_key)
        if success:
            self._notify("OCR model updated", "positive")
            if self._dialog is not None:
                self._dialog.close()
        else:
            self._notify("Failed to apply OCR model", "negative")

    def sync_control_state(self) -> None:
        """Force trigger button enabled state to the latest computed value."""
        if self._trigger_button is None:
            return
        enabled = not bool(
            getattr(self.project_state_model, "is_controls_disabled", False)
        )
        self._trigger_button.set_enabled(enabled)
        self._trigger_button.update()
