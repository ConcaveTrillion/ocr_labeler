"""Tests for line operations functionality."""

from unittest.mock import Mock

from ocr_labeler.operations.ocr.line_operations import LineOperations


class TestLineOperations:
    """Test the LineOperations class functionality."""

    def test_copy_ground_truth_to_ocr_success(self):
        """Test successful GT→OCR copy with valid data."""
        # Create mock page and line structure
        mock_word1 = Mock()
        mock_word1.text = "incorrect"
        mock_word1.ground_truth_text = "correct"

        mock_word2 = Mock()
        mock_word2.text = "wrong"
        mock_word2.ground_truth_text = "right"

        mock_line = Mock()
        mock_line.words = [mock_word1, mock_word2]

        mock_page = Mock()
        mock_page.lines = [mock_line]

        # Test the copy function
        line_ops = LineOperations()
        result = line_ops.copy_ground_truth_to_ocr(mock_page, 0)

        # Verify results
        assert result is True
        assert mock_word1.text == "correct"
        assert mock_word2.text == "right"

    def test_copy_ground_truth_to_ocr_no_page(self):
        """Test GT→OCR copy with no page."""
        line_ops = LineOperations()
        result = line_ops.copy_ground_truth_to_ocr(None, 0)

        assert result is False

    def test_copy_ground_truth_to_ocr_invalid_line_index(self):
        """Test GT→OCR copy with invalid line index."""
        mock_page = Mock()
        mock_page.lines = []

        line_ops = LineOperations()
        result = line_ops.copy_ground_truth_to_ocr(mock_page, 0)

        assert result is False

    def test_copy_ground_truth_to_ocr_no_ground_truth(self):
        """Test GT→OCR copy with no ground truth text."""
        mock_word = Mock()
        mock_word.text = "original"
        mock_word.ground_truth_text = ""

        mock_line = Mock()
        mock_line.words = [mock_word]

        mock_page = Mock()
        mock_page.lines = [mock_line]

        line_ops = LineOperations()
        result = line_ops.copy_ground_truth_to_ocr(mock_page, 0)

        # Should return False since no GT text was copied
        assert result is False
        assert mock_word.text == "original"  # Unchanged

    def test_copy_ground_truth_to_ocr_empty_words(self):
        """Test GT→OCR copy with empty words list."""
        mock_line = Mock()
        mock_line.words = []

        mock_page = Mock()
        mock_page.lines = [mock_line]

        line_ops = LineOperations()
        result = line_ops.copy_ground_truth_to_ocr(mock_page, 0)

        assert result is False

    def test_copy_ocr_to_ground_truth_success(self):
        """Test successful OCR→GT copy with valid data."""
        mock_word1 = Mock()
        mock_word1.text = "correct"
        mock_word1.ground_truth_text = "incorrect"

        mock_word2 = Mock()
        mock_word2.text = "right"
        mock_word2.ground_truth_text = "wrong"

        mock_line = Mock()
        mock_line.words = [mock_word1, mock_word2]

        mock_page = Mock()
        mock_page.lines = [mock_line]

        line_ops = LineOperations()
        result = line_ops.copy_ocr_to_ground_truth(mock_page, 0)

        # Verify results
        assert result is True
        assert mock_word1.ground_truth_text == "correct"
        assert mock_word2.ground_truth_text == "right"

    def test_copy_ocr_to_ground_truth_no_page(self):
        """Test OCR→GT copy with no page."""
        line_ops = LineOperations()
        result = line_ops.copy_ocr_to_ground_truth(None, 0)

        assert result is False

    def test_copy_ocr_to_ground_truth_no_ocr_text(self):
        """Test OCR→GT copy with no OCR text."""
        mock_word = Mock()
        mock_word.text = ""
        mock_word.ground_truth_text = "original"

        mock_line = Mock()
        mock_line.words = [mock_word]

        mock_page = Mock()
        mock_page.lines = [mock_line]

        line_ops = LineOperations()
        result = line_ops.copy_ocr_to_ground_truth(mock_page, 0)

        # Should return False since no OCR text was copied
        assert result is False

    def test_clear_ground_truth_for_line_success(self):
        """Test successful ground truth clearing."""
        mock_word1 = Mock()
        mock_word1.ground_truth_text = "text1"

        mock_word2 = Mock()
        mock_word2.ground_truth_text = "text2"

        mock_line = Mock()
        mock_line.words = [mock_word1, mock_word2]

        mock_page = Mock()
        mock_page.lines = [mock_line]

        line_ops = LineOperations()
        result = line_ops.clear_ground_truth_for_line(mock_page, 0)

        # Verify results
        assert result is True
        assert mock_word1.ground_truth_text == ""
        assert mock_word2.ground_truth_text == ""

    def test_clear_ground_truth_for_line_no_ground_truth(self):
        """Test ground truth clearing with no existing ground truth."""
        mock_word = Mock()
        mock_word.ground_truth_text = ""

        mock_line = Mock()
        mock_line.words = [mock_word]

        mock_page = Mock()
        mock_page.lines = [mock_line]

        line_ops = LineOperations()
        result = line_ops.clear_ground_truth_for_line(mock_page, 0)

        # Should return False since no GT text was cleared
        assert result is False

    def test_validate_line_consistency_success(self):
        """Test line validation with mixed matches and mismatches."""
        mock_word1 = Mock()
        mock_word1.text = "same"
        mock_word1.ground_truth_text = "same"

        mock_word2 = Mock()
        mock_word2.text = "different"
        mock_word2.ground_truth_text = "changed"

        mock_word3 = Mock()
        mock_word3.text = "no_gt"
        mock_word3.ground_truth_text = ""

        mock_line = Mock()
        mock_line.words = [mock_word1, mock_word2, mock_word3]

        mock_page = Mock()
        mock_page.lines = [mock_line]

        line_ops = LineOperations()
        result = line_ops.validate_line_consistency(mock_page, 0)

        # Verify results
        assert result["valid"] is True
        assert result["words"] == 3
        assert result["with_gt"] == 2  # Only word1 and word2 have GT text
        assert result["matches"] == 1  # Only word1 matches
        assert result["mismatches"] == 1  # Only word2 mismatches
        assert result["accuracy"] == 0.5  # 1 match out of 2 with GT
        assert len(result["mismatch_details"]) == 1
        assert result["mismatch_details"][0]["word_index"] == 1
        assert result["mismatch_details"][0]["ocr_text"] == "different"
        assert result["mismatch_details"][0]["gt_text"] == "changed"

    def test_validate_line_consistency_no_page(self):
        """Test line validation with no page."""
        line_ops = LineOperations()
        result = line_ops.validate_line_consistency(None, 0)

        assert result["valid"] is False
        assert "No page provided" in result["error"]

    def test_validate_line_consistency_invalid_index(self):
        """Test line validation with invalid line index."""
        mock_page = Mock()
        mock_page.lines = []

        line_ops = LineOperations()
        result = line_ops.validate_line_consistency(mock_page, 0)

        assert result["valid"] is False
        assert "out of range" in result["error"]

    def test_validate_line_consistency_empty_line(self):
        """Test line validation with empty line."""
        mock_line = Mock()
        mock_line.words = []

        mock_page = Mock()
        mock_page.lines = [mock_line]

        line_ops = LineOperations()
        result = line_ops.validate_line_consistency(mock_page, 0)

        assert result["valid"] is True
        assert result["words"] == 0
        assert result["with_gt"] == 0
        assert result["matches"] == 0
        assert result["mismatches"] == 0
