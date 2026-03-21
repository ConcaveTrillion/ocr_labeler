from __future__ import annotations

from types import SimpleNamespace

import pytest

from ocr_labeler.views.projects.pages.word_edit_dialog import (
    handle_word_image_click,
    render_word_split_marker,
)
from ocr_labeler.views.projects.pages.word_match import WordMatchView


def test_merge_clears_selection_before_callback(monkeypatch):
    seen = {}

    view = WordMatchView()
    view.selected_line_indices = {1, 2, 3}
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)

    def merge_callback(indices: list[int]) -> bool:
        seen["indices"] = indices
        seen["selection_during_callback"] = sorted(view.selected_line_indices)
        return True

    view.merge_lines_callback = merge_callback
    view._handle_merge_selected_lines()

    assert seen["indices"] == [1, 2, 3]
    assert seen["selection_during_callback"] == []
    assert view.selected_line_indices == set()


def test_merge_restores_selection_on_failure(monkeypatch):
    view = WordMatchView()
    view.selected_line_indices = {4, 5}
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)

    view.merge_lines_callback = lambda _indices: False
    view._handle_merge_selected_lines()

    assert view.selected_line_indices == {4, 5}


def test_delete_clears_selection_before_callback(monkeypatch):
    seen = {}

    view = WordMatchView()
    view.selected_line_indices = {1, 2}
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)

    def delete_callback(indices: list[int]) -> bool:
        seen["indices"] = indices
        seen["selection_during_callback"] = sorted(view.selected_line_indices)
        return True

    view.delete_lines_callback = delete_callback
    view._handle_delete_selected_lines()

    assert seen["indices"] == [1, 2]
    assert seen["selection_during_callback"] == []
    assert view.selected_line_indices == set()


def test_delete_restores_selection_on_failure(monkeypatch):
    view = WordMatchView()
    view.selected_line_indices = {6}
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)

    view.delete_lines_callback = lambda _indices: False
    view._handle_delete_selected_lines()

    assert view.selected_line_indices == {6}


def test_delete_single_line_callback_invoked(monkeypatch):
    seen = {}

    view = WordMatchView()
    view.selected_line_indices = {2, 4}
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)

    def delete_callback(indices: list[int]) -> bool:
        seen["indices"] = indices
        seen["selection_during_callback"] = sorted(view.selected_line_indices)
        return True

    view.delete_lines_callback = delete_callback
    view._handle_delete_line(5)

    assert seen["indices"] == [5]
    assert seen["selection_during_callback"] == []
    assert view.selected_line_indices == set()


def test_delete_single_line_restores_selection_on_failure(monkeypatch):
    view = WordMatchView()
    view.selected_line_indices = {3}
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)

    view.delete_lines_callback = lambda _indices: False
    view._handle_delete_line(7)

    assert view.selected_line_indices == {3}


def test_copy_ocr_to_gt_success(monkeypatch):
    seen = {}

    view = WordMatchView(copy_ocr_to_gt_callback=lambda line_index: line_index == 2)

    def capture_notify(message: str, type_: str = "info"):
        seen["message"] = message
        seen["type"] = type_

    monkeypatch.setattr(view, "_safe_notify", capture_notify)

    view._handle_copy_ocr_to_gt(2)

    assert seen["type"] == "positive"
    assert "Copied OCR to ground truth text" in seen["message"]


def test_copy_ocr_to_gt_no_ocr_text(monkeypatch):
    seen = {}

    view = WordMatchView(copy_ocr_to_gt_callback=lambda _line_index: False)

    def capture_notify(message: str, type_: str = "info"):
        seen["message"] = message
        seen["type"] = type_

    monkeypatch.setattr(view, "_safe_notify", capture_notify)

    view._handle_copy_ocr_to_gt(0)

    assert seen["type"] == "warning"
    assert "No OCR text found" in seen["message"]


def test_top_grid_copy_page_gt_to_ocr_uses_all_lines(monkeypatch):
    seen: dict[str, object] = {}

    view = WordMatchView()
    view.view_model.line_matches = [
        SimpleNamespace(line_index=2, paragraph_index=0, word_matches=[object()]),
        SimpleNamespace(line_index=0, paragraph_index=0, word_matches=[object()]),
        SimpleNamespace(line_index=1, paragraph_index=1, word_matches=[object()]),
    ]
    view.selected_line_indices = {99}
    view.selected_word_indices = {(99, 0)}
    view.selected_paragraph_indices = {9}
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)

    def copy_callback(line_index: int) -> bool:
        seen.setdefault("calls", []).append(line_index)
        seen["line_selection_during_callback"] = sorted(view.selected_line_indices)
        seen["word_selection_during_callback"] = sorted(view.selected_word_indices)
        seen["paragraph_selection_during_callback"] = sorted(
            view.selected_paragraph_indices
        )
        return True

    view.copy_gt_to_ocr_callback = copy_callback
    view._handle_copy_page_gt_to_ocr()

    assert seen["calls"] == [0, 1, 2]
    assert seen["line_selection_during_callback"] == []
    assert seen["word_selection_during_callback"] == []
    assert seen["paragraph_selection_during_callback"] == []


def test_top_grid_copy_paragraph_ocr_to_gt_uses_selected_paragraph_lines(monkeypatch):
    seen: dict[str, object] = {}

    view = WordMatchView()
    view.view_model.line_matches = [
        SimpleNamespace(line_index=0, paragraph_index=0, word_matches=[object()]),
        SimpleNamespace(line_index=1, paragraph_index=1, word_matches=[object()]),
        SimpleNamespace(line_index=3, paragraph_index=1, word_matches=[object()]),
    ]
    view.selected_paragraph_indices = {1}
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)

    def copy_callback(line_index: int) -> bool:
        seen.setdefault("calls", []).append(line_index)
        return True

    view.copy_ocr_to_gt_callback = copy_callback
    view._handle_copy_selected_paragraphs_ocr_to_gt()

    assert seen["calls"] == [1, 3]


def test_top_grid_copy_lines_gt_to_ocr_uses_effective_selected_lines(monkeypatch):
    seen: dict[str, object] = {}

    view = WordMatchView()
    view.selected_line_indices = {4}
    view.selected_word_indices = {(2, 0), (2, 1)}
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)

    def copy_callback(line_index: int) -> bool:
        seen.setdefault("calls", []).append(line_index)
        return True

    view.copy_gt_to_ocr_callback = copy_callback
    view._handle_copy_selected_lines_gt_to_ocr()

    assert seen["calls"] == [2, 4]


def test_top_grid_copy_words_ocr_to_gt_uses_selected_words_only(monkeypatch):
    seen: dict[str, object] = {}

    view = WordMatchView()
    view.selected_word_indices = {(5, 2), (5, 3), (1, 0), (1, 1)}
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)
    view.selected_line_indices = {9}
    view.selected_paragraph_indices = {4}

    def should_not_be_used(_line_index: int) -> bool:
        raise AssertionError("line-level OCR→GT callback should not be used")

    def selected_words_callback(word_keys: list[tuple[int, int]]) -> bool:
        seen["calls"] = sorted(word_keys)
        seen["selection_during_callback"] = sorted(view.selected_word_indices)
        return True

    view.copy_ocr_to_gt_callback = should_not_be_used
    view.copy_selected_words_ocr_to_gt_callback = selected_words_callback
    view._handle_copy_selected_words_ocr_to_gt()

    assert seen["calls"] == [(1, 0), (1, 1), (5, 2), (5, 3)]
    assert seen["selection_during_callback"] == []


def test_merge_uses_word_selection_when_no_line_checkboxes(monkeypatch):
    seen = {}

    view = WordMatchView()
    view.selected_word_indices = {(1, 0), (3, 2), (3, 4)}
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)

    def merge_callback(indices: list[int]) -> bool:
        seen["indices"] = indices
        seen["line_selection_during_callback"] = sorted(view.selected_line_indices)
        seen["word_selection_during_callback"] = sorted(view.selected_word_indices)
        return True

    view.merge_lines_callback = merge_callback
    view._handle_merge_selected_lines()

    assert seen["indices"] == [1, 3]
    assert seen["line_selection_during_callback"] == []
    assert seen["word_selection_during_callback"] == []


