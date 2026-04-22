from __future__ import annotations

import contextlib
import logging
from dataclasses import dataclass, field
from functools import wraps
from pathlib import Path
from typing import TYPE_CHECKING, Callable

from nicegui import Event
from pd_book_tools.ocr.page import Page  # type: ignore

from ..models.page_model import PageModel
from ..operations.ocr.bbox_operations import BboxOperations
from ..operations.ocr.page_operations import PageOperations
from ..operations.persistence.persistence_paths_operations import (
    PersistencePathsOperations,
)

if TYPE_CHECKING:
    from ..models.project_model import Project
    from .project_state import ProjectState

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WordStyleChangedEvent:
    """Typed event emitted when a single word's style flags are updated."""

    page_index: int
    line_index: int
    word_index: int
    italic: bool
    small_caps: bool
    blackletter: bool
    left_footnote: bool
    right_footnote: bool


@dataclass(frozen=True)
class WordGroundTruthChangedEvent:
    """Typed event emitted when a single word's GT text is updated."""

    page_index: int
    line_index: int
    word_index: int
    ground_truth_text: str


@dataclass(frozen=True)
class WordValidationChangedEvent:
    """Typed event emitted when a single word's validation state is toggled."""

    page_index: int
    line_index: int
    word_index: int
    is_validated: bool


class _GroundTruthRematchSkipped(Exception):
    """Raised when GT rematch cannot proceed (no GT text or missing methods)."""


