"""Tests for LineMatch model including image cropping functionality."""

from unittest.mock import MagicMock

import numpy as np

from ocr_labeler.models.line_match_model import LineMatch
from ocr_labeler.models.word_match_model import MatchStatus, WordMatch


class TestLineMatch:
    """Tests for LineMatch dataclass."""

    def test_line_match_creation(self):
        """Test basic LineMatch creation."""
        word_matches = [
            WordMatch(
                ocr_text="hello",
                ground_truth_text="hello",
                match_status=MatchStatus.EXACT,
                fuzz_score=100.0,
            )
        ]

        line_match = LineMatch(
            line_index=0,
            ocr_line_text="hello",
            ground_truth_line_text="hello",
            word_matches=word_matches,
        )

        assert line_match.line_index == 0
        assert line_match.ocr_line_text == "hello"
        assert line_match.ground_truth_line_text == "hello"
        assert len(line_match.word_matches) == 1

    def test_line_match_with_page_image_and_line_object(self):
        """Test LineMatch with page_image and line_object."""
        page_image = np.zeros((100, 100, 3), dtype=np.uint8)
        line_object = MagicMock()

        line_match = LineMatch(
            line_index=0,
            ocr_line_text="test",
            ground_truth_line_text="test",
            word_matches=[],
            page_image=page_image,
            line_object=line_object,
        )

        assert line_match.page_image is page_image
        assert line_match.line_object is line_object

    def test_exact_match_count(self):
        """Test exact_match_count property."""
        word_matches = [
            WordMatch("hello", "hello", MatchStatus.EXACT),
            WordMatch("world", "world", MatchStatus.EXACT),
            WordMatch("test", "tests", MatchStatus.FUZZY),
        ]

        line_match = LineMatch(
            line_index=0,
            ocr_line_text="hello world test",
            ground_truth_line_text="hello world tests",
            word_matches=word_matches,
        )

        assert line_match.exact_match_count == 2

    def test_fuzzy_match_count(self):
        """Test fuzzy_match_count property."""
        word_matches = [
            WordMatch("hello", "hello", MatchStatus.EXACT),
            WordMatch("wrld", "world", MatchStatus.FUZZY),
            WordMatch("tst", "test", MatchStatus.FUZZY),
        ]

        line_match = LineMatch(
            line_index=0,
            ocr_line_text="hello wrld tst",
            ground_truth_line_text="hello world test",
            word_matches=word_matches,
        )

        assert line_match.fuzzy_match_count == 2

    def test_mismatch_count(self):
        """Test mismatch_count property."""
        word_matches = [
            WordMatch("hello", "hello", MatchStatus.EXACT),
            WordMatch("bad", "good", MatchStatus.MISMATCH),
            WordMatch("wrong", "right", MatchStatus.MISMATCH),
        ]

        line_match = LineMatch(
            line_index=0,
            ocr_line_text="hello bad wrong",
            ground_truth_line_text="hello good right",
            word_matches=word_matches,
        )

        assert line_match.mismatch_count == 2

    def test_unmatched_counts(self):
        """Test unmatched_gt_count and unmatched_ocr_count."""
        word_matches = [
            WordMatch("hello", "hello", MatchStatus.EXACT),
            WordMatch("", "extra", MatchStatus.UNMATCHED_GT),
            WordMatch("orphan", "", MatchStatus.UNMATCHED_OCR),
        ]

        line_match = LineMatch(
            line_index=0,
            ocr_line_text="hello orphan",
            ground_truth_line_text="hello extra",
            word_matches=word_matches,
        )

        assert line_match.unmatched_gt_count == 1
        assert line_match.unmatched_ocr_count == 1

    def test_overall_match_status_exact(self):
        """Test overall_match_status when all words match exactly."""
        word_matches = [
            WordMatch("hello", "hello", MatchStatus.EXACT),
            WordMatch("world", "world", MatchStatus.EXACT),
        ]

        line_match = LineMatch(
            line_index=0,
            ocr_line_text="hello world",
            ground_truth_line_text="hello world",
            word_matches=word_matches,
        )

        assert line_match.overall_match_status == MatchStatus.EXACT

    def test_overall_match_status_fuzzy(self):
        """Test overall_match_status when some words match fuzzily."""
        word_matches = [
            WordMatch("hello", "hello", MatchStatus.EXACT),
            WordMatch("wrld", "world", MatchStatus.FUZZY),
        ]

        line_match = LineMatch(
            line_index=0,
            ocr_line_text="hello wrld",
            ground_truth_line_text="hello world",
            word_matches=word_matches,
        )

        assert line_match.overall_match_status == MatchStatus.FUZZY

    def test_overall_match_status_mismatch(self):
        """Test overall_match_status when words don't match."""
        word_matches = [
            WordMatch("bad", "good", MatchStatus.MISMATCH),
            WordMatch("wrong", "right", MatchStatus.MISMATCH),
        ]

        line_match = LineMatch(
            line_index=0,
            ocr_line_text="bad wrong",
            ground_truth_line_text="good right",
            word_matches=word_matches,
        )

        assert line_match.overall_match_status == MatchStatus.MISMATCH

    def test_overall_match_status_empty(self):
        """Test overall_match_status with no word matches."""
        line_match = LineMatch(
            line_index=0,
            ocr_line_text="",
            ground_truth_line_text="",
            word_matches=[],
        )

        assert line_match.overall_match_status == MatchStatus.MISMATCH