def test_merge_lines_clears_paragraph_selection_before_callback(monkeypatch):
    seen = {}

    view = WordMatchView()
    view.selected_line_indices = {1, 2}
    view.selected_paragraph_indices = {0, 1}
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)

    def merge_callback(indices: list[int]) -> bool:
        seen["indices"] = indices
        seen["paragraph_selection_during_callback"] = sorted(
            view.selected_paragraph_indices
        )
        return True

    view.merge_lines_callback = merge_callback
    view._handle_merge_selected_lines()

    assert seen["indices"] == [1, 2]
    assert seen["paragraph_selection_during_callback"] == []
    assert view.selected_paragraph_indices == set()


def test_merge_lines_restores_paragraph_selection_on_failure(monkeypatch):
    view = WordMatchView()
    view.selected_line_indices = {4, 5}
    view.selected_paragraph_indices = {1}
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)

    view.merge_lines_callback = lambda _indices: False
    view._handle_merge_selected_lines()

    assert view.selected_paragraph_indices == {1}


def test_delete_restores_word_selection_on_failure(monkeypatch):
    view = WordMatchView()
    view.selected_word_indices = {(2, 1), (4, 0)}
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)

    view.delete_lines_callback = lambda _indices: False
    view._handle_delete_selected_lines()

    assert view.selected_word_indices == {(2, 1), (4, 0)}


def test_line_selection_selects_all_words_for_line():
    view = WordMatchView()
    view.view_model.line_matches = [
        SimpleNamespace(line_index=2, word_matches=[object(), object(), object()])
    ]

    view._on_line_selection_change(2, True)

    assert view.selected_line_indices == {2}
    assert view.selected_word_indices == {(2, 0), (2, 1), (2, 2)}


def test_all_words_selected_auto_selects_line():
    view = WordMatchView()
    view.view_model.line_matches = [
        SimpleNamespace(line_index=1, word_matches=[object(), object()])
    ]

    view._on_word_selection_change((1, 0), True)
    assert 1 not in view.selected_line_indices

    view._on_word_selection_change((1, 1), True)
    assert 1 in view.selected_line_indices


def test_set_selected_words_emits_selection_callback():
    view = WordMatchView()
    view.view_model.line_matches = [
        SimpleNamespace(line_index=0, word_matches=[object()])
    ]
    seen = {}
    view.set_selection_change_callback(
        lambda selection: seen.setdefault("s", selection)
    )

    view.set_selected_words({(0, 0)})

    assert seen["s"] == {(0, 0)}


def test_group_lines_by_paragraph_orders_unassigned_last():
    view = WordMatchView()
    line_matches = [
        SimpleNamespace(line_index=2, paragraph_index=None),
        SimpleNamespace(line_index=0, paragraph_index=1),
        SimpleNamespace(line_index=1, paragraph_index=0),
        SimpleNamespace(line_index=3, paragraph_index=0),
    ]

    grouped = view._group_lines_by_paragraph(line_matches)

    assert [paragraph_index for paragraph_index, _ in grouped] == [0, 1, None]
    assert [line.line_index for line in grouped[0][1]] == [1, 3]
    assert [line.line_index for line in grouped[1][1]] == [0]
    assert [line.line_index for line in grouped[2][1]] == [2]


def test_set_selected_paragraphs_emits_selection_callback():
    view = WordMatchView()
    view.view_model.line_matches = [
        SimpleNamespace(line_index=0, paragraph_index=0, word_matches=[object()]),
        SimpleNamespace(line_index=1, paragraph_index=1, word_matches=[object()]),
    ]
    seen = {}
    view.set_paragraph_selection_change_callback(
        lambda selection: seen.setdefault("p", selection)
    )

    view.set_selected_paragraphs({0, 2})

    assert seen["p"] == {0}
    assert view.selected_paragraph_indices == {0}


def test_set_selected_paragraphs_selects_all_lines_and_words():
    view = WordMatchView()
    view.view_model.line_matches = [
        SimpleNamespace(
            line_index=0,
            paragraph_index=0,
            word_matches=[object(), object()],
        ),
        SimpleNamespace(
            line_index=1,
            paragraph_index=0,
            word_matches=[object()],
        ),
        SimpleNamespace(
            line_index=2,
            paragraph_index=1,
            word_matches=[object()],
        ),
    ]

    view.set_selected_paragraphs({0})

    assert view.selected_paragraph_indices == {0}
    assert view.selected_line_indices == {0, 1}
    assert view.selected_word_indices == {(0, 0), (0, 1), (1, 0)}


def test_refresh_line_checkbox_states_does_not_raise_on_attribute_error(monkeypatch):
    """Attribute errors during checkbox updates are treated as benign UI edge cases."""
    view = WordMatchView()
    checkbox = object()
    view._line_checkbox_refs = {1: checkbox}

    monkeypatch.setattr(view, "_has_active_ui_context", lambda _checkbox: True)
    monkeypatch.setattr(view, "_is_line_checked", lambda _line_index: True)

    def raise_attribute_error(*_args, **_kwargs):
        raise AttributeError("missing internal checkbox attr")

    monkeypatch.setattr(view, "_set_checkbox_value", raise_attribute_error)

    view._refresh_line_checkbox_states()


def test_refresh_line_checkbox_states_raises_on_real_runtime_error(monkeypatch):
    """Unexpected runtime failures should still propagate to avoid hidden corruption."""
    view = WordMatchView()
    checkbox = object()
    view._line_checkbox_refs = {1: checkbox}

    monkeypatch.setattr(view, "_has_active_ui_context", lambda _checkbox: True)
    monkeypatch.setattr(view, "_is_line_checked", lambda _line_index: True)
    monkeypatch.setattr(view, "_is_disposed_ui_error", lambda _error: False)

    def raise_runtime_error(*_args, **_kwargs):
        raise RuntimeError("real runtime error")

    monkeypatch.setattr(view, "_set_checkbox_value", raise_runtime_error)

    with pytest.raises(RuntimeError, match="real runtime error"):
        view._refresh_line_checkbox_states()


def test_set_checkbox_value_without_setter_does_not_raise():
    """Checkbox objects without set_value support should be skipped without errors."""
    view = WordMatchView()
    view._set_checkbox_value(object(), True)


def test_on_paragraph_selection_change_clears_paragraph_lines_and_words_when_unchecked():
    view = WordMatchView()
    view.view_model.line_matches = [
        SimpleNamespace(
            line_index=0,
            paragraph_index=0,
            word_matches=[object(), object()],
        ),
        SimpleNamespace(
            line_index=1,
            paragraph_index=0,
            word_matches=[object()],
        ),
        SimpleNamespace(
            line_index=2,
            paragraph_index=1,
            word_matches=[object()],
        ),
    ]
    view.selected_paragraph_indices = {0}
    view.selected_line_indices = {0, 1, 2}
    view.selected_word_indices = {(0, 0), (0, 1), (1, 0), (2, 0)}

    view._on_paragraph_selection_change(0, False)

    assert view.selected_paragraph_indices == set()
    assert view.selected_line_indices == {2}
    assert view.selected_word_indices == {(2, 0)}


def test_merge_paragraphs_clears_selection_before_callback(monkeypatch):
    seen = {}

    view = WordMatchView()
    view.selected_paragraph_indices = {1, 2, 3}
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)

    def merge_callback(indices: list[int]) -> bool:
        seen["indices"] = indices
        seen["selection_during_callback"] = sorted(view.selected_paragraph_indices)
        return True

    view.merge_paragraphs_callback = merge_callback
    view._handle_merge_selected_paragraphs()

    assert seen["indices"] == [1, 2, 3]
    assert seen["selection_during_callback"] == []
    assert view.selected_paragraph_indices == set()


