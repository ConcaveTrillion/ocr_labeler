from __future__ import annotations

import contextlib
import hashlib
import logging
from typing import TYPE_CHECKING

from nicegui import binding, ui
from pd_book_tools.ocr.page import Page

if TYPE_CHECKING:
    from pd_book_tools.ocr.word import Word

from ....state import PageState
from ....state.page_state import (
    WordGroundTruthChangedEvent,
    WordStyleChangedEvent,
    WordValidationChangedEvent,
)
from .word_match import WordMatchView

logger = logging.getLogger(__name__)


@binding.bindable_dataclass
class TextTabsModel:
    """Holds references to the text editor data from page state. Don't directly bind to page state, bindable properties avoid tight coupling with state management classes."""

    _page_state: PageState | None = None
    gt_text: str = ""  # Ground Truth text
    ocr_text: str = ""  # OCR text

    def __init__(self, page_state: PageState | None = None):
        logger.debug(
            "Initializing TextTabsModel with page_state: %s", page_state is not None
        )
        self._page_state = page_state
        if self._page_state:
            logger.debug("Registering page state change listener")
            self._page_state.on_change.append(self._on_page_state_change)
            logger.debug("Registered page state change listener")
        self.update()

    # Only propagate one-way from PageState to model
    #
    # def __setattr__(self, name: str, value):
    #     """Intercept attribute changes to propagate to PageState."""
    #     super().__setattr__(name, value)
    #     if name == "gt_text" and self._page_state:
    #         logger.debug("Propagating GT text change to PageState: '%s...'", value[:50])
    #         self._page_state.current_gt_text = value
    #     elif name == "ocr_text" and self._page_state:
    #         logger.debug("Propagating OCR text change to PageState: '%s...'", value[:50])
    #         self._page_state.current_ocr_text = value

    def update(self):
        """Sync model from PageState."""
        logger.debug("Updating TextTabsModel from PageState")
        if self._page_state:
            self.gt_text = self._page_state.current_gt_text
            self.ocr_text = self._page_state.current_ocr_text
            logger.debug("GT text updated to: '%s...'", self.gt_text[:50])
            logger.debug("OCR text updated to: '%s...'", self.ocr_text[:50])
        else:
            logger.debug("No page state available, clearing text")
            self.gt_text = ""
            self.ocr_text = ""

    def _on_page_state_change(self):
        """Listener for PageState changes; update model properties."""
        logger.debug("PageState change detected, updating model")
        self.update()
        # Notify TextTabs that state changed so it can update word matches
        logger.debug(
            "Checking for callback: hasattr=%s, is_set=%s",
            hasattr(self, "_on_state_change_callback"),
            getattr(self, "_on_state_change_callback", None) is not None,
        )
        if (
            hasattr(self, "_on_state_change_callback")
            and self._on_state_change_callback
        ):
            logger.debug("Calling TextTabs state change callback")
            self._on_state_change_callback()
        else:
            # Only log as debug in case this is a test scenario with mocks
            logger.debug("TextTabs callback not set or not callable")


def _make_page_callback(
    page_state: PageState | None,
    method_name: str,
    description: str | None = None,
):
    """Create a callback that delegates to ``page_state.<method>(*args)``.

    Returns ``None`` when *page_state* is ``None`` or does not have *method_name*.
    """
    if page_state is None or not hasattr(page_state, method_name):
        return None
    method = getattr(page_state, method_name)
    label = description or method_name

    def callback(*args, **kwargs) -> bool:
        logger.debug("%s", label)
        result = method(*args, **kwargs)
        logger.debug("%s result: %s", label, result)
        return result

    return callback


