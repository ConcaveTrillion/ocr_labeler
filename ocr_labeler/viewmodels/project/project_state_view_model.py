import logging
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from nicegui import binding

from ...state import ProjectState
from ..shared.base_viewmodel import BaseViewModel

if TYPE_CHECKING:
    from ..app.app_state_view_model import AppStateViewModel

logger = logging.getLogger(__name__)


@binding.bindable_dataclass
class ProjectStateViewModel(BaseViewModel):
    """View model for project-specific state and navigation."""

    _project_state: Optional[ProjectState] = None
    _app_state_model: "AppStateViewModel | None" = None

    # UI-bound properties
    is_navigating: bool = False
    page_total: int = 0
    current_page_index: int = 0
    is_project_loading: bool = False
    loading_status: str = ""  # Detailed status message for current loading operation
    project_root: str = ""
    project_root_resolved: str = ""
    is_busy: bool = False
    busy_message: str = ""
    is_action_busy: bool = False
    can_navigate: bool = False
    can_navigate_override: bool = False
    can_navigate_prev: bool = False
    can_navigate_next: bool = False
    is_controls_disabled: bool = False
    # Convenience computed properties for direct UI binding
    prev_disabled: bool = False
    next_disabled: bool = False
    goto_disabled: bool = False

    def __init__(
        self,
        project_state: ProjectState,
        app_state_model: "AppStateViewModel | None" = None,
    ):
        logger.debug(
            f"Initializing ProjectStateViewModel with project_state: {project_state.project.project_id is not None}"
        )

        if project_state is not None and isinstance(project_state, ProjectState):
            self._project_state = project_state
            logger.debug("Registering project state change listener")
            self._project_state.on_change.append(self._on_project_state_change)
            logger.debug("Registered project state change listener")
        else:
            logger.error(
                "Project state of type ProjectState not provided to ProjectStateViewModel!"
            )
            raise ValueError(
                "Project state of type ProjectState not provided to ProjectStateViewModel!"
            )

        self._app_state_model = app_state_model
        if self._app_state_model:
            logger.debug("Registering app state model change listener")
            self._app_state_model._app_state.on_change.append(self._on_app_state_change)
            logger.debug("Registered app state model change listener")

        # Initialize base class first
        super().__init__()

        # Set initial values directly (avoiding binding during __init__)
        object.__setattr__(self, "can_navigate", False)
        object.__setattr__(self, "can_navigate_prev", False)
        object.__setattr__(self, "can_navigate_next", False)
        object.__setattr__(self, "is_controls_disabled", False)
        object.__setattr__(self, "can_navigate_override", False)
        object.__setattr__(self, "is_action_busy", False)
        object.__setattr__(self, "busy_message", "")

        # Don't call update() in __init__ for bindable dataclasses - let state change listeners handle it

    def override_can_navigate(self, can_navigate_override: bool):
        """Override can_navigate property, e.g. to disable navigation during modal dialogs and requests."""
        logger.debug(f"Setting can_navigate_override to {can_navigate_override}")
        old_value = self.can_navigate_override
        self.can_navigate_override = can_navigate_override
        if old_value != self.can_navigate_override:
            self.notify_property_changed(
                "can_navigate_override", self.can_navigate_override
            )
            self._update_navigation_properties()

    def set_action_busy(self, is_busy: bool, message: str = ""):
        """Set or clear a manual busy state for long-running actions.

        Args:
            is_busy: Whether the action is busy.
            message: Optional message to display during the busy state.
        """
        logger.debug(f"Setting action busy to {is_busy} with message: {message}")
        self.is_action_busy = is_busy
        self.busy_message = message if is_busy else ""
        self.update()
        self._update_navigation_properties()

    def update(self):
        """Sync model from ProjectState via state change listener."""
        logger.debug("Updating ProjectStateViewModel from ProjectState")
        if self._project_state:
            project = getattr(self._project_state, "project", None)
            if project is None:
                logger.warning(
                    "ProjectStateViewModel.update called with no active project; "
                    "using empty navigation state"
                )
                self.page_total = 0
                self.current_page_index = -1
            else:
                self.page_total = project.page_count()
                self.current_page_index = self._project_state.current_page_index
            self.is_navigating = self._project_state.is_navigating
            self.is_project_loading = self._project_state.is_project_loading
            self.loading_status = self._project_state.loading_status
            self.is_busy = (
                self._project_state.is_project_loading
                or self._project_state.is_navigating
                or self.is_action_busy
            )
            self.project_root = str(self._project_state.project_root)
            # Resolve project root path if possible for display
            self.project_root_resolved = (
                str(
                    self._project_state.project_root.resolve()
                    if isinstance(self._project_state.project_root, Path)
                    else ""
                )
                if self._project_state.project_root
                else ""
            )

            self._update_navigation_properties()

            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Project page total: {self.page_total}")
                logger.debug(f"Current page index: {self.current_page_index}")
                logger.debug(f"Is navigating: {self.is_navigating}")
                logger.debug(f"Is project loading: {self.is_project_loading}")
                logger.debug(f"Loading status: {self.loading_status}")
                logger.debug(f"Is busy: {self.is_busy}")
                logger.debug(f"Project root: {self.project_root}")
                logger.debug(f"Project root resolved: {self.project_root_resolved}")
                logger.debug(f"Can navigate: {self.can_navigate}")
                logger.debug(f"Can navigate prev: {self.can_navigate_prev}")
                logger.debug(f"Can navigate next: {self.can_navigate_next}")
                logger.debug("ProjectStateViewModel update complete")
        else:
            logger.error(
                "No project state available when updating ProjectStateViewModel!"
            )
            raise ValueError(
                "No project state available when updating ProjectStateViewModel!"
            )

    def _update_navigation_properties(self):
        """Update navigation-related computed properties."""
        self.can_navigate = self.page_total > 0 and not self.can_navigate_override
        self.can_navigate_prev = self.current_page_index > 0 and self.can_navigate
        self.can_navigate_next = (
            self.current_page_index < self.page_total - 1 and self.can_navigate
        )

        # Update combined disabled state
        app_loading = (
            self._app_state_model.is_project_loading if self._app_state_model else False
        )
        self.is_controls_disabled = app_loading or self.can_navigate_override

        # Derived disabled flags for direct UI binding convenience. These
        # combine the global "controls disabled" flag with per-direction
        # availability so UI elements can bind to a single boolean.
        self.prev_disabled = self.is_controls_disabled or (not self.can_navigate_prev)
        self.next_disabled = self.is_controls_disabled or (not self.can_navigate_next)
        self.goto_disabled = self.is_controls_disabled or (not self.can_navigate)

    def _on_project_state_change(self):
        """Listener for ProjectState changes; update model properties."""
        logger.debug("Project State change detected, updating model")
        # Update internal properties from the ProjectState
        self.update()
        # Notify any view listeners that the viewmodel state has changed so views
        # can refresh. Use a generic property name to avoid having to enumerate
        # every changed attribute here.
        try:
            self.notify_property_changed("project_state", True)
        except Exception:
            logger.debug(
                "Failed to notify property change for project_state", exc_info=True
            )

    def _on_app_state_change(self):
        """Listener for AppState changes; update computed properties."""
        logger.debug("App State change detected, updating computed properties")
        self._update_navigation_properties()
        # Notify listeners so UI can re-evaluate derived flags that depend on AppState
        try:
            self.notify_property_changed("app_state", True)
        except Exception:
            logger.debug(
                "Failed to notify property change for app_state", exc_info=True
            )

    # Command methods for UI actions

    def command_navigate_to_page(self, page_index: int) -> bool:
        """Command to navigate to a specific page.

        Args:
            page_index: The page index to navigate to.

        Returns:
            True if navigation was successful, False otherwise.
        """
        try:
            if not self.can_navigate:
                logger.warning("Navigation not allowed in current state")
                return False

            if not (0 <= page_index < self.page_total):
                logger.warning(
                    f"Page index {page_index} out of range [0, {self.page_total})"
                )
                return False

            # Use the project's navigation method
            self._project_state.goto_page_index(page_index)
            return True

        except Exception as e:
            logger.exception(f"Error navigating to page {page_index}: {e}")
            return False

    def command_navigate_next(self) -> bool:
        """Command to navigate to the next page.

        Returns:
            True if navigation was successful, False otherwise.
        """
        if not self.can_navigate_next:
            logger.debug("Cannot navigate to next page")
            return False

        return self.command_navigate_to_page(self.current_page_index + 1)

    def command_navigate_prev(self) -> bool:
        """Command to navigate to the previous page.

        Returns:
            True if navigation was successful, False otherwise.
        """
        if not self.can_navigate_prev:
            logger.debug("Cannot navigate to previous page")
            return False

        return self.command_navigate_to_page(self.current_page_index - 1)

    def command_navigate_first(self) -> bool:
        """Command to navigate to the first page.

        Returns:
            True if navigation was successful, False otherwise.
        """
        if not self.can_navigate or self.page_total == 0:
            logger.debug("Cannot navigate to first page")
            return False

        return self.command_navigate_to_page(0)

    def command_navigate_last(self) -> bool:
        """Command to navigate to the last page.

        Returns:
            True if navigation was successful, False otherwise.
        """
        if not self.can_navigate or self.page_total == 0:
            logger.debug("Cannot navigate to last page")
            return False

        return self.command_navigate_to_page(self.page_total - 1)

    def command_get_page_display_info(self, page_index: Optional[int] = None) -> dict:
        """Command to get display information for a page.

        Args:
            page_index: Page index to get info for. If None, uses current page.

        Returns:
            Dictionary with page display information.
        """
        idx = page_index if page_index is not None else self.current_page_index

        try:
            page_info = {
                "index": idx,
                "display_number": idx + 1,  # 1-based for display
                "total_pages": self.page_total,
                "is_current": idx == self.current_page_index,
                "can_navigate_to": self.can_navigate and 0 <= idx < self.page_total,
            }
            return page_info
        except Exception as e:
            logger.exception(f"Error getting page display info for page {idx}: {e}")
            return {
                "index": idx,
                "display_number": idx + 1,
                "total_pages": self.page_total,
                "is_current": False,
                "can_navigate_to": False,
            }

    def command_get_navigation_status(self) -> dict:
        """Command to get current navigation status.

        Returns:
            Dictionary with navigation status information.
        """
        return {
            "current_page": self.current_page_index,
            "total_pages": self.page_total,
            "can_navigate_prev": self.can_navigate_prev,
            "can_navigate_next": self.can_navigate_next,
            "can_navigate": self.can_navigate,
            "is_navigating": self.is_navigating,
            "is_busy": self.is_busy,
            "is_controls_disabled": self.is_controls_disabled,
        }

    def command_save_page(self) -> bool:
        """Command to save the current page.

        Returns:
            True if save was successful, False otherwise.
        """
        try:
            if not self._project_state:
                logger.error("No project state available for save")
                return False
            return self._project_state.save_current_page()
        except Exception as e:
            logger.exception(f"Error saving current page: {e}")
            return False

    def command_load_page(self) -> bool:
        """Command to load the current page from saved files.

        Returns:
            True if load was successful, False otherwise.
        """
        try:
            if not self._project_state:
                logger.error("No project state available for load")
                return False
            return self._project_state.load_current_page()
        except Exception as e:
            logger.exception(f"Error loading current page: {e}")
            return False

    def command_refine_bboxes(self) -> bool:
        """Command to refine all bounding boxes in the current page.

        Returns:
            True if refinement was successful, False otherwise.
        """
        try:
            if not self._project_state:
                logger.error("No project state available for bbox refinement")
                return False
            return self._project_state.refine_all_bboxes()
        except Exception as e:
            logger.exception(f"Error refining bboxes: {e}")
            return False

    def command_expand_refine_bboxes(self) -> bool:
        """Command to expand and refine all bounding boxes in the current page.

        Returns:
            True if expansion and refinement was successful, False otherwise.
        """
        try:
            if not self._project_state:
                logger.error("No project state available for bbox expand & refine")
                return False
            return self._project_state.expand_and_refine_all_bboxes()
        except Exception as e:
            logger.exception(f"Error expanding and refining bboxes: {e}")
            return False

    def command_reload_page_with_ocr(self) -> bool:
        """Command to reload the current page with OCR processing.

        Returns:
            True if reload was successful, False otherwise.
        """
        try:
            if not self._project_state:
                logger.error("No project state available for OCR reload")
                return False
            self._project_state.reload_current_page_with_ocr()
            return True
        except Exception as e:
            logger.exception(f"Error reloading page with OCR: {e}")
            return False
