from __future__ import annotations

import logging
from pathlib import Path

from ocr_labeler.app import NiceGuiLabeler


def test_session_logging_does_not_override_logger_levels(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    root_logger = logging.getLogger()
    app_logger = logging.getLogger("ocr_labeler")

    original_root_level = root_logger.level
    original_app_level = app_logger.level

    try:
        root_logger.setLevel(logging.WARNING)
        app_logger.setLevel(logging.INFO)

        labeler = NiceGuiLabeler(project_root=tmp_path, enable_session_logging=True)
        handler, session_id = labeler._setup_session_logging()

        assert handler is not None
        assert root_logger.level == logging.WARNING
        assert app_logger.level == logging.INFO
    finally:
        if "labeler" in locals() and handler is not None:
            labeler._cleanup_session_logging(handler, session_id)
        root_logger.setLevel(original_root_level)
        app_logger.setLevel(original_app_level)