class TextTabs:
    """Right side textual data tabs (Matches placeholder, Ground Truth, OCR)."""

    def __init__(
        self,
        page_state: PageState | None = None,
        page_index=0,
        original_image_source_provider=None,
        word_image_page_index_provider=None,
        on_save_page=None,
        on_load_page=None,
    ):
        logger.info("Initializing TextTabs for page %s", page_index)
        logger.debug("Page state provided: %s", page_state is not None)
        self.page_state = page_state
        self.page_index = page_index
        self._disposed = False
        self._original_image_source_provider = original_image_source_provider
        self._word_image_page_index_provider = word_image_page_index_provider
        self._pending_word_match_page: Page | None = None

        # Instantiate the model as the intermediary
        self.model = TextTabsModel(page_state)

        # Register callback so model can notify us of state changes
        # Do this BEFORE any updates so callbacks work from the start
        self.model._on_state_change_callback = self._on_page_state_changed

        # Set the page index on the page_state so it knows which page to cache
        if page_state:
            page_state._current_page_index = page_index
            logger.debug("Set current page index to %s", page_index)

        self._register_state_listeners()

        # Create callback for GT→OCR copy functionality
        copy_callback = _make_page_callback(
            page_state, "copy_ground_truth_to_ocr", "Copy GT to OCR"
        )
        copy_ocr_to_gt_callback = _make_page_callback(
            page_state, "copy_ocr_to_ground_truth", "Copy OCR to GT"
        )
        copy_selected_words_ocr_to_gt_callback = _make_page_callback(
            page_state,
            "copy_selected_words_ocr_to_ground_truth",
            "Copy selected words OCR to GT",
        )

        merge_lines_callback = _make_page_callback(
            page_state, "merge_lines", "Merge selected lines"
        )
        delete_lines_callback = _make_page_callback(
            page_state, "delete_lines", "Delete selected lines"
        )
        merge_paragraphs_callback = _make_page_callback(
            page_state, "merge_paragraphs", "Merge selected paragraphs"
        )
        delete_paragraphs_callback = _make_page_callback(
            page_state, "delete_paragraphs", "Delete selected paragraphs"
        )
        split_paragraph_after_line_callback = _make_page_callback(
            page_state,
            "split_paragraph_after_line",
            "Split paragraph after line",
        )

        split_paragraph_with_selected_lines_callback = None
        if page_state:

            def split_paragraph_with_selected_lines_callback(
                line_indices: list[int],
            ) -> bool:
                previous_key_head = (
                    self._last_word_match_page_key[:4]
                    if self._last_word_match_page_key is not None
                    else None
                )
                logger.debug(
                    "[split_by_selection] callback.start lines=%s last_key_head=%s",
                    line_indices,
                    previous_key_head,
                )
                result = page_state.split_paragraph_with_selected_lines(
                    line_indices,
                )
                logger.debug(
                    "[split_by_selection] callback.done success=%s last_key_head_now=%s",
                    result,
                    (
                        self._last_word_match_page_key[:4]
                        if self._last_word_match_page_key is not None
                        else None
                    ),
                )
                return result

        split_line_after_word_callback = _make_page_callback(
            page_state, "split_line_after_word", "Split line after word"
        )

        delete_words_callback = _make_page_callback(
            page_state, "delete_words", "Delete selected words"
        )
        merge_word_left_callback = _make_page_callback(
            page_state, "merge_word_left", "Merge word left"
        )
        merge_word_right_callback = _make_page_callback(
            page_state, "merge_word_right", "Merge word right"
        )
        split_word_callback = _make_page_callback(
            page_state, "split_word", "Split word"
        )
        split_word_vertical_closest_line_callback = _make_page_callback(
            page_state,
            "split_word_vertically_and_assign_to_closest_line",
            "Split word vertical closest-line",
        )
        rebox_word_callback = _make_page_callback(
            page_state, "rebox_word", "Rebox word"
        )
        add_word_callback = _make_page_callback(page_state, "add_word", "Add word")
        nudge_word_bbox_callback = _make_page_callback(
            page_state, "nudge_word_bbox", "Nudge word bbox"
        )
        erase_pixels_rect_callback = _make_page_callback(
            page_state, "erase_pixels_rect", "Erase pixels in rectangle"
        )
        refine_words_callback = _make_page_callback(
            page_state, "refine_words", "Refine selected words"
        )
        expand_then_refine_words_callback = _make_page_callback(
            page_state,
            "expand_then_refine_words",
            "Expand-then-refine selected words",
        )
        expand_word_bboxes_callback = _make_page_callback(
            page_state,
            "expand_word_bboxes",
            "Expand word bboxes",
        )
        refine_lines_callback = _make_page_callback(
            page_state, "refine_lines", "Refine selected lines"
        )
        expand_then_refine_lines_callback = _make_page_callback(
            page_state,
            "expand_then_refine_lines",
            "Expand-then-refine selected lines",
        )
        expand_line_bboxes_callback = _make_page_callback(
            page_state, "expand_line_bboxes", "Expand line bboxes"
        )
        refine_paragraphs_callback = _make_page_callback(
            page_state,
            "refine_paragraphs",
            "Refine selected paragraphs",
        )
        expand_then_refine_paragraphs_callback = _make_page_callback(
            page_state,
            "expand_then_refine_paragraphs",
            "Expand-then-refine selected paragraphs",
        )
        expand_paragraph_bboxes_callback = _make_page_callback(
            page_state,
            "expand_paragraph_bboxes",
            "Expand paragraph bboxes",
        )
        split_line_with_selected_words_callback = _make_page_callback(
            page_state,
            "split_line_with_selected_words",
            "Create line from selected words",
        )
        split_lines_into_selected_unselected_callback = _make_page_callback(
            page_state,
            "split_lines_into_selected_and_unselected_words",
            "Split lines into selected/unselected words",
        )
        group_selected_words_into_paragraph_callback = _make_page_callback(
            page_state,
            "group_selected_words_into_new_paragraph",
            "Group selected words into paragraph",
        )
        edit_word_ground_truth_callback = _make_page_callback(
            page_state,
            "update_word_ground_truth",
            "Update word GT",
        )
        set_word_attributes_callback = _make_page_callback(
            page_state,
            "update_word_attributes",
            "Update word attributes",
        )
        toggle_word_validated_callback = _make_page_callback(
            page_state,
            "toggle_word_validated",
            "Toggle word validated",
        )
        set_words_validated_callback = _make_page_callback(
            page_state,
            "set_words_validated",
            "Set words validated (batch)",
        )

        apply_word_style_callback = None
        if set_word_attributes_callback is not None:

            def apply_word_style_callback(style: str):
                return self.word_match_view.word_operations.apply_style_to_selection(
                    style
                )

        apply_word_style_scope_callback = None
        if page_state and hasattr(page_state, "notify"):

            def apply_word_style_scope_callback(scope: str):
                return self.word_match_view.word_operations.apply_scope_to_selection(
                    scope
                )

        notify_callback = None
        if (
            page_state
            and hasattr(page_state, "_project_state")
            and page_state._project_state
        ):

            def notify_callback(message: str, type_: str = "info") -> None:
                page_state._project_state.queue_notification(message, type_)

        self.word_match_view = WordMatchView(
            copy_gt_to_ocr_callback=copy_callback,
            copy_ocr_to_gt_callback=copy_ocr_to_gt_callback,
            copy_selected_words_ocr_to_gt_callback=copy_selected_words_ocr_to_gt_callback,
            merge_lines_callback=merge_lines_callback,
            delete_lines_callback=delete_lines_callback,
            merge_paragraphs_callback=merge_paragraphs_callback,
            delete_paragraphs_callback=delete_paragraphs_callback,
            split_paragraph_after_line_callback=split_paragraph_after_line_callback,
            split_paragraph_with_selected_lines_callback=split_paragraph_with_selected_lines_callback,
            split_line_after_word_callback=split_line_after_word_callback,
            delete_words_callback=delete_words_callback,
            merge_word_left_callback=merge_word_left_callback,
            merge_word_right_callback=merge_word_right_callback,
            split_word_callback=split_word_callback,
            split_word_vertical_closest_line_callback=split_word_vertical_closest_line_callback,
            rebox_word_callback=rebox_word_callback,
            add_word_callback=add_word_callback,
            nudge_word_bbox_callback=nudge_word_bbox_callback,
            erase_pixels_rect_callback=erase_pixels_rect_callback,
            refine_words_callback=refine_words_callback,
            expand_then_refine_words_callback=expand_then_refine_words_callback,
            expand_word_bboxes_callback=expand_word_bboxes_callback,
            refine_lines_callback=refine_lines_callback,
            expand_then_refine_lines_callback=expand_then_refine_lines_callback,
            expand_line_bboxes_callback=expand_line_bboxes_callback,
            refine_paragraphs_callback=refine_paragraphs_callback,
            expand_then_refine_paragraphs_callback=expand_then_refine_paragraphs_callback,
            expand_paragraph_bboxes_callback=expand_paragraph_bboxes_callback,
            split_line_with_selected_words_callback=split_line_with_selected_words_callback,
            split_lines_into_selected_unselected_callback=split_lines_into_selected_unselected_callback,
            group_selected_words_into_paragraph_callback=group_selected_words_into_paragraph_callback,
            edit_word_ground_truth_callback=edit_word_ground_truth_callback,
            set_word_attributes_callback=set_word_attributes_callback,
            toggle_word_validated_callback=toggle_word_validated_callback,
            set_words_validated_callback=set_words_validated_callback,
            notify_callback=notify_callback,
            original_image_source_provider=original_image_source_provider,
        )
        self.word_match_view.apply_word_style_callback = apply_word_style_callback
        self.word_match_view.apply_word_style_scope_callback = (
            apply_word_style_scope_callback
        )
        self.container = None
        self._last_word_match_page_key = None

    def _register_state_listeners(self) -> None:
        """Register state listeners once per TextTabs instance."""
        if self.page_state and hasattr(self.page_state, "on_word_ground_truth_change"):
            self.page_state.on_word_ground_truth_change.subscribe(
                self._on_word_ground_truth_changed
            )

        if self.page_state and hasattr(self.page_state, "on_word_style_change"):
            self.page_state.on_word_style_change.subscribe(self._on_word_style_changed)

        if self.page_state and hasattr(self.page_state, "on_word_validation_change"):
            self.page_state.on_word_validation_change.subscribe(
                self._on_word_validation_changed
            )

        project_state = (
            self.page_state._project_state
            if self.page_state and hasattr(self.page_state, "_project_state")
            else None
        )
        if project_state and project_state.on_change is not None:
            if self._on_project_state_changed not in project_state.on_change:
                logger.debug("Registering ProjectState change listener")
                project_state.on_change.append(self._on_project_state_changed)

    def _unregister_state_listeners(self) -> None:
        """Remove listeners to prevent stale callbacks after UI teardown."""
        if self.page_state and self.page_state.on_change is not None:
            with contextlib.suppress(ValueError):
                self.page_state.on_change.remove(self.model._on_page_state_change)

        if self.page_state and hasattr(self.page_state, "on_word_ground_truth_change"):
            with contextlib.suppress(Exception):
                self.page_state.on_word_ground_truth_change.unsubscribe(
                    self._on_word_ground_truth_changed
                )

        if self.page_state and hasattr(self.page_state, "on_word_style_change"):
            with contextlib.suppress(Exception):
                self.page_state.on_word_style_change.unsubscribe(
                    self._on_word_style_changed
                )

        if self.page_state and hasattr(self.page_state, "on_word_validation_change"):
            with contextlib.suppress(Exception):
                self.page_state.on_word_validation_change.unsubscribe(
                    self._on_word_validation_changed
                )

        project_state = (
            self.page_state._project_state
            if self.page_state and hasattr(self.page_state, "_project_state")
            else None
        )
        if project_state and project_state.on_change is not None:
            with contextlib.suppress(ValueError):
                project_state.on_change.remove(self._on_project_state_changed)

    def _is_disposed_ui_error(self, error: RuntimeError) -> bool:
        message = str(error).lower()
        return "client this element belongs to has been deleted" in message or (
            "parent element" in message and "deleted" in message
        )

    def _current_page_state_index(self) -> int:
        """Return the live current page index from page state.

        ``self.page_index`` is captured at construction time and is not updated
        on navigation, so it cannot be used to filter targeted update events
        for pages other than the initial one.  Targeted handlers should use
        this helper instead.
        """
        page_state = self.page_state
        if page_state is None:
            return -1
        return int(getattr(page_state, "_current_page_index", -1))

    def _is_ui_alive(self) -> bool:
        """Check whether the built container still belongs to an active UI tree."""
        if self._disposed:
            return False
        if self.container is None:
            # Not built yet, so callbacks should remain registered.
            return True

        try:
            _ = self.container.client
            return True
        except RuntimeError as error:
            if self._is_disposed_ui_error(error):
                logger.debug("TextTabs container has been disposed")
                return False
            raise

    def _ensure_attached(self) -> bool:
        """Detach stale listeners when this view is no longer attached."""
        if self._is_ui_alive():
            return True

        if not self._disposed:
            logger.debug("Detaching stale TextTabs listeners")
            self._unregister_state_listeners()
            self._disposed = True
        return False

    def build(self):
        logger.info("Building TextTabs UI components")
        # Root container uses Quasar growth classes; so flex children can shrink.
        # Root must be flex container with so nested 100% heights can resolve
        with ui.column().classes("full-width full-height gap-0") as col:
            # Actions toolbar row - right-aligned, above the tabs
            with ui.row().classes("full-width justify-start"):
                self.word_match_view.toolbar.build_actions_toolbar()
            logger.debug("Creating tabs container")
            with ui.tabs() as text_tabs:
                ui.tab("Matches")
                ui.tab("Ground Truth")
                ui.tab("OCR")
            # Panels area should expand to fill remaining height (col makes it flex already).
            logger.debug("Creating tab panels")
            with (
                ui.tab_panels(text_tabs, value="Matches")
                .classes("full-width full-height column gap-0 q-pa-none no-padding")
                .style("padding: 0; margin: 0;")
            ):
                # Matches panel with word matching view
                with (
                    ui.tab_panel("Matches")
                    .classes("full-width full-height column q-pa-none no-padding")
                    .style("padding: 0;")
                ):
                    logger.debug("Building word match view")
                    self.word_match_view.build()
                # Ground Truth panel
                with ui.tab_panel("Ground Truth").classes(
                    "full-width full-height column"
                ):
                    logger.debug("Building ground truth panel")
                    with ui.column().classes("full-width full-height"):
                        self.gt_text = ui.codemirror("", language="plaintext").classes(
                            "full-width full-height monospace"
                        )
                        # Don't use bind_value for large text - it's slow
                        # We'll update directly in _update_text_editors()
                        logger.debug("Created GT text editor (manual updates)")
                # OCR panel
                with ui.tab_panel("OCR").classes("full-width full-height column"):
                    logger.debug("Building OCR panel")
                    with ui.column().classes("full-width full-height"):
                        self.ocr_text = ui.codemirror("", language="plaintext").classes(
                            "full-width full-height monospace"
                        )
                        # Don't use bind_value for large text - it's slow
                        # We'll update directly in _update_text_editors()
                        logger.debug("Created OCR text editor (manual updates)")
        self.container = col
        logger.info("TextTabs UI build completed")

        # Update text editors with initial values from model
        self._update_text_editors()

        # Perform initial word match update if page is already available
        if self.page_state and hasattr(self.page_state, "current_page"):
            page = self.page_state.current_page
            if page:
                logger.debug("Performing initial word match update with current page")
                self.update_word_matches(page)
            else:
                logger.debug("No current page available at build time")

        return col

    def _update_text_editors(self):
        """Update text editor values directly (avoids slow binding propagation)."""
        if hasattr(self, "gt_text") and self.gt_text:
            self.gt_text.value = self.model.gt_text
        if hasattr(self, "ocr_text") and self.ocr_text:
            self.ocr_text.value = self.model.ocr_text

    def _on_page_state_changed(self):
        """Called when page state changes; update word matches automatically."""
        if not self._ensure_attached():
            return
        logger.debug("TextTabs received page state change notification")
        # Update text editors directly instead of relying on bindings
        self._update_text_editors()
        if self.page_state and hasattr(self.page_state, "current_page"):
            page = self.page_state.current_page
            logger.debug("Current page available: %s", page is not None)
            self.update_word_matches(page)
        else:
            logger.debug("No page state or current_page available")
            self.update_word_matches(None)

    def _on_word_ground_truth_changed(self, event: WordGroundTruthChangedEvent) -> None:
        """Apply targeted GT updates to WordMatchView."""
        if not self._ensure_attached():
            return
        if event.page_index != self._current_page_state_index():
            return
        if not getattr(self, "word_match_view", None):
            return

        logger.debug(
            "[word_match_refresh] targeted.word_gt_changed.consumed page=%s line=%s word=%s",
            event.page_index,
            event.line_index,
            event.word_index,
        )
        self.word_match_view.gt_editing.apply_word_ground_truth_change(
            event.line_index,
            event.word_index,
            event.ground_truth_text,
        )

        page = self.page_state.current_page if self.page_state is not None else None
        if page is not None:
            self._last_word_match_page_key = self._build_word_match_page_key(page)

    def _on_word_style_changed(self, event: WordStyleChangedEvent) -> None:
        """Apply targeted style updates to WordMatchView."""
        if not self._ensure_attached():
            return
        if event.page_index != self._current_page_state_index():
            return
        if not getattr(self, "word_match_view", None):
            return

        logger.debug(
            "[word_match_refresh] targeted.word_style_changed.consumed page=%s line=%s word=%s",
            event.page_index,
            event.line_index,
            event.word_index,
        )
        logger.debug(
            "[word_match_refresh] targeted.word_style_changed line=%s word=%s",
            event.line_index,
            event.word_index,
        )
        self.word_match_view.gt_editing.apply_word_style_change(
            event.line_index,
            event.word_index,
            event.italic,
            event.small_caps,
            event.blackletter,
            event.left_footnote,
            event.right_footnote,
        )

        # Coalesce with the broad PageState.on_change refresh path by updating the
        # last seen dedupe key to the current page snapshot after this targeted edit.
        # This keeps fallback full refresh behavior intact while avoiding duplicate
        # style-only rerenders.
        page = self.page_state.current_page if self.page_state is not None else None
        if page is not None:
            self._last_word_match_page_key = self._build_word_match_page_key(page)

    def _on_word_validation_changed(self, event: WordValidationChangedEvent) -> None:
        """Apply targeted validation updates to WordMatchView."""
        if not self._ensure_attached():
            return
        if event.page_index != self._current_page_state_index():
            return
        if not getattr(self, "word_match_view", None):
            return

        logger.debug(
            "[word_match_refresh] targeted.word_validation_changed line=%s word=%s validated=%s",
            event.line_index,
            event.word_index,
            event.is_validated,
        )
        self.word_match_view.apply_word_validation_change(
            event.line_index,
            event.word_index,
            event.is_validated,
        )

        page = self.page_state.current_page if self.page_state is not None else None
        if page is not None:
            self._last_word_match_page_key = self._build_word_match_page_key(page)

    def _on_project_state_changed(self):
        """Called when project state changes (e.g., navigation); update word matches."""
        if not self._ensure_attached():
            return
        logger.debug("TextTabs received project state change notification")
        # Read current page from in-memory cache only; do not call
        # ProjectState.current_page_model() here because it may trigger synchronous
        # OCR/page loading and block UI updates/notifications.
        if (
            self.page_state
            and hasattr(self.page_state, "_project_state")
            and self.page_state._project_state
        ):
            project_state = self.page_state._project_state
            page = None
            project = getattr(project_state, "project", None)
            index = getattr(project_state, "current_page_index", None)
            if (
                project is not None
                and hasattr(project, "pages")
                and index is not None
                and 0 <= index < len(project.pages)
            ):
                page = project.pages[index]
            logger.debug("Current page from ProjectState: %s", page is not None)
            # Update the PageState's current_page reference so both are in sync
            if page is not None:
                self.page_state.current_page = page
            self.update_word_matches(page)
        else:
            logger.debug("No ProjectState reference available")
            self.update_word_matches(None)

    # ----- Word match coordination -------------------------------------------------

    def update_word_matches(self, page: Page | None):
        """Refresh the word match panel with the provided page data."""
        if not self._ensure_attached():
            return
        if not getattr(self, "word_match_view", None):
            logger.debug("Word match view not initialized; skipping update")
            return

        if page is None:
            logger.debug("No page available for word matches; clearing view")
            self.word_match_view.clear()
            self._last_word_match_page_key = None
            self._pending_word_match_page = None
            return

        expected_page_index = self._safe_page_index(getattr(page, "index", -1))
        source_ready = self._word_image_source_ready_for_page(expected_page_index)
        if not source_ready:
            logger.debug(
                "Deferring word match render until word image source is ready for page_index=%s",
                expected_page_index,
            )
            self._pending_word_match_page = page
            return

        self._pending_word_match_page = None

        page_key = self._build_word_match_page_key(page)
        logger.debug(
            "[word_match_refresh] dedupe.check prev_key_head=%s next_key_head=%s",
            self._last_word_match_page_key[:4]
            if self._last_word_match_page_key is not None
            else None,
            page_key[:4],
        )
        if page_key == self._last_word_match_page_key:
            logger.debug(
                "[word_match_refresh] dedupe.skip key_head=%s",
                page_key[:4],
            )
            return

        logger.debug(
            "Updating word matches for page: %s",
            getattr(page, "name", getattr(page, "index", "unknown")),
        )
        self.word_match_view.update_from_page(page)
        self._last_word_match_page_key = page_key

    def on_word_image_source_ready(self, page_index: int) -> None:
        """Render deferred word matches once the correct page image source is ready."""
        pending_page = self._pending_word_match_page
        if pending_page is None:
            return

        pending_index = self._safe_page_index(getattr(pending_page, "index", -1))
        ready_index = self._safe_page_index(page_index)
        if pending_index != ready_index:
            return

        self.update_word_matches(pending_page)

    def _word_image_source_ready_for_page(self, expected_page_index: int) -> bool:
        """Return True when a non-empty source exists for the requested page index."""
        provider = self._original_image_source_provider
        if not callable(provider):
            return True

        source = str(provider() or "")
        if not source:
            return False

        index_provider = self._word_image_page_index_provider
        if not callable(index_provider):
            return True

        source_page_index = self._safe_page_index(index_provider())
        return source_page_index == expected_page_index

    def _safe_page_index(self, value: object) -> int:
        """Best-effort integer conversion for page indices."""
        try:
            return int(value or -1)
        except (TypeError, ValueError):
            return -1

    def _build_word_match_page_key(self, page: Page) -> tuple:
        """Build a lightweight key representing word-match-relevant page state."""
        paragraph_fingerprint = ""
        paragraphs = getattr(page, "paragraphs", None)
        if paragraphs:
            paragraph_fingerprint_builder = hashlib.sha1()
            for paragraph in paragraphs:
                paragraph_lines = getattr(paragraph, "lines", [])
                paragraph_payload = (
                    f"{getattr(paragraph, 'text', '')}\x1f{len(paragraph_lines)}"
                )
                paragraph_fingerprint_builder.update(
                    paragraph_payload.encode("utf-8", errors="ignore")
                )
            paragraph_fingerprint = paragraph_fingerprint_builder.hexdigest()

        lines = getattr(page, "lines", None)
        if lines:
            fingerprint_builder = hashlib.sha1()
            for line in lines:
                words = getattr(line, "words", [])
                unmatched_gt_words = getattr(line, "unmatched_ground_truth_words", [])
                words_payload = "\x1e".join(
                    (
                        f"{getattr(word, 'text', '')}\x1d"
                        f"{getattr(word, 'ground_truth_text', '')}\x1d"
                        f"{self._word_bbox_signature(word)}\x1d"
                        f"{self._word_style_signature(word)}"
                    )
                    for word in words
                )
                line_payload = (
                    f"{getattr(line, 'text', '')}\x1f"
                    f"{getattr(line, 'ground_truth_text', '')}\x1f"
                    f"{len(words)}\x1f{len(unmatched_gt_words)}\x1f"
                    f"{words_payload}"
                )
                fingerprint_builder.update(
                    line_payload.encode("utf-8", errors="ignore")
                )

            line_count = len(lines)
            first_line_text = (
                str(getattr(lines[0], "text", "")) if line_count > 0 else ""
            )
            last_line_text = (
                str(getattr(lines[-1], "text", ""))
                if line_count > 1
                else first_line_text
            )
            return (
                getattr(page, "name", None),
                getattr(page, "index", None),
                "lines",
                line_count,
                first_line_text,
                last_line_text,
                fingerprint_builder.hexdigest(),
                paragraph_fingerprint,
            )

        blocks = getattr(page, "blocks", None)
        if not blocks:
            return (
                getattr(page, "name", None),
                getattr(page, "index", None),
                0,
                "",
                "",
            )

        block_count = len(blocks)
        first_line_text = str(getattr(blocks[0], "text", "")) if block_count > 0 else ""
        last_line_text = (
            str(getattr(blocks[-1], "text", "")) if block_count > 1 else first_line_text
        )

        return (
            getattr(page, "name", None),
            getattr(page, "index", None),
            "blocks",
            block_count,
            first_line_text,
            last_line_text,
            paragraph_fingerprint,
        )

    def _word_bbox_signature(self, word: "Word") -> str:
        """Return a stable bbox signature for dedupe checks."""
        sig = word.bbox_signature
        if sig is None:
            return ""
        return f"{sig[0]:.6f}:{sig[1]:.6f}:{sig[2]:.6f}:{sig[3]:.6f}:{int(sig[4])}"

    def _word_style_signature(self, word: "Word") -> str:
        """Return stable style signature for dedupe checks."""
        italic = word.read_style_attribute("italic", aliases=("is_italic",))
        small_caps = word.read_style_attribute(
            "small_caps",
            aliases=("is_small_caps",),
        )
        blackletter = word.read_style_attribute(
            "blackletter",
            aliases=("is_blackletter",),
        )
        left_footnote = word.read_style_attribute(
            "left_footnote",
            aliases=("is_left_footnote",),
        )
        right_footnote = word.read_style_attribute(
            "right_footnote",
            aliases=("is_right_footnote",),
        )
        return f"{int(italic)}:{int(small_caps)}:{int(blackletter)}:{int(left_footnote)}:{int(right_footnote)}"
