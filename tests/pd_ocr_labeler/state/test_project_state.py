from __future__ import annotations

import json
import logging
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from pd_ocr_labeler.models.page_model import PageModel
from pd_ocr_labeler.operations.persistence.persistence_paths_operations import (
    PersistencePathsOperations,
)
from pd_ocr_labeler.state import project_state as project_state_module
from pd_ocr_labeler.state.project_state import ProjectState, SaveProjectResult


def test_project_state_initialization():
    """Test that ProjectState initializes correctly."""
    state = ProjectState()
    assert state.project is not None
    assert state.current_page_index == 0
    assert state.current_page_model() is None  # No pages loaded yet
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
    assert state.current_page_model() is None


def test_load_current_page_success(tmp_path):
    """Test load_current_page when file exists and loads successfully."""
    # Create a valid JSON file
    save_dir = tmp_path / "save_test"
    save_dir.mkdir(parents=True)

    json_file = save_dir / "test_project_001.json"
    json_data = {
        "source_lib": "doctr-pd-labeled",
        "source_path": "test_image.png",
        "pages": [{"type": "Page", "items": [], "width": 800, "height": 600}],
    }

    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(json_data, f)

    # Mock Page.from_dict and the page operations
    with patch("pd_ocr_labeler.operations.ocr.page_operations.Page") as mock_page_class:
        mock_page = Mock()
        mock_page_class.from_dict.return_value = mock_page

        # Set up project state
        state = ProjectState()
        state.project_root = Path("/test/project")
        state.current_page_index = 0

        # Mock the project.pages list
        mock_project = Mock()
        mock_project.pages = [None]  # Initially None, should be replaced
        mock_project.ground_truth_map = {}
        state.project = mock_project

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
        "source_lib": "doctr-pd-labeled",
        "source_path": "test_image.png",
        "pages": [{"type": "Page", "items": []}],
    }

    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(json_data, f)

    # Mock Page.from_dict
    with patch("pd_ocr_labeler.operations.ocr.page_operations.Page") as mock_page_class:
        mock_page = Mock()
        mock_page_class.from_dict.return_value = mock_page

        # Set up project state with specific project root
        state = ProjectState()
        state.project_root = Path("my_book_project")
        state.current_page_index = 0

        # Mock the project.pages list
        mock_project = Mock()
        mock_project.pages = [None]
        mock_project.ground_truth_map = {}
        state.project = mock_project

        # Test without providing project_id
        result = state.load_current_page(
            save_directory=str(save_dir),
            # No project_id provided
        )

        assert result is True
        assert state.project.pages[0] is mock_page


def test_ensure_page_replaces_cached_page_with_disk_page(tmp_path):
    """Ensure in-memory cached OCR page is replaced when a disk-labeled page exists."""
    state = ProjectState()
    state.project_root = tmp_path

    image_path = tmp_path / "001.png"
    image_path.write_bytes(b"img")

    cached_page = MagicMock()
    cached_page.page_source = "cached_ocr"

    project = Mock()
    project.pages = [cached_page]
    project.image_paths = [image_path]
    project.ground_truth_map = {}
    state.project = project

    disk_page = MagicMock()

    with (
        patch.object(
            state.page_ops, "can_load_page", return_value=Mock(can_load=True)
        ) as mock_can_load,
        patch.object(
            state.page_ops,
            "load_page_model",
            return_value=(PageModel(page=disk_page, page_source="filesystem"), None),
        ) as mock_load,
        patch.object(state, "notify") as mock_notify,
    ):
        result = state.ensure_page_model(0)

    workspace_save_dir = str(PersistencePathsOperations.get_saved_projects_root())
    assert result is not None
    assert result.page is disk_page
    assert state.project.pages[0] is disk_page
    assert disk_page.page_source == "filesystem"
    mock_can_load.assert_called_once_with(
        page_number=1,
        project_root=tmp_path,
        save_directory=workspace_save_dir,
        project_id=None,
    )
    mock_load.assert_called_once_with(
        page_number=1,
        project_root=tmp_path,
        save_directory=workspace_save_dir,
        project_id=None,
    )
    mock_notify.assert_called_once()