def test_split_paragraph_after_line_restores_selection_on_failure(monkeypatch):
    view = WordMatchView()
    view.selected_line_indices = {4}
    view.selected_word_indices = {(4, 0)}
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)

    view.split_paragraph_after_line_callback = lambda _line_index: False
    view._handle_split_paragraph_after_selected_line()

    assert view.selected_line_indices == {4}
    assert view.selected_word_indices == {(4, 0)}


def test_split_paragraph_after_line_requires_single_selected_line(monkeypatch):
    view = WordMatchView()
    seen = {}

    def notify(message: str, type_: str = "info"):
        seen["message"] = message
        seen["type"] = type_

    monkeypatch.setattr(view, "_safe_notify", notify)
    view.split_paragraph_after_line_callback = lambda _line_index: True
    view.selected_line_indices = {1, 2}

    view._handle_split_paragraph_after_selected_line()

    assert seen["type"] == "warning"
    assert "exactly one line" in seen["message"]


def test_split_paragraph_by_selected_lines_uses_selected_line_checkboxes(monkeypatch):
    seen = {}
    view = WordMatchView()
    view.selected_line_indices = {1, 3}
    view.selected_word_indices = {(1, 0), (3, 2)}
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)

    def split_callback(indices: list[int]) -> bool:
        seen["indices"] = indices
        seen["line_selection_during_callback"] = sorted(view.selected_line_indices)
        seen["word_selection_during_callback"] = sorted(view.selected_word_indices)
        return True

    view.split_paragraph_with_selected_lines_callback = split_callback
    view._handle_split_paragraph_by_selected_lines()

    assert seen["indices"] == [1, 3]
    assert seen["line_selection_during_callback"] == []
    assert seen["word_selection_during_callback"] == []


def test_split_paragraph_by_selected_lines_requires_line_selection(monkeypatch):
    seen = {}
    view = WordMatchView()
    view.selected_word_indices = {(1, 0), (3, 2)}

    def notify(message: str, type_: str = "info"):
        seen["message"] = message
        seen["type"] = type_

    monkeypatch.setattr(view, "_safe_notify", notify)
    view.split_paragraph_with_selected_lines_callback = lambda _indices: True

    view._handle_split_paragraph_by_selected_lines()

    assert seen["type"] == "warning"
    assert "Select one or more lines" in seen["message"]


def test_split_paragraph_by_selected_lines_restores_selection_on_failure(monkeypatch):
    view = WordMatchView()
    view.selected_line_indices = {2}
    view.selected_word_indices = {(2, 0)}
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)

    view.split_paragraph_with_selected_lines_callback = lambda _indices: False
    view._handle_split_paragraph_by_selected_lines()

    assert view.selected_line_indices == {2}
    assert view.selected_word_indices == {(2, 0)}


def test_split_line_after_selected_word_requires_single_word(monkeypatch):
    view = WordMatchView()
    view.selected_word_indices = {(1, 0), (1, 1)}
    seen = {}

    def notify(message: str, type_: str = "info"):
        seen["message"] = message
        seen["type"] = type_

    monkeypatch.setattr(view, "_safe_notify", notify)
    view.split_line_after_word_callback = lambda _line_index, _word_index: True

    view._handle_split_line_after_selected_word()

    assert seen["type"] == "warning"
    assert "exactly one word" in seen["message"]


def test_split_line_after_selected_word_clears_selection_before_callback(monkeypatch):
    seen = {}
    view = WordMatchView()
    view.selected_line_indices = {1}
    view.selected_word_indices = {(1, 2)}
    view.selected_paragraph_indices = {0}
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)

    def split_callback(line_index: int, word_index: int) -> bool:
        seen["args"] = (line_index, word_index)
        seen["selection_during_callback"] = (
            sorted(view.selected_line_indices),
            sorted(view.selected_word_indices),
            sorted(view.selected_paragraph_indices),
        )
        return True

    view.split_line_after_word_callback = split_callback
    view._handle_split_line_after_selected_word()

    assert seen["args"] == (1, 2)
    assert seen["selection_during_callback"] == ([], [], [])
    assert view.selected_line_indices == set()
    assert view.selected_word_indices == set()
    assert view.selected_paragraph_indices == set()


def test_split_line_after_selected_word_restores_selection_on_failure(monkeypatch):
    view = WordMatchView()
    view.selected_line_indices = {3}
    view.selected_word_indices = {(3, 1)}
    view.selected_paragraph_indices = {1}
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)

    view.split_line_after_word_callback = lambda _line_index, _word_index: False
    view._handle_split_line_after_selected_word()

    assert view.selected_line_indices == {3}
    assert view.selected_word_indices == {(3, 1)}
    assert view.selected_paragraph_indices == {1}


def test_group_selected_words_into_new_paragraph_clears_selection_before_callback(
    monkeypatch,
):
    seen = {}

    view = WordMatchView()
    view.selected_line_indices = {1, 2}
    view.selected_word_indices = {(1, 1), (2, 0)}
    view.selected_paragraph_indices = {0}
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)

    def group_callback(word_keys: list[tuple[int, int]]) -> bool:
        seen["word_keys"] = word_keys
        seen["selection_during_callback"] = (
            sorted(view.selected_line_indices),
            sorted(view.selected_word_indices),
            sorted(view.selected_paragraph_indices),
        )
        return True

    view.group_selected_words_into_paragraph_callback = group_callback
    view._handle_group_selected_words_into_new_paragraph()

    assert seen["word_keys"] == [(1, 1), (2, 0)]
    assert seen["selection_during_callback"] == ([], [], [])
    assert view.selected_line_indices == set()
    assert view.selected_word_indices == set()
    assert view.selected_paragraph_indices == set()


def test_group_selected_words_into_new_paragraph_restores_selection_on_failure(
    monkeypatch,
):
    view = WordMatchView()
    view.selected_line_indices = {4}
    view.selected_word_indices = {(4, 0)}
    view.selected_paragraph_indices = {2}
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)

    view.group_selected_words_into_paragraph_callback = lambda _word_keys: False
    view._handle_group_selected_words_into_new_paragraph()

    assert view.selected_line_indices == {4}
    assert view.selected_word_indices == {(4, 0)}
    assert view.selected_paragraph_indices == {2}


def test_delete_paragraphs_clears_selection_before_callback(monkeypatch):
    seen = {}

    view = WordMatchView()
    view.selected_paragraph_indices = {1, 3}
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)

    def delete_callback(indices: list[int]) -> bool:
        seen["indices"] = indices
        seen["selection_during_callback"] = sorted(view.selected_paragraph_indices)
        return True

    view.delete_paragraphs_callback = delete_callback
    view._handle_delete_selected_paragraphs()

    assert seen["indices"] == [1, 3]
    assert seen["selection_during_callback"] == []
    assert view.selected_paragraph_indices == set()


def test_delete_paragraphs_restores_selection_on_failure(monkeypatch):
    view = WordMatchView()
    view.selected_paragraph_indices = {2}
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)

    view.delete_paragraphs_callback = lambda _indices: False
    view._handle_delete_selected_paragraphs()

    assert view.selected_paragraph_indices == {2}


def test_delete_words_clears_selection_before_callback(monkeypatch):
    seen = {}

    view = WordMatchView()
    view.selected_line_indices = {1}
    view.selected_word_indices = {(1, 0), (2, 1)}
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)

    def delete_callback(word_keys: list[tuple[int, int]]) -> bool:
        seen["word_keys"] = word_keys
        seen["line_selection_during_callback"] = sorted(view.selected_line_indices)
        seen["word_selection_during_callback"] = sorted(view.selected_word_indices)
        return True

    view.delete_words_callback = delete_callback
    view._handle_delete_selected_words()

    assert seen["word_keys"] == [(1, 0), (2, 1)]
    assert seen["line_selection_during_callback"] == []
    assert seen["word_selection_during_callback"] == []
    assert view.selected_line_indices == set()
    assert view.selected_word_indices == set()


def test_delete_words_restores_selection_on_failure(monkeypatch):
    view = WordMatchView()
    view.selected_line_indices = {3}
    view.selected_word_indices = {(3, 0)}
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)

    view.delete_words_callback = lambda _word_keys: False
    view._handle_delete_selected_words()

    assert view.selected_line_indices == {3}
    assert view.selected_word_indices == {(3, 0)}


