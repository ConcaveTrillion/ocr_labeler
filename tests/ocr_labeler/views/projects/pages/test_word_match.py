from __future__ import annotations

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
