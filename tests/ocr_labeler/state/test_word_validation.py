"""Tests for per-word validation state with rollup and persistence."""

from __future__ import annotations

from pd_book_tools.geometry.bounding_box import BoundingBox
from pd_book_tools.geometry.point import Point
from pd_book_tools.ocr.block import Block, BlockCategory, BlockChildType
from pd_book_tools.ocr.page import Page
from pd_book_tools.ocr.word import Word

from ocr_labeler.models.line_match_model import LineMatch
from ocr_labeler.models.user_page_persistence import (
    UserPageEnvelope,
    UserPagePayload,
    UserPageProvenance,
    UserPageSchema,
    UserPageSource,
)
from ocr_labeler.models.word_match_model import MatchStatus, WordMatch
from ocr_labeler.state.page_state import (
    PageState,
    WordValidationChangedEvent,
)


def _bbox(x1: int, y1: int, x2: int, y2: int) -> BoundingBox:
    return BoundingBox(Point(x1, y1), Point(x2, y2), is_normalized=False)


def _word(text: str, x: int, gt: str = "") -> Word:
    return Word(
        text=text,
        bounding_box=_bbox(x, 0, x + 10, 10),
        ocr_confidence=1.0,
        ground_truth_text=gt,
    )


def _line(words: list[Word], x: int) -> Block:
    return Block(
        items=words,
        bounding_box=_bbox(x, 0, x + 20, 10),
        child_type=BlockChildType.WORDS,
        block_category=BlockCategory.LINE,
    )


def _paragraph(lines: list[Block], y: int) -> Block:
    return Block(
        items=lines,
        bounding_box=_bbox(0, y, 80, y + 20),
        child_type=BlockChildType.BLOCKS,
        block_category=BlockCategory.PARAGRAPH,
    )


def _make_page(paragraphs: list[Block]) -> Page:
    return Page(items=paragraphs, width=100, height=100, page_index=0)


# ---------------------------------------------------------------------------
# toggle_word_validated
# ---------------------------------------------------------------------------


def test_toggle_word_validated_sets_and_clears_flag():
    """toggle_word_validated sets/clears the validated flag and notifies."""
    w = _word("hello", 0)
    line = _line([w], 0)
    para = _paragraph([line], 0)
    page = _make_page([para])

    state = PageState()
    state.current_page = page

    notified = []
    state.on_change = [lambda: notified.append(True)]

    # Toggle on
    assert state.toggle_word_validated(0, 0, 0) is True
    assert "validated" in w.word_labels
    assert len(notified) == 1

    # Toggle off
    assert state.toggle_word_validated(0, 0, 0) is True
    assert "validated" not in w.word_labels
    assert len(notified) == 2


def test_toggle_word_validated_emits_event():
    """toggle_word_validated emits WordValidationChangedEvent."""
    w = _word("hello", 0)
    line = _line([w], 0)
    para = _paragraph([line], 0)
    page = _make_page([para])

    state = PageState()
    state.current_page = page

    events: list[WordValidationChangedEvent] = []
    state.on_word_validation_change.subscribe(lambda e: events.append(e))

    state.toggle_word_validated(0, 0, 0)

    assert len(events) == 1
    assert events[0].is_validated is True
    assert events[0].line_index == 0
    assert events[0].word_index == 0


def test_toggle_word_validated_invalid_indices():
    """toggle_word_validated returns False for out-of-range indices."""
    w = _word("hello", 0)
    line = _line([w], 0)
    para = _paragraph([line], 0)
    page = _make_page([para])

    state = PageState()
    state.current_page = page

    assert state.toggle_word_validated(0, 5, 0) is False
    assert state.toggle_word_validated(0, 0, 5) is False


# ---------------------------------------------------------------------------
# Line rollup
# ---------------------------------------------------------------------------


def test_line_match_validation_rollup():
    """LineMatch computes partial and full validation from word matches."""
    wm1 = WordMatch(
        ocr_text="a",
        ground_truth_text="a",
        match_status=MatchStatus.EXACT,
        is_validated=True,
    )
    wm2 = WordMatch(
        ocr_text="b",
        ground_truth_text="b",
        match_status=MatchStatus.EXACT,
        is_validated=False,
    )
    wm3 = WordMatch(
        ocr_text="c",
        ground_truth_text="c",
        match_status=MatchStatus.EXACT,
        is_validated=True,
    )

    line_match = LineMatch(
        line_index=0,
        ocr_line_text="a b c",
        ground_truth_line_text="a b c",
        word_matches=[wm1, wm2, wm3],
    )

    assert line_match.validated_word_count == 2
    assert line_match.total_word_count == 3
    assert line_match.is_fully_validated is False

    # Now validate all
    wm2.is_validated = True
    assert line_match.validated_word_count == 3
    assert line_match.is_fully_validated is True