def test_merge_word_left_clears_selection_before_callback(monkeypatch):
    seen = {}

    view = WordMatchView()
    view.selected_line_indices = {1}
    view.selected_word_indices = {(1, 2)}
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)

    def merge_callback(line_index: int, word_index: int) -> bool:
        seen["args"] = (line_index, word_index)
        seen["line_selection_during_callback"] = sorted(view.selected_line_indices)
        seen["word_selection_during_callback"] = sorted(view.selected_word_indices)
        return True

    view.merge_word_left_callback = merge_callback
    view._handle_merge_word_left(1, 2)

    assert seen["args"] == (1, 2)
    assert seen["line_selection_during_callback"] == []
    assert seen["word_selection_during_callback"] == []


def test_merge_word_left_success_rerenders_target_line(monkeypatch):
    view = WordMatchView(merge_word_left_callback=lambda _line_index, _word_index: True)
    seen = {"refreshed": [], "rerendered": []}
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        view,
        "_refresh_local_line_match_from_line_object",
        lambda line_index: seen["refreshed"].append(line_index) or True,
    )
    monkeypatch.setattr(
        view,
        "_rerender_line_card",
        lambda line_index: seen["rerendered"].append(line_index),
    )

    view._handle_merge_word_left(1, 1)

    assert seen["refreshed"] == [1]
    assert seen["rerendered"] == [1]


def test_merge_word_left_restores_selection_on_failure(monkeypatch):
    view = WordMatchView()
    view.selected_line_indices = {2}
    view.selected_word_indices = {(2, 1)}
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)

    view.merge_word_left_callback = lambda _line_index, _word_index: False
    view._handle_merge_word_left(2, 1)

    assert view.selected_line_indices == {2}
    assert view.selected_word_indices == {(2, 1)}


def test_merge_word_right_clears_selection_before_callback(monkeypatch):
    seen = {}

    view = WordMatchView()
    view.selected_line_indices = {1}
    view.selected_word_indices = {(1, 0)}
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)

    def merge_callback(line_index: int, word_index: int) -> bool:
        seen["args"] = (line_index, word_index)
        seen["line_selection_during_callback"] = sorted(view.selected_line_indices)
        seen["word_selection_during_callback"] = sorted(view.selected_word_indices)
        return True

    view.merge_word_right_callback = merge_callback
    view._handle_merge_word_right(1, 0)

    assert seen["args"] == (1, 0)
    assert seen["line_selection_during_callback"] == []
    assert seen["word_selection_during_callback"] == []


def test_merge_word_right_success_rerenders_target_line(monkeypatch):
    view = WordMatchView(
        merge_word_right_callback=lambda _line_index, _word_index: True
    )
    seen = {"refreshed": [], "rerendered": []}
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        view,
        "_refresh_local_line_match_from_line_object",
        lambda line_index: seen["refreshed"].append(line_index) or True,
    )
    monkeypatch.setattr(
        view,
        "_rerender_line_card",
        lambda line_index: seen["rerendered"].append(line_index),
    )

    view._handle_merge_word_right(1, 0)

    assert seen["refreshed"] == [1]
    assert seen["rerendered"] == [1]


def test_merge_word_right_restores_selection_on_failure(monkeypatch):
    view = WordMatchView()
    view.selected_line_indices = {4}
    view.selected_word_indices = {(4, 0)}
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)

    view.merge_word_right_callback = lambda _line_index, _word_index: False
    view._handle_merge_word_right(4, 0)

    assert view.selected_line_indices == {4}
    assert view.selected_word_indices == {(4, 0)}


def test_merge_selected_words_requires_contiguous_words_single_line(monkeypatch):
    seen = {}
    view = WordMatchView()
    view.selected_word_indices = {(1, 0), (2, 1)}
    view.merge_word_right_callback = lambda _line_index, _word_index: True

    def capture_notify(message: str, type_: str = "info"):
        seen["message"] = message
        seen["type"] = type_

    monkeypatch.setattr(view, "_safe_notify", capture_notify)

    view._handle_merge_selected_words()

    assert seen["type"] == "warning"
    assert "single line" in seen["message"]


def test_merge_selected_words_uses_repeated_merge_right(monkeypatch):
    seen = {"calls": []}
    view = WordMatchView()
    view.selected_line_indices = {1}
    view.selected_word_indices = {(1, 1), (1, 2), (1, 3)}
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)

    def merge_callback(line_index: int, word_index: int) -> bool:
        seen["calls"].append((line_index, word_index))
        seen["selection_during_callback"] = (
            sorted(view.selected_line_indices),
            sorted(view.selected_word_indices),
        )
        return True

    view.merge_word_right_callback = merge_callback
    view._handle_merge_selected_words()

    assert seen["calls"] == [(1, 1), (1, 1)]
    assert seen["selection_during_callback"] == ([], [])
    assert view.selected_line_indices == set()
    assert view.selected_word_indices == set()


def test_merge_selected_words_restores_selection_on_failure(monkeypatch):
    view = WordMatchView()
    view.selected_line_indices = {2}
    view.selected_word_indices = {(2, 0), (2, 1)}
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)

    view.merge_word_right_callback = lambda _line_index, _word_index: False
    view._handle_merge_selected_words()

    assert view.selected_line_indices == {2}
    assert view.selected_word_indices == {(2, 0), (2, 1)}


def test_merge_selected_words_button_state(monkeypatch):
    view = WordMatchView()
    view.merge_words_button = SimpleNamespace(disabled=None)
    view.merge_word_right_callback = lambda _line_index, _word_index: True

    view.selected_word_indices = {(0, 0), (0, 1)}
    view._update_action_button_state()
    assert view.merge_words_button.disabled is False

    view.selected_word_indices = {(0, 0), (0, 2)}
    view._update_action_button_state()
    assert view.merge_words_button.disabled is True


def test_delete_single_word_clears_selection_before_callback(monkeypatch):
    seen = {}

    view = WordMatchView()
    view.selected_line_indices = {2}
    view.selected_word_indices = {(2, 1), (2, 2)}
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)

    def delete_callback(word_keys: list[tuple[int, int]]) -> bool:
        seen["word_keys"] = word_keys
        seen["line_selection_during_callback"] = sorted(view.selected_line_indices)
        seen["word_selection_during_callback"] = sorted(view.selected_word_indices)
        return True

    view.delete_words_callback = delete_callback
    view._handle_delete_single_word(2, 1)

    assert seen["word_keys"] == [(2, 1)]
    assert seen["line_selection_during_callback"] == []
    assert seen["word_selection_during_callback"] == []


def test_delete_single_word_success_rerenders_target_line(monkeypatch):
    view = WordMatchView(delete_words_callback=lambda _word_keys: True)
    seen = {"refreshed": [], "rerendered": []}
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        view,
        "_refresh_local_line_match_from_line_object",
        lambda line_index: seen["refreshed"].append(line_index) or True,
    )
    monkeypatch.setattr(
        view,
        "_rerender_line_card",
        lambda line_index: seen["rerendered"].append(line_index),
    )

    view._handle_delete_single_word(2, 1)

    assert seen["refreshed"] == [2]
    assert seen["rerendered"] == [2]


def test_delete_single_word_restores_selection_on_failure(monkeypatch):
    view = WordMatchView()
    view.selected_line_indices = {5}
    view.selected_word_indices = {(5, 0)}
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)

    view.delete_words_callback = lambda _word_keys: False
    view._handle_delete_single_word(5, 0)

    assert view.selected_line_indices == {5}
    assert view.selected_word_indices == {(5, 0)}


