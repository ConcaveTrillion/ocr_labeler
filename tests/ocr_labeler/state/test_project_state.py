from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from ocr_labeler.state import project_state as project_state_module
from ocr_labeler.state.project_state import ProjectState


def test_project_state_initialization():
    """Test that ProjectState initializes correctly."""
    state = ProjectState()
    assert state.project is not None
    assert state.current_page_index == 0
    assert state.current_page() is None  # No pages loaded yet
    assert state.is_project_loading is False
    assert state.on_change == []


def test_project_state_notification():
    """Test that ProjectState notification system works."""
    state = ProjectState()
    calls = []
    state.on_change.append(lambda: calls.append("notified"))
    state.notify()
    assert calls == ["notified"]


def test_project_state_delegation():
    """Test that ProjectState methods delegate correctly."""
    state = ProjectState()

    # Test navigation methods exist and can be called
    # (These won't do much without a loaded project, but they shouldn't crash)
    state.next_page()
    state.prev_page()
    state.goto_page_number(1)

    # Test current page returns None when no project loaded
    assert state.current_page() is None


def test_load_current_page_success(tmp_path):
    """Test load_current_page when file exists and loads successfully."""
    # Create a valid JSON file
    save_dir = tmp_path / "save_test"
    save_dir.mkdir(parents=True)

    json_file = save_dir / "test_project_001.json"
    json_data = {
        "source_lib": "doctr-pgdp-labeled",
        "source_path": "test_image.png",
        "pages": [{"type": "Page", "items": [], "width": 800, "height": 600}],
    }

    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(json_data, f)

    # Mock Page.from_dict and the page operations
    with patch("ocr_labeler.operations.ocr.page_operations.Page") as mock_page_class:
        mock_page = Mock()
        mock_page_class.from_dict.return_value = mock_page

        # Set up project state
        state = ProjectState()
        state.project_root = Path("/test/project")
        state.current_page_index = 0

        # Mock the project.pages list
        mock_project = Mock()
        mock_project.pages = [None]  # Initially None, should be replaced
        state.project = mock_project

        # Test load_current_page
        result = state.load_current_page(
            save_directory=str(save_dir),
            project_id="test_project",
        )

        assert result is True
        assert state.project.pages[0] is mock_page
        mock_page_class.from_dict.assert_called_once_with(json_data["pages"][0])


def test_load_current_page_no_saved_file(tmp_path):
    """Test load_current_page when no saved file exists."""
    save_dir = tmp_path / "save_test"
    save_dir.mkdir(parents=True)

    state = ProjectState()
    state.project_root = Path("/test/project")
    state.current_page_index = 0

    result = state.load_current_page(
        save_directory=str(save_dir),
        project_id="test_project",
    )

    assert result is False


def test_load_current_page_invalid_index(tmp_path):
    """Test load_current_page when current_page_index is out of range."""
    save_dir = tmp_path / "save_test"
    save_dir.mkdir(parents=True)

    state = ProjectState()
    state.project_root = Path("/test/project")
    state.current_page_index = 5  # Out of range

    # Mock project with only 3 pages
    mock_project = Mock()
    mock_project.pages = [Mock(), Mock(), Mock()]
    state.project = mock_project

    result = state.load_current_page(
        save_directory=str(save_dir),
        project_id="test_project",
    )

    assert result is False


def test_load_current_page_negative_index(tmp_path):
    """Test load_current_page when current_page_index is negative."""
    save_dir = tmp_path / "save_test"
    save_dir.mkdir(parents=True)

    state = ProjectState()
    state.project_root = Path("/test/project")
    state.current_page_index = -1

    result = state.load_current_page(
        save_directory=str(save_dir),
        project_id="test_project",
    )

    assert result is False


def test_load_current_page_generates_project_id_from_root(tmp_path):
    """Test that project ID is generated from project_root when not provided."""
    save_dir = tmp_path / "save_test"
    save_dir.mkdir(parents=True)

    # Create valid JSON file with expected filename
    json_file = save_dir / "my_book_project_001.json"
    json_data = {
        "source_lib": "doctr-pgdp-labeled",
        "source_path": "test_image.png",
        "pages": [{"type": "Page", "items": []}],
    }

    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(json_data, f)

    # Mock Page.from_dict
    with patch("ocr_labeler.operations.ocr.page_operations.Page") as mock_page_class:
        mock_page = Mock()
        mock_page_class.from_dict.return_value = mock_page

        # Set up project state with specific project root
        state = ProjectState()
        state.project_root = Path("my_book_project")
        state.current_page_index = 0

        # Mock the project.pages list
        mock_project = Mock()
        mock_project.pages = [None]
        state.project = mock_project

        # Test without providing project_id
        result = state.load_current_page(
            save_directory=str(save_dir),
            # No project_id provided
        )

        assert result is True
        assert state.project.pages[0] is mock_page


