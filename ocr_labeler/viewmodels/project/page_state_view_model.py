"""Page state view model for displaying page images in MVVM pattern."""

from __future__ import annotations

import logging
from typing import Optional

from nicegui import binding

from ...state import PageState
from ...state.project_state import ProjectState
from ..shared.base_viewmodel import BaseViewModel

logger = logging.getLogger(__name__)


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

    # Page state reference
    _page_state: Optional[PageState] = None

    def __init__(self, page_state: PageState | None):
        logger.debug("Initializing PageStateViewModel")
        super().__init__()

        # Accept None here and defer binding until a valid state is provided.
        # This prevents initialization-time errors when UI constructs viewmodels
        # before the ProjectState has been created/populated.
        if page_state is None:
            logger.debug(
                "PageStateViewModel initialized without page_state; deferring binding until available"
            )
            self._project_state = None
            self._page_state = None
            return

        # Support being passed either a PageState (per-page) or a ProjectState
        # If passed ProjectState, bind to its current_page_state and listen for
        # project-level changes so we can rebind to the newly active PageState.
        self._project_state: ProjectState | None = None

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

    def _on_project_state_change(self):
        """Handle project-level changes by rebinding to the new current PageState."""
        if not self._project_state:
            return
        try:
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
                self._update_image_sources()
        except Exception as e:
            logger.exception("Error rebinding to new PageState: %s", e)

    def _on_page_state_change(self):
        """Listener for PageState changes; update image sources."""
        logger.debug("PageState change detected, updating image sources")
        self._update_image_sources()

    def _update_image_sources(self):
        """Update all image sources from the current page."""
        logger.debug("_update_image_sources: Starting image source update")
        if not self._page_state:
            logger.warning(
                "_update_image_sources: No page state available for image source update"
            )
            self._clear_image_sources()
            return

        # Get current page. Support two shapes:
        # - ProjectState: exposes current_page() method
        # - PageState: exposes current_page attribute (optional Page)
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

        logger.debug(f"_update_image_sources: Current page: {current_page}")
        # If PageState does not expose a current_page instance, but we are bound to
        # a ProjectState, try to get the page via the ProjectState helper. This
        # covers cases where PageState manages per-page caches but the ProjectState
        # is the authoritative source for loading the page object.
        if not current_page and getattr(self, "_project_state", None) is not None:
            try:
                logger.debug(
                    "_update_image_sources: attempting to get current page from ProjectState"
                )
                current_page = self._project_state.current_page()
                logger.debug(
                    f"_update_image_sources: got page from ProjectState: {current_page}"
                )
            except Exception:
                logger.debug(
                    "_update_image_sources: failed to get page from ProjectState"
                )
            # If ProjectState.current_page() didn't return a page (tests may stub
            # pages directly into the project's pages list), try a direct index
            # lookup into the project's pages list.
            if current_page is None:
                try:
                    proj = getattr(self._project_state, "project", None)
                    idx = getattr(self._project_state, "current_page_index", None)
                    if proj is not None and hasattr(proj, "pages") and idx is not None:
                        try:
                            current_page = proj.pages[idx]
                            logger.debug(
                                f"_update_image_sources: got page from project.pages[{idx}]: {current_page}"
                            )
                        except Exception:
                            current_page = None
                except Exception:
                    current_page = None
        if not current_page:
            logger.debug(
                "_update_image_sources: No current page available, clearing image sources"
            )
            self._clear_image_sources()
            return

        logger.debug(
            f"_update_image_sources: Updating image sources for page: {getattr(current_page, 'name', 'unknown')}"
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

        # Define image attribute mappings
        image_mappings = [
            ("original_image_source", "cv2_numpy_page_image"),
            ("paragraphs_image_source", "cv2_numpy_page_image_paragraph_with_bboxes"),
            ("lines_image_source", "cv2_numpy_page_image_line_with_bboxes"),
            ("words_image_source", "cv2_numpy_page_image_word_with_bboxes"),
            (
                "mismatches_image_source",
                "cv2_numpy_page_image_matched_word_with_colors",
            ),
        ]

        # Refresh page images only if needed (avoid flicker from redundant refreshes)
        needs_refresh = False
        for _, attr_name in image_mappings:
            if getattr(current_page, attr_name, None) is None:
                needs_refresh = True
                break
        if needs_refresh and hasattr(current_page, "refresh_page_images"):
            try:
                logger.debug("_update_image_sources: Refreshing page images")
                current_page.refresh_page_images()
            except Exception as e:
                logger.warning(
                    "_update_image_sources: Failed to refresh page images: %s", e
                )

        # Update each image source
        for prop_name, attr_name in image_mappings:
            image_attr = getattr(current_page, attr_name, None)
            logger.debug(
                f"_update_image_sources: {attr_name} = {type(image_attr)} {'(None)' if image_attr is None else f'(shape: {image_attr.shape})' if hasattr(image_attr, 'shape') else '(no shape attr)'}"
            )
            new_value = self._encode_image(image_attr)

            # Only update if the source actually changed to reduce flicker
            current_value = getattr(self, prop_name, "")
            if new_value != current_value:
                # For bindable dataclass properties, just set the value directly
                # NiceGUI will handle the binding automatically
                setattr(self, prop_name, new_value)
                logger.debug(
                    f"_update_image_sources: Set {prop_name}: {'success' if new_value else 'cleared'} (length: {len(new_value) if new_value else 0})"
                )
            else:
                logger.debug(
                    f"_update_image_sources: {prop_name} unchanged; skipping update"
                )

    def _encode_image(self, np_img) -> str:
        """Encode a numpy image to a base64 data URL."""
        if np_img is None:
            logger.debug("No image to encode")
            return ""

        try:
            import base64

            import cv2

            # Ensure image is in the right format
            if len(np_img.shape) == 2:
                # Grayscale image, convert to RGB
                np_img = cv2.cvtColor(np_img, cv2.COLOR_GRAY2RGB)
            elif np_img.shape[2] == 4:
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

    def _clear_image_sources(self):
        """Clear all image sources."""
        image_props = [
            "original_image_source",
            "paragraphs_image_source",
            "lines_image_source",
            "words_image_source",
            "mismatches_image_source",
        ]

        for prop_name in image_props:
            # For bindable dataclass properties, just set the value directly
            setattr(self, prop_name, "")

        # Clear exposed metadata as well
        self.page_index = -1
        self.page_source = ""

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
