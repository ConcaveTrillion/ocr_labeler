"""Tests for WordMatchViewModel validation propagation."""

from __future__ import annotations

from types import SimpleNamespace

from pd_ocr_labeler.models.word_match_model import MatchStatus, WordMatch
from pd_ocr_labeler.viewmodels.project.word_match_view_model import WordMatchViewModel


def _word(text: str, gt: str = "", labels=None):
    """Build a minimal word-like object for _create_word_match."""
    return SimpleNamespace(
        text=text,
        ground_truth_text=gt,
        word_labels=labels or [],
    )


def test_create_word_match_propagates_validated_label():
    vm = WordMatchViewModel()
    word = _word("hello", gt="hello", labels=["validated"])

    wm = vm._create_word_match(0, word)

    assert wm is not None
    assert wm.is_validated is True


def test_create_word_match_defaults_to_not_validated():
    vm = WordMatchViewModel()
    word = _word("hello", gt="hello")

    wm = vm._create_word_match(0, word)

    assert wm is not None
    assert wm.is_validated is False


def test_create_word_match_validated_with_other_labels():
    vm = WordMatchViewModel()
    word = _word("hello", gt="hello", labels=["italic", "validated", "small_caps"])

    wm = vm._create_word_match(0, word)

    assert wm is not None
    assert wm.is_validated is True


def test_update_statistics_includes_validated_count():
    vm = WordMatchViewModel()

    wm_validated = WordMatch(
        ocr_text="a",
        ground_truth_text="a",
        match_status=MatchStatus.EXACT,
        word_index=0,
        is_validated=True,
    )
    wm_not = WordMatch(
        ocr_text="b",
        ground_truth_text="b",
        match_status=MatchStatus.EXACT,
        word_index=1,
        is_validated=False,
    )
    from pd_ocr_labeler.models.line_match_model import LineMatch

    vm.line_matches = [
        LineMatch(
            line_index=0,
            ocr_line_text="a b",
            ground_truth_line_text="a b",
            word_matches=[wm_validated, wm_not],
        ),
    ]
    vm._update_statistics()

    assert vm.validated_words_count == 1
    assert vm.total_words == 2
