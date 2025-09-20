from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Dict

from nicegui import binding, ui

from ...state import AppState

logger = logging.getLogger(__name__)


class ProjectLoadControls:
    """Project selection + path label row.

    Responsibilities:
    - Let user choose and load a project
    - Show the fully resolved selected project directory path (right aligned, wrapped)
    """

    def __init__(self, state: AppState):
        self.state: AppState = state
        self._project_options: Dict[str, Path] = {}

    # UI refs (populated in build)
    _row: ui.element | None = None
    select: ui.select | None = None
    path_label: ui.label | None = None
    load_project_button: ui.button | None = None

    def build(self) -> ui.element:
        # Ensure state project lists populated once at build time
        if not getattr(self.state, "available_projects", None):
            try:
                self.state.refresh_projects()
            except Exception:  # pragma: no cover
                logger.warning("Project refresh failed", exc_info=True)
                pass

        with ui.row().classes("w-full items-center gap-2") as row:
            self._row = row

            # Bind select options and value to AppState
            self.select = ui.select(
                label="Project",
                options=self.state.project_keys,
                value=self.state.selected_project_key,
                with_input=False,
            )
            binding.bind_to(self.select, "options", self.state, "project_keys")
            binding.bind_to(self.select, "value", self.state, "selected_project_key")

            # Ensure options populated now that select exists (state may have been
            # initialized before UI creation). Safe no-op if already current.
            try:  # pragma: no cover - UI side effect
                self.state.refresh_projects()
            except Exception:  # pragma: no cover - defensive
                logger.warning("Project refresh failed", exc_info=True)

            # Update tooltip when selection changes
            def _update_tooltip():
                key = self.state.selected_project_key
                path = self.state.available_projects.get(key) if key else None
                if path:
                    self.select.tooltip = str(path)

            self.select.on("update:model-value", lambda e: _update_tooltip())
            _update_tooltip()

            # LOAD button bound disabled state to is_loading
            self.load_project_button = ui.button(
                "LOAD", on_click=self._load_selected_project
            )

            # NiceGUI buttons don't have direct binding for disabled, do manual reaction
            def _toggle_button():  # pragma: no cover - UI side effect
                if self.state.is_loading:
                    try:
                        self.load_project_button.disable()
                    except Exception:
                        pass
                else:
                    try:
                        self.load_project_button.enable()
                    except Exception:
                        pass

            prev_on_change = self.state.on_change

            def _chained():  # pragma: no cover - UI side effect
                if prev_on_change:
                    try:
                        prev_on_change()
                    except Exception:
                        pass
                _toggle_button()

            self.state.on_change = _chained
            _toggle_button()

            ui.space()
            self.path_label = (
                ui.label("")
                .classes(
                    "text-xs text-gray-500 font-mono text-right flex-1 overflow-hidden"
                )
                .style("white-space:normal; word-break:break-all;")
            )
            try:
                binding.bind_text(
                    self.path_label,
                    self.state.project_state,
                    "project_root",
                    lambda p: str(Path(p).resolve()),
                )
            except Exception:  # pragma: no cover - binding fallback
                self.update_path_label()
        return row

    # --- Data ops ---
    def populate(self):  # pragma: no cover - kept for backward compatibility
        # Now handled by reactive refresh_projects; just trigger refresh
        try:
            self.state.refresh_projects()
        except Exception as exc:  # noqa: BLE001
            ui.notify(f"Project list failed: {exc}", type="warning")

    async def _load_selected_project(self):  # pragma: no cover - UI side effects
        """Async project load using a background thread.

        We leverage NiceGUI's async event handler support so the UI can
        immediately render the spinner (triggered by AppState.is_loading)
        while the blocking `AppState.load_project` runs in a thread.
        """
        if self.state.is_loading:
            return
        key = self.state.selected_project_key
        if not key:
            ui.notify("No project selected", type="warning")
            return
        # Ensure mapping is fresh
        if not self.state.available_projects:
            self.state.refresh_projects()
        path = self.state.available_projects.get(key)
        if not path:
            ui.notify("Project path missing", type="negative")
            return

        # Set loading state so global spinner & hiding logic engage
        self.state.project_state.is_loading = True
        self.state.is_project_loading = True
        self.state.notify()
        for ctrl in (self.load_project_button, self.select):
            if ctrl:
                try:
                    ctrl.disable()
                except Exception:  # pragma: no cover
                    pass

        # Yield once to let UI update before heavy work
        await asyncio.sleep(0)
        try:
            await self.state.load_project(path)
            self.update_path_label()
            ui.notify(f"Loaded {key}", type="positive")
        except Exception as exc:  # noqa: BLE001
            # Ensure loading state cleared if load_project failed early
            self.state.project_state.is_loading = False
            self.state.notify()
            ui.notify(f"Load failed: {exc}", type="negative")
        finally:
            for ctrl in (self.load_project_button, self.select):
                if ctrl:
                    try:
                        ctrl.enable()
                    except Exception:  # pragma: no cover
                        pass

    def update_path_label(self):  # pragma: no cover - formatting
        try:
            if self.path_label:
                self.path_label.text = str(
                    Path(self.state.project_state.project_root).resolve()
                )
        except Exception:
            logger.warning("Path label update failed", exc_info=True)
            pass
