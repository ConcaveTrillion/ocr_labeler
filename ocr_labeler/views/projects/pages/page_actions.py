from __future__ import annotations

import logging

from nicegui import binding, ui

from ....viewmodels.project.page_state_view_model import PageStateViewModel
from ....viewmodels.project.project_state_view_model import ProjectStateViewModel
from ...callbacks import PageActionCallback
from ...shared.button_styles import style_action_button

logger = logging.getLogger(__name__)


class PageActions:  # pragma: no cover - UI wrapper file
    """Page-level actions independent from project-level navigation."""

    def __init__(
        self,
        project_viewmodel: ProjectStateViewModel,
        page_viewmodel: PageStateViewModel,
        on_save_page: PageActionCallback | None = None,
        on_load_page: PageActionCallback | None = None,
        on_reload_ocr: PageActionCallback | None = None,
    ):
        logger.debug("Initializing PageActions")
        self.project_viewmodel = project_viewmodel
        self.page_viewmodel = page_viewmodel
        self._on_save_page = on_save_page
        self._on_load_page = on_load_page
        self._on_reload_ocr = on_reload_ocr

        self.save_button = None
        self.load_button = None
        self.reload_ocr_button = None
        self.page_name_box = None
        self.page_source_label = None
        self.page_source_tooltip = None
        self._notified_error_keys: set[str] = set()

    def _notify(self, message: str, type_: str = "warning") -> None:
        """Route notifications through session queue with UI fallback."""
        app_state_model = getattr(self.project_viewmodel, "_app_state_model", None)
        app_state = getattr(app_state_model, "_app_state", None)
        if app_state is not None:
            app_state.queue_notification(message, type_)
            return
        ui.notify(message, type=type_)

    def _notify_once(self, key: str, message: str, type_: str = "warning") -> None:
        """Emit a notification once per key to avoid toast spam."""
        if key in self._notified_error_keys:
            return
        self._notified_error_keys.add(key)
        self._notify(message, type_)

    def _bind_from_safe(
        self,
        target: object,
        target_property: str,
        source: object,
        source_property: str,
        *,
        key: str,
        message: str,
    ) -> None:
        """Bind with user-visible warning if binding setup fails."""
        try:
            binding.bind_from(
                target,
                target_property,
                source,
                source_property,
            )
        except Exception:
            logger.exception(
                "Binding failed: %s.%s <- %s.%s",
                type(target).__name__,
                target_property,
                type(source).__name__,
                source_property,
            )
            self._notify_once(key, message, type_="warning")

    def build(self) -> ui.element:
        logger.debug("Building PageActions UI")
        with ui.row().classes("items-center gap-2") as container:
            if self._on_reload_ocr:
                self.reload_ocr_button = ui.button(
                    "Reload OCR", on_click=self._on_reload_ocr
                )
                style_action_button(self.reload_ocr_button, size="md")

            if self._on_save_page:
                self.save_button = ui.button("Save Page", on_click=self._on_save_page)
                style_action_button(self.save_button, size="md")

            if self._on_load_page:
                self.load_button = ui.button("Load Page", on_click=self._on_load_page)
                style_action_button(self.load_button, size="md")

            ui.separator().props("vertical")
            self.page_name_box = ui.button("-", on_click=lambda _event: None).classes(
                "pointer-events-none"
            )

            self.page_source_label = ui.button(
                "", on_click=lambda _event: None
            ).classes("pointer-events-none")
            with self.page_source_label:
                self.page_source_tooltip = ui.tooltip("")
            self._bind_from_safe(
                self.page_source_label,
                "text",
                self.page_viewmodel,
                "current_page_source_text",
                key="page-actions-source-text-binding",
                message="Page source label may not update automatically",
            )
            if self.page_source_tooltip:
                self._bind_from_safe(
                    self.page_source_tooltip,
                    "text",
                    self.page_viewmodel,
                    "current_page_source_tooltip",
                    key="page-actions-source-tooltip-binding",
                    message="Page source tooltip may not update automatically",
                )

        self._bind_disabled_states()
        return container

    def set_page_metadata(self, name: str) -> None:
        """Update page-level metadata labels."""
        if self.page_name_box:
            self.page_name_box.text = name if name else "-"

    def _bind_disabled_states(self) -> None:
        """Bind disabled state from view model to all page action buttons."""
        buttons = [
            self.reload_ocr_button,
            self.save_button,
            self.load_button,
        ]

        for button in buttons:
            if button is None:
                continue
            self._bind_from_safe(
                button,
                "disable",
                self.project_viewmodel,
                "is_controls_disabled",
                key="page-actions-controls-disabled-binding",
                message="Some page action buttons may not reflect disabled state",
            )
