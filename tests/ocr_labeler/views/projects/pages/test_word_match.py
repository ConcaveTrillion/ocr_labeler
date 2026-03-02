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
