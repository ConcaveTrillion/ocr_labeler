"""Page state view model for displaying page images in MVVM pattern."""

from __future__ import annotations

import hashlib
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from nicegui import background_tasks, binding, run

from ...state import PageState
from ...state.project_state import ProjectState
from ..shared.base_viewmodel import BaseViewModel

logger = logging.getLogger(__name__)

# Shared thread pool for image encoding to prevent thread pool exhaustion
# Limit to 4 concurrent encoding operations to prevent overwhelming the system
_image_encoding_executor = ThreadPoolExecutor(
    max_workers=4, thread_name_prefix="img_encode"
)


@binding.bindable_dataclass
class PageStateViewModel(BaseViewModel):
    """View model for page-specific state and image display."""

    # UI-bound image source properties
    original_image_source: str = ""
    paragraphs_image_source: str = ""
    lines_image_source: str = ""
    words_image_source: str = ""
    mismatches_image_source: str = ""

    # Exposed page metadata for UI binding
    page_index: int = -1
    page_source: str = ""
    current_page_source_text: str = ""
    current_page_source_tooltip: str = ""

    # Page state reference
    _page_state: Optional[PageState] = None

    # Flag to prevent concurrent updates
    _update_in_progress: bool = False
    _update_scheduled: bool = False

    # Cache for encoded images to avoid re-encoding unchanged images
    _encoded_image_cache: dict[str, str] = None

    # Callback for direct image updates (bypasses binding to avoid websocket issues)
    _image_update_callback: Optional[callable] = None
    _last_image_callback_signature: tuple | None = None
    _image_update_schedule_count: int = 0
    _image_update_schedule_skip_count: int = 0
    _image_update_emit_count: int = 0
    _image_update_emit_skip_count: int = 0

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
        self._encoded_image_cache: dict[str, str] = {}
        self._image_update_callback: Optional[callable] = None
        self._last_image_callback_signature: tuple | None = None
        self._image_update_schedule_count: int = 0
        self._image_update_schedule_skip_count: int = 0
        self._image_update_emit_count: int = 0
        self._image_update_emit_skip_count: int = 0

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
        self.paragraphs_image_source = ""
        self.lines_image_source = ""
        self.words_image_source = ""
        self.mismatches_image_source = ""

        if not keep_metadata:
            self.page_index = -1
            self.page_source = ""
        self.current_page_source_text = ""
        self.current_page_source_tooltip = ""

    def _bind_to_page_state(self, page_state: PageState | None):
        """Bind the viewmodel to a PageState instance, managing listeners."""
        # Remove previous listener if present
        try:
            if (
                self._page_state
                and self._on_page_state_change in self._page_state.on_change
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

    def _schedule_image_update(self):
        """Schedule an async image update using NiceGUI's background task API.

        Uses NiceGUI's background_tasks.create() to properly handle async operations
        without interfering with the event loop.
        """
        # Skip if an update is already in progress to prevent cascading updates
        if self._update_in_progress:
            self._image_update_schedule_skip_count += 1
            logger.debug("_schedule_image_update: update already in progress, skipping")
            logger.info(
                "[_schedule_image_update] Skip in-progress (scheduled=%d, schedule_skips=%d, emitted=%d, emit_skips=%d)",
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

            # Refresh page images using NiceGUI's io_bound for IO operations
            image_mappings = self._image_mappings()
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

            # Encode images using NiceGUI's io_bound API
            # Use caching to avoid re-encoding unchanged images
            encoded_results = []
            for prop_name, attr_name in image_mappings:
                np_img = getattr(current_page, attr_name, None)
                encoded = await run.io_bound(
                    self._encode_image_cached,
                    np_img,
                    attr_name,
                )
                encoded_results.append((prop_name, encoded))

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
            for prop_name, attr_name in image_mappings:
                np_img = getattr(current_page, attr_name, None)
                encoded = self._encode_image(np_img)
                encoded_results.append((prop_name, encoded))

            self._apply_encoded_results(encoded_results, current_page)
            logger.debug("_update_image_sources_blocking: completed")
        finally:
            self._update_scheduled = False

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
            ("paragraphs_image_source", "cv2_numpy_page_image_paragraph_with_bboxes"),
            ("lines_image_source", "cv2_numpy_page_image_line_with_bboxes"),
            ("words_image_source", "cv2_numpy_page_image_word_with_bboxes"),
            (
                "mismatches_image_source",
                "cv2_numpy_page_image_matched_word_with_colors",
            ),
        ]

    def set_image_update_callback(self, callback: callable):
        """Register a callback for direct image updates (bypasses data binding)."""
        self._image_update_callback = callback
        self._last_image_callback_signature = None
        self._image_update_emit_count = 0
        self._image_update_emit_skip_count = 0
        logger.debug("Image update callback registered")

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
                logger.debug(
                    f"_apply_encoded_results: Stored {prop_name} (length: {len(new_value) if new_value else 0})"
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

    def _compute_image_hash(self, np_img) -> str:
        """Compute a hash of the image for caching purposes."""
        if np_img is None:
            return "none"
        try:
            # Use image shape and a sample of pixels for fast hashing
            # This avoids hashing the entire image which would be slow
            h, w = np_img.shape[:2]
            # Sample 100 evenly distributed pixels
            sample_indices = [
                (i * h // 10, j * w // 10) for i in range(10) for j in range(10)
            ]
            sample_data = bytes(
                [
                    np_img[i, j, 0] if len(np_img.shape) == 3 else np_img[i, j]
                    for i, j in sample_indices
                    if i < h and j < w
                ]
            )
            shape_data = (
                f"{h}x{w}x{np_img.shape[2] if len(np_img.shape) == 3 else 1}".encode()
            )
            return hashlib.md5(shape_data + sample_data).hexdigest()
        except Exception:
            # If hashing fails, use a timestamp-based fallback
            import time

            return f"fallback_{time.time()}"

    def _encode_image_cached(self, np_img, cache_key: str) -> str:
        """Encode image with caching to avoid re-encoding unchanged images."""
        if np_img is None:
            return ""

        # Compute hash of the image
        img_hash = self._compute_image_hash(np_img)
        full_cache_key = f"{cache_key}_{img_hash}"

        # Check cache first
        if full_cache_key in self._encoded_image_cache:
            logger.debug(f"Using cached encoding for {cache_key}")
            return self._encoded_image_cache[full_cache_key]

        # Encode the image
        encoded = self._encode_image_sync(np_img)

        # Cache the result (limit cache size to prevent memory issues)
        if len(self._encoded_image_cache) > 50:
            # Remove oldest entries (simple FIFO)
            keys_to_remove = list(self._encoded_image_cache.keys())[:10]
            for key in keys_to_remove:
                del self._encoded_image_cache[key]

        self._encoded_image_cache[full_cache_key] = encoded
        return encoded

    def _encode_image_sync(self, np_img) -> str:
        """Encode a numpy image to a base64 data URL (synchronous)."""
        if np_img is None:
            logger.debug("No image to encode")
            return ""

        shape = getattr(np_img, "shape", None)
        if not isinstance(shape, tuple):
            logger.debug("Unsupported image object for encoding; skipping")
            return ""

        try:
            import base64

            import cv2

            # Ensure image is in the right format
            if len(shape) == 2:
                # Grayscale image, convert to RGB
                np_img = cv2.cvtColor(np_img, cv2.COLOR_GRAY2RGB)
            elif len(shape) > 2 and shape[2] == 4:
                # RGBA image, convert to RGB
                np_img = cv2.cvtColor(np_img, cv2.COLOR_RGBA2RGB)

            # Resize large images to make them more manageable
            height, width = np_img.shape[:2]
            max_dimension = 1200  # Reasonable max size for web display

            if width > max_dimension or height > max_dimension:
                # Calculate new dimensions maintaining aspect ratio
                if width > height:
                    new_width = max_dimension
                    new_height = int(height * max_dimension / width)
                else:
                    new_height = max_dimension
                    new_width = int(width * max_dimension / height)

                np_img = cv2.resize(
                    np_img, (new_width, new_height), interpolation=cv2.INTER_AREA
                )
                logger.debug(
                    f"Resized image from {width}x{height} to {new_width}x{new_height}"
                )

            # Encode to PNG
            success, buffer = cv2.imencode(".png", np_img)
            if success:
                encoded = base64.b64encode(buffer.tobytes()).decode("ascii")
                data_url = f"data:image/png;base64,{encoded}"
                logger.debug(f"Successfully encoded image, size: {len(data_url)} chars")
                return data_url
            else:
                logger.warning("cv2.imencode failed to encode image")
                return ""

        except Exception as e:
            logger.exception(f"Failed to encode image: {e}")
            return ""

        # Backward compatibility for tests monkeypatching _encode_image
        # (legacy name before async refactor)

    def _encode_image(self, np_img):  # pragma: no cover - legacy alias
        return self._encode_image_sync(np_img)

    def _clear_image_sources(self, keep_metadata: bool = False):
        """Clear all image sources.

        Args:
            keep_metadata: When True, preserve page_index/page_source values so
                navigation UI stays consistent while images are hidden.
        """
        self._initialize_bindable_defaults(keep_metadata=keep_metadata)
        # Clear the cache when clearing image sources
        if hasattr(self, "_encoded_image_cache"):
            self._encoded_image_cache.clear()

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