def test_split_word_clears_selection_before_callback(monkeypatch):
    seen = {}

    view = WordMatchView()
    view.selected_line_indices = {1}
    view.selected_word_indices = {(1, 2)}
    view._word_split_fractions[(1, 2)] = 0.5
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)

    def split_callback(line_index: int, word_index: int, split_fraction: float) -> bool:
        seen["args"] = (line_index, word_index, split_fraction)
        seen["line_selection_during_callback"] = sorted(view.selected_line_indices)
        seen["word_selection_during_callback"] = sorted(view.selected_word_indices)
        return True

    view.split_word_callback = split_callback
    view._handle_split_word(1, 2)

    assert seen["args"] == (1, 2, 0.5)
    assert seen["line_selection_during_callback"] == []
    assert seen["word_selection_during_callback"] == []


def test_split_word_success_rerenders_target_line(monkeypatch):
    view = WordMatchView(
        split_word_callback=lambda _line_index, _word_index, _split_fraction: True
    )
    seen = {"refreshed": [], "rerendered": []}
    view._word_split_fractions[(3, 1)] = 0.4
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        view,
        "_refresh_local_line_match_from_line_object",
        lambda line_index: seen["refreshed"].append(line_index) or True,
    )
    monkeypatch.setattr(
        view,
        "_rerender_line_card",
        lambda line_index: seen["rerendered"].append(line_index),
    )

    view._handle_split_word(3, 1)

    assert seen["refreshed"] == [3]
    assert seen["rerendered"] == [3]


def test_split_word_restores_selection_on_failure(monkeypatch):
    view = WordMatchView()
    view.selected_line_indices = {3}
    view.selected_word_indices = {(3, 1)}
    view._word_split_fractions[(3, 1)] = 0.25
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)

    view.split_word_callback = lambda _line_index, _word_index, _split_fraction: False
    view._handle_split_word(3, 1)

    assert view.selected_line_indices == {3}
    assert view.selected_word_indices == {(3, 1)}


def test_split_word_requires_selected_marker(monkeypatch):
    seen = {}
    view = WordMatchView()

    def notify(message: str, type_: str = "info"):
        seen["message"] = message
        seen["type"] = type_

    monkeypatch.setattr(view, "_safe_notify", notify)
    view.split_word_callback = lambda _line_index, _word_index, _split_fraction: True

    view._handle_split_word(0, 0)

    assert seen["type"] == "warning"
    assert "choose split position" in seen["message"]


def test_split_word_vertical_closest_line_clears_selection_before_callback(
    monkeypatch,
):
    seen = {}

    view = WordMatchView()
    view.selected_line_indices = {1}
    view.selected_word_indices = {(1, 2)}
    view._word_split_fractions[(1, 2)] = 0.5
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)
    monkeypatch.setattr(view, "_update_summary", lambda: None)
    monkeypatch.setattr(view, "_update_lines_display", lambda: None)

    def split_callback(line_index: int, word_index: int, split_fraction: float) -> bool:
        seen["args"] = (line_index, word_index, split_fraction)
        seen["line_selection_during_callback"] = sorted(view.selected_line_indices)
        seen["word_selection_during_callback"] = sorted(view.selected_word_indices)
        return True

    view.split_word_vertical_closest_line_callback = split_callback
    view._handle_split_word_vertical_closest_line(1, 2)

    assert seen["args"] == (1, 2, 0.5)
    assert seen["line_selection_during_callback"] == []
    assert seen["word_selection_during_callback"] == []


def test_split_word_vertical_closest_line_requires_selected_marker(monkeypatch):
    seen = {}
    view = WordMatchView()

    def notify(message: str, type_: str = "info"):
        seen["message"] = message
        seen["type"] = type_

    monkeypatch.setattr(view, "_safe_notify", notify)
    view.split_word_vertical_closest_line_callback = (
        lambda _line_index, _word_index, _split_fraction: True
    )

    view._handle_split_word_vertical_closest_line(0, 0)

    assert seen["type"] == "warning"
    assert "choose split position" in seen["message"]


def test_render_word_split_marker_shows_default_guide_without_selection():
    view = WordMatchView()
    split_key = (2, 3)
    image = SimpleNamespace(content=None)
    view._word_split_image_refs[split_key] = image
    view._word_split_image_sizes[split_key] = (40.0, 18.0)

    render_word_split_marker(view, split_key)
    assert image.content == ""

    view._word_split_hover_keys.add(split_key)
    render_word_split_marker(view, split_key)

    assert image.content is not None
    assert "stroke-dasharray" in image.content
    assert 'x1="20.00"' in image.content


def test_render_word_split_marker_keeps_hover_guide_after_selection():
    view = WordMatchView()
    split_key = (5, 1)
    image = SimpleNamespace(content=None)
    view._word_split_image_refs[split_key] = image
    view._word_split_image_sizes[split_key] = (80.0, 24.0)
    view._word_split_marker_x[split_key] = 30.0
    view._word_split_marker_y[split_key] = 10.0
    view._word_split_hover_keys.add(split_key)
    view._word_split_hover_positions[split_key] = (52.0, 14.0)

    render_word_split_marker(view, split_key)

    assert image.content is not None
    assert 'x1="30.00"' in image.content
    assert 'y1="10.00"' in image.content
    assert 'x1="52.00"' in image.content
    assert 'y1="14.00"' in image.content
    assert "stroke-dasharray" in image.content


def test_handle_word_image_click_falls_back_to_generic_x_coordinate(monkeypatch):
    view = WordMatchView(split_word_callback=lambda *_args: True)
    split_key = (1, 2)
    view._word_split_image_sizes[split_key] = (100.0, 20.0)
    view._word_split_button_refs[split_key] = SimpleNamespace(disabled=True)
    view._line_word_match_by_ocr_index = lambda _line_index, _word_index: (
        SimpleNamespace(ocr_text="alphabet")
    )
    event = SimpleNamespace(x=25.0)
    handle_word_image_click(view, 1, 2, event)

    assert view._word_split_fractions[split_key] == pytest.approx(0.25)
    assert view._word_split_marker_x[split_key] == pytest.approx(25.0)


def test_crop_word_to_marker_prefers_stored_y_fraction(monkeypatch):
    seen = {}

    def nudge_callback(
        line_index: int,
        word_index: int,
        left_delta: float,
        right_delta: float,
        top_delta: float,
        bottom_delta: float,
        refine_after: bool,
    ) -> bool:
        seen["args"] = (
            line_index,
            word_index,
            left_delta,
            right_delta,
            top_delta,
            bottom_delta,
            refine_after,
        )
        return True

    view = WordMatchView(nudge_word_bbox_callback=nudge_callback)
    split_key = (1, 2)
    view._word_split_fractions[split_key] = 0.5
    view._word_split_y_fractions[split_key] = 0.75
    view._word_split_marker_y[split_key] = 5.0
    view._word_split_image_sizes[split_key] = (100.0, 20.0)
    view._line_word_match_by_ocr_index = lambda *_args: SimpleNamespace(
        word_object=SimpleNamespace(
            bounding_box=SimpleNamespace(width=80.0, height=40.0),
        )
    )
    view._line_match_by_index = lambda _line_index: None
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        view,
        "_refresh_local_line_match_from_line_object",
        lambda _line_index: None,
    )
    monkeypatch.setattr(view, "_update_summary", lambda: None)
    monkeypatch.setattr(view, "_rerender_line_card", lambda _line_index: None)
    monkeypatch.setattr(
        view,
        "_refresh_open_word_dialog_for",
        lambda _line_index, _word_index: None,
    )
    monkeypatch.setattr(view, "_update_action_button_state", lambda: None)
    monkeypatch.setattr(view, "_emit_selection_changed", lambda: None)

    view._handle_crop_word_to_marker(1, 2, "above")

    assert seen["args"] == (1, 2, 0.0, 0.0, -30.0, 0.0, False)