def test_ensure_page_checks_disk_before_cache(tmp_path):
    """Ensure user-labeled disk directory is checked before OCR cache directory."""
    state = ProjectState()
    state.project_root = tmp_path

    image_path = tmp_path / "001.png"
    image_path.write_bytes(b"img")

    project = Mock()
    project.pages = [None]
    project.image_paths = [image_path]
    project.ground_truth_map = {}
    state.project = project

    cached_page = MagicMock()

    with (
        patch.object(
            state.page_ops,
            "can_load_page",
            side_effect=[
                Mock(can_load=False),
                Mock(can_load=True),
            ],
        ) as mock_can_load,
        patch.object(
            state.page_ops,
            "load_page_model",
            return_value=(PageModel(page=cached_page, page_source="cached_ocr"), None),
        ) as mock_load,
        patch.object(state, "notify"),
    ):
        result = state.ensure_page_model(0)

    assert result is not None
    assert result.page is cached_page
    assert state.project.pages[0] is cached_page
    assert mock_can_load.call_count == 2
    workspace_save_dir = str(PersistencePathsOperations.get_saved_projects_root())
    cache_save_dir = str(PersistencePathsOperations.get_page_image_cache_root())
    assert (
        mock_can_load.call_args_list[0].kwargs["save_directory"] == workspace_save_dir
    )
    assert mock_can_load.call_args_list[1].kwargs["save_directory"] == cache_save_dir
    mock_load.assert_called_once_with(
        page_number=1,
        project_root=tmp_path,
        save_directory=cache_save_dir,
        project_id=None,
    )


def test_ensure_page_loads_workspace_labeled_before_cache(tmp_path):
    """Ensure workspace-level labeled pages are treated as disk pages before cache."""
    state = ProjectState()
    state.project_root = tmp_path

    image_path = tmp_path / "001.png"
    image_path.write_bytes(b"img")

    project = Mock()
    project.pages = [None]
    project.image_paths = [image_path]
    project.ground_truth_map = {}
    state.project = project

    labeled_page = MagicMock()

    with (
        patch.object(
            state.page_ops,
            "can_load_page",
            side_effect=[Mock(can_load=True)],
        ) as mock_can_load,
        patch.object(
            state.page_ops,
            "load_page_model",
            return_value=(PageModel(page=labeled_page, page_source="filesystem"), None),
        ) as mock_load,
        patch.object(state, "notify"),
    ):
        result = state.ensure_page_model(0)

    assert result is not None
    assert result.page is labeled_page
    assert state.project.pages[0] is labeled_page
    assert labeled_page.page_source == "filesystem"
    assert mock_can_load.call_count == 1
    workspace_save_dir = str(PersistencePathsOperations.get_saved_projects_root())
    assert (
        mock_can_load.call_args_list[0].kwargs["save_directory"] == workspace_save_dir
    )
    mock_load.assert_called_once_with(
        page_number=1,
        project_root=tmp_path,
        save_directory=workspace_save_dir,
        project_id=None,
    )


def test_ensure_page_model_force_ocr_ignores_loaded_labeled_page(tmp_path):
    """force_ocr should bypass loaded labeled page and run OCR parser."""
    state = ProjectState()
    state.project_root = tmp_path

    image_path = tmp_path / "001.png"
    image_path.write_bytes(b"img")

    labeled_page = MagicMock()
    labeled_page.page_source = "filesystem"

    project = Mock()
    project.pages = [labeled_page]
    project.image_paths = [image_path]
    project.ground_truth_map = {}
    state.project = project

    ocr_page = MagicMock()
    ocr_page.name = "001.png"
    ocr_page.index = 0
    ocr_page.image_path = str(image_path)

    with (
        patch.object(state, "notify"),
        patch.object(state.page_ops, "can_load_page") as mock_can_load,
        patch.object(state.page_ops, "load_page_model") as mock_load,
        patch.object(state.page_ops, "save_page", return_value=False),
    ):
        state.page_ops.page_parser = Mock(return_value=ocr_page)

        page_model = state.ensure_page_model(0, force_ocr=True)

    assert page_model is not None
    assert state.page_ops.page_parser.call_count == 1
    mock_can_load.assert_not_called()
    mock_load.assert_not_called()
    assert state.project.pages[0] is ocr_page
    assert page_model.page is ocr_page
    assert page_model.page_source in {"ocr", "cached_ocr"}


