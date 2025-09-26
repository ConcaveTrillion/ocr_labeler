from __future__ import annotations

import logging

from nicegui import ui

from ....viewmodels.project.project_state_view_model import ProjectStateViewModel

logger = logging.getLogger(__name__)


class PageControls:  # pragma: no cover - UI wrapper file
    """Navigation + open directory row."""

    def __init__(
        self,
        viewmodel: ProjectStateViewModel,
        on_prev,
        on_next,
        on_goto,
        on_save_page=None,
        on_load_page=None,
    ):
        logger.debug("Initializing PageControls")
        self.viewmodel = viewmodel
        self._on_prev = on_prev
        self._on_next = on_next
        self._on_goto = on_goto
        self._on_save_page = on_save_page
        self._on_load_page = on_load_page
        # UI refs
        self.row = None
        self.page_index_box = (
            None  # non-interactive button-style box showing current page name
        )
        self.dir_input = None
        self.page_input = None
        self.page_name = None
        self.page_total = None
        self.save_button = None
        self.load_button = None
        self.reload_ocr_button = None
        self.page_source_label = None

    def build(self) -> ui.element:
        logger.debug("Building PageControls UI")
        with ui.column().classes("gap-2") as container:
            # First row: Navigation controls
            with ui.row().classes("items-center gap-2"):
                ui.button("Prev", on_click=self._on_prev)
                ui.button("Next", on_click=self._on_next)
                ui.button(
                    "Go To:", on_click=lambda: self._on_goto(self.page_input.value)
                )
                self.page_input = (
                    ui.number(label="Page", value=1, min=1, format="%d")
                    .on(
                        "keydown.enter",
                        lambda e: self._on_goto(self.page_input.value),
                    )
                    .on("blur", lambda e: self._on_goto(self.page_input.value))
                )
                self.page_total = ui.label("")

                # Add Reload with OCR button
                ui.separator().props("vertical")
                self.reload_ocr_button = ui.button(
                    "Reload OCR", on_click=self._reload_with_ocr
                ).classes("bg-orange-600 hover:bg-orange-700 text-white")

            # Second row: Page info
            with ui.row().classes("items-center gap-2"):
                # Non-clickable button-style box for current page (PNG filename)
                self.page_index_box = (
                    ui.button("-", on_click=lambda: None).classes(
                        "pointer-events-none"
                    )  # visually identical to button, no interaction
                )

                # Page source indicator
                ui.separator().props("vertical")
                self.page_source_label = (
                    ui.button("UNKNOWN", on_click=lambda: None).classes(
                        "pointer-events-none"
                    )  # visually identical to button, no interaction
                )

                # Save and Load buttons
                if self._on_save_page:
                    ui.separator().props("vertical")
                    self.save_button = ui.button(
                        "Save Page", on_click=self._on_save_page
                    ).classes("bg-green-600 hover:bg-green-700 text-white")

                if self._on_load_page:
                    ui.separator().props("vertical")
                    self.load_button = ui.button(
                        "Load Page", on_click=self._on_load_page
                    ).classes("bg-blue-600 hover:bg-blue-700 text-white")

        return container

    # Convenience for refresh
    def set_page(self, index_plus_one: int, name: str, total: int):
        logger.debug(f"Setting page to {index_plus_one}, name: {name}, total: {total}")
        # Update page name display box (styled like a disabled button)
        if self.page_index_box:
            try:
                # NiceGUI button stores its label text in .text
                self.page_index_box.text = name if name else "-"
            except Exception:  # pragma: no cover - defensive
                pass
        if self.page_input:
            self.page_input.value = index_plus_one
        if self.page_total:
            self.page_total.text = f"/ {total}" if total else "/ 0"

        # Update page source
        if self.page_source_label:
            try:
                # For now, access through the underlying state
                # TODO: Add page source to viewmodel
                if hasattr(self.viewmodel, "_project_state"):
                    self.page_source_label.text = (
                        self.viewmodel._project_state.current_page_source_text
                    )
                else:
                    self.page_source_label.text = "UNKNOWN"
            except Exception:  # pragma: no cover - defensive
                pass

    def _reload_with_ocr(self):
        """Reload the current page with OCR processing."""
        logger.debug("Reloading page with OCR")
        try:
            # For now, access through the underlying state
            # TODO: Add reload command to viewmodel
            if hasattr(self.viewmodel, "_project_state"):
                self.viewmodel._project_state.reload_current_page_with_ocr()
                logger.debug("Page reloaded with OCR successfully")
                ui.notify("Page reloaded with OCR", type="positive")
            else:
                logger.error("Cannot reload OCR - no access to project state")
                ui.notify("Cannot reload OCR - state not available", type="negative")
        except Exception as e:
            logger.error(f"Failed to reload with OCR: {e}")
            ui.notify(f"Failed to reload with OCR: {e}", type="negative")
