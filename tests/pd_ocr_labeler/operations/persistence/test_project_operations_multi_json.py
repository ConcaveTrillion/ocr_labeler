"""Tests for multi-JSON ground truth merge (pages_manifest.json support)."""

from __future__ import annotations

import json
from pathlib import Path

from pd_ocr_labeler.operations.persistence.project_operations import ProjectOperations


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


class TestApplyPageIndexOffset:
    def test_numeric_key_with_extension_is_shifted(self):
        ops = ProjectOperations()
        result = ops._apply_page_index_offset({"042.png": "text"}, offset=100)
        assert "142.png" in result
        assert result["142.png"] == "text"

    def test_zero_offset_is_identity(self):
        ops = ProjectOperations()
        data = {"001.png": "a", "002.png": "b"}
        assert ops._apply_page_index_offset(data, 0) == data

    def test_non_numeric_key_is_unchanged(self):
        ops = ProjectOperations()
        result = ops._apply_page_index_offset({"front-page.png": "intro"}, offset=10)
        assert "front-page.png" in result

    def test_numeric_key_without_extension(self):
        ops = ProjectOperations()
        result = ops._apply_page_index_offset({"001": "text"}, offset=50)
        assert "051" in result

    def test_zero_padding_preserved_to_3_digits(self):
        ops = ProjectOperations()
        result = ops._apply_page_index_offset({"001.png": "text"}, offset=1)
        assert "002.png" in result


class TestLoadGroundTruthFromDirectory:
    def test_loads_pages_json_when_no_manifest(self, tmp_path):
        pages_json = tmp_path / "pages.json"
        _write_json(pages_json, {"001.png": "hello world"})
        ops = ProjectOperations()
        result = ops.load_ground_truth_from_directory(tmp_path)
        # The normalized map may contain multiple key variants
        assert any("001" in k for k in result.keys())
        assert any(result[k] == "hello world" for k in result if "001" in k)

    def test_returns_empty_when_no_files(self, tmp_path):
        ops = ProjectOperations()
        result = ops.load_ground_truth_from_directory(tmp_path)
        assert result == {}

    def test_manifest_takes_precedence_over_pages_json(self, tmp_path):
        # Create both files; manifest should win
        _write_json(tmp_path / "pages.json", {"001.png": "from pages.json"})
        _write_json(tmp_path / "source1.json", {"001.png": "from manifest"})
        _write_json(
            tmp_path / "pages_manifest.json",
            {"sources": [{"file": "source1.json", "offset": 0}]},
        )
        ops = ProjectOperations()
        result = ops.load_ground_truth_from_directory(tmp_path)
        # At least one key should have the manifest value
        assert any("from manifest" in v for v in result.values())

    def test_manifest_merges_two_sources_with_offsets(self, tmp_path):
        # First batch: pages 001-003 (offset 0)
        _write_json(tmp_path / "batch1.json", {"001.png": "page1", "002.png": "page2"})
        # Second batch: pages 001-002 but with offset 2 → 003, 004
        _write_json(tmp_path / "batch2.json", {"001.png": "page3", "002.png": "page4"})
        _write_json(
            tmp_path / "pages_manifest.json",
            {
                "sources": [
                    {"file": "batch1.json", "offset": 0},
                    {"file": "batch2.json", "offset": 2},
                ]
            },
        )
        ops = ProjectOperations()
        result = ops.load_ground_truth_from_directory(tmp_path)
        # 001.png → page1, 002.png → page2, 003.png → page3, 004.png → page4
        assert result.get("001.png") == "page1" or any(
            "page1" in v for k, v in result.items() if "001" in k
        )
        assert any("page3" in v for k, v in result.items() if "003" in k)
        assert any("page4" in v for k, v in result.items() if "004" in k)

    def test_manifest_skips_missing_source_file(self, tmp_path):
        _write_json(
            tmp_path / "pages_manifest.json",
            {"sources": [{"file": "missing.json", "offset": 0}]},
        )
        ops = ProjectOperations()
        result = ops.load_ground_truth_from_directory(tmp_path)
        assert result == {}

    def test_manifest_falls_back_to_pages_json_on_manifest_error(self, tmp_path):
        # Write an invalid manifest
        (tmp_path / "pages_manifest.json").write_text("not json", encoding="utf-8")
        _write_json(tmp_path / "pages.json", {"001.png": "fallback text"})
        ops = ProjectOperations()
        result = ops.load_ground_truth_from_directory(tmp_path)
        assert any("fallback text" in v for v in result.values())

    def test_manifest_ignores_non_dict_entry(self, tmp_path):
        _write_json(tmp_path / "pages_manifest.json", {"sources": ["not a dict"]})
        ops = ProjectOperations()
        result = ops.load_ground_truth_from_directory(tmp_path)
        assert result == {}

    def test_manifest_ignores_entry_without_file_key(self, tmp_path):
        _write_json(
            tmp_path / "pages_manifest.json",
            {"sources": [{"offset": 0}]},  # missing "file"
        )
        ops = ProjectOperations()
        result = ops.load_ground_truth_from_directory(tmp_path)
        assert result == {}