def test_ensure_page_model_skips_disk_replace_after_force_ocr_override(tmp_path):
    """After force OCR, normal ensure calls should not auto-replace with labeled disk page."""
    state = ProjectState()
    state.project_root = tmp_path

    image_path = tmp_path / "001.png"
    image_path.write_bytes(b"img")

    raw_page = MagicMock()
    raw_page.page_source = "cached_ocr"

    state.project = Mock(
        pages=[raw_page],
        image_paths=[image_path],
        ground_truth_map={},
    )
    state.page_models[0] = PageModel(page=raw_page, page_source="cached_ocr")
    state._force_ocr_page_overrides.add(0)

    with (
        patch.object(state, "notify") as mock_notify,
        patch.object(state.page_ops, "can_load_page") as mock_can_load,
        patch.object(state.page_ops, "load_page_model") as mock_load,
    ):
        page_model = state.ensure_page_model(0, force_ocr=False)

    assert page_model is not None
    assert page_model.page is raw_page
    assert page_model.page_source == "cached_ocr"
    mock_can_load.assert_not_called()
    mock_load.assert_not_called()
    mock_notify.assert_not_called()


def test_ensure_page_logs_timing_for_cached_ocr_load(tmp_path, caplog):
    """Ensure cached OCR loads emit structured page load timing logs."""
    state = ProjectState()
    state.project_root = tmp_path

    image_path = tmp_path / "001.png"
    image_path.write_bytes(b"img")

    project = Mock()
    project.pages = [None]
    project.image_paths = [image_path]
    project.ground_truth_map = {}
    state.project = project

    cached_page = MagicMock()

    with (
        caplog.at_level(logging.INFO),
        patch.object(
            state.page_ops,
            "can_load_page",
            side_effect=[
                Mock(can_load=False),
                Mock(can_load=True),
            ],
        ),
        patch.object(
            state.page_ops,
            "load_page_model",
            return_value=(PageModel(page=cached_page, page_source="cached_ocr"), None),
        ),
        patch.object(state, "notify"),
    ):
        state.ensure_page_model(0)

    timing_messages = [
        record.getMessage()
        for record in caplog.records
        if "page_model_load_timing:" in record.getMessage()
    ]
    assert timing_messages
    assert any(
        "source=cached_ocr" in message and "status=loaded" in message
        for message in timing_messages
    )


