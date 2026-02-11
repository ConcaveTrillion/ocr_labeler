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
        on_refine_bboxes=None,
        on_expand_refine_bboxes=None,
        on_reload_ocr=None,
    ):
        logger.debug("Initializing PageControls")
        self.viewmodel = viewmodel
        self._on_prev = on_prev
        self._on_next = on_next
        self._on_goto = on_goto
        self._on_save_page = on_save_page
        self._on_load_page = on_load_page
        self._on_refine_bboxes = on_refine_bboxes
        self._on_expand_refine_bboxes = on_expand_refine_bboxes
        self._on_reload_ocr = on_reload_ocr
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
        self.refine_bboxes_button = None
        self.expand_refine_bboxes_button = None
        self.page_source_label = None

    def build(self) -> ui.element:
        logger.debug("Building PageControls UI")
        with ui.column().classes("gap-2") as container:
            # First row: Navigation controls
            with ui.row().classes("items-center gap-2"):
                # Prev: disabled when controls are disabled or cannot navigate prev
                self.prev_button = ui.button("Prev", on_click=self._on_prev)
                # Next: disabled when controls are disabled or cannot navigate next
                self.next_button = ui.button("Next", on_click=self._on_next)
                # Go To: disable when controls are disabled
                self.goto_button = ui.button(
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

                # Bind disabled state from viewmodel using NiceGUI binding helpers.
                # Use the viewmodel's derived boolean properties (prev_disabled,
                # next_disabled, goto_disabled, and is_controls_disabled) so the
                # UI updates reactively without polling.
                try:
                    from nicegui import binding

                    # Buttons: bind their `disabled` property directly from the
                    # viewmodel derived flags.
                    binding.bind_from(
                        self.prev_button, "disabled", self.viewmodel, "prev_disabled"
                    )
                    binding.bind_from(
                        self.next_button, "disabled", self.viewmodel, "next_disabled"
                    )

                    # GoTo and page input
                    binding.bind_from(
                        self.goto_button, "disabled", self.viewmodel, "goto_disabled"
                    )
                    if self.page_input:
                        binding.bind_from(
                            self.page_input,
                            "disabled",
                            self.viewmodel,
                            "is_controls_disabled",
                        )

                    # Reload/Save/Load buttons disabled when controls disabled
                    if self.reload_ocr_button:
                        binding.bind_from(
                            self.reload_ocr_button,
                            "disabled",
                            self.viewmodel,
                            "is_controls_disabled",
                        )
                    if self.save_button:
                        binding.bind_from(
                            self.save_button,
                            "disabled",
                            self.viewmodel,
                            "is_controls_disabled",
                        )
                    if self.load_button:
                        binding.bind_from(
                            self.load_button,
                            "disabled",
                            self.viewmodel,
                            "is_controls_disabled",
                        )
                    if self.refine_bboxes_button:
                        binding.bind_from(
                            self.refine_bboxes_button,
                            "disabled",
                            self.viewmodel,
                            "is_controls_disabled",
                        )
                    if self.expand_refine_bboxes_button:
                        binding.bind_from(
                            self.expand_refine_bboxes_button,
                            "disabled",
                            self.viewmodel,
                            "is_controls_disabled",
                        )
                except Exception:
                    # Defensive - if binding fails, ignore and leave controls enabled
                    pass

            # Loading status row - shows what's happening during navigation
            with ui.row().classes("items-center gap-2"):
                self.loading_status_label = ui.label("").classes(
                    "text-sm text-gray-600 italic"
                )
                # Bind to viewmodel's loading_status property
                try:
                    from nicegui import binding

                    binding.bind_from(
                        self.loading_status_label,
                        "text",
                        self.viewmodel,
                        "loading_status",
                    )
                except Exception:
                    # Defensive - if binding fails, status just won't update
                    pass

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
                    ui.button("", on_click=lambda: None).classes(
                        "pointer-events-none"
                    )  # visually identical to button, no interaction
                )
                # Bind the text to viewmodel's current_page_source_text
                try:
                    from nicegui import binding

                    binding.bind_from(
                        self.page_source_label,
                        "text",
                        self.viewmodel,
                        "current_page_source_text",
                    )
                except Exception:
                    # Defensive - if binding fails, set static text
                    self.page_source_label.text = "UNKNOWN"

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

                if self._on_refine_bboxes:
                    ui.separator().props("vertical")
                    self.refine_bboxes_button = ui.button(
                        "Refine Bboxes", on_click=self._on_refine_bboxes
                    ).classes("bg-purple-600 hover:bg-purple-700 text-white")

                if self._on_expand_refine_bboxes:
                    self.expand_refine_bboxes_button = ui.button(
                        "Expand & Refine", on_click=self._on_expand_refine_bboxes
                    ).classes("bg-indigo-600 hover:bg-indigo-700 text-white")

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

        # Note: page_source_label is now bound to viewmodel.current_page_source_text
        # and updates automatically - no manual update needed

    async def _reload_with_ocr(self):
        """Reload the current page with OCR processing."""
        logger.debug("Reloading page with OCR")
        # If we have a dedicated callback, use it (it handles async/notifications)
        if self._on_reload_ocr:
            # NiceGUI can handle both sync and async callbacks in on_click
            # but since PROJECT_VIEW._reload_ocr_async is async, we should
            # just pass it or call it.
            import asyncio

            if asyncio.iscoroutinefunction(self._on_reload_ocr):
                await self._on_reload_ocr()
            else:
                self._on_reload_ocr()
            return

        # Fallback to direct viewmodel call
        try:
            if hasattr(self.viewmodel, "command_reload_page_with_ocr"):
                import asyncio

                success = await asyncio.to_thread(
                    self.viewmodel.command_reload_page_with_ocr
                )
                if success:
                    logger.debug("Page reloaded with OCR successfully")
                    ui.notify("Page reloaded with OCR", type="positive")
                else:
                    logger.warning("Page reload with OCR failed")
                    ui.notify("Failed to reload with OCR", type="negative")
            else:
                logger.error("Cannot reload OCR - viewmodel command not available")
                ui.notify("Cannot reload OCR - command not available", type="negative")
        except Exception as e:
            logger.error(f"Failed to reload with OCR: {e}")
            ui.notify(f"Failed to reload with OCR: {e}", type="negative")
