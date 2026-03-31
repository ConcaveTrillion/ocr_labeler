from __future__ import annotations

import logging
import os
from pathlib import Path

from nicegui import binding, events, ui

from ...routing import build_project_url
from ...viewmodels.app.app_state_view_model import AppStateViewModel
from ...viewmodels.project.project_state_view_model import ProjectStateViewModel
from ..shared.button_styles import style_action_button

logger = logging.getLogger(__name__)


class ProjectLoadControls:
    """Project selection + path label row.

    Responsibilities:
    - Let user choose and load a project
    - Show the fully resolved selected project directory path (right aligned, wrapped)
    """

    def __init__(
        self,
        app_state_model: AppStateViewModel,
        project_state_model: ProjectStateViewModel,
    ):
        self.app_state_model = app_state_model
        self.project_state_model = project_state_model
        self._notified_error_keys: set[str] = set()
        self._source_folder_dialog: ui.dialog | None = None
        self._source_path_input: ui.input | None = None
        self._path_picker_current_dir: Path = Path.home()
        self._path_picker_current_label: ui.label | None = None
        self._path_picker_breadcrumbs: ui.row | None = None
        self._path_picker_list_container: ui.column | None = None

    def _notify(self, message: str, type_: str = "info"):
        """Route notifications through per-session queue with UI fallback."""
        app_state = getattr(self.app_state_model, "_app_state", None)
        if app_state is not None:
            app_state.queue_notification(message, type_)
            return

        ui.notify(message, type=type_)

    def _notify_once(self, key: str, message: str, type_: str = "warning") -> None:
        """Emit a notification once per key to avoid repeated toasts."""
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

    def _bind_safe(
        self,
        target: object,
        target_property: str,
        source: object,
        source_property: str,
        *,
        key: str,
        message: str,
    ) -> None:
        """Two-way bind with user-visible warning if setup fails."""
        try:
            binding.bind(
                target,
                target_property,
                source,
                source_property,
            )
        except Exception:
            logger.exception(
                "Two-way binding failed: %s.%s <-> %s.%s",
                type(target).__name__,
                target_property,
                type(source).__name__,
                source_property,
            )
            self._notify_once(key, message, type_="warning")

    def _bind_disabled_from_safe(
        self,
        target: object,
        source: object,
        source_property: str,
        *,
        key: str,
        message: str,
    ) -> None:
        """Bind a disabled flag onto NiceGUI's enabled property safely."""
        try:
            target.bind_enabled_from(  # type: ignore[attr-defined]
                source,
                source_property,
                backward=lambda disabled: not bool(disabled),
            )
        except Exception:
            logger.exception(
                "Disabled binding failed: %s.enabled <- not %s.%s",
                type(target).__name__,
                type(source).__name__,
                source_property,
            )
            self._notify_once(key, message, type_="warning")

    def build(self) -> ui.element:
        with (
            ui.dialog() as self._source_folder_dialog,
            ui.card().classes("min-w-[42rem] max-w-[90vw]"),
        ):
            ui.label("Source Projects Folder").classes("text-lg font-bold")
            ui.label("Root folder scanned for project subdirectories.").classes(
                "text-sm text-gray-500"
            )
            self._path_picker_current_label = ui.label("").classes(
                "text-xs text-gray-600 font-mono break-all"
            )
            self._path_picker_breadcrumbs = ui.row().classes(
                "w-full items-center gap-1 flex-wrap"
            )
            self._source_path_input = ui.input("Path").classes("w-full font-mono")
            self._source_path_input.on("keydown.enter", self._on_source_path_enter)
            with ui.row().classes("w-full justify-between gap-2"):
                ui.button("Home", on_click=self._path_picker_go_home).props("flat")
                ui.button("Up", on_click=self._path_picker_go_up).props("flat")
                ui.button(
                    "Open Typed Path", on_click=self._open_typed_source_path
                ).props("flat")
            with ui.scroll_area().classes("w-full h-64 border rounded"):
                self._path_picker_list_container = ui.column().classes(
                    "w-full gap-1 p-2"
                )
            with ui.row().classes("w-full justify-end gap-2 pt-2"):
                ui.button("Use Current", on_click=self._use_current_folder).props(
                    "flat"
                )
                ui.button("Cancel", on_click=self._source_folder_dialog.close).props(
                    "flat"
                )
                ui.button("Apply", on_click=self._apply_source_folder)

        with ui.row().classes("w-full items-center gap-2") as row:
            # Bind select options and value to AppState model
            options = self.app_state_model.project_keys
            selected_key = self.app_state_model.selected_project_key
            if selected_key not in options:
                selected_key = None

            self.select = ui.select(
                label="Project",
                options=options,
                value=selected_key,
                with_input=False,
            )

            # LOAD button bound disabled state to is_loading
            self.load_project_button = ui.button(
                "LOAD", on_click=self._load_selected_project
            )
            style_action_button(self.load_project_button, size="md")

            self.source_folder_button = ui.button(
                icon="folder_open", on_click=self._open_source_folder_dialog
            )
            style_action_button(self.source_folder_button, size="md")

            ui.space()

            self.path_label = (
                ui.label("")
                .classes(
                    "text-xs text-gray-500 font-mono text-right flex-1 overflow-hidden"
                )
                .style("white-space:normal; word-break:break-all;")
            )

            self._bind_from_safe(
                self.select,
                "options",
                self.app_state_model,
                "project_keys",
                key="project-load-select-options-binding",
                message="Project list may not update automatically",
            )
            self._bind_safe(
                self.select,
                "value",
                self.app_state_model,
                "selected_project_key",
                key="project-load-select-value-binding",
                message="Project selection sync may not update automatically",
            )

            # Bind controls disabled state to combined busy/loading state
            controls = [
                self.select,
                self.load_project_button,
                self.source_folder_button,
            ]
            for control in controls:
                self._bind_disabled_from_safe(
                    control,
                    self.project_state_model,
                    "is_controls_disabled",
                    key="project-load-controls-disabled-binding",
                    message="Load controls may not reflect disabled state",
                )

            self._bind_from_safe(
                self.path_label,
                "text",
                self.project_state_model,
                "project_root_resolved",
                key="project-load-path-binding",
                message="Project path label may not update automatically",
            )
        self.sync_control_states()
        return row

    def sync_control_states(self) -> None:
        """Apply the latest disabled state directly to all load controls."""
        enabled = not bool(
            getattr(self.project_state_model, "is_controls_disabled", False)
        )

        for control in (
            getattr(self, "select", None),
            getattr(self, "load_project_button", None),
            getattr(self, "source_folder_button", None),
        ):
            if control is None:
                continue
            control.set_enabled(enabled)
            control.update()

    async def _load_selected_project(
        self,
        _event: events.ClickEventArguments | None = None,
    ):
        """Load the selected project using the ViewModel."""
        key = self.app_state_model.selected_project_key
        if not key:
            self._notify("No project selected", "warning")
            return

        # Prevent multiple clicks during loading
        if self.project_state_model.is_controls_disabled:
            logger.debug("Load button clicked while disabled, ignoring")
            return

        try:
            await self.app_state_model.command_load_selected_project()
            # Update browser URL to reflect the loaded project
            url = build_project_url(key)
            ui.navigate.history.replace(url)
            logger.debug(f"Browser URL updated to: {url}")
        except Exception as exc:  # noqa: BLE001
            self._notify(f"Load failed: {exc}", "negative")
            logger.error(f"Failed to load project '{key}': {exc}")

    async def _open_source_folder_dialog(
        self,
        _event: events.ClickEventArguments | None = None,
    ) -> None:
        """Pre-fill the source folder dialog with the current root and open it."""
        start_dir = Path.home()
        raw = self.app_state_model.source_projects_root_str
        if self._source_path_input is not None:
            self._source_path_input.value = raw
        if raw:
            try:
                candidate = Path(raw).expanduser().resolve()
                candidate.mkdir(parents=True, exist_ok=True)
                if candidate.is_dir():
                    start_dir = candidate
            except Exception:
                logger.warning("Failed to prepare source root '%s'", raw, exc_info=True)
        self._path_picker_current_dir = start_dir
        self._path_picker_refresh()
        if self._source_folder_dialog is not None:
            self._source_folder_dialog.open()

    def _path_picker_refresh(self) -> None:
        """Refresh picker UI state for current directory."""
        if self._path_picker_current_label is not None:
            self._path_picker_current_label.text = str(self._path_picker_current_dir)

        self._path_picker_refresh_breadcrumbs()

        if self._path_picker_list_container is None:
            return

        try:
            children = sorted(
                [p for p in self._path_picker_current_dir.iterdir() if p.is_dir()],
                key=lambda p: p.name.lower(),
            )
        except Exception:
            logger.exception(
                "Failed to list subdirectories for picker at %s",
                self._path_picker_current_dir,
            )
            children = []

        self._path_picker_list_container.clear()
        with self._path_picker_list_container:
            if not children:
                ui.label("No subdirectories").classes("text-sm text-gray-500")
            for child in children:
                ui.button(
                    f"{child.name}/",
                    on_click=lambda _e=None, next_dir=child: self._open_child_directory(
                        next_dir
                    ),
                ).props("flat align=left").classes("w-full justify-start font-mono")

    def _path_picker_refresh_breadcrumbs(self) -> None:
        """Render breadcrumb buttons for fast parent directory navigation."""
        if self._path_picker_breadcrumbs is None:
            return

        current = self._path_picker_current_dir.resolve()
        parts = current.parts
        separator = os.sep

        self._path_picker_breadcrumbs.clear()
        with self._path_picker_breadcrumbs:
            if not parts:
                ui.button(
                    str(current),
                    on_click=lambda _e=None, target=current: self._open_child_directory(
                        target
                    ),
                ).props("flat dense").classes("text-xs")
                return

            cumulative: Path | None = None
            for idx, part in enumerate(parts):
                if idx > 0 and not (idx == 1 and str(parts[0]) == separator):
                    ui.label(separator).classes("text-xs text-gray-500 font-mono px-1")
                cumulative = Path(part) if idx == 0 else cumulative / part
                ui.button(
                    part,
                    on_click=lambda _e=None, target=cumulative: (
                        self._open_child_directory(target)
                    ),
                ).props("flat dense no-caps").classes(
                    "text-xs font-mono border rounded px-2"
                )

    def _open_child_directory(self, next_dir: Path) -> None:
        """Navigate picker to the selected child directory."""
        if next_dir.exists() and next_dir.is_dir():
            self._path_picker_current_dir = next_dir
            if self._source_path_input is not None:
                self._source_path_input.value = str(next_dir)
            self._path_picker_refresh()

    async def _path_picker_go_home(
        self,
        _event: events.ClickEventArguments | None = None,
    ) -> None:
        """Navigate picker to the user's home directory."""
        self._path_picker_current_dir = Path.home()
        self._path_picker_refresh()

    async def _path_picker_go_up(
        self,
        _event: events.ClickEventArguments | None = None,
    ) -> None:
        """Navigate picker to parent directory."""
        parent = self._path_picker_current_dir.parent
        if parent != self._path_picker_current_dir:
            self._path_picker_current_dir = parent
            if self._source_path_input is not None:
                self._source_path_input.value = str(parent)
            self._path_picker_refresh()

    async def _on_source_path_enter(
        self,
        _event: events.GenericEventArguments | None = None,
    ) -> None:
        """Navigate picker when Enter is pressed in the path input."""
        await self._open_typed_source_path()

    async def _open_typed_source_path(
        self,
        _event: events.ClickEventArguments | None = None,
    ) -> None:
        """Open the directory currently typed in the path input."""
        if self._source_path_input is None:
            return

        raw = str(self._source_path_input.value or "").strip()
        if not raw:
            return

        try:
            next_dir = Path(raw).expanduser().resolve()
        except Exception:
            self._notify("Invalid path syntax", "warning")
            return

        if not next_dir.exists() or not next_dir.is_dir():
            self._notify("Directory not found", "warning")
            return

        self._path_picker_current_dir = next_dir
        self._source_path_input.value = str(next_dir)
        self._path_picker_refresh()

    async def _use_current_folder(
        self,
        _event: events.ClickEventArguments | None = None,
    ) -> None:
        """Copy currently browsed directory into the path input."""
        if self._source_path_input is not None:
            self._source_path_input.value = str(self._path_picker_current_dir)

    async def _apply_source_folder(self) -> None:
        """Apply the source folder change and rescan projects."""
        if self._source_path_input is None:
            return
        path_str = self._source_path_input.value or ""
        success = await self.app_state_model.command_set_source_projects_root(path_str)
        if success:
            self._notify("Source folder updated — projects rescanned", "positive")
        else:
            self._notify("Invalid path — source folder not changed", "warning")
        if self._source_folder_dialog is not None:
            self._source_folder_dialog.close()