@dataclass
class PageState:
    """Page-specific state management. Oversees page loading, caching, and operations.

    Responsibilities:
    - Handle page loading and caching
    - Manage page-specific operations (save/load, copy ground truth to OCR)
    - Provide access to current page data
    """

    page_ops: PageOperations = field(default_factory=PageOperations)
    on_change: list[Callable[[], None]] | None = field(default_factory=list)
    on_word_ground_truth_change: Event[WordGroundTruthChangedEvent] = field(
        default_factory=Event
    )
    on_word_style_change: Event[WordStyleChangedEvent] = field(default_factory=Event)
    on_word_validation_change: Event[WordValidationChangedEvent] = field(
        default_factory=Event
    )

    # Reference to project for accessing pages (set by ProjectState)
    _project: Project | None = field(default=None, init=False)
    _project_root: Path | None = field(default=None, init=False)
    _project_state: "ProjectState" | None = field(
        default=None, init=False
    )  # Reference to parent ProjectState
    current_page: Page | None = field(default=None, init=False)
    current_page_model: PageModel | None = field(default=None, init=False)
    original_page: Page | None = field(default=None, init=False)

    # Cached text values for current page
    _cached_page_index: int = field(default=-1, init=False)
    _cached_ocr_text: str = field(default="", init=False)
    _cached_gt_text: str = field(default="", init=False)
    _overlay_refresh_nonce_counter: int = field(default=0, init=False)
    _page_index: int = field(default=0, init=False)

    def notify(self):
        """Notify listeners of state changes."""
        for listener in list(self.on_change or []):
            try:
                listener()
            except Exception:
                logger.exception("PageState.notify: listener callback failed")

    def _emit_word_style_changed(self, event: WordStyleChangedEvent) -> None:
        """Notify listeners of a targeted word-style mutation."""
        logger.debug(
            "[word_style_event] emitted page=%s line=%s word=%s italic=%s small_caps=%s blackletter=%s",
            event.page_index,
            event.line_index,
            event.word_index,
            event.italic,
            event.small_caps,
            event.blackletter,
        )
        self.on_word_style_change.emit(event)

    def _emit_word_ground_truth_changed(
        self,
        event: WordGroundTruthChangedEvent,
    ) -> None:
        """Notify listeners of a targeted word GT mutation."""
        logger.debug(
            "[word_gt_event] emitted page=%s line=%s word=%s text=%r",
            event.page_index,
            event.line_index,
            event.word_index,
            event.ground_truth_text,
        )
        self.on_word_ground_truth_change.emit(event)

    def _emit_word_validation_changed(
        self,
        event: WordValidationChangedEvent,
    ) -> None:
        """Notify listeners of a targeted word validation toggle."""
        logger.debug(
            "[word_validation_event] emitted page=%s line=%s word=%s validated=%s",
            event.page_index,
            event.line_index,
            event.word_index,
            event.is_validated,
        )
        self.on_word_validation_change.emit(event)

    def _resolve_workspace_save_directory(
        self, save_directory: str | Path | None
    ) -> str:
        """Resolve save directory using user-local defaults and explicit overrides."""
        return PersistencePathsOperations.resolve_workspace_save_directory(
            save_directory
        )

    def _on_project_state_change(self):
        """Handle project state changes to sync page index."""
        if self._project_state:
            # Sync the current page index from project state
            new_index = self._project_state.current_page_index
            if new_index != self._current_page_index:
                logger.debug(
                    "PageState: Syncing page index from ProjectState: %s -> %s",
                    self._current_page_index,
                    new_index,
                )
                self._current_page_index = new_index
                # Force update of text cache for the new page
                self._update_text_cache(force=True)
                # Notify our own listeners
                self.notify()
                return

            # If index didn't change, we may still need to refresh cached text when
            # async loading completes for this page. Without this, caches can remain
            # stuck at "Loading..." after Next/Back/Goto navigation.
            if not self._project:
                return

            has_loading_placeholder = (
                self._cached_ocr_text == "Loading..."
                or self._cached_gt_text == "Loading..."
            )
            page_is_loaded = (
                0 <= self._current_page_index < len(self._project.pages)
                and self._project.pages[self._current_page_index] is not None
            )

            if has_loading_placeholder and page_is_loaded:
                logger.debug(
                    "PageState: Refreshing text cache for index %s after async load completion",
                    self._current_page_index,
                )
                self._update_text_cache(force=True)

    def notify_on_completion(func):
        """Decorator to call self.notify() after method completion."""

        @wraps(func)
        def wrapper(self, *args, **kwargs):
            result = func(self, *args, **kwargs)
            self.notify()
            return result

        return wrapper

    @notify_on_completion
    def set_project_context(
        self, project: Project, project_root: Path, project_state: "ProjectState"
    ):
        """Set the project context for page operations."""
        self._project = project
        self._project_root = project_root
        self._project_state = project_state
        # Register listener for project state changes to sync page index
        if self._project_state:
            self._project_state.on_change.append(self._on_project_state_change)

    def get_page_model(self, index: int, force_ocr: bool = False) -> PageModel | None:
        """Get page model at the specified index, loading it if necessary."""
        if not self._project_state:
            logger.warning("PageState.get_page_model: no project state set")
            return None

        logger.debug(
            "PageState.get_page_model: index=%s, force_ocr=%s", index, force_ocr
        )

        # Delegate to ProjectState for page loading
        page_model = self._project_state.ensure_page_model(index, force_ocr=force_ocr)
        page = page_model.page if page_model is not None else None

        # Cache the page reference so downstream consumers (e.g., word match view,
        # GT→OCR copy helpers) can access the most recent page without triggering
        # another ensure/load cycle.
        self.current_page = page
        self.current_page_model = page_model

        # If loaded from OCR and no original stored yet, store a copy
        page_source = page_model.page_source if page_model is not None else None
        if page_source is None:
            page_source = (
                str(getattr(page, "page_source", "")) if page is not None else ""
            )

        if (
            page is not None
            and page_source == "ocr"
            and self.original_page is None
            and hasattr(page, "to_dict")
        ):
            try:
                self.original_page = Page.from_dict(page.to_dict())
            except Exception:
                logger.debug(
                    "PageState.get_page_model: unable to snapshot original page",
                    exc_info=True,
                )

        return page_model

    def copy_ground_truth_to_ocr(self, line_index: int) -> bool:
        """Copy ground truth text to OCR text for all words in the specified line.

        Args:
            line_index: Zero-based line index to process

        Returns:
            bool: True if any modifications were made, False otherwise
        """
        page = self.current_page
        if not page:
            logger.critical("No page available for GT→OCR copy.")
            return False

        # Import inside method to allow test monkeypatching
        try:
            from ..operations.ocr.line_operations import LineOperations

            line_ops = LineOperations()
            result = line_ops.copy_ground_truth_to_ocr(page, line_index)

            if result:
                # Trigger UI refresh to show updated matches
                self._invalidate_text_cache()
                self.notify()

            return result
        except Exception:
            logger.exception("Error in GT→OCR copy for line %s", line_index)
            return False

    def copy_ocr_to_ground_truth(self, line_index: int) -> bool:
        """Copy OCR text to ground truth text for all words in the specified line.

        Args:
            line_index: Zero-based line index to process

        Returns:
            bool: True if any modifications were made, False otherwise
        """
        page = self.current_page
        if not page:
            logger.critical("No page available for OCR→GT copy.")
            return False

        # Import inside method to allow test monkeypatching
        try:
            from ..operations.ocr.line_operations import LineOperations

            line_ops = LineOperations()
            result = line_ops.copy_ocr_to_ground_truth(page, line_index)

            if result:
                # Trigger UI refresh to show updated matches
                self._invalidate_text_cache()
                self.notify()

            return result
        except Exception:
            logger.exception("Error in OCR→GT copy for line %s", line_index)
            return False

    def update_word_ground_truth(
        self,
        line_index: int,
        word_index: int,
        ground_truth_text: str,
    ) -> bool:
        """Update ground truth text for a single word on the current page.

        Args:
            line_index: Zero-based line index.
            word_index: Zero-based word index.
            ground_truth_text: New GT text value.

        Returns:
            bool: True if update succeeded, False otherwise.
        """
        page = self.current_page
        if not page:
            logger.critical("No page available for word GT update.")
            return False

        try:
            from ..operations.ocr.line_operations import LineOperations

            line_ops = LineOperations()
            result = line_ops.update_word_ground_truth(
                page,
                line_index,
                word_index,
                ground_truth_text,
            )

            if result:
                self._invalidate_text_cache()
                self._emit_word_ground_truth_changed(
                    WordGroundTruthChangedEvent(
                        page_index=self._current_page_index,
                        line_index=line_index,
                        word_index=word_index,
                        ground_truth_text=str(ground_truth_text or ""),
                    )
                )
                self.notify()

            return result
        except Exception as e:
            logger.exception(
                "Error updating word GT line=%s word=%s: %s",
                line_index,
                word_index,
                e,
            )
            return False

    def copy_selected_words_ocr_to_ground_truth(
        self,
        word_keys: list[tuple[int, int]],
    ) -> bool:
        """Copy OCR text to GT for only selected words on the current page."""
        page = self.current_page
        if not page:
            logger.critical("No page available for selected-word OCR→GT copy.")
            return False

        try:
            from ..operations.ocr.line_operations import LineOperations

            line_ops = LineOperations()
            result = line_ops.copy_selected_words_ocr_to_ground_truth(page, word_keys)

            if result:
                self._invalidate_text_cache()
                self.notify()

            return result
        except Exception as e:
            logger.exception(
                "Error in selected-word OCR→GT copy: %s",
                e,
            )
            return False

    def update_word_attributes(
        self,
        line_index: int,
        word_index: int,
        italic: bool,
        small_caps: bool,
        blackletter: bool,
        left_footnote: bool,
        right_footnote: bool,
    ) -> bool:
        """Update style attributes for a single word on the current page.

        Args:
            line_index: Zero-based line index.
            word_index: Zero-based word index.
            italic: Whether word is italic.
            small_caps: Whether word is small caps.
            blackletter: Whether word is blackletter.
            left_footnote: Whether word has a left footnote marker.
            right_footnote: Whether word has a right footnote marker.

        Returns:
            bool: True if update succeeded, False otherwise.
        """
        page = self.current_page
        if not page:
            logger.critical("No page available for word attribute update.")
            return False

        try:
            from ..operations.ocr.line_operations import LineOperations

            line_ops = LineOperations()
            result = line_ops.update_word_attributes(
                page,
                line_index,
                word_index,
                italic,
                small_caps,
                blackletter,
                left_footnote,
                right_footnote,
            )

            if result:
                self._invalidate_text_cache()
                self._emit_word_style_changed(
                    WordStyleChangedEvent(
                        page_index=self._current_page_index,
                        line_index=line_index,
                        word_index=word_index,
                        italic=bool(italic),
                        small_caps=bool(small_caps),
                        blackletter=bool(blackletter),
                        left_footnote=bool(left_footnote),
                        right_footnote=bool(right_footnote),
                    )
                )
                self.notify()

            return result
        except Exception as e:
            logger.exception(
                "Error updating word attributes line=%s word=%s: %s",
                line_index,
                word_index,
                e,
            )
            return False

    def toggle_word_validated(
        self,
        line_index: int,
        word_index: int,
    ) -> bool:
        """Toggle the validated flag for a single word on the current page.

        Returns:
            True if toggle succeeded, False otherwise.
        """
        page = self.current_page
        if not page:
            logger.critical("No page available for word validation toggle.")
            return False

        try:
            lines = list(getattr(page, "lines", []) or [])
            if line_index < 0 or line_index >= len(lines):
                logger.warning(
                    "toggle_word_validated: invalid line_index=%s", line_index
                )
                return False

            words = list(getattr(lines[line_index], "words", []) or [])
            if word_index < 0 or word_index >= len(words):
                logger.warning(
                    "toggle_word_validated: invalid word_index=%s", word_index
                )
                return False

            word = words[word_index]
            labels = set(getattr(word, "word_labels", []) or [])
            is_validated = "validated" not in labels
            if is_validated:
                labels.add("validated")
            else:
                labels.discard("validated")
            word.word_labels = list(labels)

            self._invalidate_text_cache()
            self._emit_word_validation_changed(
                WordValidationChangedEvent(
                    page_index=self._current_page_index,
                    line_index=line_index,
                    word_index=word_index,
                    is_validated=is_validated,
                )
            )
            self._auto_save_to_cache()
            self.notify()
            return True
        except Exception as e:
            logger.exception(
                "Error toggling word validation line=%s word=%s: %s",
                line_index,
                word_index,
                e,
            )
            return False

    @notify_on_completion
    def persist_page_to_file(
        self,
        page_index: int,
        save_directory: str | Path | None = None,
        project_id: str | None = None,
        update_page_source: bool = True,
    ) -> bool:
        """Save a specific page using PageOperations.

        Args:
            page_index: Zero-based page index to save
            save_directory: Directory to save files. When omitted, uses the
                default user-local labeled-projects directory.
            project_id: Project identifier. If None, derives from project root directory name.
            update_page_source: Whether to mark page source as `filesystem` after save.

        Returns:
            bool: True if save was successful, False otherwise.
        """
        if not self._project_root:
            logger.error("PageState.save_page: no project root set")
            return False

        page_model: PageModel | None = None

        # Prefer the actively edited in-memory page when saving the current page.
        # This avoids re-loading an older filesystem copy just before save.
        if page_index == self._current_page_index and self.current_page is not None:
            page_model = self.current_page_model
            if page_model is None or page_model.page is not self.current_page:
                current_source = (
                    str(getattr(self.current_page, "page_source", "ocr")) or "ocr"
                )
                page_model = PageModel(
                    page=self.current_page,
                    page_source=current_source,
                    image_path=getattr(self.current_page, "image_path", None),
                    name=getattr(self.current_page, "name", None),
                    index=page_index,
                    ocr_provenance=getattr(self.current_page, "ocr_provenance", None),
                    saved_provenance=(
                        self.current_page_model.saved_provenance
                        if self.current_page_model is not None
                        else None
                    ),
                )
                self.current_page_model = page_model

                if self._project_state is not None:
                    self._project_state.upsert_page_model(
                        page_index=page_index,
                        page=self.current_page,
                        source=current_source,
                    )
                    synced_model = self._project_state.get_page_model(page_index)
                    if synced_model is not None:
                        page_model = synced_model

        if page_model is None:
            page_model = self.get_page_model(page_index)
        if page_model is None:
            logger.error("No page available at index %s to save", page_index)
            return False

        resolved_save_directory = self._resolve_workspace_save_directory(save_directory)

        success = self.page_ops.save_page(
            page=page_model,
            project_root=self._project_root,
            save_directory=resolved_save_directory,
            project_id=project_id,
            source_lib=self._project.source_lib
            if self._project
            else "doctr-pgdp-labeled",
            original_page=self.original_page,
        )

        if success:
            if update_page_source and self._project_state:
                self._project_state.set_page_source(page_index, "filesystem")

        return success

    @notify_on_completion
    def load_page_from_file(
        self,
        page_index: int,
        save_directory: str | Path | None = None,
        project_id: str | None = None,
    ) -> bool:
        """Load a specific page from saved files.

        Args:
            page_index: Zero-based page index to load
            save_directory: Directory where files were saved. When omitted,
                uses the default user-local labeled-projects directory.
            project_id: Project identifier. If None, derives from project root directory name.

        Returns:
            bool: True if load was successful, False otherwise.
        """
        if not self._project or not self._project_root:
            logger.error("PageState.load_page: project context not set")
            return False

        resolved_save_directory = self._resolve_workspace_save_directory(save_directory)

        loaded_result = self.page_ops.load_page_model(
            page_number=page_index + 1,  # Convert to 1-based
            project_root=self._project_root,
            save_directory=resolved_save_directory,
            project_id=project_id,
        )

        if loaded_result is None:
            logger.warning("No saved page found for index %s", page_index)
            return False

        loaded_page_model, original_page_dict = loaded_result
        loaded_page = loaded_page_model.page

        # Inject ground truth text if available — but skip if the loaded
        # page already carries per-word GT (i.e. user edits from a prior save).
        if self._page_has_word_ground_truth(loaded_page):
            logger.debug(
                "Loaded page %s already has per-word GT; skipping bulk re-match",
                page_index,
            )
        else:
            gt_text = self._resolve_ground_truth_text(
                page=loaded_page,
                page_model=loaded_page_model,
                page_index=page_index,
            )
            if gt_text:
                try:
                    loaded_page.add_ground_truth(gt_text)
                    logger.debug("Injected ground truth for loaded page %s", page_index)
                except Exception as e:
                    logger.warning(
                        "Failed to add ground truth to loaded page %s: %s",
                        page_index,
                        e,
                    )

        # Replace the page in the project
        if 0 <= page_index < len(self._project.pages):
            self._project.pages[page_index] = loaded_page
            self.current_page = loaded_page
            self.current_page_model = loaded_page_model
            if self._project_state:
                self._project_state.upsert_page_model(
                    page_index=page_index,
                    page=loaded_page,
                    source="filesystem",
                )
            # Set original page if available
            if original_page_dict:
                self.original_page = Page.from_dict(original_page_dict)
            logger.info("Successfully loaded page at index %s", page_index)
            # Invalidate cache since page content changed
            self._invalidate_text_cache()
            return True
        else:
            logger.error("Page index %s out of range for project pages", page_index)
            return False

    def find_ground_truth_text(
        self, page_name: str, ground_truth_map: dict
    ) -> str | None:
        """Find ground truth text for a page from the ground truth mapping.

        Args:
            page_name: Name of the page file
            ground_truth_map: Mapping of page names to ground truth text

        Returns:
            Ground truth text if found, None otherwise
        """
        return self.page_ops.find_ground_truth_text(page_name, ground_truth_map)

    def _resolve_ground_truth_text(
        self,
        page: object | None,
        page_model: object | None,
        page_index: int,
    ) -> str:
        """Resolve GT text using multiple page/model/project identifiers."""
        if not self._project:
            return ""

        ground_truth_map = getattr(self._project, "ground_truth_map", None)
        if not isinstance(ground_truth_map, dict) or not ground_truth_map:
            return ""

        gt_candidates: list[object] = [
            getattr(page, "name", None),
            getattr(page_model, "name", None),
            getattr(page, "image_path", None),
            getattr(page_model, "image_path", None),
        ]

        project_image_paths = getattr(self._project, "image_paths", None)
        if isinstance(project_image_paths, list) and 0 <= page_index < len(
            project_image_paths
        ):
            image_path = project_image_paths[page_index]
            gt_candidates.append(image_path)
            gt_candidates.append(getattr(image_path, "name", None))

        seen: set[str] = set()
        for candidate in gt_candidates:
            if candidate is None:
                continue

            lookup_key = str(candidate)
            if not lookup_key or lookup_key in seen:
                continue
            seen.add(lookup_key)

            matched = self.find_ground_truth_text(lookup_key, ground_truth_map)
            if isinstance(matched, str) and matched.strip():
                return matched

        return ""

    @property
    def current_page_source(self) -> str | None:
        """Get raw source identifier for the current page.

        Returns:
            None when no page is available, "loading" when loading/navigating,
            or the raw page_source string ("filesystem", "cached_ocr", "ocr", "fallback").
        """
        if self._project_state and (
            self._project_state.is_project_loading or self._project_state.is_navigating
        ):
            return "loading"

        if (
            not self._project
            or not self._project.pages
            or self._current_page_index < 0
            or self._current_page_index >= len(self._project.pages)
        ):
            return None

        page = self._project.pages[self._current_page_index]
        if page is None:
            return None

        page_source = "ocr"
        if self._project_state and hasattr(self._project_state, "get_page_model"):
            page_model = self._project_state.get_page_model(self._current_page_index)
            if page_model is not None:
                page_source = page_model.page_source
            else:
                page_source = str(getattr(page, "page_source", "ocr"))

        return page_source

    @property
    def current_page_source_tooltip(self) -> str:
        """Get provenance tooltip text for the current page source badge."""
        if self._project_state and (
            self._project_state.is_project_loading or self._project_state.is_navigating
        ):
            return ""

        if (
            not self._project
            or not self._project.pages
            or self._current_page_index < 0
            or self._current_page_index >= len(self._project.pages)
        ):
            return ""

        page = self._project.pages[self._current_page_index]
        if page is None:
            return ""

        if not self._project_state:
            return ""

        page_model = None
        if self._project_state and hasattr(self._project_state, "get_page_model"):
            page_model = self._project_state.get_page_model(self._current_page_index)

        return self._project_state.page_ops.get_page_provenance_summary(
            page_model if page_model is not None else page
        )

    @property
    def current_page_export_status_enum(self) -> str | None:
        """Return the raw export status value for the current page.

        Returns:
            The ExportStatus string constant (e.g. "exported", "stale",
            "not_exported"), or None when not applicable.
        """
        if not self._project_state:
            return None
        if self._project_state.is_project_loading or self._project_state.is_navigating:
            return None
        try:
            return self._project_state.get_page_export_status(self._current_page_index)
        except Exception:
            logger.debug("Failed to check export status", exc_info=True)
            return None

    @notify_on_completion
    def reload_page_with_ocr(self, page_index: int) -> None:
        """Reload a specific page with OCR processing, bypassing any saved version.

        Args:
            page_index: Zero-based page index to reload
        """
        if not self._project:
            logger.warning("PageState.reload_page_with_ocr: no project context set")
            return

        if 0 <= page_index < len(self._project.pages):
            # Force-remove on-disk page image cache artifacts for this page so
            # reload always rebuilds fresh overlay images.
            self._invalidate_page_image_cache(page_index)

            # Clear the cached page to force reload
            self._project.pages[page_index] = None
            if self.current_page_model and self.current_page_model.index == page_index:
                self.current_page_model = None
            if self._project_state:
                self._project_state.clear_page_model(page_index)
            # Reload with force_ocr=True
            page_model = self.get_page_model(page_index, force_ocr=True)
            if page_model is not None:
                self._refresh_page_overlay_images(page_model.page)
                # Invalidate cache since page content changed
                self._invalidate_text_cache()
        else:
            logger.warning(
                "PageState.reload_page_with_ocr: page_index %s out of range", page_index
            )

    def _invalidate_page_image_cache(self, page_index: int) -> None:
        """Remove all cached overlay image files for a single page."""
        if self._project_root is None:
            return

        project_id = self._project_root.name
        if not project_id:
            return

        page_number = page_index + 1
        cache_root = PersistencePathsOperations.get_page_image_cache_root()
        cache_pattern = f"{project_id}_{page_number:03d}_*"
        deleted_files = 0

        for cache_file in cache_root.glob(cache_pattern):
            if not cache_file.is_file():
                continue
            with contextlib.suppress(Exception):
                cache_file.unlink()
                deleted_files += 1

        if deleted_files:
            logger.debug(
                "PageState._invalidate_page_image_cache: removed %s files for page %s",
                deleted_files,
                page_number,
            )

    def reload_current_page_with_ocr(self, current_page_index: int) -> None:
        """Reload the current page with OCR processing, bypassing any saved version.

        Args:
            current_page_index: Zero-based index of the current page
        """
        self.reload_page_with_ocr(current_page_index)

    def save_current_page(
        self,
        current_page_index: int,
        save_directory: str | Path | None = None,
        project_id: str | None = None,
    ) -> bool:
        """Save the current page.

        Args:
            current_page_index: Zero-based index of the current page
            save_directory: Directory to save files. When omitted, uses the
                default user-local labeled-projects directory.
            project_id: Project identifier. If None, derives from project root directory name.

        Returns:
            bool: True if save was successful, False otherwise.
        """
        return self.persist_page_to_file(
            page_index=current_page_index,
            save_directory=save_directory,
            project_id=project_id,
        )

    def load_current_page(
        self,
        current_page_index: int,
        save_directory: str | Path | None = None,
        project_id: str | None = None,
    ) -> bool:
        """Load the current page from saved files.

        Args:
            current_page_index: Zero-based index of the current page
            save_directory: Directory where files were saved. When omitted,
                uses the default user-local labeled-projects directory.
            project_id: Project identifier. If None, derives from project root directory name.

        Returns:
            bool: True if load was successful, False otherwise.
        """
        return self.load_page_from_file(
            page_index=current_page_index,
            save_directory=save_directory,
            project_id=project_id,
        )

    def _dispatch_line_op(
        self,
        line_op_name: str,
        operation_label: str,
        *args,
        _finalize: str = "structural",
        _reraise: bool = False,
        **kwargs,
    ) -> bool:
        """Dispatch a structural page operation on the current page.

        Consolidates the repeated guard / call / finalize / error-handling
        boilerplate shared by all structural and bbox editing methods.

        Args:
            line_op_name: Method name on ``Page``.
            operation_label: Human-readable label for log messages.
            *args: Positional arguments forwarded to the page method.
            _finalize: ``"structural"`` or ``"bbox"`` — selects the
                post-success finalizer.
            _reraise: When *True*, re-raise exceptions instead of
                returning *False*.
            **kwargs: Keyword arguments forwarded to the operation.
        """
        page = self.current_page
        if not page:
            logger.critical("No page available for %s", operation_label)
            return False

        try:
            result = getattr(page, line_op_name)(*args, **kwargs)
            if result:
                if _finalize == "structural":
                    self._finalize_structural_edit(page, operation_label)
                else:
                    self._finalize_bbox_edit(page)
            return result
        except Exception as e:
            logger.exception("Error in %s: %s", operation_label, e)
            if _reraise:
                raise
            return False

    def _dispatch_bbox_op(
        self,
        bbox_op_name: str,
        operation_label: str,
        *args,
        _reraise: bool = False,
        **kwargs,
    ) -> bool:
        """Dispatch a selection-scoped bbox operation via ``BboxOperations``.

        Consolidates the guard / call / finalize / error-handling boilerplate
        shared by all word/line/paragraph bbox refinement and expansion methods.

        Args:
            bbox_op_name: Method name on ``BboxOperations``.
            operation_label: Human-readable label for log messages.
            *args: Positional arguments forwarded after ``page``.
            _reraise: When *True*, re-raise exceptions instead of returning *False*.
            **kwargs: Keyword arguments forwarded to the operation.
        """
        page = self.current_page
        if not page:
            logger.critical("No page available for %s", operation_label)
            return False
        try:
            result = getattr(BboxOperations(), bbox_op_name)(page, *args, **kwargs)
            if result:
                self._finalize_bbox_edit(page)
            return result
        except Exception as e:
            logger.exception("Error in %s: %s", operation_label, e)
            if _reraise:
                raise
            return False

    def _dispatch_block_op(
        self,
        block_op_name: str,
        operation_label: str,
        line_index: int,
        *args,
        _finalize: str = "structural",
        _reraise: bool = False,
        **kwargs,
    ) -> bool:
        """Dispatch an operation directly on a line block (Block) within the current page.

        Resolves *line_index* to the corresponding line block and calls
        ``block_op_name`` on it, bypassing the Page-level method.

        Args:
            block_op_name: Method name on the ``Block`` (line) object.
            operation_label: Human-readable label for log messages.
            line_index: Zero-based index of the line to operate on.
            *args: Positional arguments forwarded to the block method.
            _finalize: ``"structural"`` or ``"bbox"`` — selects the
                post-success finalizer.
            _reraise: When *True*, re-raise exceptions instead of
                returning *False*.
            **kwargs: Keyword arguments forwarded to the operation.
        """
        page = self.current_page
        if not page:
            logger.critical("No page available for %s", operation_label)
            return False

        lines = list(page.lines)
        if line_index < 0 or line_index >= len(lines):
            logger.warning(
                "%s: line_index %s out of range (0-%s)",
                operation_label,
                line_index,
                len(lines) - 1,
            )
            return False

        try:
            result = getattr(lines[line_index], block_op_name)(*args, **kwargs)
            if result:
                if _finalize == "structural":
                    self._finalize_structural_edit(page, operation_label)
                else:
                    self._finalize_bbox_edit(page)
            return result
        except Exception as e:
            logger.exception("Error in %s: %s", operation_label, e)
            if _reraise:
                raise
            return False

    def _dispatch_word_op(
        self,
        word_op_name: str,
        operation_label: str,
        line_index: int,
        word_index: int,
        *args,
        _finalize: str = "structural",
        _reraise: bool = False,
        _pass_page_image: bool = False,
        **kwargs,
    ) -> bool:
        """Dispatch an operation directly on a Word within the current page.

        Resolves *(line_index, word_index)* to the target ``Word`` and calls
        *word_op_name* on it.  When *_pass_page_image* is ``True`` the current
        page's CV2 numpy image is prepended to *args*, enabling image-aware
        ``Word`` methods (e.g. ``refine_bbox``, ``expand_then_refine_bbox``) to
        be called without additional plumbing.

        Args:
            word_op_name: Method name on the ``Word`` object.
            operation_label: Human-readable label for log messages.
            line_index: Zero-based index of the line containing the word.
            word_index: Zero-based index of the word within the line.
            *args: Positional arguments forwarded to the word method.
            _finalize: ``"structural"`` or ``"bbox"`` — selects the
                post-success finalizer.
            _reraise: When *True*, re-raise exceptions instead of
                returning *False*.
            _pass_page_image: When *True*, prepend the current page's CV2
                numpy image to *args* before calling the word method.
            **kwargs: Keyword arguments forwarded to the operation.
        """
        page = self.current_page
        if not page:
            logger.critical("No page available for %s", operation_label)
            return False

        lines = list(page.lines)
        if line_index < 0 or line_index >= len(lines):
            logger.warning(
                "%s: line_index %s out of range (0-%s)",
                operation_label,
                line_index,
                len(lines) - 1,
            )
            return False

        words = list(lines[line_index].words)
        if word_index < 0 or word_index >= len(words):
            logger.warning(
                "%s: word_index %s out of range (0-%s)",
                operation_label,
                word_index,
                len(words) - 1,
            )
            return False

        if _pass_page_image:
            args = (page.cv2_numpy_page_image, *args)

        try:
            result = getattr(words[word_index], word_op_name)(*args, **kwargs)
            if result:
                if _finalize == "structural":
                    self._finalize_structural_edit(page, operation_label)
                else:
                    self._finalize_bbox_edit(page)
            return result
        except Exception as e:
            logger.exception("Error in %s: %s", operation_label, e)
            if _reraise:
                raise
            return False

    def merge_lines(self, line_indices: list[int]) -> bool:
        """Merge selected lines on the current page into the first selected line.

        Args:
            line_indices: Zero-based line indices to merge.

        Returns:
            bool: True if merge succeeded, False otherwise.
        """
        return self._dispatch_line_op("merge_lines", "line merge", line_indices)

    def delete_lines(self, line_indices: list[int]) -> bool:
        """Delete selected lines on the current page.

        Args:
            line_indices: Zero-based line indices to delete.

        Returns:
            bool: True if deletion succeeded, False otherwise.
        """
        return self._dispatch_line_op("delete_lines", "line deletion", line_indices)

    def merge_paragraphs(self, paragraph_indices: list[int]) -> bool:
        """Merge selected paragraphs on the current page into the first selected paragraph.

        Args:
            paragraph_indices: Zero-based paragraph indices to merge.

        Returns:
            bool: True if merge succeeded, False otherwise.
        """
        return self._dispatch_line_op(
            "merge_paragraphs", "paragraph merge", paragraph_indices
        )

    def delete_paragraphs(self, paragraph_indices: list[int]) -> bool:
        """Delete selected paragraphs on the current page.

        Args:
            paragraph_indices: Zero-based paragraph indices to delete.

        Returns:
            bool: True if deletion succeeded, False otherwise.
        """
        return self._dispatch_line_op(
            "delete_paragraphs", "paragraph deletion", paragraph_indices
        )

    def split_paragraphs(self, paragraph_indices: list[int]) -> bool:
        """Split selected paragraphs on the current page into one paragraph per line.

        Args:
            paragraph_indices: Zero-based paragraph indices to split.

        Returns:
            bool: True if any selected paragraph was split, False otherwise.
        """
        return self._dispatch_line_op(
            "split_paragraphs", "paragraph split", paragraph_indices
        )

    def split_paragraph_after_line(self, line_index: int) -> bool:
        """Split the current line's paragraph immediately after the selected line.

        Args:
            line_index: Zero-based line index used as split point.

        Returns:
            bool: True if split succeeded, False otherwise.
        """
        return self._dispatch_line_op(
            "split_paragraph_after_line",
            "paragraph split-after-line",
            line_index,
        )

    def split_paragraph_with_selected_lines(self, line_indices: list[int]) -> bool:
        """Split one paragraph into selected lines and unselected lines.

        Args:
            line_indices: Zero-based selected line indices.

        Returns:
            bool: True if split succeeded, False otherwise.
        """
        return self._dispatch_line_op(
            "split_paragraph_with_selected_lines",
            "paragraph split-by-selected-lines",
            line_indices,
        )

    def delete_words(self, word_keys: list[tuple[int, int]]) -> bool:
        """Delete selected words on the current page.

        Args:
            word_keys: List of (line_index, word_index) pairs to delete.

        Returns:
            bool: True if deletion succeeded, False otherwise.
        """
        return self._dispatch_line_op("delete_words", "word deletion", word_keys)

    def merge_word_left(self, line_index: int, word_index: int) -> bool:
        """Merge selected word into its immediate left neighbor.

        Args:
            line_index: Zero-based line index.
            word_index: Zero-based word index.

        Returns:
            bool: True if merge succeeded, False otherwise.
        """
        return self._dispatch_block_op(
            "merge_word_left", "word merge-left", line_index, word_index
        )

    def merge_word_right(self, line_index: int, word_index: int) -> bool:
        """Merge selected word with its immediate right neighbor.

        Args:
            line_index: Zero-based line index.
            word_index: Zero-based word index.

        Returns:
            bool: True if merge succeeded, False otherwise.
        """
        return self._dispatch_block_op(
            "merge_word_right", "word merge-right", line_index, word_index
        )

    def split_word(
        self,
        line_index: int,
        word_index: int,
        split_fraction: float,
    ) -> bool:
        """Split a selected word into two words on the current page.

        Args:
            line_index: Zero-based line index.
            word_index: Zero-based word index.
            split_fraction: Relative split position in range (0, 1).

        Returns:
            bool: True if split succeeded, False otherwise.
        """
        return self._dispatch_block_op(
            "split_word_at_fraction",
            "word split",
            line_index,
            word_index,
            split_fraction,
        )

    def split_word_vertically_and_assign_to_closest_line(
        self,
        line_index: int,
        word_index: int,
        split_fraction: float,
    ) -> bool:
        """Split a word and assign each split piece to the closest line by y-midpoint.

        Args:
            line_index: Zero-based source line index.
            word_index: Zero-based word index.
            split_fraction: Relative split position in range (0, 1).

        Returns:
            bool: True if split/reassignment succeeded, False otherwise.
        """
        return self._dispatch_line_op(
            "split_word_vertically_and_assign_to_closest_line",
            "word split vertical closest-line",
            line_index,
            word_index,
            split_fraction,
        )

    def split_line_after_word(
        self,
        line_index: int,
        word_index: int,
    ) -> bool:
        """Split a selected line into two lines after the selected word.

        Args:
            line_index: Zero-based line index.
            word_index: Zero-based word index used as the split point.

        Returns:
            bool: True if split succeeded, False otherwise.
        """
        return self._dispatch_line_op(
            "split_line_after_word", "line split-after-word", line_index, word_index
        )

    def rebox_word(
        self,
        line_index: int,
        word_index: int,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
    ) -> bool:
        """Replace an existing word bounding box on the current page.

        Args:
            line_index: Zero-based line index.
            word_index: Zero-based word index.
            x1: Left x-coordinate in page pixel space.
            y1: Top y-coordinate in page pixel space.
            x2: Right x-coordinate in page pixel space.
            y2: Bottom y-coordinate in page pixel space.

        Returns:
            bool: True if rebox succeeded, False otherwise.
        """
        return self._dispatch_line_op(
            "rebox_word",
            "word rebox",
            line_index,
            word_index,
            x1,
            y1,
            x2,
            y2,
            _finalize="bbox",
        )

    def add_word(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        text: str = "",
    ) -> bool:
        """Insert a new word into the nearest line on the current page.

        Args:
            x1: Left x-coordinate in page pixel space.
            y1: Top y-coordinate in page pixel space.
            x2: Right x-coordinate in page pixel space.
            y2: Bottom y-coordinate in page pixel space.
            text: Optional initial OCR text for the new word (default "").

        Returns:
            bool: True if the word was added successfully, False otherwise.
        """
        return self._dispatch_line_op(
            "add_word_to_page", "add word", x1, y1, x2, y2, text=text, _finalize="bbox"
        )

    def nudge_word_bbox(
        self,
        line_index: int,
        word_index: int,
        left_delta: float,
        right_delta: float,
        top_delta: float,
        bottom_delta: float,
        refine_after: bool = True,
    ) -> bool:
        """Resize a word bounding box by per-edge pixel deltas on the current page.

        Args:
            line_index: Zero-based line index.
            word_index: Zero-based word index.
            left_delta: Left-edge size delta in pixels (+ expands left, - contracts).
            right_delta: Right-edge size delta in pixels (+ expands right, - contracts).
            top_delta: Top-edge size delta in pixels (+ expands up, - contracts).
            bottom_delta: Bottom-edge size delta in pixels (+ expands down, - contracts).
            refine_after: Whether to run word-level refine after applying nudge.

        Returns:
            bool: True if nudge succeeded, False otherwise.
        """
        return self._dispatch_line_op(
            "nudge_word_bbox",
            "word bbox nudge",
            line_index,
            word_index,
            left_delta,
            right_delta,
            top_delta,
            bottom_delta,
            refine_after=refine_after,
            _finalize="bbox",
            _reraise=True,
        )

    def refine_words(
        self,
        word_keys: list[tuple[int, int]],
    ) -> bool:
        """Refine selected words on the current page.

        Args:
            word_keys: Selected (line_index, word_index) tuples.

        Returns:
            bool: True if refine succeeded, False otherwise.
        """
        return self._dispatch_bbox_op("refine_words", "word refine", word_keys)

    def expand_then_refine_words(
        self,
        word_keys: list[tuple[int, int]],
    ) -> bool:
        """Expand then refine selected words on the current page.

        Args:
            word_keys: Selected (line_index, word_index) tuples.

        Returns:
            bool: True if expand/refine succeeded, False otherwise.
        """
        return self._dispatch_bbox_op(
            "expand_then_refine_words", "expand-then-refine words", word_keys
        )

    def expand_word_bboxes(
        self,
        word_keys: list[tuple[int, int]],
        padding_px: float = 2.0,
    ) -> bool:
        """Expand selected word bboxes by uniform pixel padding on the current page.

        Args:
            word_keys: Selected (line_index, word_index) tuples.
            padding_px: Pixels to add on each edge.

        Returns:
            bool: True if expand succeeded, False otherwise.
        """
        return self._dispatch_bbox_op(
            "expand_word_bboxes", "expand word bboxes", word_keys, padding_px=padding_px
        )

    def refine_lines(self, line_indices: list[int]) -> bool:
        """Refine selected lines on the current page.

        Args:
            line_indices: Selected line indices.

        Returns:
            bool: True if refine succeeded, False otherwise.
        """
        return self._dispatch_bbox_op("refine_lines", "line refine", line_indices)

    def refine_paragraphs(
        self,
        paragraph_indices: list[int],
    ) -> bool:
        """Refine selected paragraphs on the current page.

        Args:
            paragraph_indices: Selected paragraph indices.

        Returns:
            bool: True if refine succeeded, False otherwise.
        """
        return self._dispatch_bbox_op(
            "refine_paragraphs", "paragraph refine", paragraph_indices
        )

    def expand_then_refine_lines(
        self,
        line_indices: list[int],
    ) -> bool:
        """Expand then refine selected lines on the current page.

        Args:
            line_indices: Selected line indices.

        Returns:
            bool: True if expand/refine succeeded, False otherwise.
        """
        return self._dispatch_bbox_op(
            "expand_then_refine_lines", "expand-then-refine lines", line_indices
        )

    def expand_then_refine_paragraphs(
        self,
        paragraph_indices: list[int],
    ) -> bool:
        """Expand then refine selected paragraphs on the current page.

        Args:
            paragraph_indices: Selected paragraph indices.

        Returns:
            bool: True if expand/refine succeeded, False otherwise.
        """
        return self._dispatch_bbox_op(
            "expand_then_refine_paragraphs",
            "expand-then-refine paragraphs",
            paragraph_indices,
        )

    def expand_line_bboxes(
        self,
        line_indices: list[int],
        padding_px: float = 2.0,
    ) -> bool:
        """Expand all word bboxes in selected lines by uniform pixel padding.

        Args:
            line_indices: Selected line indices.
            padding_px: Pixels to add on each edge.

        Returns:
            bool: True if expand succeeded, False otherwise.
        """
        return self._dispatch_bbox_op(
            "expand_line_bboxes",
            "expand line bboxes",
            line_indices,
            padding_px=padding_px,
        )

    def expand_paragraph_bboxes(
        self,
        paragraph_indices: list[int],
        padding_px: float = 2.0,
    ) -> bool:
        """Expand all word bboxes in selected paragraphs by uniform pixel padding.

        Args:
            paragraph_indices: Selected paragraph indices.
            padding_px: Pixels to add on each edge.

        Returns:
            bool: True if expand succeeded, False otherwise.
        """
        return self._dispatch_bbox_op(
            "expand_paragraph_bboxes",
            "expand paragraph bboxes",
            paragraph_indices,
            padding_px=padding_px,
        )

    def split_line_with_selected_words(
        self,
        word_keys: list[tuple[int, int]],
    ) -> bool:
        """Extract selected words into one new line.

        Args:
            word_keys: Selected (line_index, word_index) tuples.

        Returns:
            bool: True if extraction succeeded, False otherwise.
        """
        return self._dispatch_line_op(
            "split_line_with_selected_words",
            "selected-word single-line extraction",
            word_keys,
        )

    def split_lines_into_selected_and_unselected_words(
        self,
        word_keys: list[tuple[int, int]],
    ) -> bool:
        """Split each affected line into selected/unselected word lines."""
        return self._dispatch_line_op(
            "split_lines_into_selected_and_unselected_words",
            "selected/unselected per-line split",
            word_keys,
        )

    def group_selected_words_into_new_paragraph(
        self,
        word_keys: list[tuple[int, int]],
    ) -> bool:
        """Move selected words into a newly created paragraph.

        Args:
            word_keys: Selected (line_index, word_index) tuples.

        Returns:
            bool: True if grouping succeeded, False otherwise.
        """
        return self._dispatch_line_op(
            "group_selected_words_into_new_paragraph",
            "selected-word paragraph grouping",
            word_keys,
        )

    def get_page_texts(self, page_index: int) -> tuple[str, str]:
        """Get OCR and ground truth text for a page.

        Args:
            page_index: Zero-based page index

        Returns:
            Tuple of (ocr_text, ground_truth_text) where each is a string
        """
        if not self._project:
            return "", ""

        page_model = self.get_page_model(page_index)
        if not page_model:
            return "", ""
        page = page_model.page

        # Get OCR text from page
        ocr_text = getattr(page, "text", "") or ""
        if isinstance(ocr_text, str):
            ocr_text = ocr_text if ocr_text.strip() else ""
        else:
            ocr_text = ""

        # Get ground truth text from state mapping
        gt_text = self._resolve_ground_truth_text(
            page=page,
            page_model=page_model,
            page_index=page_index,
        )

        if isinstance(gt_text, str):
            gt_text = gt_text if gt_text.strip() else ""
        else:
            gt_text = ""

        return ocr_text, gt_text

    @property
    def current_ocr_text(self) -> str:
        """Get the OCR text for the current page (cached for performance)."""
        # Recover from stale loading placeholders when the page is already loaded
        # (e.g., initial project render before any navigation event).
        if self._has_loading_placeholder() and self._is_current_page_loaded():
            self._update_text_cache(force=True)
        self._update_text_cache()
        return self._cached_ocr_text

    @current_ocr_text.setter
    def current_ocr_text(self, value: str):
        """Set the OCR text for the current page (no-op as OCR text is read-only)."""
        logger.warning("Attempted to set OCR text, but OCR text is read-only")

    @property
    def current_gt_text(self) -> str:
        """Get the ground truth text for the current page (cached for performance)."""
        # Recover from stale loading placeholders when the page is already loaded
        # (e.g., initial project render before any navigation event).
        if self._has_loading_placeholder() and self._is_current_page_loaded():
            self._update_text_cache(force=True)
        self._update_text_cache()
        return self._cached_gt_text

    @current_gt_text.setter
    def current_gt_text(self, value: str):
        """Set the ground truth text for the current page."""
        if self._project and 0 <= self._current_page_index < len(self._project.pages):
            page = self._project.pages[self._current_page_index]
            if page and hasattr(page, "name"):
                self._project.ground_truth_map[page.name] = value
                self._invalidate_text_cache()
                logger.debug("Updated ground truth for page %s", page.name)

    def _invalidate_text_cache(self):
        """Invalidate the cached text values when page content changes."""
        self._cached_page_index = -1
        self._cached_ocr_text = ""
        self._cached_gt_text = ""

    @staticmethod
    def _page_has_word_ground_truth(page: object) -> bool:
        """Return True if any word on the page already carries ground truth text."""
        lines = getattr(page, "lines", None)
        if not lines:
            return False
        try:
            for line in lines:
                words = getattr(line, "words", None)
                if not words:
                    continue
                for word in words:
                    gt = getattr(word, "ground_truth_text", None)
                    if gt is not None and gt != "":
                        return True
        except TypeError:
            return False
        return False

    def _rematch_page_ground_truth(self, page: object, operation: str) -> None:
        """Re-apply page-level ground truth mapping after structural edits.

        Raises:
            _GroundTruthRematchSkipped: when GT text is unavailable or the
                page type lacks the required GT methods.
        """
        gt_text = self._resolve_ground_truth_text(
            page=page,
            page_model=self.current_page_model,
            page_index=self._current_page_index,
        )
        if not gt_text:
            raise _GroundTruthRematchSkipped("no GT text available")

        remove_ground_truth = getattr(page, "remove_ground_truth", None)
        add_ground_truth = getattr(page, "add_ground_truth", None)
        if not callable(remove_ground_truth) or not callable(add_ground_truth):
            raise _GroundTruthRematchSkipped(
                f"page type {type(page).__name__} lacks GT methods"
            )

        remove_ground_truth()
        add_ground_truth(gt_text)
        logger.debug(
            "Re-matched ground truth after %s for page index %s",
            operation,
            self._current_page_index,
        )

    def _finalize_structural_edit(self, page: object, operation: str) -> None:
        """Run post-success page updates after structural OCR edits."""
        self._clear_all_validation(page)

        try:
            self._rematch_page_ground_truth(page, operation)
        except _GroundTruthRematchSkipped:
            logger.debug("Skipping GT rematch after %s (no GT available)", operation)
        except Exception:
            logger.exception("Failed to re-match ground truth after %s", operation)

        self._refresh_page_overlay_images(page)
        self._invalidate_text_cache()
        self._auto_save_to_cache()
        self.notify()

    def _clear_all_validation(self, page: object) -> None:
        """Remove 'validated' label from all words on the page."""
        try:
            for line in getattr(page, "lines", []) or []:
                for word in getattr(line, "words", []) or []:
                    labels = getattr(word, "word_labels", None)
                    if labels and "validated" in labels:
                        labels_set = set(labels)
                        labels_set.discard("validated")
                        word.word_labels = list(labels_set)
        except Exception:
            logger.debug("Error clearing validation labels", exc_info=True)

    def _snapshot_word_ground_truth(self, page: object) -> dict[tuple[int, int], str]:
        """Return a snapshot of per-word GT text keyed by (line_index, word_index)."""
        snapshot: dict[tuple[int, int], str] = {}
        try:
            for li, line in enumerate(getattr(page, "lines", []) or []):
                for wi, word in enumerate(getattr(line, "words", []) or []):
                    snapshot[(li, wi)] = str(
                        getattr(word, "ground_truth_text", "") or ""
                    )
        except Exception:
            logger.debug("Error snapshotting word GT", exc_info=True)
        return snapshot

    def _clear_validation_for_changed_gt(
        self,
        page: object,
        gt_snapshot: dict[tuple[int, int], str],
    ) -> None:
        """Clear 'validated' only for words whose GT changed relative to the snapshot."""
        try:
            for li, line in enumerate(getattr(page, "lines", []) or []):
                for wi, word in enumerate(getattr(line, "words", []) or []):
                    old_gt = gt_snapshot.get((li, wi))
                    new_gt = str(getattr(word, "ground_truth_text", "") or "")
                    if old_gt != new_gt:
                        labels = getattr(word, "word_labels", None)
                        if labels and "validated" in labels:
                            labels_set = set(labels)
                            labels_set.discard("validated")
                            word.word_labels = list(labels_set)
        except Exception:
            logger.debug(
                "Error clearing validation for changed GT words", exc_info=True
            )

    @notify_on_completion
    def rematch_ground_truth(self) -> bool:
        """Explicitly re-run bulk GT matching on the current page.

        Wipes any per-word GT edits and re-matches from the source GT text.
        Called by the UI when the user intentionally wants to refresh GT.
        Validation is cleared only for words whose GT actually changed.

        Returns:
            True if GT was successfully re-matched, False otherwise.
        """
        page = self.current_page
        if page is None:
            logger.warning("rematch_ground_truth: no current page")
            return False

        # Snapshot per-word GT before rematch
        gt_snapshot = self._snapshot_word_ground_truth(page)

        try:
            self._rematch_page_ground_truth(page, "explicit rematch")
        except _GroundTruthRematchSkipped:
            return False

        # Clear validation only for words whose GT actually changed
        self._clear_validation_for_changed_gt(page, gt_snapshot)

        self._invalidate_text_cache()
        self._auto_save_to_cache()
        logger.info(
            "Re-matched ground truth for page index %s",
            self._current_page_index,
        )
        return True

    def _finalize_bbox_edit(self, page: object) -> None:
        """Run post-success updates after bbox-only edits."""
        self._refresh_page_overlay_images(page)
        self._auto_save_to_cache()
        self.notify()

    def _auto_save_to_cache(self) -> None:
        """Persist the current page to the cache directory after edits.

        This is a best-effort save so work is not lost if the app crashes.
        Failures are logged but do not propagate.
        """
        try:
            page_index = self._current_page_index
            if page_index < 0 or self.current_page is None:
                return
            if not self._project_root:
                return

            save_dir = str(PersistencePathsOperations.get_page_image_cache_root())
            success = self.persist_page_to_file(
                page_index,
                save_directory=save_dir,
                update_page_source=False,
            )
            if success:
                logger.debug("Auto-saved page %d to cache after edit", page_index)
            else:
                logger.debug("Auto-save to cache failed for page %d", page_index)
        except Exception:
            logger.debug("Auto-save to cache error", exc_info=True)

    def _refresh_page_overlay_images(self, page: object) -> None:
        """Refresh page overlay images so bbox layers redraw after line edits."""
        overlay_attrs = (
            "cv2_numpy_page_image_paragraph_with_bboxes",
            "cv2_numpy_page_image_line_with_bboxes",
            "cv2_numpy_page_image_word_with_bboxes",
            "cv2_numpy_page_image_matched_word_with_colors",
        )

        for attr_name in overlay_attrs:
            with contextlib.suppress(Exception):
                setattr(page, attr_name, None)

        # Invalidate cached image filenames so the view model's fast path
        # doesn't serve stale overlay images from disk.
        if self.current_page_model is not None:
            self.current_page_model.cached_image_filenames = None

        # Force downstream image URL cache-busting for this edit cycle.
        with contextlib.suppress(Exception):
            setattr(
                page,
                "_ocr_labeler_overlay_refresh_nonce",
                self._next_overlay_refresh_nonce(),
            )

        refresh_method = getattr(page, "refresh_page_images", None)
        if callable(refresh_method):
            with contextlib.suppress(Exception):
                refresh_method()
                return

        # If page has no refresh method, cleared overlay attrs ensure downstream
        # viewmodel refresh path regenerates overlays lazily.

    def _next_overlay_refresh_nonce(self) -> str:
        """Return a strictly increasing nonce used to bust overlay-image URL caches."""
        self._overlay_refresh_nonce_counter += 1
        return str(self._overlay_refresh_nonce_counter)

    def _has_loading_placeholder(self) -> bool:
        """Check whether cached texts are currently in loading-placeholder state."""
        return (
            self._cached_ocr_text == "Loading..."
            or self._cached_gt_text == "Loading..."
        )

    def _is_current_page_loaded(self) -> bool:
        """Return True if current page index points to a materialized page in project cache."""
        if not self._project:
            return False
        if not (0 <= self._current_page_index < len(self._project.pages)):
            return False
        return self._project.pages[self._current_page_index] is not None

    def _update_text_cache(self, force: bool = False):
        """Update cached text values for the current page."""
        if force or self._cached_page_index != self._current_page_index:
            # Only update cache if page is already loaded to avoid triggering OCR
            if (
                0 <= self._current_page_index < len(self._project.pages)
                and self._project.pages[self._current_page_index] is not None
            ):
                logger.debug(
                    "Updating text cache for page index %s", self._current_page_index
                )
                self._cached_ocr_text, self._cached_gt_text = self.get_page_texts(
                    self._current_page_index
                )
                self._cached_page_index = self._current_page_index
                logger.debug(
                    "Updated text cache for page index %s", self._current_page_index
                )
            else:
                logger.debug(
                    "Page at index %s not loaded; cannot update text cache",
                    self._current_page_index,
                )
                # Page not loaded yet, keep old cache or set to loading
                if self._cached_page_index == -1 or force:
                    logger.debug(
                        "Setting text cache to 'Loading...' for page index %s",
                        self._current_page_index,
                    )
                    self._cached_ocr_text = "Loading..."
                    self._cached_gt_text = "Loading..."
                    self._cached_page_index = self._current_page_index
            self.notify()

    @property
    def _current_page_index(self) -> int:
        """Get the current page index."""
        return self._page_index

    @_current_page_index.setter
    def _current_page_index(self, value: int):
        """Set the current page index."""
        if self._page_index != value:
            self._invalidate_text_cache()
        self._page_index = value