def test_crop_word_to_marker_uses_marker_y_when_fraction_missing(monkeypatch):
    seen = {}

    def nudge_callback(
        line_index: int,
        word_index: int,
        left_delta: float,
        right_delta: float,
        top_delta: float,
        bottom_delta: float,
        refine_after: bool,
    ) -> bool:
        seen["args"] = (
            line_index,
            word_index,
            left_delta,
            right_delta,
            top_delta,
            bottom_delta,
            refine_after,
        )
        return True

    view = WordMatchView(nudge_word_bbox_callback=nudge_callback)
    split_key = (1, 2)
    view._word_split_fractions[split_key] = 0.5
    view._word_split_marker_y[split_key] = 5.0
    view._word_split_image_sizes[split_key] = (100.0, 20.0)
    view._line_word_match_by_ocr_index = lambda *_args: SimpleNamespace(
        word_object=SimpleNamespace(
            bounding_box=SimpleNamespace(width=80.0, height=40.0),
        )
    )
    view._line_match_by_index = lambda _line_index: None
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        view,
        "_refresh_local_line_match_from_line_object",
        lambda _line_index: None,
    )
    monkeypatch.setattr(view, "_update_summary", lambda: None)
    monkeypatch.setattr(view, "_rerender_line_card", lambda _line_index: None)
    monkeypatch.setattr(
        view,
        "_refresh_open_word_dialog_for",
        lambda _line_index, _word_index: None,
    )
    monkeypatch.setattr(view, "_update_action_button_state", lambda: None)
    monkeypatch.setattr(view, "_emit_selection_changed", lambda: None)

    view._handle_crop_word_to_marker(1, 2, "below")

    assert seen["args"] == (1, 2, 0.0, 0.0, 0.0, -30.0, False)


def test_crop_above_works_with_only_y_marker(monkeypatch):
    seen = {}

    def nudge_callback(
        line_index: int,
        word_index: int,
        left_delta: float,
        right_delta: float,
        top_delta: float,
        bottom_delta: float,
        refine_after: bool,
    ) -> bool:
        seen["args"] = (
            line_index,
            word_index,
            left_delta,
            right_delta,
            top_delta,
            bottom_delta,
            refine_after,
        )
        return True

    view = WordMatchView(nudge_word_bbox_callback=nudge_callback)
    split_key = (2, 3)
    view._word_split_y_fractions[split_key] = 0.25
    view._word_split_image_sizes[split_key] = (100.0, 40.0)
    view._line_word_match_by_ocr_index = lambda *_args: SimpleNamespace(
        word_object=SimpleNamespace(
            bounding_box=SimpleNamespace(width=80.0, height=40.0),
        )
    )
    view._line_match_by_index = lambda _line_index: None
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        view, "_refresh_local_line_match_from_line_object", lambda _line_index: None
    )
    monkeypatch.setattr(view, "_update_summary", lambda: None)
    monkeypatch.setattr(view, "_rerender_line_card", lambda _line_index: None)
    monkeypatch.setattr(
        view, "_refresh_open_word_dialog_for", lambda _line_index, _word_index: None
    )
    monkeypatch.setattr(view, "_update_action_button_state", lambda: None)
    monkeypatch.setattr(view, "_emit_selection_changed", lambda: None)

    view._handle_crop_word_to_marker(2, 3, "above")

    assert seen["args"] == (2, 3, 0.0, 0.0, -10.0, 0.0, False)


def test_crop_left_works_with_only_x_marker(monkeypatch):
    seen = {}

    def nudge_callback(
        line_index: int,
        word_index: int,
        left_delta: float,
        right_delta: float,
        top_delta: float,
        bottom_delta: float,
        refine_after: bool,
    ) -> bool:
        seen["args"] = (
            line_index,
            word_index,
            left_delta,
            right_delta,
            top_delta,
            bottom_delta,
            refine_after,
        )
        return True

    view = WordMatchView(nudge_word_bbox_callback=nudge_callback)
    split_key = (2, 3)
    view._word_split_fractions[split_key] = 0.25
    view._word_split_image_sizes[split_key] = (100.0, 40.0)
    view._line_word_match_by_ocr_index = lambda *_args: SimpleNamespace(
        word_object=SimpleNamespace(
            bounding_box=SimpleNamespace(width=80.0, height=40.0),
        )
    )
    view._line_match_by_index = lambda _line_index: None
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        view, "_refresh_local_line_match_from_line_object", lambda _line_index: None
    )
    monkeypatch.setattr(view, "_update_summary", lambda: None)
    monkeypatch.setattr(view, "_rerender_line_card", lambda _line_index: None)
    monkeypatch.setattr(
        view, "_refresh_open_word_dialog_for", lambda _line_index, _word_index: None
    )
    monkeypatch.setattr(view, "_update_action_button_state", lambda: None)
    monkeypatch.setattr(view, "_emit_selection_changed", lambda: None)

    view._handle_crop_word_to_marker(2, 3, "left")

    assert seen["args"] == (2, 3, -20.0, 0.0, 0.0, 0.0, False)


def test_render_word_split_marker_uses_fraction_for_scaled_image():
    view = WordMatchView(split_word_callback=lambda *_args: True)
    split_key = (1, 2)
    image = SimpleNamespace(content="")
    view._word_split_image_refs[split_key] = image
    view._word_split_image_sizes[split_key] = (200.0, 100.0)
    view._word_split_fractions[split_key] = 0.25
    view._word_split_y_fractions[split_key] = 0.4
    view._word_split_marker_x[split_key] = 30.0
    view._word_split_marker_y[split_key] = 10.0

    render_word_split_marker(view, split_key)

    assert 'x1="50.00"' in image.content
    assert 'y1="40.00"' in image.content


def test_start_rebox_word_sets_pending_and_requests_image_mode(monkeypatch):
    seen = {}
    view = WordMatchView(rebox_word_callback=lambda *_args: True)
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)
    view.set_rebox_request_callback(
        lambda line_index, word_index: seen.setdefault(
            "target", (line_index, word_index)
        )
    )

    view._handle_start_rebox_word(2, 4)

    assert seen["target"] == (2, 4)
    assert view._pending_rebox_word_key == (2, 4)


def test_apply_rebox_bbox_clears_selection_before_callback(monkeypatch):
    seen = {}

    def rebox_callback(
        line_index: int,
        word_index: int,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
    ) -> bool:
        seen["args"] = (line_index, word_index, x1, y1, x2, y2)
        seen["selection_during_callback"] = (
            sorted(view.selected_line_indices),
            sorted(view.selected_word_indices),
        )
        return True

    view = WordMatchView(rebox_word_callback=rebox_callback)
    view.selected_line_indices = {1}
    view.selected_word_indices = {(1, 2)}
    view._pending_rebox_word_key = (1, 2)
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)

    view.apply_rebox_bbox(10.0, 11.0, 20.0, 21.0)

    assert seen["args"] == (1, 2, 10.0, 11.0, 20.0, 21.0)
    assert seen["selection_during_callback"] == ([], [])
    assert view._pending_rebox_word_key is None


def test_apply_rebox_bbox_restores_selection_on_failure(monkeypatch):
    view = WordMatchView(rebox_word_callback=lambda *_args: False)
    view.selected_line_indices = {3}
    view.selected_word_indices = {(3, 0)}
    view._pending_rebox_word_key = (3, 0)
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)

    view.apply_rebox_bbox(1.0, 2.0, 3.0, 4.0)

    assert view.selected_line_indices == {3}
    assert view.selected_word_indices == {(3, 0)}
    assert view._pending_rebox_word_key == (3, 0)


def test_refine_selected_words_clears_selection_before_callback(monkeypatch):
    seen = {}

    def refine_words_callback(word_keys: list[tuple[int, int]]) -> bool:
        seen["word_keys"] = word_keys
        seen["selection_during_callback"] = (
            sorted(view.selected_line_indices),
            sorted(view.selected_word_indices),
        )
        return True

    view = WordMatchView(refine_words_callback=refine_words_callback)
    view.selected_line_indices = {1}
    view.selected_word_indices = {(1, 0), (1, 1)}
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)

    view._handle_refine_selected_words()

    assert seen["word_keys"] == [(1, 0), (1, 1)]
    assert seen["selection_during_callback"] == ([], [])


def test_refine_selected_lines_clears_selection_before_callback(monkeypatch):
    seen = {}

    def refine_lines_callback(line_indices: list[int]) -> bool:
        seen["line_indices"] = line_indices
        seen["selection_during_callback"] = (
            sorted(view.selected_line_indices),
            sorted(view.selected_word_indices),
        )
        return True

    view = WordMatchView(refine_lines_callback=refine_lines_callback)
    view.selected_line_indices = {2}
    view.selected_word_indices = {(2, 0)}
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)

    view._handle_refine_selected_lines()

    assert seen["line_indices"] == [2]
    assert seen["selection_during_callback"] == ([], [])


