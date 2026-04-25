"""Export dialog for DocTR training data export."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Callable

from nicegui import ui

if TYPE_CHECKING:
    from ....viewmodels.project.project_state_view_model import (
        ProjectStateViewModel,
    )

logger = logging.getLogger(__name__)


class ExportDialog:  # pragma: no cover - UI wrapper file
    """Modal dialog offering export options: all pages, current page, per-style."""

    def __init__(
        self,
        project_viewmodel: "ProjectStateViewModel",
        notify: Callable[[str, str], None],
    ):
        self._vm = project_viewmodel
        self._notify = notify
        self._dialog: ui.dialog | None = None
        self._results_container: ui.column | None = None
        self._style_checkboxes_container: ui.column | None = None
        self._all_checkbox: ui.checkbox | None = None
        self._style_checkboxes: dict[str, ui.checkbox] = {}
        self._updating_checkboxes = False
        self._scope_radio: ui.radio | None = None
        self._export_button: ui.button | None = None
        self._pages_loaded = False

    def build(self) -> ui.dialog:
        """Build and return the dialog (call once during view setup)."""
        with (
            ui.dialog() as self._dialog,
            ui.card().classes("min-w-[28rem] max-w-[90vw]"),
        ):
            ui.label("Export to DocTR Training Format").classes("text-lg font-bold")
            ui.label(
                "All exports require every word on the page to be validated."
            ).classes("text-sm text-gray-500")

            ui.separator()
            ui.label("Export Scope").classes("text-sm font-semibold")
            self._scope_radio = ui.radio(
                {"current": "Current Page", "all": "All Validated Pages"},
                value="current",
                on_change=self._on_scope_changed,
            ).props("inline")

            ui.separator()
            ui.label("Style Filter").classes("text-sm font-semibold")
            ui.label(
                "Select which styles to include in the export. "
                "'All' exports every word regardless of style."
            ).classes("text-xs text-gray-500")

            self._style_checkboxes_container = ui.column().classes("w-full gap-0")

            ui.separator()

            self._export_button = ui.button(
                "Export",
                on_click=self._on_export_clicked,
            ).props("outline")

            ui.separator()
            self._results_container = ui.column().classes("w-full gap-1")

            with ui.row().classes("w-full justify-end pt-2"):
                ui.button("Close", on_click=self._dialog.close).props("flat")

        return self._dialog

    def open(self) -> None:
        """Open the dialog and refresh style checkboxes."""
        if self._dialog is None:
            logger.warning("ExportDialog.open() called but dialog is None")
            return
        # Reset to current-page scope each time
        if self._scope_radio:
            self._scope_radio.set_value("current")
        self._pages_loaded = False
        try:
            self._refresh_style_checkboxes()
        except Exception:
            logger.exception("Failed to refresh style checkboxes")
        if self._results_container:
            self._results_container.clear()
        self._dialog.open()

    async def _on_scope_changed(self, _e) -> None:
        """When scope changes to 'all', load saved pages from disk."""
        if self._scope_radio is None or self._scope_radio.value != "all":
            return
        if self._pages_loaded:
            # Already loaded this session
            self._refresh_style_checkboxes()
            return

        self._notify("Loading saved pages from disk...", "info")
        if self._results_container:
            self._results_container.clear()
            with self._results_container:
                ui.spinner(size="sm")
                ui.label("Loading saved pages...").classes("text-sm text-gray-500")

        await asyncio.sleep(0.1)

        try:
            loaded = self._vm.load_all_saved_pages()
            self._pages_loaded = True
            if self._results_container:
                self._results_container.clear()
            if loaded > 0:
                self._notify(f"Loaded {loaded} page(s) from disk", "positive")
            else:
                self._notify("All saved pages already in memory", "info")
            self._refresh_style_checkboxes()
        except Exception:
            logger.exception("Failed to load saved pages")
            self._notify("Failed to load saved pages", "warning")
            if self._results_container:
                self._results_container.clear()

    def _refresh_style_checkboxes(self) -> None:
        """Populate style checkboxes based on available styles."""
        if self._style_checkboxes_container is None:
            return
        self._style_checkboxes_container.clear()
        self._style_checkboxes.clear()
        self._all_checkbox = None

        styles = self._vm.get_available_styles()
        current_page_styles = self._vm.get_current_page_styles()
        scope_is_current = (
            self._scope_radio is not None and self._scope_radio.value == "current"
        )

        with self._style_checkboxes_container:
            self._all_checkbox = ui.checkbox(
                "All (no style filter)", value=True, on_change=self._on_all_toggled
            )
            if not styles:
                ui.label("No specific styles found on validated pages.").classes(
                    "text-sm text-gray-400 italic pl-4"
                )
            else:
                for style in styles:
                    cb = ui.checkbox(
                        style.title(),
                        value=False,
                        on_change=self._on_style_toggled,
                    ).classes("pl-4")
                    if scope_is_current and style not in current_page_styles:
                        cb.props("disable")
                        cb.tooltip("No words with this style on the current page")
                    self._style_checkboxes[style] = cb

    def _on_all_toggled(self, _e) -> None:
        """When 'All' is checked, uncheck individual styles; vice versa."""
        if self._updating_checkboxes or self._all_checkbox is None:
            return
        self._updating_checkboxes = True
        try:
            if self._all_checkbox.value:
                for cb in self._style_checkboxes.values():
                    cb.set_value(False)
        finally:
            self._updating_checkboxes = False

    def _on_style_toggled(self, _e) -> None:
        """When any style checkbox changes, update the 'All' checkbox."""
        if self._updating_checkboxes or self._all_checkbox is None:
            return
        self._updating_checkboxes = True
        try:
            any_checked = any(cb.value for cb in self._style_checkboxes.values())
            if any_checked:
                self._all_checkbox.set_value(False)
            elif not any_checked and not self._all_checkbox.value:
                # Nothing selected — re-enable All
                self._all_checkbox.set_value(True)
        finally:
            self._updating_checkboxes = False

    def _get_selected_styles(self) -> list[str]:
        """Return list of selected style names, empty means all/unfiltered."""
        if self._all_checkbox and self._all_checkbox.value:
            return []
        return [s for s, cb in self._style_checkboxes.items() if cb.value]

    async def _on_export_clicked(self) -> None:
        """Handle Export button click — use radio scope."""
        scope = self._scope_radio.value if self._scope_radio else "current"
        await self._run_selected_export(scope)

    async def _run_selected_export(self, scope: str) -> None:
        """Run export for all selected styles (or unfiltered if 'All')."""
        selected = self._get_selected_styles()
        if not selected:
            # "All" mode — single unfiltered export
            await self._run_export(scope, "all")
        else:
            # Export each selected style separately into its own subfolder
            for style in selected:
                await self._run_export(scope, style)

    async def _run_export(self, scope: str, style: str) -> None:
        """Execute an export operation.

        Parameters
        ----------
        scope : ``"current"`` or ``"all"``
        style : ``"all"`` for unfiltered, or a style label name
        """
        from ....operations.export.doctr_export import WordFilter

        word_filter = None
        subfolder = style
        if style != "all":
            word_filter = WordFilter(style_labels=frozenset({style}))

        if self._results_container:
            self._results_container.clear()
            with self._results_container:
                ui.spinner(size="sm")
                ui.label("Exporting...").classes("text-sm text-gray-500")

        await asyncio.sleep(0.1)

        try:
            if scope == "current":
                stats = self._vm.command_export_page(
                    subfolder=subfolder,
                    word_filter=word_filter,
                )
            else:
                stats = self._vm.command_export_all_pages(
                    subfolder=subfolder,
                    word_filter=word_filter,
                )

            self._show_results(scope, style, stats)
        except ValueError as exc:
            self._show_error(str(exc))
        except Exception as exc:  # noqa: BLE001
            logger.error("Export failed: %s", exc)
            self._show_error(f"Export failed: {exc}")

    def _show_results(self, scope: str, style: str, stats) -> None:
        """Display export results in the dialog."""
        if self._results_container is None:
            return
        self._results_container.clear()

        label = f"{scope.title()} / {style}"
        with self._results_container:
            if stats.pages_exported > 0:
                ui.label(
                    f"✅ {label}: {stats.pages_exported} page(s) exported — "
                    f"{stats.words_exported_detection} detection, "
                    f"{stats.words_exported_recognition} recognition words"
                ).classes("text-sm text-green-700")
                if stats.pages_skipped_not_validated:
                    ui.label(
                        f"⚠️ {stats.pages_skipped_not_validated} page(s) skipped "
                        f"(not validated)"
                    ).classes("text-sm text-orange-600")
                self._notify(
                    f"Exported {stats.pages_exported} page(s) to '{style}/'",
                    "positive",
                )
            elif stats.pages_scanned > 0:
                ui.label(
                    f"⚠️ {label}: No pages exported "
                    f"({stats.pages_skipped_not_validated} not validated, "
                    f"{stats.pages_skipped_no_image} no image)"
                ).classes("text-sm text-orange-600")
                self._notify("No pages exported", "warning")
            else:
                ui.label(f"⚠️ {label}: No pages available").classes(
                    "text-sm text-orange-600"
                )

    def _show_error(self, message: str) -> None:
        """Display an error in the dialog results area."""
        if self._results_container is None:
            return
        self._results_container.clear()
        with self._results_container:
            ui.label(f"❌ {message}").classes("text-sm text-red-600")
        self._notify(message, "warning")
