from __future__ import annotations

import logging

from nicegui import binding, ui

from ....viewmodels.project.project_state_view_model import ProjectStateViewModel

logger = logging.getLogger(__name__)


class PageActions:  # pragma: no cover - UI wrapper file
    """Page-level actions independent from project-level navigation."""

    def __init__(
        self,
        viewmodel: ProjectStateViewModel,
        on_save_page=None,
        on_load_page=None,
        on_refine_bboxes=None,
        on_expand_refine_bboxes=None,
        on_reload_ocr=None,
    ):
        logger.debug("Initializing PageActions")
        self.viewmodel = viewmodel
        self._on_save_page = on_save_page
        self._on_load_page = on_load_page
        self._on_refine_bboxes = on_refine_bboxes
        self._on_expand_refine_bboxes = on_expand_refine_bboxes
        self._on_reload_ocr = on_reload_ocr

        self.save_button = None
        self.load_button = None
        self.reload_ocr_button = None
        self.refine_bboxes_button = None
        self.expand_refine_bboxes_button = None

    def build(self) -> ui.element:
        logger.debug("Building PageActions UI")
        with ui.row().classes("items-center gap-2") as container:
            if self._on_reload_ocr:
                self.reload_ocr_button = ui.button(
                    "Reload OCR", on_click=self._on_reload_ocr
                ).classes("bg-orange-600 hover:bg-orange-700 text-white")

            if self._on_save_page:
                self.save_button = ui.button(
                    "Save Page", on_click=self._on_save_page
                ).classes("bg-green-600 hover:bg-green-700 text-white")

            if self._on_load_page:
                self.load_button = ui.button(
                    "Load Page", on_click=self._on_load_page
                ).classes("bg-blue-600 hover:bg-blue-700 text-white")

            if self._on_refine_bboxes:
                self.refine_bboxes_button = ui.button(
                    "Refine Bboxes", on_click=self._on_refine_bboxes
                ).classes("bg-purple-600 hover:bg-purple-700 text-white")

            if self._on_expand_refine_bboxes:
                self.expand_refine_bboxes_button = ui.button(
                    "Expand & Refine", on_click=self._on_expand_refine_bboxes
                ).classes("bg-indigo-600 hover:bg-indigo-700 text-white")

        self._bind_disabled_states()
        return container

    def _bind_disabled_states(self) -> None:
        """Bind disabled state from view model to all page action buttons."""
        buttons = [
            self.reload_ocr_button,
            self.save_button,
            self.load_button,
            self.refine_bboxes_button,
            self.expand_refine_bboxes_button,
        ]

        for button in buttons:
            if button is None:
                continue
            try:
                binding.bind_from(
                    button,
                    "disabled",
                    self.viewmodel,
                    "is_controls_disabled",
                )
            except Exception:
                logger.debug(
                    "Failed to bind disabled state for page action button",
                    exc_info=True,
                )
