"""Page state view model for displaying page images in MVVM pattern."""

from __future__ import annotations

import hashlib
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from nicegui import background_tasks, binding, run

from ...operations.persistence.persistence_paths_operations import (
    PersistencePathsOperations,
)
from ...state import PageState
from ...state.project_state import ProjectState
from ..shared.base_viewmodel import BaseViewModel

logger = logging.getLogger(__name__)

# Shared thread pool for image encoding to prevent thread pool exhaustion
# Limit to 4 concurrent encoding operations to prevent overwhelming the system
_image_encoding_executor = ThreadPoolExecutor(
    max_workers=4, thread_name_prefix="img_encode"
)

# Maximum total byte size of encoded images held in the per-viewmodel cache.
# len() of a base64 data-URL string is a close proxy for encoded byte count.
# Short label inserted into cached filenames for each numpy image attribute.
# Format: {project_id}_{page:03d}_{image_type}_{content_hash}{ext}
_IMAGE_TYPE_LABELS: dict[str, str] = {
    "cv2_numpy_page_image": "original",
}


@binding.bindable_dataclass
class PageStateViewModel(BaseViewModel):
    """View model for page-specific state and image display."""

    # UI-bound image source properties
    original_image_source: str = ""
    word_view_original_image_source: str = ""
    word_view_image_page_index: int = -1

    # Exposed page metadata for UI binding
    page_index: int = -1
    page_source: str = ""
    current_page_source_text: str = ""
    current_page_source_tooltip: str = ""
    current_export_status_text: str = ""

    # Page state reference
    _page_state: PageState | None = None

    # Flag to prevent concurrent updates
    _update_in_progress: bool = False
    _update_scheduled: bool = False
    _update_reschedule_requested: bool = False

    # Callback for direct image updates (bypasses binding to avoid websocket issues)
    _image_update_callback: callable | None = None
    _word_view_image_ready_callback: callable | None = None
    _last_image_callback_signature: tuple | None = None
    _image_update_schedule_count: int = 0
    _image_update_schedule_skip_count: int = 0
    _image_update_emit_count: int = 0
    _image_update_emit_skip_count: int = 0
    _word_image_cache_dir: Path | None = None

    def __init__(self, page_state: PageState | None):
        logger.debug("Initializing PageStateViewModel")
        super().__init__()

        # Ensure all bindable attributes exist before any NiceGUI binding occurs
        # so that early refreshes during view construction do not trip strict
        # binding checks. These defaults are overwritten as soon as real data
        # flows in from the bound PageState.
        self._initialize_bindable_defaults()

        # Always define these to avoid attribute errors when a page_state is
        # not yet available during early UI construction.
        self._project_state: ProjectState | None = None
        self._page_state: PageState | None = None
        self._update_in_progress: bool = False
        self._update_scheduled: bool = False
        self._update_reschedule_requested: bool = False
        self._image_update_callback: callable | None = None
        self._word_view_image_ready_callback: callable | None = None
        self._last_image_callback_signature: tuple | None = None
        self._image_update_schedule_count: int = 0
        self._image_update_schedule_skip_count: int = 0
        self._image_update_emit_count: int = 0
        self._image_update_emit_skip_count: int = 0
        self._word_image_cache_dir: Path = (
            PersistencePathsOperations.get_page_image_cache_root()
        )
        self._word_image_cache_dir.mkdir(parents=True, exist_ok=True)

        # Accept None here and defer binding until a valid state is provided.
        # This prevents initialization-time errors when UI constructs viewmodels
        # before the ProjectState has been created/populated.
        if page_state is None:
            logger.debug(
                "PageStateViewModel initialized without page_state; deferring binding until available"
            )
            return

        # Support being passed either a PageState (per-page) or a ProjectState
        # If passed ProjectState, bind to its current_page_state and listen for
        # project-level changes so we can rebind to the newly active PageState.
        if isinstance(page_state, ProjectState):
            # Bind to project-level state: get the current page's PageState
            self._project_state = page_state
            initial = self._project_state.current_page_state
            self._bind_to_page_state(initial)

            # Expose the current page index immediately for UI bindings even if
            # the page object hasn't been materialized yet.
            try:
                self.page_index = int(self._project_state.current_page_index)
            except Exception:
                self.page_index = -1

            # Listen for project-level changes so we can rebind when navigation occurs
            logger.debug("Registering project state change listener for page rebinding")
            self._project_state.on_change.append(self._on_project_state_change)
        else:
            # Assume a PageState was provided
            self._bind_to_page_state(page_state)

        logger.debug("PageStateViewModel initialized successfully")

        # Update image sources immediately in case page is already loaded
        logger.debug("Performing initial image source update")
        self._update_image_sources()

    def _initialize_bindable_defaults(self, keep_metadata: bool = False):
        """Initialize all properties that NiceGUI bindings expect to exist."""

        self.original_image_source = ""
        self.word_view_original_image_source = ""
        self.word_view_image_page_index = -1

        if not keep_metadata:
            self.page_index = -1
            self.page_source = ""
        self.current_page_source_text = ""
        self.current_page_source_tooltip = ""

    def _bind_to_page_state(self, page_state: PageState | None):
        """Bind the viewmodel to a PageState instance, managing listeners."""
        # Remove previous listener if present
        try:
            if self._page_state and self._has_change_listener(
                getattr(self._page_state, "on_change", None),
                self._on_page_state_change,
            ):
                self._page_state.on_change.remove(self._on_page_state_change)
        except Exception:
            # best-effort removal
            pass

        # Attach new page_state
        self._page_state = page_state
        if self._page_state is not None:
            try:
                self._page_state.on_change.append(self._on_page_state_change)
            except Exception:
                # Ensure on_change exists as a list; defensive
                try:
                    self._page_state.on_change = [self._on_page_state_change]
                except Exception:
                    pass
        self._sync_source_badge()

    @staticmethod
    def _has_change_listener(listeners: object, callback: object) -> bool:
        """Return whether a change-listener container already includes a callback."""
        try:
            return callback in listeners
        except TypeError:
            return False
        except Exception:
            return False

    @staticmethod
    def _normalize_cached_filenames(cached_filenames: object) -> dict[str, str]:
        """Return cached filenames only when they are stored as a plain mapping."""
        if isinstance(cached_filenames, dict):
            return cached_filenames
        return {}

    def _resolve_project_root_for_cache_persistence(self) -> Path | None:
        """Return the best available project root for cache persistence operations."""
        project_root = getattr(self._project_state, "project_root", None)
        if project_root is not None:
            return project_root
        return getattr(self._page_state, "_project_root", None)

    async def _persist_cached_images_async(
        self,
        current_page_model: object,
        project_id: str,
    ) -> None:
        """Delegate cached image bookkeeping to page operations."""
        page_ops = getattr(self._page_state, "page_ops", None)
        project_root = self._resolve_project_root_for_cache_persistence()
        if page_ops is None or project_root is None:
            return
        await run.io_bound(
            page_ops.update_cached_images_in_json,
            current_page_model,
            project_root,
            project_id=project_id,
        )

    def _persist_cached_images_blocking(
        self,
        current_page_model: object,
        project_id: str,
    ) -> None:
        """Blocking wrapper for cached image bookkeeping via page operations."""
        page_ops = getattr(self._page_state, "page_ops", None)
        project_root = self._resolve_project_root_for_cache_persistence()
        if page_ops is None or project_root is None:
            return
        page_ops.update_cached_images_in_json(
            current_page_model,
            project_root,
            project_id=project_id,
        )

    def _on_project_state_change(self):
        """Handle project-level changes by rebinding to the new current PageState."""
        if not self._project_state:
            return
        try:
            # If navigation just started, clear existing images to avoid old→new flash.
            if getattr(self._project_state, "is_navigating", False):
                self._clear_image_sources(keep_metadata=True)

            new_page_state = self._project_state.current_page_state
            # Rebind only if the underlying PageState instance changed
            if new_page_state is not self._page_state:
                logger.debug(
                    "Project state changed - rebinding PageStateViewModel to new PageState"
                )
                self._bind_to_page_state(new_page_state)
                # Refresh images from newly bound page
                # Update the exposed index immediately; images will follow
                try:
                    self.page_index = int(self._project_state.current_page_index)
                except Exception:
                    self.page_index = -1
        except Exception as e:
            logger.exception("Error rebinding to new PageState: %s", e)
        finally:
            self._sync_source_badge()
            # Always schedule an update so we refresh when navigation completes
            self._schedule_image_update()

    def _on_page_state_change(self):
        """Listener for PageState changes; update image sources."""
        logger.debug("PageState change detected, updating image sources")
        self._sync_source_badge()
        self._schedule_image_update()

    def _sync_source_badge(self):
        """Synchronize source badge text/tooltip from page-domain state."""
        if not self._page_state:
            self.current_page_source_text = "(NO PAGE)"
            self.current_page_source_tooltip = ""
            self.current_export_status_text = ""
            return

        try:
            self.current_page_source_text = self._page_state.current_page_source_text
            self.current_page_source_tooltip = (
                self._page_state.current_page_source_tooltip
            )
        except Exception:
            logger.debug("Failed to sync source badge from PageState", exc_info=True)
            self.current_page_source_text = "(NO PAGE)"
            self.current_page_source_tooltip = ""

        try:
            self.current_export_status_text = (
                self._page_state.current_page_export_status
            )
        except Exception:
            logger.debug("Failed to sync export status from PageState", exc_info=True)
            self.current_export_status_text = ""

    def _schedule_image_update(self):
        """Schedule an async image update using NiceGUI's background task API.

        Uses NiceGUI's background_tasks.create() to properly handle async operations
        without interfering with the event loop.
        """
        # Skip if an update is already in progress to prevent cascading updates
        if self._update_in_progress:
            self._update_reschedule_requested = True
            self._image_update_schedule_skip_count += 1
            logger.debug("_schedule_image_update: update already in progress, skipping")
            logger.info(
                "[_schedule_image_update] Skip in-progress and coalesce rerun (scheduled=%d, schedule_skips=%d, emitted=%d, emit_skips=%d)",
                self._image_update_schedule_count,
                self._image_update_schedule_skip_count,
                self._image_update_emit_count,
                self._image_update_emit_skip_count,
            )
            return

        # Skip if an async update has already been queued but not started yet.
        if self._update_scheduled:
            self._image_update_schedule_skip_count += 1
            logger.debug("_schedule_image_update: update already scheduled, skipping")
            logger.info(
                "[_schedule_image_update] Skip already-scheduled (scheduled=%d, schedule_skips=%d, emitted=%d, emit_skips=%d)",
                self._image_update_schedule_count,
                self._image_update_schedule_skip_count,
                self._image_update_emit_count,
                self._image_update_emit_skip_count,
            )
            return

        # Skip during navigation to prevent blocking the event loop while
        # OCR/page loading is in progress (prevents "connection lost" errors)
        if self._is_navigation_in_progress_and_unloaded():
            logger.debug(
                "_schedule_image_update: navigation in progress; deferring update"
            )
            return

        pending_update = self._update_image_sources_async()
        self._update_scheduled = True
        self._image_update_schedule_count += 1
        logger.info(
            "[_schedule_image_update] Queued update (scheduled=%d, schedule_skips=%d, emitted=%d, emit_skips=%d)",
            self._image_update_schedule_count,
            self._image_update_schedule_skip_count,
            self._image_update_emit_count,
            self._image_update_emit_skip_count,
        )
        try:
            # Use NiceGUI's background task API
            background_tasks.create(pending_update)
        except (AssertionError, RuntimeError):
            self._update_scheduled = False
            try:
                pending_update.close()
            except Exception:
                pass
            # No event loop running (e.g., in test context) - use blocking fallback
            # This is safe because there's no websocket connection to timeout
            logger.debug(
                "_schedule_image_update: no usable event loop; using blocking fallback"
            )
            self._update_image_sources_blocking()
        except Exception:
            self._update_scheduled = False
            try:
                pending_update.close()
            except Exception:
                pass
            # Other errors during async scheduling - skip to avoid blocking
            logger.warning(
                "_schedule_image_update: failed to schedule async update; skipping",
                exc_info=True,
            )

    async def _update_image_sources_async(self):
        """Async image update using NiceGUI's IO-bound task API.

        Uses run.io_bound() for proper thread pool management without
        interfering with NiceGUI's event loop.
        """
        import threading

        self._update_in_progress = True
        try:
            logger.debug("_update_image_sources_async: starting image source update")
            current_page = self._get_current_page_or_clear()
            if current_page is None:
                return

            # Avoid blocking the loop during navigation until the target page is loaded
            if self._is_navigation_in_progress_and_unloaded():
                logger.debug(
                    "_update_image_sources_async: navigation in progress; skipping update"
                )
                return

            image_mappings = self._image_mappings()

            # Resolve page context once — needed for both the fast and slow paths.
            try:
                page_index = int(getattr(current_page, "index", -1) or -1)
            except (TypeError, ValueError):
                page_index = -1
            project_id = self._resolve_project_id_for_cache()
            image_extension = self._resolve_cache_image_extension(
                current_page, page_index
            )

            # Fast path: all images were cached in a previous session and the
            # files still exist on disk.  Skip refresh_page_images() entirely.
            current_page_model = self._get_current_page_model()
            cached_filenames = self._normalize_cached_filenames(
                getattr(current_page_model, "cached_image_filenames", None)
            )
            expected_types = {
                _IMAGE_TYPE_LABELS.get(attr, attr) for _, attr in image_mappings
            }
            cache_dir = self._word_image_cache_dir
            if (
                cached_filenames
                and expected_types.issubset(cached_filenames.keys())
                and all(
                    (cache_dir / fname).exists()
                    for fname in cached_filenames.values()
                    if fname
                )
            ):
                logger.debug(
                    "_update_image_sources_async: all images found in disk cache "
                    "for page %d; skipping refresh_page_images",
                    page_index,
                )
                encoded_results = []
                original_image_source = ""
                for prop_name, attr_name in image_mappings:
                    image_type = _IMAGE_TYPE_LABELS.get(attr_name, attr_name)
                    url = self._url_from_cached_filename(cached_filenames[image_type])
                    url = self._append_refresh_nonce(url, current_page)
                    encoded_results.append((prop_name, url))
                    if attr_name == "cv2_numpy_page_image":
                        original_image_source = url
                encoded_results.append(
                    ("word_view_original_image_source", original_image_source)
                )
                encoded_results.append(("word_view_image_page_index", page_index))
                if current_page_model is not None:
                    await self._persist_cached_images_async(
                        current_page_model, project_id
                    )
                self._apply_encoded_results(encoded_results, current_page)
                return

            # Slow path: generate / cache images, then persist filenames.
            needs_refresh = any(
                getattr(current_page, attr_name, None) is None
                for _, attr_name in image_mappings
            )
            if needs_refresh and hasattr(current_page, "refresh_page_images"):
                try:
                    await run.io_bound(current_page.refresh_page_images)
                except Exception as e:
                    logger.warning(
                        "_update_image_sources_async: failed to refresh page images: %s",
                        e,
                    )

            # Write all images to the shared disk cache; return static URLs.
            encoded_results = []
            original_image_source = ""
            new_cached_filenames: dict[str, str] = {}
            for prop_name, attr_name in image_mappings:
                np_img = getattr(current_page, attr_name, None)
                # Use the source image extension for the original page image;
                # PNG for generated overlays (they have no natural source format).
                ext = image_extension if attr_name == "cv2_numpy_page_image" else ".png"
                image_type = _IMAGE_TYPE_LABELS.get(attr_name, attr_name)
                source = await run.io_bound(
                    self._cache_image_to_disk,
                    np_img,
                    image_type,
                    page_index,
                    project_id,
                    ext,
                )
                source = self._append_refresh_nonce(source, current_page)
                encoded_results.append((prop_name, source))
                if attr_name == "cv2_numpy_page_image":
                    original_image_source = source
                if source:
                    # filename = last path component before the query string
                    new_cached_filenames[image_type] = source.split("?")[0].rsplit(
                        "/", 1
                    )[-1]

            if new_cached_filenames and current_page_model is not None:
                current_page_model.cached_image_filenames = new_cached_filenames
                await self._persist_cached_images_async(
                    current_page_model,
                    project_id,
                )

            # Word-view reuses the already-cached original image URL.
            encoded_results.append(
                ("word_view_original_image_source", original_image_source)
            )
            encoded_results.append(("word_view_image_page_index", page_index))

            self._apply_encoded_results(encoded_results, current_page)
            logger.debug("_update_image_sources_async: completed")
            logger.info(
                "[_update_image_sources_async] Completed - Thread: %s",
                threading.current_thread().name,
            )
        except Exception as e:
            logger.error(
                "[_update_image_sources_async] UNEXPECTED ERROR: %s", e, exc_info=True
            )
            raise
        finally:
            self._update_scheduled = False
            self._update_in_progress = False
            if self._update_reschedule_requested:
                self._update_reschedule_requested = False
                self._schedule_image_update()

    def _update_image_sources_blocking(self):
        """Synchronous image update - WARNING: blocks event loop!

        This method should ONLY be used in test contexts or when no event loop
        is running. Using this while NiceGUI's event loop is active will cause
        websocket "connection lost" errors.

        For production use, always prefer _update_image_sources_async() via
        _schedule_image_update().
        """
        logger.warning(
            "_update_image_sources_blocking: BLOCKING image update called - "
            "this may cause connection loss in production!"
        )
        self._update_in_progress = True
        try:
            current_page = self._get_current_page_or_clear()
            if current_page is None:
                return

            if self._is_navigation_in_progress_and_unloaded():
                logger.debug(
                    "_update_image_sources_blocking: navigation in progress; skipping update"
                )
                return

            image_mappings = self._image_mappings()

            try:
                page_index = int(getattr(current_page, "index", -1) or -1)
            except (TypeError, ValueError):
                page_index = -1
            project_id = self._resolve_project_id_for_cache()
            image_extension = self._resolve_cache_image_extension(
                current_page, page_index
            )

            # Fast path: use pre-cached files if available.
            current_page_model = self._get_current_page_model()
            cached_filenames = self._normalize_cached_filenames(
                getattr(current_page_model, "cached_image_filenames", None)
            )
            expected_types = {
                _IMAGE_TYPE_LABELS.get(attr, attr) for _, attr in image_mappings
            }
            cache_dir = self._word_image_cache_dir
            if (
                cached_filenames
                and expected_types.issubset(cached_filenames.keys())
                and all(
                    (cache_dir / fname).exists()
                    for fname in cached_filenames.values()
                    if fname
                )
            ):
                encoded_results = []
                original_image_source = ""
                for prop_name, attr_name in image_mappings:
                    image_type = _IMAGE_TYPE_LABELS.get(attr_name, attr_name)
                    url = self._url_from_cached_filename(cached_filenames[image_type])
                    url = self._append_refresh_nonce(url, current_page)
                    encoded_results.append((prop_name, url))
                    if attr_name == "cv2_numpy_page_image":
                        original_image_source = url
                encoded_results.append(
                    ("word_view_original_image_source", original_image_source)
                )
                encoded_results.append(("word_view_image_page_index", page_index))
                if current_page_model is not None:
                    self._persist_cached_images_blocking(current_page_model, project_id)
                self._apply_encoded_results(encoded_results, current_page)
                return

            # Slow path: generate images.
            needs_refresh = any(
                getattr(current_page, attr_name, None) is None
                for _, attr_name in image_mappings
            )
            if needs_refresh and hasattr(current_page, "refresh_page_images"):
                try:
                    current_page.refresh_page_images()
                except Exception as e:
                    logger.warning(
                        "_update_image_sources_blocking: failed to refresh page images: %s",
                        e,
                    )

            encoded_results = []
            original_image_source = ""
            new_cached_filenames: dict[str, str] = {}
            for prop_name, attr_name in image_mappings:
                np_img = getattr(current_page, attr_name, None)
                ext = image_extension if attr_name == "cv2_numpy_page_image" else ".png"
                image_type = _IMAGE_TYPE_LABELS.get(attr_name, attr_name)
                source = self._cache_image_to_disk(
                    np_img, image_type, page_index, project_id, ext
                )
                source = self._append_refresh_nonce(source, current_page)
                encoded_results.append((prop_name, source))
                if attr_name == "cv2_numpy_page_image":
                    original_image_source = source
                if source:
                    new_cached_filenames[image_type] = source.split("?")[0].rsplit(
                        "/", 1
                    )[-1]

            if new_cached_filenames and current_page_model is not None:
                current_page_model.cached_image_filenames = new_cached_filenames
                self._persist_cached_images_blocking(
                    current_page_model,
                    project_id,
                )

            encoded_results.append(
                ("word_view_original_image_source", original_image_source)
            )
            encoded_results.append(("word_view_image_page_index", page_index))

            self._apply_encoded_results(encoded_results, current_page)
            logger.debug("_update_image_sources_blocking: completed")
        finally:
            self._update_scheduled = False
            self._update_in_progress = False
            if self._update_reschedule_requested:
                self._update_reschedule_requested = False
                self._schedule_image_update()

    def _update_image_sources(self):
        """Maintain backward compatibility for direct calls."""
        self._schedule_image_update()

        # Get current page. Support two shapes:
        # - PageState: exposes current_page attribute (optional Page)
        # - ProjectState-backed context: inspect in-memory project.pages cache only

    def _get_current_page_or_clear(self):
        """Return the current page or clear bindings if unavailable."""
        logger.debug("_get_current_page_or_clear: fetching current page")
        if not self._page_state:
            logger.warning(
                "_get_current_page_or_clear: No page state available for image source update"
            )
            self._clear_image_sources()
            return None

        current_page = None
        try:
            maybe = getattr(self._page_state, "current_page", None)
            if callable(maybe):
                current_page = maybe()
            else:
                # attribute-style PageState.current_page
                current_page = maybe
        except Exception:
            # Defensive fallback
            try:
                current_page = self._page_state and getattr(
                    self._page_state, "current_page", None
                )
            except Exception:
                current_page = None

        logger.debug(f"_get_current_page_or_clear: Current page: {current_page}")
        # If we are navigating and don't yet have a page object, avoid triggering
        # synchronous loads from ProjectState; keep existing images until the
        # navigation completes and the background load finishes.
        navigating = getattr(self._project_state, "is_navigating", False)

        # If PageState does not expose a current_page instance, but we are bound to
        # a ProjectState, inspect the in-memory project pages cache directly.
        # Do not call ProjectState.current_page_model() here because it can trigger
        # synchronous page/OCR loading and block UI updates (including queued
        # notifications) during route-driven initialization.
        if (not current_page) and getattr(self, "_project_state", None) is not None:
            if not navigating:
                try:
                    proj = getattr(self._project_state, "project", None)
                    idx = getattr(self._project_state, "current_page_index", None)
                    if proj is not None and hasattr(proj, "pages") and idx is not None:
                        try:
                            current_page = proj.pages[idx]
                            logger.debug(
                                f"_get_current_page_or_clear: got page from project.pages[{idx}]: {current_page}"
                            )
                        except Exception:
                            current_page = None
                except Exception:
                    current_page = None
            else:
                logger.debug(
                    "_get_current_page_or_clear: navigation in progress; deferring page lookup"
                )

        if not current_page:
            # During navigation, keep existing images instead of clearing
            if navigating:
                logger.debug(
                    "_get_current_page_or_clear: no page yet while navigating; keeping prior images"
                )
                return None
            logger.debug(
                "_get_current_page_or_clear: No current page available, clearing image sources"
            )
            self._clear_image_sources()
            return None

        logger.debug(
            f"_get_current_page_or_clear: Updating image sources for page: {getattr(current_page, 'name', 'unknown')}"
        )

        # Expose page metadata for UI bindings
        try:
            idx_val = getattr(current_page, "index", -1)
            # Allow zero index; only fallback when None or missing
            if idx_val is None:
                self.page_index = -1
            else:
                self.page_index = int(idx_val)
        except Exception:
            self.page_index = -1
        try:
            self.page_source = str(getattr(current_page, "page_source", "") or "")
        except Exception:
            self.page_source = ""

        logger.debug(
            f"_get_current_page_or_clear: Page metadata - index: {self.page_index}, source: {self.page_source}"
        )
        return current_page

    def _is_navigation_in_progress_and_unloaded(self) -> bool:
        """True when navigating and target page isn't loaded yet."""
        if getattr(self, "_project_state", None) is None:
            return False
        try:
            if getattr(self._project_state, "is_navigating", False):
                pages = getattr(self._project_state.project, "pages", [])
                idx = getattr(self._project_state, "current_page_index", -1)
                if not (0 <= idx < len(pages)) or pages[idx] is None:
                    return True
        except Exception:
            logger.debug(
                "_is_navigation_in_progress_and_unloaded: inspection failed; treating as navigating",
                exc_info=True,
            )
            return True
        return False

    def _image_mappings(self):
        return [
            ("original_image_source", "cv2_numpy_page_image"),
        ]

    def set_image_update_callback(self, callback: callable):
        """Register a callback for direct image updates (bypasses data binding)."""
        self._image_update_callback = callback
        self._last_image_callback_signature = None
        self._image_update_emit_count = 0
        self._image_update_emit_skip_count = 0
        logger.debug("Image update callback registered")

    def set_word_view_image_ready_callback(self, callback: callable | None):
        """Register callback fired when word-view original image source is ready."""
        self._word_view_image_ready_callback = callback

    def _apply_encoded_results(self, results, current_page):
        import threading

        logger.info(
            "[_apply_encoded_results] Entry - Thread: %s, Applying %d image updates",
            threading.current_thread().name,
            len(results),
        )

        # Store properties for state tracking
        for prop_name, new_value in results:
            current_value = getattr(self, prop_name, "")
            if new_value != current_value:
                # Update property silently (for state storage only)
                object.__setattr__(self, prop_name, new_value)
                value_size = 0
                try:
                    value_size = len(new_value) if new_value else 0
                except TypeError:
                    value_size = 1 if new_value is not None else 0
                logger.debug(
                    f"_apply_encoded_results: Stored {prop_name} (length: {value_size})"
                )

        if self._word_view_image_ready_callback:
            try:
                source = str(getattr(self, "word_view_original_image_source", "") or "")
                page_index = int(getattr(self, "word_view_image_page_index", -1) or -1)
                if source:
                    self._word_view_image_ready_callback(page_index, source)
            except Exception:
                logger.debug(
                    "Word-view image ready callback failed",
                    exc_info=True,
                )

        # Use callback for UI update instead of triggering data binding
        if self._image_update_callback:
            callback_signature = self._build_callback_signature(results)
            if callback_signature == self._last_image_callback_signature:
                self._image_update_emit_skip_count += 1
                logger.debug(
                    "[_apply_encoded_results] Skipping callback; image payload unchanged"
                )
                logger.info(
                    "[_apply_encoded_results] Callback skipped (unchanged payload, emitted=%d, emit_skips=%d)",
                    self._image_update_emit_count,
                    self._image_update_emit_skip_count,
                )
                return

            logger.info(
                "[_apply_encoded_results] Calling image update callback with %d images",
                len(results),
            )
            try:
                # Pass all images at once to avoid multiple websocket updates
                image_dict = {prop_name: value for prop_name, value in results}
                self._image_update_callback(image_dict)
                self._image_update_emit_count += 1
                self._last_image_callback_signature = callback_signature
                logger.info(
                    "[_apply_encoded_results] Callback completed successfully (emitted=%d, emit_skips=%d)",
                    self._image_update_emit_count,
                    self._image_update_emit_skip_count,
                )
            except Exception as e:
                logger.error(
                    "[_apply_encoded_results] ERROR in callback: %s",
                    e,
                    exc_info=True,
                )
        else:
            # Fallback to data binding if no callback registered
            logger.warning(
                "[_apply_encoded_results] No callback registered, using data binding (may cause issues)"
            )
            for prop_name, new_value in results:
                current_value = getattr(self, prop_name, "")
                if new_value != current_value:
                    try:
                        setattr(self, prop_name, new_value)
                    except Exception as e:
                        logger.error(
                            "[_apply_encoded_results] ERROR setting %s: %s",
                            prop_name,
                            e,
                            exc_info=True,
                        )
                        raise

        logger.info(
            "[_apply_encoded_results] Exit - All %d updates applied", len(results)
        )

    def _build_callback_signature(self, results: list[tuple[str, str]]) -> tuple:
        """Build stable signature for callback payload deduplication."""
        return tuple(results)

    def _append_refresh_nonce(self, source: str, current_page: object) -> str:
        """Append structural-edit nonce to image URL to force browser refresh."""
        if not source:
            return source

        # Only mutate shared static-cache URLs; synthetic test sources like
        # "encoded:..." should remain unchanged for deterministic assertions.
        if not source.startswith("/_word_image_cache/"):
            return source

        refresh_nonce = getattr(
            current_page, "_ocr_labeler_overlay_refresh_nonce", None
        )
        if not refresh_nonce:
            return source

        separator = "&" if "?" in source else "?"
        return f"{source}{separator}r={refresh_nonce}"

    def _compute_image_hash(self, np_img) -> str:
        """Compute a hash of the image for caching purposes."""
        if np_img is None:
            return "none"
        try:
            contiguous = np.ascontiguousarray(np_img)
            shape_data = repr(contiguous.shape).encode("utf-8")
            dtype_data = str(contiguous.dtype).encode("utf-8")
            image_data = memoryview(contiguous).tobytes()
            return hashlib.md5(
                shape_data + b"|" + dtype_data + b"|" + image_data
            ).hexdigest()
        except Exception:
            # If hashing fails, use a timestamp-based fallback
            import time

            return f"fallback_{time.time()}"

    def _cache_image_to_disk(
        self,
        np_img,
        image_type: str,
        page_index: int,
        project_id: str,
        image_extension: str,
    ) -> str:
        """Write a processed page image to the shared on-disk cache and return its static URL.

        The cache is shared across server sessions and keyed by project, page, image
        type, and a content hash of the (resized) image.  Because overlay images
        (paragraphs/lines/words/mismatches) are content-hashed after OCR bounding
        boxes are applied, any change to OCR output automatically produces a new
        cache entry without touching existing files for other pages.

        Returns a /_word_image_cache/ static URL, or "" on failure.
        """
        if np_img is None:
            return ""

        shape = getattr(np_img, "shape", None)
        if not isinstance(shape, tuple):
            return ""

        cache_dir = self._word_image_cache_dir or (
            PersistencePathsOperations.get_page_image_cache_root()
        )
        cache_dir.mkdir(parents=True, exist_ok=True)

        try:
            import cv2

            # Normalise colour space so all cached files are consistent.
            if len(shape) == 2:
                np_img = cv2.cvtColor(np_img, cv2.COLOR_GRAY2RGB)
            elif len(shape) > 2 and shape[2] == 4:
                np_img = cv2.cvtColor(np_img, cv2.COLOR_RGBA2RGB)

            height, width = np_img.shape[:2]
            max_dimension = 1200
            if width > max_dimension or height > max_dimension:
                if width > height:
                    new_width = max_dimension
                    new_height = max(1, int(height * max_dimension / width))
                else:
                    new_height = max_dimension
                    new_width = max(1, int(width * max_dimension / height))
                np_img = cv2.resize(
                    np_img, (new_width, new_height), interpolation=cv2.INTER_AREA
                )

            img_hash = self._compute_image_hash(np_img)
            safe_page_index = max(-1, int(page_index))
            safe_project_id = (project_id or "project").strip() or "project"
            safe_image_type = (image_type or "image").strip() or "image"
            page_number = max(1, safe_page_index + 1)
            normalized_extension = self._normalize_cache_extension(image_extension)
            file_name = f"{safe_project_id}_{page_number:03d}_{safe_image_type}_{img_hash}{normalized_extension}"
            output_path = cache_dir / file_name

            if not output_path.exists():
                encode_options: list[int] = []
                if normalized_extension in {".jpg", ".jpeg"}:
                    encode_options = [int(cv2.IMWRITE_JPEG_QUALITY), 90]
                success, buffer = cv2.imencode(
                    normalized_extension, np_img, encode_options
                )
                if not success:
                    return ""
                output_path.write_bytes(buffer.tobytes())

            return f"/_word_image_cache/{file_name}?v={img_hash[:8]}"
        except Exception:
            logger.debug("Failed caching image to disk", exc_info=True)
            return ""

    def _get_current_page_model(self):
        """Return the current PageModel from the bound state, or None."""
        state = self._page_state
        if state is None:
            return None
        maybe = getattr(state, "current_page_model", None)
        if callable(maybe):
            try:
                return maybe()
            except Exception:
                return None
        return maybe

    @staticmethod
    def _url_from_cached_filename(filename: str) -> str:
        """Reconstruct a /_word_image_cache/ static URL from a bare filename.

        The filename format is ``{project}_{page:03d}_{type}_{hash}{ext}``.
        The hash embedded in the stem is reused as the cache-busting query param.
        """
        stem = Path(filename).stem  # e.g. "proj_001_original_abc123def456"
        hash_part = stem.rsplit("_", 1)[-1]  # "abc123def456"
        return f"/_word_image_cache/{filename}?v={hash_part[:8]}"

    def _resolve_project_id_for_cache(self) -> str:
        """Return project_id for cache filenames, matching saved page file conventions."""
        project_state = getattr(self, "_project_state", None)
        project = getattr(project_state, "project", None) if project_state else None
        project_id = str(getattr(project, "project_id", "") or "").strip()
        if project_id:
            return project_id

        project_root = (
            getattr(project_state, "project_root", None) if project_state else None
        )
        try:
            root_name = str(getattr(project_root, "name", "") or "").strip()
            if root_name:
                return root_name
        except Exception:
            pass

        return "project"

    def _resolve_cache_image_extension(self, current_page, page_index: int) -> str:
        """Resolve extension from the original page image path; fallback to .jpg."""
        candidates: list[object] = []
        candidates.append(getattr(current_page, "image_path", None))
        candidates.append(getattr(current_page, "name", None))

        project_state = getattr(self, "_project_state", None)
        project = getattr(project_state, "project", None) if project_state else None
        image_paths = getattr(project, "image_paths", None) if project else None
        if isinstance(image_paths, list) and 0 <= page_index < len(image_paths):
            candidates.append(image_paths[page_index])

        for candidate in candidates:
            try:
                suffix = Path(str(candidate)).suffix.lower()
            except Exception:
                continue
            normalized = self._normalize_cache_extension(suffix)
            if normalized:
                return normalized

        return ".jpg"

    def _normalize_cache_extension(self, suffix: str | None) -> str:
        """Normalize cache extension to supported formats with sensible fallback."""
        value = str(suffix or "").strip().lower()
        if not value:
            return ".jpg"
        if not value.startswith("."):
            value = f".{value}"
        if value in {".jpg", ".jpeg", ".png"}:
            return value
        return ".jpg"

    def _clear_image_sources(self, keep_metadata: bool = False):
        """Clear all image sources.

        Args:
            keep_metadata: When True, preserve page_index/page_source values so
                navigation UI stays consistent while images are hidden.
        """
        self._initialize_bindable_defaults(keep_metadata=keep_metadata)

    # Command methods for UI actions

    def command_refresh_images(self) -> bool:
        """Command to refresh all image sources.

        Returns:
            True if refresh was successful.
        """
        try:
            logger.debug("Refreshing image sources via command")
            self._update_image_sources()
            return True
        except Exception:
            logger.exception("Error refreshing images")
            return False