def test_refine_selected_paragraphs_clears_selection_before_callback(monkeypatch):
    seen = {}

    def refine_paragraphs_callback(paragraph_indices: list[int]) -> bool:
        seen["paragraph_indices"] = paragraph_indices
        seen["selection_during_callback"] = sorted(view.selected_paragraph_indices)
        return True

    view = WordMatchView(refine_paragraphs_callback=refine_paragraphs_callback)
    view.selected_paragraph_indices = {0, 2}
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)

    view._handle_refine_selected_paragraphs()

    assert seen["paragraph_indices"] == [0, 2]
    assert seen["selection_during_callback"] == []


def test_refine_single_word_clears_selection_before_callback(monkeypatch):
    seen = {}

    def refine_words_callback(word_keys: list[tuple[int, int]]) -> bool:
        seen["word_keys"] = word_keys
        seen["selection_during_callback"] = (
            sorted(view.selected_line_indices),
            sorted(view.selected_word_indices),
        )
        return True

    view = WordMatchView(refine_words_callback=refine_words_callback)
    view.selected_line_indices = {4}
    view.selected_word_indices = {(4, 1)}
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)

    view._handle_refine_single_word(4, 1)

    assert seen["word_keys"] == [(4, 1)]
    assert seen["selection_during_callback"] == ([], [])


def test_toggle_bbox_fine_tune_opens_and_closes_editor(monkeypatch):
    view = WordMatchView(nudge_word_bbox_callback=lambda *_args: True)
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)
    rerendered: list[tuple[int, int]] = []
    monkeypatch.setattr(
        view,
        "_rerender_word_column",
        lambda line_index, word_index: rerendered.append((line_index, word_index)),
    )

    view._toggle_bbox_fine_tune(1, 2)
    assert (1, 2) in view._bbox_editor_open_keys

    view._toggle_bbox_fine_tune(1, 2)
    assert (1, 2) not in view._bbox_editor_open_keys
    assert rerendered == [(1, 2), (1, 2)]


def test_nudge_single_word_bbox_accumulates_pending_without_callback(monkeypatch):
    seen = {}

    def nudge_callback(
        line_index: int,
        word_index: int,
        left_delta: float,
        right_delta: float,
        top_delta: float,
        bottom_delta: float,
        refine_after: bool,
    ) -> bool:
        seen["args"] = (
            line_index,
            word_index,
            left_delta,
            right_delta,
            top_delta,
            bottom_delta,
            refine_after,
        )
        seen["selection_during_callback"] = (
            sorted(view.selected_line_indices),
            sorted(view.selected_word_indices),
        )
        return True

    view = WordMatchView(nudge_word_bbox_callback=nudge_callback)
    view._bbox_nudge_step_px = 5
    view.selected_line_indices = {2}
    view.selected_word_indices = {(2, 1)}
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)

    view._handle_nudge_single_word_bbox(
        2,
        1,
        left_units=-1.0,
        right_units=1.0,
        top_units=0.0,
        bottom_units=1.0,
    )

    assert seen == {}
    assert view._bbox_pending_deltas[(2, 1)] == (-5.0, 5.0, 0.0, 5.0)
    assert view.selected_line_indices == {2}
    assert view.selected_word_indices == {(2, 1)}


def test_apply_pending_single_word_bbox_clears_selection_before_callback(monkeypatch):
    seen = {}

    def nudge_callback(
        line_index: int,
        word_index: int,
        left_delta: float,
        right_delta: float,
        top_delta: float,
        bottom_delta: float,
        refine_after: bool,
    ) -> bool:
        seen["args"] = (
            line_index,
            word_index,
            left_delta,
            right_delta,
            top_delta,
            bottom_delta,
            refine_after,
        )
        seen["selection_during_callback"] = (
            sorted(view.selected_line_indices),
            sorted(view.selected_word_indices),
        )
        return True

    view = WordMatchView(nudge_word_bbox_callback=nudge_callback)
    view.selected_line_indices = {2}
    view.selected_word_indices = {(2, 1)}
    view._bbox_pending_deltas[(2, 1)] = (-5.0, 5.0, 0.0, 5.0)
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)

    view._apply_pending_single_word_bbox_nudge(2, 1)

    assert seen["args"] == (2, 1, -5.0, 5.0, 0.0, 5.0, True)
    assert seen["selection_during_callback"] == ([], [])
    assert (2, 1) not in view._bbox_pending_deltas


def test_apply_pending_single_word_bbox_without_refine(monkeypatch):
    seen = {}

    def nudge_callback(
        line_index: int,
        word_index: int,
        left_delta: float,
        right_delta: float,
        top_delta: float,
        bottom_delta: float,
        refine_after: bool,
    ) -> bool:
        seen["args"] = (
            line_index,
            word_index,
            left_delta,
            right_delta,
            top_delta,
            bottom_delta,
            refine_after,
        )
        return True

    notifications: list[tuple[str, str]] = []
    view = WordMatchView(nudge_word_bbox_callback=nudge_callback)
    view._bbox_pending_deltas[(2, 1)] = (-5.0, 5.0, 0.0, 5.0)
    monkeypatch.setattr(
        view,
        "_safe_notify",
        lambda message, type_="info": notifications.append((message, type_)),
    )

    view._apply_pending_single_word_bbox_nudge(2, 1, refine_after=False)

    assert seen["args"] == (2, 1, -5.0, 5.0, 0.0, 5.0, False)
    assert notifications[-1] == ("Applied bbox fine-tune edits", "positive")


def test_expand_then_refine_single_word_clears_selection_before_callback(monkeypatch):
    seen = {}

    def expand_then_refine_callback(word_keys: list[tuple[int, int]]) -> bool:
        seen["word_keys"] = word_keys
        seen["selection_during_callback"] = (
            sorted(view.selected_line_indices),
            sorted(view.selected_word_indices),
        )
        return True

    view = WordMatchView(
        expand_then_refine_words_callback=expand_then_refine_callback,
    )
    view.selected_line_indices = {4}
    view.selected_word_indices = {(4, 1)}
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)

    view._handle_expand_then_refine_single_word(4, 1)

    assert seen["word_keys"] == [(4, 1)]
    assert seen["selection_during_callback"] == ([], [])


def test_set_bbox_nudge_step_updates_step_and_refreshes(monkeypatch):
    view = WordMatchView()
    seen: list[tuple[int, int]] = []
    view._bbox_editor_open_keys = {(2, 1), (3, 0)}
    monkeypatch.setattr(
        view,
        "_rerender_word_column",
        lambda line_index, word_index: seen.append((line_index, word_index)),
    )

    view._set_bbox_nudge_step("10")

    assert view._bbox_nudge_step_px == 10
    assert seen == [(2, 1), (3, 0)]


def test_bbox_nudge_step_defaults_to_five_px():
    view = WordMatchView()

    assert view._bbox_nudge_step_px == 5


def test_display_signature_changes_when_word_bbox_changes():
    view = WordMatchView()
    bbox = SimpleNamespace(
        minX=10.0, minY=20.0, maxX=30.0, maxY=40.0, is_normalized=False
    )
    word_object = SimpleNamespace(bounding_box=bbox)
    word_match = SimpleNamespace(
        match_status=SimpleNamespace(value="exact"),
        ocr_text="token",
        ground_truth_text="token",
        fuzz_score=1.0,
        word_object=word_object,
    )
    line_match = SimpleNamespace(
        line_index=0,
        paragraph_index=0,
        overall_match_status=SimpleNamespace(value="exact"),
        exact_match_count=1,
        fuzzy_match_count=0,
        mismatch_count=0,
        unmatched_gt_count=0,
        unmatched_ocr_count=0,
        word_matches=[word_match],
    )
    view.view_model.line_matches = [line_match]

    before = view._compute_display_signature()
    bbox.maxX = 35.0
    after = view._compute_display_signature()

    assert before != after