def test_line_match_empty_not_fully_validated():
    """An empty line is not considered fully validated."""
    line_match = LineMatch(
        line_index=0,
        ocr_line_text="",
        ground_truth_line_text="",
        word_matches=[],
    )
    assert line_match.is_fully_validated is False


# ---------------------------------------------------------------------------
# Persistence round-trip
# ---------------------------------------------------------------------------


def test_word_attributes_validated_round_trip():
    """validated flag survives serialize/deserialize via word_attributes."""
    envelope = UserPageEnvelope(
        schema=UserPageSchema(),
        provenance=UserPageProvenance(saved_at="2026-03-30T00:00:00Z"),
        source=UserPageSource(
            project_id="book-1",
            page_index=0,
            page_number=1,
            image_path="images/001.png",
        ),
        payload=UserPagePayload(
            page={"type": "Page", "items": []},
            word_attributes={
                "0:0": {
                    "italic": False,
                    "small_caps": False,
                    "blackletter": False,
                    "left_footnote": False,
                    "right_footnote": False,
                    "validated": True,
                },
                "0:1": {
                    "italic": True,
                    "small_caps": False,
                    "blackletter": False,
                    "left_footnote": False,
                    "right_footnote": False,
                    "validated": False,
                },
            },
        ),
    )

    restored = UserPageEnvelope.from_dict(envelope.to_dict())

    assert restored.payload.word_attributes is not None
    assert restored.payload.word_attributes["0:0"]["validated"] is True
    assert restored.payload.word_attributes["0:1"]["validated"] is False


# ---------------------------------------------------------------------------
# WordMatch model
# ---------------------------------------------------------------------------


def test_word_match_is_validated_field():
    """WordMatch models carry is_validated field."""
    wm = WordMatch(
        ocr_text="test",
        ground_truth_text="test",
        match_status=MatchStatus.EXACT,
        is_validated=True,
    )
    assert wm.is_validated is True

    wm_default = WordMatch(
        ocr_text="test",
        ground_truth_text="test",
        match_status=MatchStatus.EXACT,
    )
    assert wm_default.is_validated is False


# ---------------------------------------------------------------------------
# Structural edit clears validation
# ---------------------------------------------------------------------------


def test_structural_edit_clears_validation(monkeypatch):
    """Structural edits (via _finalize_structural_edit) clear all validation."""
    w1 = _word("hello", 0, gt="hello")
    w2 = _word("world", 20, gt="world")
    w1.word_labels = list(w1.word_labels) + ["validated"]
    w2.word_labels = list(w2.word_labels) + ["validated"]
    line = _line([w1, w2], 0)
    para = _paragraph([line], 0)
    page = _make_page([para])

    state = PageState()
    state.current_page = page

    # _finalize_structural_edit will try to rematch GT and refresh overlays.
    # Stub out the methods that require project context.
    monkeypatch.setattr(state, "_refresh_page_overlay_images", lambda page: None)
    monkeypatch.setattr(state, "_auto_save_to_cache", lambda: None)

    state._finalize_structural_edit(page, "test merge")

    assert "validated" not in w1.word_labels
    assert "validated" not in w2.word_labels


# ---------------------------------------------------------------------------
# Rematch GT: selective validation reset
# ---------------------------------------------------------------------------


def test_rematch_gt_preserves_validation_for_unchanged_words(monkeypatch):
    """rematch_ground_truth only clears validation for words whose GT changed."""
    w1 = _word("hello", 0, gt="hello")
    w2 = _word("world", 20, gt="world")
    w1.word_labels = list(w1.word_labels) + ["validated"]
    w2.word_labels = list(w2.word_labels) + ["validated"]
    line = _line([w1, w2], 0)
    para = _paragraph([line], 0)
    page = _make_page([para])

    state = PageState()
    state.current_page = page
    state._cached_page_index = 0

    # Simulate rematch that changes only w2's GT
    def mock_rematch(page_obj, operation):
        w2.ground_truth_text = "earth"

    monkeypatch.setattr(state, "_rematch_page_ground_truth", mock_rematch)
    monkeypatch.setattr(state, "_auto_save_to_cache", lambda: None)

    result = state.rematch_ground_truth()
    assert result is True

    # w1 unchanged GT -> keeps validation
    assert "validated" in w1.word_labels
    # w2 changed GT -> loses validation
    assert "validated" not in w2.word_labels