def test_ensure_page_loader_failure_logs_warning_not_error(tmp_path, caplog):
    """Ensure OCR loader fallback path does not emit ERROR logs from ProjectState."""
    state = ProjectState()
    state.project_root = tmp_path

    image_path = tmp_path / "001.png"
    image_path.write_bytes(b"img")

    project = Mock()
    project.pages = [None]
    project.image_paths = [image_path]
    project.ground_truth_map = {}
    state.project = project

    with (
        caplog.at_level(logging.WARNING),
        patch.object(
            state.page_ops,
            "can_load_page",
            side_effect=[
                Mock(can_load=False),
                Mock(can_load=False),
                Mock(can_load=False),
            ],
        ),
        patch.object(
            state.page_ops,
            "page_parser",
            side_effect=RuntimeError("ocr boom"),
        ),
        patch.object(state, "notify"),
    ):
        page_model = state.ensure_page_model(0)

    assert page_model is not None
    assert page_model.page_source == "fallback"

    project_state_errors = [
        record
        for record in caplog.records
        if record.name == "pd_ocr_labeler.state.project_state"
        and record.levelno >= logging.ERROR
    ]
    assert not project_state_errors


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

    from pd_ocr_labeler.models.project_model import Project

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
            "pd_ocr_labeler.operations.ocr.page_operations.PageOperations.save_page",
            side_effect=mock_save_page,
        ),
        patch(
            "pd_ocr_labeler.operations.ocr.page_operations.PageOperations.load_page_model",
            side_effect=lambda *args, **kwargs: None,
        ),
        patch.object(state.page_ops, "page_parser", return_value=mock_page),
    ):
        # 2. Verify initial status is RAW OCR (via get_page to initialize PageState)
        state.get_or_load_page_model(0)
        assert state.current_page_state.current_page_source == "ocr"

        # 3. Perform save
        save_dir = tmp_path / "labeled"
        success = state.save_current_page(save_directory=str(save_dir))

        # 4. Verify save was successful and label changed
        assert success is True
        assert state.current_page_state.current_page_source == "filesystem"
        assert mock_page.page_source == "filesystem"


def test_current_page_source_tooltip_for_labeled_page(tmp_path):
    """Labeled pages should expose provenance summary for UI tooltip."""
    from pd_ocr_labeler.models.project_model import Project

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
        tooltip = state.current_page_state.current_page_source_tooltip

    assert "Saved: 2026-02-15T12:00:00Z" in tooltip
    assert "OCR: doctr (0.10.0)" in tooltip
    mock_summary.assert_called_once_with(page)


def test_current_page_source_tooltip_for_cached_ocr_page(tmp_path):
    """Cached OCR pages should expose provenance summary for UI tooltip."""
    from pd_ocr_labeler.models.project_model import Project

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
        tooltip = state.current_page_state.current_page_source_tooltip

    assert "Saved: 2026-02-15T12:00:00Z" in tooltip
    assert "OCR: doctr (0.10.0)" in tooltip
    mock_summary.assert_called_once_with(page)


def test_current_page_source_tooltip_for_raw_ocr_page_with_saved_metadata(tmp_path):
    """RAW OCR pages should expose saved provenance tooltip when available."""
    from pd_ocr_labeler.models.project_model import Project

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

    with patch.object(
        state.page_ops,
        "get_page_provenance_summary",
        return_value="Saved: 2026-02-15T12:00:00Z",
    ) as mock_summary:
        tooltip = state.current_page_state.current_page_source_tooltip

    assert "Saved: 2026-02-15T12:00:00Z" in tooltip
    mock_summary.assert_called_once_with(page)


def test_refine_all_bboxes_success(tmp_path):
    """Test refine_all_bboxes with a valid page."""
    from unittest.mock import patch

    from pd_ocr_labeler.models.project_model import Project

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
        mock_page_state.get_page_model.return_value = mock_page
        mock_get_page_state.return_value = mock_page_state

        # Call refine_all_bboxes
        result = state.refine_all_bboxes(padding_px=3)

        # Verify
        assert result is True
        mock_refine.assert_called_once_with(page=mock_page, padding_px=3)
        mock_page_state.notify.assert_called_once()


def test_reload_current_page_with_ocr_notifies_and_refreshes_cache():
    """Reload OCR should force cache refresh and notify listeners for same-page updates."""
    state = ProjectState()
    state.current_page_index = 0

    mock_page_state = MagicMock()

    with (
        patch.object(state, "get_page_state", return_value=mock_page_state),
        patch.object(state, "_invalidate_text_cache") as mock_invalidate,
        patch.object(state, "_update_text_cache") as mock_update_cache,
        patch.object(state, "notify") as mock_notify,
    ):
        state.reload_current_page_with_ocr()

    mock_page_state.reload_page_with_ocr.assert_called_once_with(
        0, use_edited_image=False
    )
    mock_invalidate.assert_called_once()
    mock_update_cache.assert_called_once_with(force=True)
    mock_notify.assert_called_once()


