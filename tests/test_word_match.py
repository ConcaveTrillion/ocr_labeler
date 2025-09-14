"""Tests for word match functionality and GT→OCR copy operations."""

from unittest.mock import Mock

from ocr_labeler.state.project_state import ProjectState
from ocr_labeler.views.word_match import WordMatchView


class TestGTToOCRCopy:
    """Test the GT→OCR copy functionality."""

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

        # Create project state and mock the current_page method
        project_state = ProjectState()
        project_state.current_page = Mock(return_value=mock_page)

        # Test the copy function
        result = project_state.copy_ground_truth_to_ocr(0)

        # Verify results
        assert result is True
        assert mock_word1.text == "correct"
        assert mock_word2.text == "right"

    def test_copy_ground_truth_to_ocr_no_page(self):
        """Test GT→OCR copy with no current page."""
        project_state = ProjectState()
        project_state.current_page = Mock(return_value=None)

        result = project_state.copy_ground_truth_to_ocr(0)

        assert result is False

    def test_copy_ground_truth_to_ocr_invalid_line_index(self):
        """Test GT→OCR copy with invalid line index."""
        mock_page = Mock()
        mock_page.lines = []

        project_state = ProjectState()
        project_state.current_page = Mock(return_value=mock_page)

        result = project_state.copy_ground_truth_to_ocr(0)

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

        project_state = ProjectState()
        project_state.current_page = Mock(return_value=mock_page)

        result = project_state.copy_ground_truth_to_ocr(0)

        # Should return False since no GT text was copied
        assert result is False
        assert mock_word.text == "original"  # Unchanged

    def test_word_match_view_with_callback(self):
        """Test WordMatchView initialization with callback."""
        mock_callback = Mock(return_value=True)
        view = WordMatchView(copy_gt_to_ocr_callback=mock_callback)

        assert view.copy_gt_to_ocr_callback == mock_callback

    def test_word_match_view_handle_copy_success(self):
        """Test WordMatchView handle copy with successful callback."""
        from unittest.mock import patch

        mock_callback = Mock(return_value=True)
        view = WordMatchView(copy_gt_to_ocr_callback=mock_callback)

        # Mock ui.notify to avoid NiceGUI dependency in test
        with patch("ocr_labeler.views.word_match.ui.notify") as mock_notify:
            view._handle_copy_gt_to_ocr(0)

            mock_callback.assert_called_once_with(0)
            mock_notify.assert_called_once_with(
                "Copied ground truth to OCR text for line 1", type="positive"
            )

    def test_word_match_view_handle_copy_no_callback(self):
        """Test WordMatchView handle copy with no callback."""
        from unittest.mock import patch

        view = WordMatchView(copy_gt_to_ocr_callback=None)

        with patch("ocr_labeler.views.word_match.ui.notify") as mock_notify:
            view._handle_copy_gt_to_ocr(0)

            mock_notify.assert_called_once_with(
                "Copy function not available", type="warning"
            )
