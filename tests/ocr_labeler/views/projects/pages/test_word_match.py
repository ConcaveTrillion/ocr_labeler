from __future__ import annotations

from types import SimpleNamespace

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


def test_split_paragraph_by_selected_lines_uses_effective_line_selection(monkeypatch):
    seen = {}
    view = WordMatchView()
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


def test_split_paragraph_by_selected_lines_restores_selection_on_failure(monkeypatch):
    view = WordMatchView()
    view.selected_line_indices = {2}
    view.selected_word_indices = {(2, 0)}
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)

    view.split_paragraph_with_selected_lines_callback = lambda _indices: False
    view._handle_split_paragraph_by_selected_lines()

    assert view.selected_line_indices == {2}
    assert view.selected_word_indices == {(2, 0)}


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


def test_merge_word_right_restores_selection_on_failure(monkeypatch):
    view = WordMatchView()
    view.selected_line_indices = {4}
    view.selected_word_indices = {(4, 0)}
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)

    view.merge_word_right_callback = lambda _line_index, _word_index: False
    view._handle_merge_word_right(4, 0)

    assert view.selected_line_indices == {4}
    assert view.selected_word_indices == {(4, 0)}


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


def test_delete_single_word_restores_selection_on_failure(monkeypatch):
    view = WordMatchView()
    view.selected_line_indices = {5}
    view.selected_word_indices = {(5, 0)}
    monkeypatch.setattr(view, "_safe_notify", lambda *args, **kwargs: None)

    view.delete_words_callback = lambda _word_keys: False
    view._handle_delete_single_word(5, 0)

    assert view.selected_line_indices == {5}
    assert view.selected_word_indices == {(5, 0)}