def test_reload_current_page_with_ocr_edited_image_mode_passes_flag():
    """Edited-image OCR reload should be forwarded to PageState with explicit flag."""
    state = ProjectState()
    state.current_page_index = 2

    mock_page_state = MagicMock()

    with (
        patch.object(state, "get_page_state", return_value=mock_page_state),
        patch.object(state, "_invalidate_text_cache") as mock_invalidate,
        patch.object(state, "_update_text_cache") as mock_update_cache,
        patch.object(state, "notify") as mock_notify,
    ):
        state.reload_current_page_with_ocr(use_edited_image=True)

    mock_page_state.reload_page_with_ocr.assert_called_once_with(
        2, use_edited_image=True
    )
    mock_invalidate.assert_called_once()
    mock_update_cache.assert_called_once_with(force=True)
    mock_notify.assert_called_once()


def test_refine_all_bboxes_no_page(tmp_path):
    """Test refine_all_bboxes when no page is available."""
    from pd_ocr_labeler.models.project_model import Project

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
        mock_page_state.get_page_model.return_value = None  # No page available
        mock_get_page_state.return_value = mock_page_state

        # Call refine_all_bboxes
        result = state.refine_all_bboxes()

        # Verify
        assert result is False


def test_expand_and_refine_all_bboxes_success(tmp_path):
    """Test expand_and_refine_all_bboxes success."""
    from pd_ocr_labeler.models.project_model import Project

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
        mock_page_state.get_page_model.return_value = mock_page
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
    from pd_ocr_labeler.models.project_model import Project

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
        mock_page_state.get_page_model.return_value = None  # No page available
        mock_get_page_state.return_value = mock_page_state

        # Call expand_and_refine_all_bboxes
        result = state.expand_and_refine_all_bboxes()

        # Verify
        assert result is False


# ------------------------------------------------------------------
# SaveProjectResult & save_all_pages
# ------------------------------------------------------------------


class TestSaveProjectResult:
    """Tests for the SaveProjectResult dataclass."""

    def test_defaults(self):
        result = SaveProjectResult()
        assert result.saved_count == 0
        assert result.skipped_count == 0
        assert result.failed_count == 0
        assert result.total_count == 0

    def test_summary_no_pages(self):
        result = SaveProjectResult()
        assert result.summary == "No pages to save"

    def test_summary_all_saved(self):
        result = SaveProjectResult(saved_count=3, total_count=3)
        assert "3 saved" in result.summary
        assert "of 3 pages" in result.summary

    def test_summary_with_failures(self):
        result = SaveProjectResult(saved_count=2, failed_count=1, total_count=3)
        assert "2 saved" in result.summary
        assert "1 failed" in result.summary

    def test_summary_with_skipped(self):
        result = SaveProjectResult(saved_count=1, skipped_count=2, total_count=3)
        assert "1 saved" in result.summary
        assert "2 skipped" in result.summary