class TestLineMatchImageCropping:
    """Tests for LineMatch image cropping functionality."""

    def test_get_cropped_image_no_line_object(self):
        """Test get_cropped_image returns None when line_object is missing."""
        page_image = np.zeros((100, 100, 3), dtype=np.uint8)

        line_match = LineMatch(
            line_index=0,
            ocr_line_text="test",
            ground_truth_line_text="test",
            word_matches=[],
            page_image=page_image,
            line_object=None,
        )

        result = line_match.get_cropped_image()
        assert result is None

    def test_get_cropped_image_no_page_image(self):
        """Test get_cropped_image returns None when page_image is missing."""
        line_object = MagicMock()

        line_match = LineMatch(
            line_index=0,
            ocr_line_text="test",
            ground_truth_line_text="test",
            word_matches=[],
            page_image=None,
            line_object=line_object,
        )

        result = line_match.get_cropped_image()
        assert result is None

    def test_get_cropped_image_no_bbox(self):
        """Test get_cropped_image returns None when bounding_box is missing."""
        page_image = np.zeros((100, 100, 3), dtype=np.uint8)
        line_object = MagicMock()
        line_object.bounding_box = None

        line_match = LineMatch(
            line_index=0,
            ocr_line_text="test",
            ground_truth_line_text="test",
            word_matches=[],
            page_image=page_image,
            line_object=line_object,
        )

        result = line_match.get_cropped_image()
        assert result is None

    def test_get_cropped_image_normalized_bbox(self):
        """Test get_cropped_image with normalized bounding box."""
        # Create a 100x100 test image with white rectangle in middle
        page_image = np.zeros((100, 100, 3), dtype=np.uint8)
        page_image[20:40, 10:90] = 255  # White rectangle

        # Create mock bounding box (normalized coordinates)
        bbox = MagicMock()
        bbox.is_normalized = True
        bbox.minX = 0.1
        bbox.minY = 0.2
        bbox.maxX = 0.9
        bbox.maxY = 0.4

        # Mock the scale method to return pixel bbox
        pixel_bbox = MagicMock()
        pixel_bbox.minX = 10.0
        pixel_bbox.minY = 20.0
        pixel_bbox.maxX = 90.0
        pixel_bbox.maxY = 40.0
        bbox.scale.return_value = pixel_bbox

        line_object = MagicMock()
        line_object.bounding_box = bbox

        line_match = LineMatch(
            line_index=0,
            ocr_line_text="test",
            ground_truth_line_text="test",
            word_matches=[],
            page_image=page_image,
            line_object=line_object,
        )

        result = line_match.get_cropped_image()

        # Verify scale was called with image dimensions
        bbox.scale.assert_called_once_with(100, 100)

        # Verify cropped image has correct shape
        assert result is not None
        assert result.shape == (20, 80, 3)  # height=40-20, width=90-10

    def test_get_cropped_image_pixel_bbox(self):
        """Test get_cropped_image with pixel bounding box."""
        # Create a 200x200 test image with white rectangle
        page_image = np.zeros((200, 200, 3), dtype=np.uint8)
        page_image[50:100, 20:180] = 255  # White rectangle

        # Create mock bounding box (pixel coordinates)
        bbox = MagicMock()
        bbox.is_normalized = False
        bbox.minX = 20.0
        bbox.minY = 50.0
        bbox.maxX = 180.0
        bbox.maxY = 100.0

        line_object = MagicMock()
        line_object.bounding_box = bbox

        line_match = LineMatch(
            line_index=0,
            ocr_line_text="test line",
            ground_truth_line_text="test line",
            word_matches=[],
            page_image=page_image,
            line_object=line_object,
        )

        result = line_match.get_cropped_image()

        # Verify cropped image has correct shape
        assert result is not None
        assert result.shape == (50, 160, 3)  # height=100-50, width=180-20

        # Verify content is white
        assert np.all(result == 255)

    def test_get_cropped_image_with_custom_page_image(self):
        """Test get_cropped_image with custom page_image parameter."""
        # Create two different images
        stored_image = np.zeros((100, 100, 3), dtype=np.uint8)
        custom_image = np.ones((100, 100, 3), dtype=np.uint8) * 127

        bbox = MagicMock()
        bbox.is_normalized = False
        bbox.minX = 10.0
        bbox.minY = 10.0
        bbox.maxX = 50.0
        bbox.maxY = 50.0

        line_object = MagicMock()
        line_object.bounding_box = bbox

        line_match = LineMatch(
            line_index=0,
            ocr_line_text="test",
            ground_truth_line_text="test",
            word_matches=[],
            page_image=stored_image,
            line_object=line_object,
        )

        # Call with custom image
        result = line_match.get_cropped_image(page_image=custom_image)

        # Verify it used custom image (gray values, not black)
        assert result is not None
        assert np.all(result == 127)

    def test_get_cropped_image_clamping(self):
        """Test get_cropped_image clamps coordinates to image bounds."""
        page_image = np.zeros((100, 100, 3), dtype=np.uint8)

        # Bbox that extends beyond image bounds
        bbox = MagicMock()
        bbox.is_normalized = False
        bbox.minX = -10.0
        bbox.minY = -5.0
        bbox.maxX = 110.0
        bbox.maxY = 105.0

        line_object = MagicMock()
        line_object.bounding_box = bbox

        line_match = LineMatch(
            line_index=0,
            ocr_line_text="test",
            ground_truth_line_text="test",
            word_matches=[],
            page_image=page_image,
            line_object=line_object,
        )

        result = line_match.get_cropped_image()

        # Should clamp to [0, 0] to [100, 100]
        assert result is not None
        assert result.shape == (100, 100, 3)

    def test_get_cropped_image_invalid_bbox(self):
        """Test get_cropped_image returns None for invalid bbox (x1 >= x2)."""
        page_image = np.zeros((100, 100, 3), dtype=np.uint8)

        # Invalid bbox where min > max
        bbox = MagicMock()
        bbox.is_normalized = False
        bbox.minX = 90.0
        bbox.minY = 50.0
        bbox.maxX = 10.0  # maxX < minX (invalid)
        bbox.maxY = 60.0

        line_object = MagicMock()
        line_object.bounding_box = bbox

        line_match = LineMatch(
            line_index=0,
            ocr_line_text="test",
            ground_truth_line_text="test",
            word_matches=[],
            page_image=page_image,
            line_object=line_object,
        )

        result = line_match.get_cropped_image()
        assert result is None

    def test_equality_with_line_object(self):
        """Test equality uses identity check for line_object."""
        line_obj1 = MagicMock()
        line_obj2 = MagicMock()

        line1 = LineMatch(
            line_index=0,
            ocr_line_text="test",
            ground_truth_line_text="test",
            word_matches=[],
            line_object=line_obj1,
        )

        line2 = LineMatch(
            line_index=0,
            ocr_line_text="test",
            ground_truth_line_text="test",
            word_matches=[],
            line_object=line_obj1,  # Same object
        )

        line3 = LineMatch(
            line_index=0,
            ocr_line_text="test",
            ground_truth_line_text="test",
            word_matches=[],
            line_object=line_obj2,  # Different object
        )

        assert line1 == line2  # Same line_object
        assert line1 != line3  # Different line_object

    def test_hash_excludes_line_object(self):
        """Test that line_object is excluded from hash."""
        line_obj1 = MagicMock()
        line_obj2 = MagicMock()

        line1 = LineMatch(
            line_index=0,
            ocr_line_text="test",
            ground_truth_line_text="test",
            word_matches=[],
            line_object=line_obj1,
        )

        line2 = LineMatch(
            line_index=0,
            ocr_line_text="test",
            ground_truth_line_text="test",
            word_matches=[],
            line_object=line_obj2,
        )

        # Hashes should be equal even with different line_objects
        assert hash(line1) == hash(line2)