def test_preview_bbox_for_word_applies_pending_deltas():
    view = WordMatchView()

    bbox = SimpleNamespace(
        minX=10.0,
        minY=20.0,
        maxX=30.0,
        maxY=40.0,
        is_normalized=False,
    )
    word_match = SimpleNamespace(word_object=SimpleNamespace(bounding_box=bbox))
    page_image = SimpleNamespace(shape=(100, 200, 3))

    preview_bbox = view._preview_bbox_for_word(
        word_match,
        page_image,
        line_index=1,
        word_index=2,
        bbox_preview_deltas=(3.0, 4.0, 5.0, 6.0),
    )

    assert preview_bbox == (7, 15, 34, 46)


def test_preview_bbox_for_word_handles_normalized_bbox():
    view = WordMatchView()

    bbox = SimpleNamespace(
        minX=0.10,
        minY=0.20,
        maxX=0.30,
        maxY=0.40,
        is_normalized=True,
    )
    word_match = SimpleNamespace(word_object=SimpleNamespace(bounding_box=bbox))
    page_image = SimpleNamespace(shape=(100, 200, 3))

    preview_bbox = view._preview_bbox_for_word(
        word_match,
        page_image,
        line_index=0,
        word_index=0,
        bbox_preview_deltas=(10.0, 0.0, 0.0, 10.0),
    )

    assert preview_bbox == (10, 20, 60, 50)


def test_word_gt_edit_invokes_callback(monkeypatch):
    seen = {}

    def update_callback(line_index: int, word_index: int, text: str) -> bool:
        seen["args"] = (line_index, word_index, text)
        return True

    view = WordMatchView(edit_word_ground_truth_callback=update_callback)
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)

    view._handle_word_gt_edit(1, 3, "new-gt")

    assert seen["args"] == (1, 3, "new-gt")


def test_word_gt_edit_warns_on_failure(monkeypatch):
    seen = {}

    view = WordMatchView(
        edit_word_ground_truth_callback=lambda _line, _word, _text: False
    )

    def notify(message: str, type_: str = "info"):
        seen["message"] = message
        seen["type"] = type_

    monkeypatch.setattr(view, "_safe_notify", notify)

    view._handle_word_gt_edit(0, 0, "x")

    assert seen["type"] == "warning"
    assert "Failed to update word ground truth" in seen["message"]


def test_word_attribute_edit_invokes_callback(monkeypatch):
    seen = {}

    def update_callback(
        line_index: int,
        word_index: int,
        italic: bool,
        small_caps: bool,
        blackletter: bool,
        left_footnote: bool,
        right_footnote: bool,
    ) -> bool:
        seen["args"] = (
            line_index,
            word_index,
            italic,
            small_caps,
            blackletter,
            left_footnote,
            right_footnote,
        )
        return True

    view = WordMatchView(set_word_attributes_callback=update_callback)
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)

    view._handle_set_word_attributes(1, 3, True, False, True, False, False)

    assert seen["args"] == (1, 3, True, False, True, False, False)


def test_word_attribute_edit_does_not_rerender_word_column(monkeypatch):
    view = WordMatchView(set_word_attributes_callback=lambda *_args: True)
    seen = {"rerendered": 0}
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        view,
        "_rerender_word_column",
        lambda *_args, **_kwargs: seen.__setitem__(
            "rerendered", seen["rerendered"] + 1
        ),
    )
    monkeypatch.setattr(
        view,
        "_set_word_style_button_states",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        view,
        "_apply_local_word_style_update",
        lambda **_kwargs: None,
    )

    view._handle_set_word_attributes(1, 3, True, False, True, False, False)

    assert seen["rerendered"] == 0


def test_toggle_word_attribute_uses_current_flags(monkeypatch):
    seen = {}
    view = WordMatchView()
    word_match = SimpleNamespace(
        word_object=SimpleNamespace(word_labels=["small_caps"])
    )
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        view, "_line_word_match_by_ocr_index", lambda *_args: word_match
    )
    monkeypatch.setattr(
        view,
        "_handle_set_word_attributes",
        lambda line_index, word_index, italic, small_caps, blackletter, left_footnote, right_footnote: (
            seen.setdefault(
                "args",
                (
                    line_index,
                    word_index,
                    italic,
                    small_caps,
                    blackletter,
                    left_footnote,
                    right_footnote,
                ),
            )
        ),
    )

    view._handle_toggle_word_attribute(2, 5, "small_caps")

    assert seen["args"] == (2, 5, False, False, False, False, False)


def test_word_attribute_tooltip_includes_active_flags():
    view = WordMatchView()
    word_match = SimpleNamespace(
        match_status=SimpleNamespace(value="mismatch"),
        fuzz_score=0.5,
        ocr_text="ocr",
        ground_truth_text="gt",
        word_object=SimpleNamespace(word_labels=["italic", "blackletter"]),
    )

    tooltip = view._create_word_tooltip(word_match)

    assert tooltip is not None
    assert "Attributes: italic, blackletter" in tooltip


def test_word_gt_input_width_prefers_current_value():
    view = WordMatchView()

    width = view._word_gt_input_width_chars("alphabet", "ocr")

    assert width == len("alphabet") + 3


def test_word_gt_input_width_falls_back_to_ocr_word():
    view = WordMatchView()

    width = view._word_gt_input_width_chars("", "token")

    assert width == len("token") + 3


def test_word_gt_input_width_has_minimum():
    view = WordMatchView()

    width = view._word_gt_input_width_chars("", "")

    assert width == 6


def test_word_gt_commit_uses_input_value_on_blur(monkeypatch):
    seen = {}
    view = WordMatchView(
        edit_word_ground_truth_callback=lambda line_index, word_index, text: (
            seen.setdefault("args", (line_index, word_index, text)) or True
        )
    )
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)

    input_stub = SimpleNamespace(value="updated-on-blur")
    view._commit_word_gt_input_change(2, 4, input_stub)

    assert seen["args"] == (2, 4, "updated-on-blur")


def test_next_word_gt_key_forward_ordering():
    view = WordMatchView()
    view._word_gt_input_refs = {
        (0, 0): object(),
        (0, 1): object(),
        (1, 0): object(),
    }

    assert view._next_word_gt_key((0, 0), reverse=False) == (0, 1)
    assert view._next_word_gt_key((0, 1), reverse=False) == (1, 0)
    assert view._next_word_gt_key((1, 0), reverse=False) is None


def test_next_word_gt_key_reverse_ordering():
    view = WordMatchView()
    view._word_gt_input_refs = {
        (0, 0): object(),
        (0, 1): object(),
        (1, 0): object(),
    }

    assert view._next_word_gt_key((1, 0), reverse=True) == (0, 1)
    assert view._next_word_gt_key((0, 1), reverse=True) == (0, 0)
    assert view._next_word_gt_key((0, 0), reverse=True) is None


def test_word_gt_keydown_ignores_non_tab(monkeypatch):
    view = WordMatchView()
    seen = {"called": False}

    monkeypatch.setattr(
        view,
        "_handle_word_gt_tab_navigation",
        lambda *_args, **_kwargs: seen.__setitem__("called", True),
    )

    event = SimpleNamespace(args={"key": "Enter", "shiftKey": False})
    view._handle_word_gt_keydown(event, (0, 0))

    assert seen["called"] is False


def test_word_gt_keydown_routes_tab_and_shift_tab(monkeypatch):
    view = WordMatchView()
    seen = []

    monkeypatch.setattr(
        view,
        "_handle_word_gt_tab_navigation",
        lambda key, reverse: seen.append((key, reverse)),
    )

    view._handle_word_gt_keydown(
        SimpleNamespace(args={"key": "Tab", "shiftKey": False}),
        (0, 1),
    )
    view._handle_word_gt_keydown(
        SimpleNamespace(args={"key": "Tab", "shiftKey": True}),
        (0, 1),
    )

    assert seen == [((0, 1), False), ((0, 1), True)]
