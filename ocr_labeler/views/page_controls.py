from __future__ import annotations

from nicegui import ui

if True:  # pragma: no cover - UI wrapper file

    class PageControls:
        """Navigation + open directory row."""

        def __init__(
            self, state, on_prev, on_next, on_goto, on_save_page=None, on_load_page=None
        ):
            self.state = state
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

        def build(self) -> ui.element:
            with ui.row().classes("items-center gap-2") as row:
                self.row = row
                # Non-clickable button-style box for current page (PNG filename)
                self.page_index_box = (
                    ui.button("-", on_click=lambda: None).classes(
                        "pointer-events-none"
                    )  # visually identical to button, no interaction
                )
                ui.button("Prev", on_click=self._on_prev)
                ui.button("Next", on_click=self._on_next)
                ui.button(
                    "Go To:", on_click=lambda: self._on_goto(self.page_input.value)
                )
                self.page_input = (
                    ui.number(label="Page", value=1, min=1, format="%d")
                    .on("keydown.enter", lambda e: self._on_goto(self.page_input.value))
                    .on("blur", lambda e: self._on_goto(self.page_input.value))
                )
                self.page_total = ui.label("")

                # Add Save Page button if callback provided
                if self._on_save_page:
                    ui.separator().props("vertical")
                    self.save_button = ui.button(
                        "Save Page", on_click=self._on_save_page
                    ).classes("bg-green-600 hover:bg-green-700 text-white")

                # Add Load Page button if callback provided
                if self._on_load_page:
                    ui.separator().props("vertical")
                    self.load_button = ui.button(
                        "Load Page", on_click=self._on_load_page
                    ).classes("bg-blue-600 hover:bg-blue-700 text-white")
            return row

        # Convenience for refresh
        def set_page(self, index_plus_one: int, name: str, total: int):
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
