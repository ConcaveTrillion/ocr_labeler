from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from ocr_labeler.views.projects.pages.text_tabs import TextTabs


class _DeletedContainer:
    @property
    def client(self):
        raise RuntimeError("The client this element belongs to has been deleted.")


def test_text_tabs_detaches_stale_listeners_when_ui_is_disposed():
    """Disposed UI containers should unregister TextTabs listeners to avoid stale callbacks."""
    project_state = SimpleNamespace(
        on_change=[],
        project=SimpleNamespace(pages=[]),
        current_page_index=0,
    )
    page_state = SimpleNamespace(
        on_change=[],
        _project_state=project_state,
        current_gt_text="",
        current_ocr_text="",
        current_page=None,
        _current_page_index=0,
        copy_ground_truth_to_ocr=lambda *_: False,
    )

    text_tabs = TextTabs(page_state=page_state)

    assert text_tabs.model._on_page_state_change in page_state.on_change
    assert text_tabs._on_project_state_changed in project_state.on_change

    text_tabs.container = _DeletedContainer()
    text_tabs._on_project_state_changed()

    assert text_tabs._disposed is True
    assert text_tabs.model._on_page_state_change not in page_state.on_change
    assert text_tabs._on_project_state_changed not in project_state.on_change


def test_text_tabs_skips_duplicate_word_match_update_for_same_page_payload():
    """Repeated update requests with identical page payload should not recompute matches."""
    project_state = SimpleNamespace(
        on_change=[],
        project=SimpleNamespace(pages=[]),
        current_page_index=0,
    )
    page_state = SimpleNamespace(
        on_change=[],
        _project_state=project_state,
        current_gt_text="",
        current_ocr_text="",
        current_page=None,
        _current_page_index=0,
        copy_ground_truth_to_ocr=lambda *_: False,
    )

    text_tabs = TextTabs(page_state=page_state)
    text_tabs.word_match_view = MagicMock()

    page = SimpleNamespace(
        name="p001.png",
        index=0,
        blocks=[SimpleNamespace(text="line1"), SimpleNamespace(text="line2")],
    )

    text_tabs.update_word_matches(page)
    text_tabs.update_word_matches(page)

    text_tabs.word_match_view.update_from_page.assert_called_once_with(page)
