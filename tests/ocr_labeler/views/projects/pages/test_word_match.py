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
    monkeypatch.setattr(view, "_update_lines_display", lambda: None)

    view._toggle_bbox_fine_tune(1, 2)
    assert (1, 2) in view._bbox_editor_open_keys

    view._toggle_bbox_fine_tune(1, 2)
    assert (1, 2) not in view._bbox_editor_open_keys


def test_nudge_single_word_bbox_accumulates_pending_without_callback(monkeypatch):
    seen = {}

    def nudge_callback(
        line_index: int,
        word_index: int,
        left_delta: float,
        right_delta: float,
        top_delta: float,
        bottom_delta: float,
    ) -> bool:
        seen["args"] = (
            line_index,
            word_index,
            left_delta,
            right_delta,
            top_delta,
            bottom_delta,
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
    ) -> bool:
        seen["args"] = (
            line_index,
            word_index,
            left_delta,
            right_delta,
            top_delta,
            bottom_delta,
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

    assert seen["args"] == (2, 1, -5.0, 5.0, 0.0, 5.0)
    assert seen["selection_during_callback"] == ([], [])
    assert (2, 1) not in view._bbox_pending_deltas


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
    seen = {"refresh": 0}
    monkeypatch.setattr(
        view,
        "_update_lines_display",
        lambda: seen.__setitem__("refresh", seen["refresh"] + 1),
    )

    view._set_bbox_nudge_step("10")

    assert view._bbox_nudge_step_px == 10
    assert seen["refresh"] == 1


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
    view._bbox_pending_deltas[(1, 2)] = (3.0, 4.0, 5.0, 6.0)

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
    )

    assert preview_bbox == (7, 15, 34, 46)


def test_preview_bbox_for_word_handles_normalized_bbox():
    view = WordMatchView()
    view._bbox_pending_deltas[(0, 0)] = (10.0, 0.0, 0.0, 10.0)

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
