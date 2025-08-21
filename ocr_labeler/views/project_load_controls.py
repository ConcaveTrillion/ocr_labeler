from __future__ import annotations
from pathlib import Path
from typing import Dict
import asyncio
from nicegui import ui

if True:  # pragma: no cover - UI helper container
    class ProjectLoadControls:
        """Project selection + path label row.

        Responsibilities:
        - Discover available projects via AppState.list_available_projects()
        - Let user choose and load a project
        - Show the fully resolved selected project directory path (right aligned, wrapped)
        """

        def __init__(self, state):
            self.state = state
            self._project_options: Dict[str, Path] = {}

        # UI refs (populated in build)
        _row: ui.element | None = None
        select: ui.select | None = None
        path_label: ui.label | None = None
        load_button: ui.button | None = None

        def build(self) -> ui.element:
            with ui.row().classes("w-full items-center gap-2") as row:
                self._row = row
                self.select = ui.select(label="Project", options=[], with_input=False)
                self.load_button = ui.button("LOAD", on_click=self._load_selected_project)
                ui.space()
                self.path_label = ui.label("") \
                    .classes("text-xs text-gray-500 font-mono text-right flex-1 overflow-hidden") \
                    .style("white-space:normal; word-break:break-all;")
            return row

        # --- Data ops ---
        def populate(self):  # pragma: no cover - UI side effects
            try:
                projects = self.state.list_available_projects()
                self._project_options = projects
                if not self.select:
                    return
                opts = sorted(projects.keys())
                self.select.options = opts if opts else ["(no projects found)"]
                if opts:
                    cur_key = Path(self.state.project_root).resolve().name
                    if cur_key in projects:
                        self.select.value = cur_key
                    elif not getattr(self.select, 'value', None):
                        self.select.value = opts[0]

                    def _update_tooltip():
                        key = getattr(self.select, 'value', None)
                        path = self._project_options.get(key) if key else None
                        if path:
                            self.select.tooltip = str(path)
                    self.select.on('update:model-value', lambda e: _update_tooltip())
                    _update_tooltip()
                self.update_path_label()
            except Exception as exc:  # noqa: BLE001
                ui.notify(f"Project list failed: {exc}", type="warning")

        async def _load_selected_project(self):  # pragma: no cover - UI side effects
            """Async project load using a background thread.

            We leverage NiceGUI's async event handler support so the UI can
            immediately render the spinner (triggered by AppState.is_loading)
            while the blocking `AppState.load_project` runs in a thread.
            """
            if not self.select or self.state.is_loading:
                return
            key = getattr(self.select, 'value', None)
            if not key:
                ui.notify("No project selected", type="warning")
                return
            path = self._project_options.get(key)
            if not path:
                ui.notify("Project path missing", type="negative")
                return

            # Set loading state so global spinner & hiding logic engage
            self.state.is_loading = True
            self.state.is_project_loading = True
            self.state.notify()
            for ctrl in (self.load_button, self.select):
                if ctrl:
                    try:
                        ctrl.disable()
                    except Exception:  # pragma: no cover
                        pass

            # Yield once to let UI update before heavy work
            await asyncio.sleep(0)
            try:
                await asyncio.to_thread(self.state.load_project, path)
                self.update_path_label()
                ui.notify(f"Loaded {key}", type="positive")
            except Exception as exc:  # noqa: BLE001
                # Ensure loading state cleared if load_project failed early
                self.state.is_loading = False
                self.state.notify()
                ui.notify(f"Load failed: {exc}", type="negative")
            finally:
                for ctrl in (self.load_button, self.select):
                    if ctrl:
                        try:
                            ctrl.enable()
                        except Exception:  # pragma: no cover
                            pass

        def update_path_label(self):  # pragma: no cover - formatting
            try:
                if self.path_label:
                    self.path_label.text = str(Path(self.state.project_root).resolve())
            except Exception:
                pass