@pytest.mark.asyncio
async def test_load_project_schedules_initial_preload(monkeypatch, tmp_path):
    """Project load should always schedule initial page preload when images exist."""
    image_path = tmp_path / "001.png"
    image_path.write_bytes(b"img")

    state = ProjectState()
    navigate_calls: list[int] = []

    async def fake_io_bound(func, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr(project_state_module.run, "io_bound", fake_io_bound)

    monkeypatch.setattr(
        project_state_module.ProjectOperations,
        "scan_project_directory",
        lambda _self, _directory: [image_path],
    )

    async def fake_load_ground_truth_map(_directory):
        return {}

    monkeypatch.setattr(state, "load_ground_truth_map", fake_load_ground_truth_map)

    monkeypatch.setattr(
        project_state_module.ProjectOperations,
        "create_project",
        lambda _self, _directory, images, _ground_truth_map: Mock(
            image_paths=images,
            pages=[None for _ in images],
            page_count=lambda: len(images),
            ground_truth_map={},
        ),
    )

    monkeypatch.setattr(
        state,
        "_navigate",
        lambda: navigate_calls.append(state.current_page_index),
    )

    await state.load_project(tmp_path)

    assert navigate_calls == [0]


def test_save_current_page_updates_source_label(tmp_path):
    """Test that saving the current page updates its source label to LABELED."""
    from pd_book_tools.ocr.page import Page

    from ocr_labeler.models.project import Project

    # 1. Setup project state with one page
    state = ProjectState()
    project_root = tmp_path / "project"
    project_root.mkdir()
    state.project_root = project_root

    # Create a dummy image
    img_path = project_root / "page_001.png"
    img_path.touch()

    # Initialize project with one page
    state.project = Project(pages=[None], image_paths=[img_path])
    state.current_page_index = 0

    # Define mock page with a proper to_dict
    mock_page = Mock(spec=Page)
    mock_page.index = 0
    mock_page.image_path = img_path
    # We use a real attribute here since it's checked by TextOperations.get_page_source_text
    mock_page.page_source = "ocr"
    mock_page.to_dict.return_value = {
        "type": "page",
        "items": [],
        "width": 100,
        "height": 100,
        "page_index": 0,
    }

    # Mock PageOperations globally at its source
    def mock_save_page(*args, **kwargs):
        save_directory = kwargs.get("save_directory", args[3] if len(args) > 3 else "")
        if "cache" in str(save_directory):
            return False  # Prevent auto-saving to cache
        return True  # Allow user saves

    with (
        patch(
            "ocr_labeler.operations.ocr.page_operations.PageOperations.save_page",
            side_effect=mock_save_page,
        ),
        patch(
            "ocr_labeler.operations.ocr.page_operations.PageOperations.load_page",
            side_effect=lambda *args, **kwargs: None,
        ),
        patch.object(state.page_ops, "page_parser", return_value=mock_page),
    ):
        # 2. Verify initial status is RAW OCR (via get_page to initialize PageState)
        state.get_page(0)
        assert state.current_page_source_text == "RAW OCR"

        # 3. Perform save
        save_dir = tmp_path / "labeled"
        success = state.save_current_page(save_directory=str(save_dir))

        # 4. Verify save was successful and label changed
        assert success is True
        assert state.current_page_source_text == "LABELED"
        assert mock_page.page_source == "filesystem"


def test_current_page_source_tooltip_for_labeled_page(tmp_path):
    """Labeled pages should expose provenance summary for UI tooltip."""
    from ocr_labeler.models.project import Project

    state = ProjectState()
    project_root = tmp_path / "project"
    project_root.mkdir()
    state.project_root = project_root

    img_path = project_root / "page_001.png"
    img_path.touch()

    page = MagicMock()
    page.page_source = "filesystem"
    state.project = Project(pages=[page], image_paths=[img_path])
    state.current_page_index = 0

    with patch.object(
        state.page_ops,
        "get_page_provenance_summary",
        return_value="Saved: 2026-02-15T12:00:00Z\nOCR: doctr (0.10.0)",
    ) as mock_summary:
        tooltip = state.current_page_source_tooltip

    assert "Saved: 2026-02-15T12:00:00Z" in tooltip
    assert "OCR: doctr (0.10.0)" in tooltip
    mock_summary.assert_called_once_with(page)


def test_current_page_source_tooltip_for_cached_ocr_page(tmp_path):
    """Cached OCR pages should expose provenance summary for UI tooltip."""
    from ocr_labeler.models.project import Project

    state = ProjectState()
    project_root = tmp_path / "project"
    project_root.mkdir()
    state.project_root = project_root

    img_path = project_root / "page_001.png"
    img_path.touch()

    page = MagicMock()
    page.page_source = "cached_ocr"
    state.project = Project(pages=[page], image_paths=[img_path])
    state.current_page_index = 0

    with patch.object(
        state.page_ops,
        "get_page_provenance_summary",
        return_value="Saved: 2026-02-15T12:00:00Z\nOCR: doctr (0.10.0)",
    ) as mock_summary:
        tooltip = state.current_page_source_tooltip

    assert "Saved: 2026-02-15T12:00:00Z" in tooltip
    assert "OCR: doctr (0.10.0)" in tooltip
    mock_summary.assert_called_once_with(page)


def test_current_page_source_tooltip_empty_for_raw_ocr_page(tmp_path):
    """RAW OCR pages should not expose source provenance tooltip."""
    from ocr_labeler.models.project import Project

    state = ProjectState()
    project_root = tmp_path / "project"
    project_root.mkdir()
    state.project_root = project_root

    img_path = project_root / "page_001.png"
    img_path.touch()

    page = MagicMock()
    page.page_source = "ocr"
    state.project = Project(pages=[page], image_paths=[img_path])
    state.current_page_index = 0

    with patch.object(state.page_ops, "get_page_provenance_summary") as mock_summary:
        tooltip = state.current_page_source_tooltip

    assert tooltip == ""
    mock_summary.assert_not_called()


def test_refine_all_bboxes_success(tmp_path):
    """Test refine_all_bboxes with a valid page."""
    from unittest.mock import patch

    from ocr_labeler.models.project import Project

    # Setup project state with one page
    state = ProjectState()
    project_root = tmp_path / "project"
    project_root.mkdir()
    state.project_root = project_root

    # Create a dummy image
    img_path = project_root / "page_001.png"
    img_path.touch()

    # Initialize project with one page
    state.project = Project(pages=[None], image_paths=[img_path])
    state.current_page_index = 0

    # Mock the page and operations
    mock_page = MagicMock()
    mock_page.name = "test_page"

    with (
        patch.object(state, "get_page_state") as mock_get_page_state,
        patch.object(
            state.page_ops, "refine_all_bboxes", return_value=True
        ) as mock_refine,
    ):
        mock_page_state = MagicMock()
        mock_page_state.get_page.return_value = mock_page
        mock_get_page_state.return_value = mock_page_state

        # Call refine_all_bboxes
        result = state.refine_all_bboxes(padding_px=3)

        # Verify
        assert result is True
        mock_refine.assert_called_once_with(page=mock_page, padding_px=3)
        mock_page_state.notify.assert_called_once()


def test_refine_all_bboxes_no_page(tmp_path):
    """Test refine_all_bboxes when no page is available."""
    from ocr_labeler.models.project import Project

    # Setup project state with one page
    state = ProjectState()
    project_root = tmp_path / "project"
    project_root.mkdir()
    state.project_root = project_root

    # Create a dummy image
    img_path = project_root / "page_001.png"
    img_path.touch()

    # Initialize project with one page
    state.project = Project(pages=[None], image_paths=[img_path])
    state.current_page_index = 0

    with patch.object(state, "get_page_state") as mock_get_page_state:
        mock_page_state = MagicMock()
        mock_page_state.get_page.return_value = None  # No page available
        mock_get_page_state.return_value = mock_page_state

        # Call refine_all_bboxes
        result = state.refine_all_bboxes()

        # Verify
        assert result is False


def test_expand_and_refine_all_bboxes_success(tmp_path):
    """Test expand_and_refine_all_bboxes success."""
    from ocr_labeler.models.project import Project

    # Setup project state with one page
    state = ProjectState()
    project_root = tmp_path / "project"
    project_root.mkdir()
    state.project_root = project_root

    # Create a dummy image
    img_path = project_root / "page_001.png"
    img_path.touch()

    # Initialize project with one page
    mock_page = MagicMock()
    state.project = Project(pages=[mock_page], image_paths=[str(img_path)])
    state.current_page_index = 0

    with (
        patch.object(state, "get_page_state") as mock_get_page_state,
        patch.object(
            state.page_ops, "expand_and_refine_all_bboxes"
        ) as mock_expand_refine,
    ):
        mock_page_state = MagicMock()
        mock_page_state.get_page.return_value = mock_page
        mock_get_page_state.return_value = mock_page_state

        mock_expand_refine.return_value = True

        # Call expand_and_refine_all_bboxes
        result = state.expand_and_refine_all_bboxes(padding_px=3)

        # Verify
        assert result is True
        mock_expand_refine.assert_called_once_with(page=mock_page, padding_px=3)
        mock_page_state.notify.assert_called_once()


def test_expand_and_refine_all_bboxes_no_page(tmp_path):
    """Test expand_and_refine_all_bboxes when no page is available."""
    from ocr_labeler.models.project import Project

    # Setup project state with one page
    state = ProjectState()
    project_root = tmp_path / "project"
    project_root.mkdir()
    state.project_root = project_root

    # Create a dummy image
    img_path = project_root / "page_001.png"
    img_path.touch()

    # Initialize project with one page
    state.project = Project(pages=[None], image_paths=[img_path])
    state.current_page_index = 0

    with patch.object(state, "get_page_state") as mock_get_page_state:
        mock_page_state = MagicMock()
        mock_page_state.get_page.return_value = None  # No page available
        mock_get_page_state.return_value = mock_page_state

        # Call expand_and_refine_all_bboxes
        result = state.expand_and_refine_all_bboxes()

        # Verify
        assert result is False
