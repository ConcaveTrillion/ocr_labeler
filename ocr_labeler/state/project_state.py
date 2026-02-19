from __future__ import annotations

import json
import logging
import threading
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter
from typing import Callable, List, Optional

from nicegui import background_tasks, run
from pd_book_tools.ocr.page import Page

from ..models.project_model import Project
from ..operations.ocr.navigation_operations import NavigationOperations
from ..operations.ocr.page_operations import PageOperations
from ..operations.ocr.text_operations import TextOperations
from ..operations.persistence.project_operations import ProjectOperations
from .page_state import PageState

logger = logging.getLogger(__name__)
page_timing_logger = logging.getLogger("ocr_labeler.page_timing")

# Constants for ground truth operations
IMAGE_EXTS = (".png", ".jpg", ".jpeg")


@dataclass
class ProjectState:
    """Project-specific state management.

    Responsibilities:
    - Manage the current project and its pages
    - Handle navigation within the project
    - Coordinate individual OCR page loading
    - Provide ground truth reload capability for the current project
    """

    project: Project = field(default_factory=Project)
    current_page_index: int = 0  # Navigation state managed here
    project_root: Path = Path("../data/source-pgdp-data/output")
    is_project_loading: bool = False
    is_navigating: bool = False
    loading_status: str = ""  # Detailed status message for current loading operation
    on_change: Optional[List[Callable[[], None]]] = field(default_factory=list)
    page_states: dict[int, PageState] = field(
        default_factory=dict
    )  # Per-page state management
    page_ops: PageOperations = field(
        default_factory=PageOperations
    )  # For backward compatibility
    notification_sink: Callable[[str, str], None] | None = None

    # Cached text values to avoid expensive recomputation during binding propagation
    _cached_ocr_text: str = field(default="", init=False)
    _cached_gt_text: str = field(default="", init=False)
    _cached_page_index: int = field(
        default=-1, init=False
    )  # Track which page the cache is for
    _notification_queue: deque[tuple[str, str]] = field(
        default_factory=deque, init=False, repr=False
    )
    _notification_lock: threading.Lock = field(
        default_factory=threading.Lock, init=False, repr=False
    )

    def queue_notification(self, message: str, kind: str = "info"):
        """Queue a user-facing notification from any thread.

        Notifications are drained by the UI thread and displayed via ui.notify.
        """
        if not message:
            return
        if self.notification_sink is not None:
            try:
                self.notification_sink(message, kind)
                return
            except Exception:
                logger.debug(
                    "notification_sink failed; using local queue", exc_info=True
                )
        with self._notification_lock:
            self._notification_queue.append((message, kind))

    def drain_notifications(self) -> list[tuple[str, str]]:
        """Drain queued notifications for UI-thread display."""
        with self._notification_lock:
            if not self._notification_queue:
                return []
            items = list(self._notification_queue)
            self._notification_queue.clear()
            return items

    def pop_notification(self) -> tuple[str, str] | None:
        """Pop a single queued notification for incremental UI display."""
        with self._notification_lock:
            if not self._notification_queue:
                return None
            return self._notification_queue.popleft()

    def notify(self):
        """Notify listeners of state changes."""
        for listener in self.on_change:
            listener()

    def _log_page_load_timing(
        self,
        *,
        index: int,
        force_ocr: bool,
        source: str,
        status: str,
        duration_ms: float,
    ) -> None:
        """Emit a structured page-load timing event."""
        page_timing_logger.info(
            "page_load_timing: index=%s force_ocr=%s source=%s status=%s duration_ms=%.1f",
            index,
            force_ocr,
            source,
            status,
            duration_ms,
        )

    def _log_page_load_timing_step(
        self,
        *,
        index: int,
        step: str,
        duration_ms: float,
        extra: str = "",
    ) -> None:
        """Emit a structured page-load step timing event."""
        suffix = f" {extra}" if extra else ""
        page_timing_logger.info(
            "page_load_timing_step: index=%s step=%s duration_ms=%.1f%s",
            index,
            step,
            duration_ms,
            suffix,
        )

    def _log_page_navigation_timing(self, *, index: int, duration_ms: float) -> None:
        """Emit a structured page-navigation timing event."""
        page_timing_logger.info(
            "page_navigation_timing: index=%s duration_ms=%.1f",
            index,
            duration_ms,
        )

    def get_page_state(self, page_index: int) -> PageState:
        """Get or create PageState for the specified page index.
        Each page gets its own state management instance.
        """
        logger.debug("get_page_state: called with page_index=%s", page_index)
        if page_index not in self.page_states:
            page_state = PageState()
            page_state.set_project_context(self.project, self.project_root, self)
            page_state.on_change.append(self.notify)
            self.page_states[page_index] = page_state
        logger.debug("get_page_state: returning page_state for index %s", page_index)
        return self.page_states[page_index]

    @property
    def current_page_state(self) -> PageState:
        """Get or create the PageState for the current page index."""
        logger.debug("current_page_state: called")
        result = self.get_page_state(self.current_page_index)
        logger.debug("current_page_state: returning page_state")
        return result

    async def load_project(
        self, directory: Path, initial_page_index: int | None = None
    ):
        """Load images; lazily OCR each page via DocTR on first access.

        Reads pages.json (if present) mapping image filename -> ground truth text.
        """
        logger.debug("load_project: called with directory=%s", directory)
        # Use ProjectOperations for I/O operations
        operations = ProjectOperations()

        # Validate directory and scan for images using operations
        # Operations are sync, so wrap with run.io_bound for async context
        directory = Path(directory)
        images = await run.io_bound(
            operations.scan_project_directory, directory
        )  # This will raise FileNotFoundError if needed
        if images is None:
            images = []

        self.is_project_loading = True
        self.notify()
        try:
            self.project_root = directory

            logger.debug("load_project: creating project with %d images", len(images))
            # Load ground truth mapping using project state's method
            ground_truth_map = await self.load_ground_truth_map(directory)
            # Use ProjectOperations to create the project with the ground truth map
            # Operations are sync, so wrap with run.io_bound
            self.project = await run.io_bound(
                operations.create_project, directory, images, ground_truth_map
            )
            # Reset navigation to the requested initial page (if valid)
            if images:
                if initial_page_index is not None and 0 <= initial_page_index < len(
                    images
                ):
                    self.current_page_index = initial_page_index
                else:
                    self.current_page_index = 0
            else:
                self.current_page_index = -1

            logger.info(
                "load_project init page selection: initial_page_index=%s, current_page_index=%s, total_pages=%s",
                initial_page_index,
                self.current_page_index,
                len(images),
            )

            # Clear page states for the new project
            self.page_states.clear()
        finally:
            self.is_project_loading = False
            self.notify()

        if images and self.current_page_index >= 0:
            self._navigate()
        logger.debug("load_project: completed, loaded %d images", len(images))

    def reload_ground_truth(self):
        """Reload ground truth for the current project."""
        logger.debug("reload_ground_truth: called")
        # Import inside method to allow test monkeypatching of module attribute
        try:
            from ..operations.persistence.project_operations import ProjectOperations

            project_ops = ProjectOperations()
            project_ops.reload_ground_truth_into_project(self)
        except Exception:  # pragma: no cover - defensive
            return
        logger.debug("reload_ground_truth: completed")

    def next_page(self):
        """Navigate to the next page."""
        logger.debug("next_page: called, current_index=%s", self.current_page_index)

        result = NavigationOperations.next_page(
            self.current_page_index, self.project.page_count() - 1
        )
        if result:
            self.current_page_index += 1
            logger.debug("next_page: moved to index=%s", self.current_page_index)
        else:
            logger.warning("next_page: already at last page, no change")

        self._navigate()
        logger.debug("next_page: completed")

    def prev_page(self):
        """Navigate to the previous page."""
        logger.debug("prev_page: called, current_index=%s", self.current_page_index)

        result = NavigationOperations.prev_page(self.current_page_index)
        if result:
            self.current_page_index -= 1
            logger.debug("prev_page: moved to index=%s", self.current_page_index)
        else:
            logger.warning("prev_page: already at first page, no change")

        self._navigate()
        logger.debug("prev_page: completed")

    def goto_page_number(self, number: int):
        """Navigate to a specific page number."""
        logger.debug("goto_page_number: called with number=%s", number)

        result, target_index = NavigationOperations.goto_page_number(
            number, self.project.page_count()
        )
        if result:
            self.goto_page_index(target_index)
        else:
            logger.warning("goto_page_number: invalid page number %s", number)

        logger.debug("goto_page_number: completed")

    def goto_page_index(self, index: int):
        """Jump to a page by zero-based index, clamping to valid range."""
        logger.debug("goto_page_index: called with index=%s", index)
        if not self.project.pages:
            self.current_page_index = -1
            logger.warning("goto_page_index: empty pages list; index set to -1")
            raise ValueError("No pages available to navigate")

        result, clamped_index = NavigationOperations.goto_page_index(
            index, self.project.page_count() - 1
        )
        if result:
            # Invalidate cache if page index actually changed
            if self.current_page_index != clamped_index:
                self._invalidate_text_cache()
            self.current_page_index = clamped_index
            logger.debug("goto_page_index: now at index=%s", self.current_page_index)
            # Notify listeners of the change
            self.notify()
            # Start async loading of the new page
            self._navigate()
        else:
            logger.warning("goto_page_index: navigation failed for index %s", index)

    def get_page(self, index: int, force_ocr: bool = False) -> Optional[Page]:
        """Get page at the specified index, loading it if necessary.

        This method delegates to ensure_page for lazy loading.
        """
        logger.debug("get_page: called with index=%s, force_ocr=%s", index, force_ocr)
        result = self.ensure_page(index, force_ocr=force_ocr)
        logger.debug("get_page: returning page for index %s", index)
        return result

    def ensure_page(self, index: int, force_ocr: bool = False) -> Optional[Page]:
        """Ensure that the Page at index is loaded, loading it if necessary.

        This method handles the state concern of lazy page loading, including:
        - Prioritizing saved pages if available (unless force_ocr is True)
        - OCR processing via page operations when available or forced
        - Ground truth text injection
        - Fallback page creation for failed OCR
        - Error handling and logging

        Args:
            index: Zero-based page index to ensure is loaded
            force_ocr: If True, skip loading saved page and force OCR processing

        Returns:
            Optional[Page]: The loaded page or None if index is invalid
        """
        ensure_started = perf_counter()

        def _log_page_timing(source: str, status: str) -> None:
            duration_ms = (perf_counter() - ensure_started) * 1000
            self._log_page_load_timing(
                index=index,
                force_ocr=force_ocr,
                source=source,
                status=status,
                duration_ms=duration_ms,
            )

        if not self.project.pages:
            logger.info("ensure_page: no pages loaded yet")
            _log_page_timing(source="none", status="no_pages")
            return None
        if not (0 <= index < len(self.project.pages)):
            logger.warning(
                "ensure_page: index %s out of range (0..%s)",
                index,
                len(self.project.pages) - 1,
            )
            _log_page_timing(source="none", status="index_out_of_range")
            return None

        def _attach_loaded_page_metadata(
            loaded_page: Page,
            page_image_path: Path,
            page_index: int,
            source: str,
        ) -> None:
            if not hasattr(loaded_page, "image_path"):
                loaded_page.image_path = str(page_image_path)  # type: ignore[attr-defined]
            if not hasattr(loaded_page, "name"):
                loaded_page.name = page_image_path.name  # type: ignore[attr-defined]
            if not hasattr(loaded_page, "index"):
                loaded_page.index = page_index  # type: ignore[attr-defined]
            loaded_page.page_source = source  # type: ignore[attr-defined]

        def _user_saved_directories() -> list[str]:
            primary_save_dir = "local-data/labeled-ocr"
            save_dirs = [primary_save_dir]

            # Backward compatibility: older sessions may have saved labeled pages
            # under the workspace's local-data directory instead of project_root.
            workspace_save_dir = (Path.cwd() / primary_save_dir).resolve()
            if self.project_root is not None:
                primary_abs = (self.project_root / primary_save_dir).resolve()
                if workspace_save_dir != primary_abs:
                    save_dirs.append(str(workspace_save_dir))
            else:
                save_dirs.append(str(workspace_save_dir))

            return save_dirs

        def _try_load_user_saved_page(
            page_index: int, img_path: Path
        ) -> Optional[Page]:
            if self.project_root is None:
                return None

            for save_directory in _user_saved_directories():
                can_load_started = perf_counter()
                user_saved_load_info = self.page_ops.can_load_page(
                    page_number=page_index + 1,
                    project_root=self.project_root,
                    save_directory=save_directory,
                    project_id=None,
                )
                can_load_duration_ms = (perf_counter() - can_load_started) * 1000
                self._log_page_load_timing_step(
                    index=page_index,
                    step="user_saved_can_load",
                    duration_ms=can_load_duration_ms,
                    extra=f"save_directory={save_directory} can_load={user_saved_load_info.can_load}",
                )
                if not user_saved_load_info.can_load:
                    continue

                logger.info(
                    "ensure_page: found user-saved candidate for index=%s at %s",
                    page_index,
                    user_saved_load_info.json_path,
                )

                load_started = perf_counter()
                loaded_result = self.page_ops.load_page(
                    page_number=page_index + 1,
                    project_root=self.project_root,
                    save_directory=save_directory,
                    project_id=None,
                )
                load_duration_ms = (perf_counter() - load_started) * 1000
                self._log_page_load_timing_step(
                    index=page_index,
                    step="user_saved_load",
                    duration_ms=load_duration_ms,
                    extra=f"save_directory={save_directory}",
                )
                if loaded_result is None:
                    continue

                loaded_page, _ = loaded_result
                logger.info(
                    "ensure_page: loaded from user-saved for index=%s (json_path=%s)",
                    page_index,
                    user_saved_load_info.json_path,
                )
                _attach_loaded_page_metadata(
                    loaded_page=loaded_page,
                    page_image_path=img_path,
                    page_index=page_index,
                    source="filesystem",
                )
                return loaded_page

            return None

        # If we already have a cached OCR page in memory, refresh from disk if a
        # user-labeled page now exists.
        current_page = self.project.pages[index]
        if (
            current_page is not None
            and not force_ocr
            and self.project_root is not None
            and getattr(current_page, "page_source", None) in {"ocr", "cached_ocr"}
        ):
            img_path = Path(self.project.image_paths[index])
            loaded_page = _try_load_user_saved_page(index, img_path)
            if loaded_page is not None:
                logger.info(
                    "ensure_page: replacing in-memory cached page with user-saved page for index=%s",
                    index,
                )
                self.project.pages[index] = loaded_page
                self.notify()
                _log_page_timing(source="filesystem", status="loaded")
                return self.project.pages[index]

        if self.project.pages[index] is None:
            img_path = Path(
                self.project.image_paths[index]
            )  # Ensure it's a Path object
            logger.debug(
                "ensure_page: cache miss for index=%s path=%s (force_ocr=%s)",
                index,
                img_path,
                force_ocr,
            )

            # Try to load from saved files first (unless forcing OCR)
            if not force_ocr and self.project_root is not None:
                logger.info("ensure_page: checking for saved page at index=%s", index)
                self.loading_status = "Checking for saved page..."
                self.queue_notification(self.loading_status, "info")
                # Don't notify here - it triggers recursion via viewmodel updates
                loaded_page = None

                # First try user-saved pages
                try:
                    user_saved_started = perf_counter()
                    loaded_page = _try_load_user_saved_page(index, img_path)
                    user_saved_duration_ms = (
                        perf_counter() - user_saved_started
                    ) * 1000
                    self._log_page_load_timing_step(
                        index=index,
                        step="user_saved_lookup",
                        duration_ms=user_saved_duration_ms,
                    )
                    if loaded_page is not None:
                        self.loading_status = "Loading page from disk..."
                        self.queue_notification(self.loading_status, "info")
                        # Don't notify here - it triggers recursion via viewmodel updates
                        self.project.pages[index] = loaded_page
                        # Notify after page is cached so UI can update (safe here, not in property getter)
                        self.notify()
                        _log_page_timing(source="filesystem", status="loaded")
                        return self.project.pages[index]
                except Exception as e:
                    logger.debug(
                        "ensure_page: failed to load user-saved page for index=%s: %s",
                        index,
                        e,
                    )

                # If no user-saved page, try cache
                if loaded_page is None:
                    try:
                        cache_can_load_started = perf_counter()
                        cache_load_info = self.page_ops.can_load_page(
                            page_number=index + 1,
                            project_root=self.project_root,
                            save_directory="local-data/labeled-ocr/cache",
                            project_id=None,
                        )
                        cache_can_load_duration_ms = (
                            perf_counter() - cache_can_load_started
                        ) * 1000
                        self._log_page_load_timing_step(
                            index=index,
                            step="cache_can_load",
                            duration_ms=cache_can_load_duration_ms,
                            extra=f"can_load={cache_load_info.can_load}",
                        )
                        if cache_load_info.can_load:
                            cache_load_started = perf_counter()
                            loaded_result = self.page_ops.load_page(
                                page_number=index + 1,  # Convert to 1-based
                                project_root=self.project_root,
                                save_directory="local-data/labeled-ocr/cache",
                                project_id=None,  # Will be derived from project_root.name
                            )
                            cache_load_duration_ms = (
                                perf_counter() - cache_load_started
                            ) * 1000
                            self._log_page_load_timing_step(
                                index=index,
                                step="cache_load",
                                duration_ms=cache_load_duration_ms,
                            )
                            if loaded_result is not None:
                                loaded_page, _ = loaded_result
                                logger.info(
                                    "ensure_page: loaded from cache for index=%s",
                                    index,
                                )
                                self.loading_status = "Loading page from cache..."
                                self.queue_notification(self.loading_status, "info")
                                # Don't notify here - it triggers recursion via viewmodel updates
                                _attach_loaded_page_metadata(
                                    loaded_page=loaded_page,
                                    page_image_path=img_path,
                                    page_index=index,
                                    source="cached_ocr",
                                )
                                self.project.pages[index] = loaded_page
                                # Notify after page is cached so UI can update (safe here, not in property getter)
                                self.notify()
                                _log_page_timing(source="cached_ocr", status="loaded")
                                return self.project.pages[index]
                    except Exception as e:
                        logger.debug(
                            "ensure_page: failed to load cached page for index=%s: %s",
                            index,
                            e,
                        )

            # Fall back to OCR processing
            if self.page_ops.page_parser:
                logger.info(
                    "ensure_page: running OCR on page at index=%s (in separate thread)",
                    index,
                )
                self.loading_status = "Running OCR on page (in background thread)..."
                self.queue_notification(self.loading_status, "info")
                # Don't notify here - it triggers recursion via viewmodel updates
                try:
                    gt_text = (
                        self.find_ground_truth_text(
                            img_path.name, self.project.ground_truth_map
                        )
                        or ""
                    )
                    ocr_started = perf_counter()
                    page_obj = self.page_ops.page_parser(img_path, index, gt_text)
                    ocr_duration_ms = (perf_counter() - ocr_started) * 1000
                    self._log_page_load_timing_step(
                        index=index,
                        step="ocr_parse",
                        duration_ms=ocr_duration_ms,
                    )
                    logger.debug(
                        "ensure_page: loader created page index=%s name=%s",
                        index,
                        getattr(page_obj, "name", img_path.name),
                    )
                    # Attach convenience attrs expected elsewhere
                    page_image_path = getattr(page_obj, "image_path", None)
                    if not isinstance(page_image_path, (str, Path)):
                        page_obj.image_path = str(img_path)  # type: ignore[attr-defined]

                    page_name = getattr(page_obj, "name", None)
                    if not isinstance(page_name, str) or not page_name:
                        page_obj.name = img_path.name  # type: ignore[attr-defined]

                    page_index = getattr(page_obj, "index", None)
                    if not isinstance(page_index, int):
                        page_obj.index = index  # type: ignore[attr-defined]

                    if not hasattr(page_obj, "page_source"):
                        page_obj.page_source = "ocr"  # type: ignore[attr-defined]
                    else:
                        page_obj.page_source = "ocr"  # type: ignore[attr-defined]
                    self.project.pages[index] = page_obj

                    # Auto-save OCR result to cache for performance
                    page_image_path = getattr(page_obj, "image_path", None)
                    if self.project_root is not None and isinstance(
                        page_image_path, (str, Path)
                    ):
                        try:
                            cache_save_started = perf_counter()
                            cache_saved = self.page_ops.save_page(
                                page=page_obj,
                                project_root=self.project_root,
                                save_directory="local-data/labeled-ocr/cache",
                                project_id=None,  # Will be derived from project_root.name
                                source_lib="doctr-pgdp-cached",
                            )
                            cache_save_duration_ms = (
                                perf_counter() - cache_save_started
                            ) * 1000
                            self._log_page_load_timing_step(
                                index=index,
                                step="cache_save",
                                duration_ms=cache_save_duration_ms,
                                extra=f"success={cache_saved}",
                            )
                            if cache_saved:
                                logger.debug(
                                    "ensure_page: auto-saved OCR result to cache for index=%s",
                                    index,
                                )
                                # Update page source to indicate it's cached
                                page_obj.page_source = "cached_ocr"  # type: ignore[attr-defined]
                            else:
                                logger.debug(
                                    "ensure_page: failed to auto-save OCR result to cache for index=%s",
                                    index,
                                )
                        except Exception as e:
                            logger.debug(
                                "ensure_page: error auto-saving to cache for index=%s: %s",
                                index,
                                e,
                            )
                    else:
                        logger.debug(
                            "ensure_page: skipping auto-cache save for index=%s due to invalid image_path",
                            index,
                        )

                    # Notify after page is cached so UI can update
                    self.notify()
                    _log_page_timing(
                        source=getattr(page_obj, "page_source", "ocr"),
                        status="loaded",
                    )
                except Exception:  # pragma: no cover - defensive
                    logger.exception(
                        "ensure_page: loader failed for index=%s path=%s; using fallback page",
                        index,
                        img_path,
                    )
                    self.queue_notification(
                        "OCR failed for page; using fallback image.", "negative"
                    )

                    # Fallback: still display original image even if OCR failed
                    self.project.pages[index] = self.create_fallback_page(
                        index, img_path
                    )
                    # Notify after fallback page is cached
                    self.notify()
                    _log_page_timing(source="fallback", status="ocr_failed")
            else:
                # No loader provided: keep legacy minimal placeholder behavior
                logger.debug(
                    "ensure_page: no loader provided, creating placeholder page for index=%s",
                    index,
                )
                self.project.pages[index] = self.create_fallback_page(index, img_path)
                _log_page_timing(source="fallback", status="no_loader")
        else:
            logger.debug("ensure_page: cache hit for index=%s", index)
            _log_page_timing(
                source=getattr(self.project.pages[index], "page_source", "memory"),
                status="cache_hit",
            )

        return self.project.pages[index]

    def current_page(self) -> Page | None:
        """Get the current page."""
        logger.debug("current_page: called, current_index=%s", self.current_page_index)
        result = self.get_page(self.current_page_index)
        logger.debug("current_page: returning page")
        return result

    def reload_current_page_with_ocr(self):
        """Reload the current page with OCR processing, bypassing any saved version."""
        logger.debug(
            "reload_current_page_with_ocr: called, current_index=%s",
            self.current_page_index,
        )
        page_state = self.get_page_state(self.current_page_index)
        page_state.reload_page_with_ocr(self.current_page_index)
        # Invalidate cache since page content may have changed
        self._invalidate_text_cache()
        logger.debug("reload_current_page_with_ocr: completed")

    def _navigate(self):
        """Internal navigation helper with loading state."""
        import threading

        logger.info(
            "[_navigate] Entry - Thread: %s, Current page index: %s, Total pages: %s",
            threading.current_thread().name,
            self.current_page_index,
            self.project.page_count(),
        )
        self.is_navigating = True
        self.notify()
        logger.info("[_navigate] Set is_navigating=True and notified")

        async def _background_load():
            import threading

            background_load_started = perf_counter()
            logger.info(
                "[_background_load] Entry - Thread: %s, Loading page index: %s",
                threading.current_thread().name,
                self.current_page_index,
            )
            try:
                # Pre-load the page at the new index
                # NOTE: run.io_bound runs in a separate thread pool to prevent
                # blocking the asyncio event loop and websocket connection
                logger.info(
                    "[_background_load] Calling run.io_bound for page %s",
                    self.current_page_index,
                )
                await run.io_bound(self.get_page, self.current_page_index)
                logger.info(
                    "[_background_load] run.io_bound completed for page %s",
                    self.current_page_index,
                )
                # Update text cache now that page is loaded
                self._update_text_cache(force=True)
                logger.info(
                    "[_background_load] Page %s loaded successfully, cache updated",
                    self.current_page_index,
                )
            except Exception as e:
                logger.error(
                    "[_background_load] ERROR loading page %s: %s",
                    self.current_page_index,
                    e,
                    exc_info=True,
                )
                raise
            finally:
                background_load_duration_ms = (
                    perf_counter() - background_load_started
                ) * 1000
                self._log_page_navigation_timing(
                    index=self.current_page_index,
                    duration_ms=background_load_duration_ms,
                )
                logger.info("[_background_load] Cleanup - Setting is_navigating=False")
                self.is_navigating = False
                self.loading_status = ""
                self.notify()
                logger.info(
                    "[_background_load] Exit - Thread: %s",
                    threading.current_thread().name,
                )

        def _schedule_async_load():
            """Schedule background load using NiceGUI's background task API.

            Uses background_tasks.create() for proper async task management
            without interfering with NiceGUI's event loop.
            """
            import threading

            logger.info(
                "[_schedule_async_load] Entry - Thread: %s",
                threading.current_thread().name,
            )
            pending_load = None
            try:
                # Use NiceGUI's background task API
                logger.info("[_schedule_async_load] Creating background task")
                pending_load = _background_load()
                background_tasks.create(pending_load)
                logger.info("[_schedule_async_load] Background task created")
                return
            except Exception as e:
                if pending_load is not None:
                    try:
                        pending_load.close()
                    except Exception:
                        pass
                logger.warning(
                    "[_schedule_async_load] Failed to create background task (%s); falling back to synchronous page load",
                    e,
                )
                # Fallback synchronous load
                try:
                    self.get_page(self.current_page_index)
                finally:
                    self.is_project_loading = False
                    self.is_navigating = False
                    self.notify()

        logger.info("[_navigate] Calling _schedule_async_load()")
        _schedule_async_load()
        logger.info("[_navigate] Exit - is_navigating=%s", self.is_navigating)

    def save_current_page(
        self,
        save_directory: str = "local-data/labeled-ocr",
        project_id: Optional[str] = None,
    ) -> bool:
        """Save the current page using its PageState.

        This is a convenience method that delegates to the PageState for the current page.

        Args:
            save_directory: Directory to save files (default: "local-data/labeled-ocr")
            project_id: Project identifier. If None, derives from project root directory name.

        Returns:
            bool: True if save was successful, False otherwise.
        """
        logger.debug(
            "save_current_page: called with save_directory=%s, project_id=%s",
            save_directory,
            project_id,
        )
        page_state = self.get_page_state(self.current_page_index)

        # Try PageState first if page is available
        if page_state.get_page(self.current_page_index) is not None:
            result = page_state.persist_page_to_file(
                page_index=self.current_page_index,
                save_directory=save_directory,
                project_id=project_id,
            )
        else:
            # Fall back to direct implementation for backward compatibility (tests)
            page = self.current_page()
            if page is None:
                logger.error("No current page available to save")
                result = False
            else:
                operations = PageOperations()
                result = operations.save_page(
                    page=page,
                    project_root=self.project_root,
                    save_directory=save_directory,
                    project_id=project_id,
                    source_lib=self.project.source_lib,
                )
                if result:
                    # Update page source to indicate it's now on the filesystem
                    if hasattr(page, "page_source"):
                        page.page_source = "filesystem"  # type: ignore[attr-defined]
                    page_state.page_sources[self.current_page_index] = "filesystem"
                    page_state.notify()
        logger.debug("save_current_page: completed, result=%s", result)
        return result

    def load_current_page(
        self,
        save_directory: str = "local-data/labeled-ocr",
        project_id: Optional[str] = None,
    ) -> bool:
        """Load the current page from saved files.

        This is a convenience method that delegates to the PageState for the current page.

        Args:
            save_directory: Directory where files were saved (default: "local-data/labeled-ocr")
            project_id: Project identifier. If None, derives from project root directory name.

        Returns:
            bool: True if load was successful, False otherwise.
        """
        logger.debug(
            "load_current_page: called with save_directory=%s, project_id=%s",
            save_directory,
            project_id,
        )
        page_state = self.get_page_state(self.current_page_index)
        success = page_state.load_page_from_file(
            page_index=self.current_page_index,
            save_directory=save_directory,
            project_id=project_id,
        )
        if success:
            # Invalidate cache since page content changed
            self._invalidate_text_cache()
        logger.debug("load_current_page: completed, success=%s", success)
        return success

    def refine_all_bboxes(self, padding_px: int = 2) -> bool:
        """Refine all bounding boxes in the current page.

        Args:
            padding_px: Padding in pixels to use for refinement (default: 2).

        Returns:
            bool: True if refinement was successful, False otherwise.
        """
        logger.debug("refine_all_bboxes: called with padding_px=%s", padding_px)
        page_state = self.get_page_state(self.current_page_index)
        page = page_state.get_page(self.current_page_index)

        if page is None:
            logger.error("No current page available to refine bboxes")
            return False

        result = self.page_ops.refine_all_bboxes(page=page, padding_px=padding_px)

        if result:
            # Invalidate cache since page content changed
            self._invalidate_text_cache()
            # Notify UI of changes
            page_state.notify()

        logger.debug("refine_all_bboxes: completed, result=%s", result)
        return result

    def expand_and_refine_all_bboxes(self, padding_px: int = 2) -> bool:
        """Expand and refine all bounding boxes in the current page.

        Args:
            padding_px: Padding in pixels to use for refinement (default: 2).

        Returns:
            bool: True if operation was successful, False otherwise.
        """
        logger.debug(
            "expand_and_refine_all_bboxes: called with padding_px=%s", padding_px
        )
        page_state = self.get_page_state(self.current_page_index)
        page = page_state.get_page(self.current_page_index)

        if page is None:
            logger.error("No current page available to expand and refine bboxes")
            return False

        result = self.page_ops.expand_and_refine_all_bboxes(
            page=page, padding_px=padding_px
        )

        if result:
            # Invalidate cache since page content changed
            self._invalidate_text_cache()
            # Notify UI of changes
            page_state.notify()

        logger.debug("expand_and_refine_all_bboxes: completed, result=%s", result)
        return result

    def refresh_page_images(self) -> bool:
        """Refresh all generated images for the current page.

        Returns:
            bool: True if refresh was successful, False otherwise.
        """
        logger.debug("refresh_page_images: called")
        page_state = self.get_page_state(self.current_page_index)
        page = page_state.get_page(self.current_page_index)

        if page is None:
            logger.error("No current page available to refresh images")
            return False

        result = self.page_ops.refresh_page_images(page=page)

        if result:
            # Notify UI of changes
            page_state.notify()

        logger.debug("refresh_page_images: completed, result=%s", result)
        return result

    @property
    def current_page_source_text(self) -> str:
        """Get the source text for the current page.

        Returns appropriate status text based on loading state and page availability.
        """
        logger.debug("current_page_source_text: called")

        # If currently loading, show loading status
        if self.is_project_loading or self.is_navigating:
            logger.debug("current_page_source_text: currently loading")
            return "LOADING..."

        # Check if page is already loaded in cache
        if (
            not self.project.pages
            or self.current_page_index < 0
            or self.current_page_index >= len(self.project.pages)
        ):
            logger.debug("current_page_source_text: no pages or invalid index")
            return "(NO PAGE)"

        # Get the page directly from cache to avoid triggering loads
        page = self.project.pages[self.current_page_index]

        # If page is not yet loaded in cache, return appropriate status
        if page is None:
            logger.debug("current_page_source_text: page not yet in cache")
            return "(NO PAGE)"

        result = TextOperations.get_page_source_text(page, False)
        logger.debug("current_page_source_text: returning text: %s", result)
        return result

    @property
    def current_page_source_tooltip(self) -> str:
        """Get provenance tooltip text for the current page source badge."""
        if self.is_project_loading or self.is_navigating:
            return ""

        if (
            not self.project.pages
            or self.current_page_index < 0
            or self.current_page_index >= len(self.project.pages)
        ):
            return ""

        page = self.project.pages[self.current_page_index]
        if page is None:
            return ""

        if TextOperations.get_page_source_text(page, False) not in (
            "LABELED",
            "CACHED OCR",
        ):
            return ""

        return self.page_ops.get_page_provenance_summary(page)

    @property
    def current_ocr_text(self) -> str:
        """Get the OCR text for the current page (cached for performance)."""
        logger.debug("current_ocr_text: called")
        self._update_text_cache()
        logger.debug("current_ocr_text: returning cached text")
        return self._cached_ocr_text

    @property
    def current_gt_text(self) -> str:
        """Get the ground truth text for the current page (cached for performance)."""
        logger.debug("current_gt_text: called")
        self._update_text_cache()
        logger.debug("current_gt_text: returning cached text")
        return self._cached_gt_text

    def _invalidate_text_cache(self):
        """Invalidate the cached text values when page content changes."""
        logger.debug("_invalidate_text_cache: called")
        self._cached_page_index = -1
        self._cached_ocr_text = ""
        self._cached_gt_text = ""
        logger.debug("_invalidate_text_cache: completed")

    def _update_text_cache(self, force: bool = False):
        """Update cached text values for the current page."""
        logger.debug("_update_text_cache: called with force=%s", force)
        if TextOperations.should_update_text_cache(
            self.current_page_index, self._cached_page_index, force
        ):
            # Only update cache if page is already loaded to avoid triggering OCR
            if TextOperations.is_page_loaded_for_cache(
                self.project.pages, self.current_page_index
            ):
                page = self.project.pages[self.current_page_index]
                self._cached_ocr_text, self._cached_gt_text = (
                    TextOperations.get_page_texts(page, self.project.ground_truth_map)
                )
                self._cached_page_index = self.current_page_index
            else:
                # Page not loaded yet, keep old cache or set to loading
                if self._cached_page_index == -1 or force:
                    self._cached_ocr_text, self._cached_gt_text = (
                        TextOperations.get_loading_text()
                    )
                    self._cached_page_index = self.current_page_index
        logger.debug("_update_text_cache: completed")

    def _normalize_ground_truth_entries(self, data: dict) -> dict[str, str]:
        """Normalize ground truth entries for flexible filename lookup.

        Creates multiple lookup keys for each entry:
        - Original key
        - Lowercase variant
        - With/without file extensions

        Parameters
        ----------
        data : dict
            Raw ground truth data from JSON

        Returns
        -------
        dict[str, str]
            Normalized lookup dictionary with multiple keys per entry
        """
        norm: dict[str, str] = {}
        for k, v in data.items():
            if not isinstance(k, str):
                continue
            text_val: str | None = (
                v if isinstance(v, str) else (str(v) if v is not None else None)
            )
            if text_val is None:
                continue
            norm[k] = text_val
            lower_k = k.lower()
            norm.setdefault(lower_k, text_val)
            if "." not in k:
                for ext in IMAGE_EXTS:
                    norm.setdefault(f"{k}{ext}", text_val)
                    norm.setdefault(f"{k}{ext}".lower(), text_val)
        return norm

    async def load_ground_truth_map(self, directory: Path) -> dict[str, str]:
        """Load and normalize ground truth data from pages.json file.

        Parameters
        ----------
        directory : Path
            Directory containing pages.json file

        Returns
        -------
        dict[str, str]
            Normalized ground truth mapping, empty dict if file not found or invalid
        """
        pages_json = directory / "pages.json"
        exists = await run.io_bound(pages_json.exists)
        if not exists:
            logger.info("No pages.json found in %s", directory)
            return {}
        try:
            raw_text = await run.io_bound(pages_json.read_text, encoding="utf-8")
            data = await run.io_bound(json.loads, raw_text)
            if isinstance(data, dict):
                norm = self._normalize_ground_truth_entries(data)
                logger.info(
                    "Loaded %d ground truth entries from %s", len(norm), pages_json
                )
                return norm
            logger.warning("pages.json root is not an object (dict): %s", pages_json)
        except Exception as exc:  # pragma: no cover - robustness
            logger.warning("Failed to load pages.json (%s): %s", pages_json, exc)
        return {}

    def find_ground_truth_text(
        self, name: str, ground_truth_map: dict[str, str]
    ) -> str | None:
        """Find ground truth text for a given page name using variant lookup.

        The normalization process adds multiple keys (with/without extension, lowercase).
        This helper attempts a list of variants in priority order to find a match.

        Parameters
        ----------
        name : str
            The image filename (e.g. "001.png") or bare page identifier
        ground_truth_map : dict[str, str]
            Normalized mapping produced by ``load_ground_truth_map``

        Returns
        -------
        str | None
            Ground truth text if found, None otherwise
        """
        if not name:
            return None
        candidates: list[str] = []
        # Original provided name
        candidates.append(name)
        # Lowercase variant
        candidates.append(name.lower())
        # If name has extension, add base name variants; else add ext variants (handled by normalization)
        if "." in name:
            base = name.rsplit(".", 1)[0]
            candidates.extend([base, base.lower()])
        # Deduplicate while preserving order
        seen = set()
        for c in candidates:
            if c in seen:
                continue
            seen.add(c)
            if c in ground_truth_map:
                return ground_truth_map[c]
        return None

    def create_fallback_page(
        self,
        index: int,
        img_path: Path,
    ) -> Page:
        """Create a fallback page when OCR fails, attaching image and ground truth if available.

        Args:
            index: Zero-based page index.
            img_path: Path to the image file.

        Returns:
            Page: A basic fallback page object.
        """
        page = Page(width=0, height=0, page_index=index, items=[])
        page.image_path = img_path  # type: ignore[attr-defined]
        page.name = img_path.name  # type: ignore[attr-defined]
        page.index = index  # type: ignore[attr-defined]
        page.ocr_failed = True  # type: ignore[attr-defined]

        # Add ground truth if available
        gt_text = self.find_ground_truth_text(
            img_path.name, self.project.ground_truth_map
        )
        if gt_text:
            page.add_ground_truth(gt_text)  # type: ignore[attr-defined]
            logger.debug("Injected ground truth for fallback page: %s", img_path.name)

        # Best-effort load image
        try:
            from cv2 import imread as cv2_imread

            img = cv2_imread(str(img_path))
            if img is not None:
                page.cv2_numpy_page_image = img  # type: ignore[attr-defined]
                logger.debug("Attached cv2 image for fallback page: %s", img_path.name)
        except Exception:
            logger.debug("cv2 load failed for fallback page: %s", img_path.name)

        return page