class TestSaveAllPages:
    """Tests for ProjectState.save_all_pages."""

    def test_no_loaded_pages_returns_zero_counts(self, tmp_path):
        state = ProjectState()
        state.project_root = tmp_path

        result = state.save_all_pages()

        assert result.total_count == 0
        assert result.saved_count == 0
        assert result.skipped_count == 0
        assert result.failed_count == 0

    def test_saves_all_loaded_pages(self, tmp_path):
        state = ProjectState()
        state.project_root = tmp_path

        # Create two page states with mock page models
        for idx in [0, 2]:
            ps = state.get_page_state(idx)
            ps._project_root = tmp_path
            mock_model = MagicMock(spec=PageModel)
            ps.get_page_model = Mock(return_value=mock_model)
            ps.persist_page_to_file = Mock(return_value=True)

        result = state.save_all_pages(save_directory=str(tmp_path))

        assert result.total_count == 2
        assert result.saved_count == 2
        assert result.skipped_count == 0
        assert result.failed_count == 0

        # Verify persist_page_to_file was called with correct args
        state.page_states[0].persist_page_to_file.assert_called_once()
        state.page_states[2].persist_page_to_file.assert_called_once()

    def test_skips_pages_without_page_model(self, tmp_path):
        state = ProjectState()
        state.project_root = tmp_path

        # Page state exists but has no loaded page model
        ps = state.get_page_state(0)
        ps._project_root = tmp_path
        ps.get_page_model = Mock(return_value=None)

        result = state.save_all_pages(save_directory=str(tmp_path))

        assert result.total_count == 1
        assert result.skipped_count == 1
        assert result.saved_count == 0

    def test_failed_save_increments_failed_count(self, tmp_path):
        state = ProjectState()
        state.project_root = tmp_path

        ps = state.get_page_state(0)
        ps._project_root = tmp_path
        mock_model = MagicMock(spec=PageModel)
        ps.get_page_model = Mock(return_value=mock_model)
        ps.persist_page_to_file = Mock(return_value=False)

        result = state.save_all_pages(save_directory=str(tmp_path))

        assert result.total_count == 1
        assert result.failed_count == 1
        assert result.saved_count == 0

    def test_exception_during_save_increments_failed_count(self, tmp_path):
        state = ProjectState()
        state.project_root = tmp_path

        ps = state.get_page_state(0)
        ps._project_root = tmp_path
        mock_model = MagicMock(spec=PageModel)
        ps.get_page_model = Mock(return_value=mock_model)
        ps.persist_page_to_file = Mock(side_effect=RuntimeError("disk full"))

        result = state.save_all_pages(save_directory=str(tmp_path))

        assert result.total_count == 1
        assert result.failed_count == 1
        assert result.saved_count == 0

    def test_mixed_results(self, tmp_path):
        """Test with a mix of successful, failed, and skipped pages."""
        state = ProjectState()
        state.project_root = tmp_path

        # Page 0: succeeds
        ps0 = state.get_page_state(0)
        ps0._project_root = tmp_path
        ps0.get_page_model = Mock(return_value=MagicMock(spec=PageModel))
        ps0.persist_page_to_file = Mock(return_value=True)

        # Page 1: no model (skipped)
        ps1 = state.get_page_state(1)
        ps1._project_root = tmp_path
        ps1.get_page_model = Mock(return_value=None)

        # Page 2: fails
        ps2 = state.get_page_state(2)
        ps2._project_root = tmp_path
        ps2.get_page_model = Mock(return_value=MagicMock(spec=PageModel))
        ps2.persist_page_to_file = Mock(return_value=False)

        result = state.save_all_pages(save_directory=str(tmp_path))

        assert result.total_count == 3
        assert result.saved_count == 1
        assert result.skipped_count == 1
        assert result.failed_count == 1


# ------------------------------------------------------------------
# ProjectStateViewModel.command_save_project
# ------------------------------------------------------------------


class TestCommandSaveProject:
    """Tests for command_save_project in the view model layer."""

    def test_command_save_project_delegates_to_state(self, tmp_path):
        from pd_ocr_labeler.viewmodels.project.project_state_view_model import (
            ProjectStateViewModel,
        )

        state = ProjectState()
        state.project_root = tmp_path

        # Set up one loaded page that will save successfully
        ps = state.get_page_state(0)
        ps._project_root = tmp_path
        ps.get_page_model = Mock(return_value=MagicMock(spec=PageModel))
        ps.persist_page_to_file = Mock(return_value=True)

        vm = ProjectStateViewModel(state)
        result = vm.command_save_project()

        assert result.saved_count == 1
        assert result.total_count == 1

    def test_command_save_project_without_state(self):
        from pd_ocr_labeler.viewmodels.project.project_state_view_model import (
            ProjectStateViewModel,
        )

        state = ProjectState()
        vm = ProjectStateViewModel(state)
        # No pages loaded → empty result
        result = vm.command_save_project()

        assert result.total_count == 0
        assert result.saved_count == 0
