"""Tests for ModelSelectionOperations: HF probe, pinning, and default picker."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from pd_ocr_labeler.operations.ocr.model_selection_operations import (
    HF_DEFAULT_REPO,
    ModelSelectionOperations,
    OCRModelOption,
)


def _local_option(
    key: str, det_path: Path, reco_path: Path, vocab: str = ""
) -> OCRModelOption:
    return OCRModelOption(
        key=key,
        label=key,
        detection_weights_path=det_path,
        recognition_weights_path=reco_path,
        vocab=vocab or None,
    )


def _hf_option(
    key: str, *, last_modified: datetime | None, revision: str | None = None
) -> OCRModelOption:
    return OCRModelOption(
        key=key,
        label=key,
        detection_weights_path=None,
        recognition_weights_path=None,
        hf_repo=HF_DEFAULT_REPO,
        hf_detection_filename="detection/x.pt",
        hf_recognition_filename="recognition/x.pt",
        hf_revision=revision,
        hf_last_modified=last_modified,
    )


def _default_option() -> OCRModelOption:
    return OCRModelOption(
        key=ModelSelectionOperations.DEFAULT_MODEL_KEY,
        label=ModelSelectionOperations.DEFAULT_MODEL_LABEL,
        detection_weights_path=None,
        recognition_weights_path=None,
    )


def _make_local_pair(tmp_path: Path, mtime: datetime) -> tuple[Path, Path]:
    det = tmp_path / "det.pt"
    reco = tmp_path / "rec.pt"
    det.write_bytes(b"")
    reco.write_bytes(b"")
    ts = mtime.timestamp()
    import os

    os.utime(det, (ts, ts))
    os.utime(reco, (ts, ts))
    return det, reco


class TestPickDefaultKeys:
    def test_returns_hf_when_no_local(self):
        now = datetime.now(timezone.utc)
        options = {
            ModelSelectionOperations.HF_LATEST_KEY: _hf_option(
                ModelSelectionOperations.HF_LATEST_KEY, last_modified=now
            ),
            ModelSelectionOperations.DEFAULT_MODEL_KEY: _default_option(),
        }
        det, reco, reason = ModelSelectionOperations.pick_default_keys(options)
        assert det == ModelSelectionOperations.HF_LATEST_KEY
        assert reco == ModelSelectionOperations.HF_LATEST_KEY
        assert reason == "hf-latest"

    def test_returns_hf_when_hf_newer_than_local(self, tmp_path):
        now = datetime.now(timezone.utc)
        det_path, reco_path = _make_local_pair(tmp_path, now - timedelta(days=10))
        options = {
            ModelSelectionOperations.HF_LATEST_KEY: _hf_option(
                ModelSelectionOperations.HF_LATEST_KEY, last_modified=now
            ),
            "all/run-2026010100": _local_option(
                "all/run-2026010100", det_path, reco_path
            ),
            ModelSelectionOperations.DEFAULT_MODEL_KEY: _default_option(),
        }
        det, reco, reason = ModelSelectionOperations.pick_default_keys(options)
        assert det == ModelSelectionOperations.HF_LATEST_KEY
        assert reason == "hf-latest"

    def test_prefers_hf_when_equal_to_local(self, tmp_path):
        now = datetime.now(timezone.utc)
        det_path, reco_path = _make_local_pair(tmp_path, now)
        options = {
            ModelSelectionOperations.HF_LATEST_KEY: _hf_option(
                ModelSelectionOperations.HF_LATEST_KEY, last_modified=now
            ),
            "all/run-eq": _local_option("all/run-eq", det_path, reco_path),
            ModelSelectionOperations.DEFAULT_MODEL_KEY: _default_option(),
        }
        det, reco, reason = ModelSelectionOperations.pick_default_keys(options)
        assert det == ModelSelectionOperations.HF_LATEST_KEY
        assert reason == "hf-latest"

    def test_returns_local_when_local_strictly_newer(self, tmp_path):
        now = datetime.now(timezone.utc)
        det_path, reco_path = _make_local_pair(tmp_path, now)
        options = {
            ModelSelectionOperations.HF_LATEST_KEY: _hf_option(
                ModelSelectionOperations.HF_LATEST_KEY,
                last_modified=now - timedelta(days=30),
            ),
            "all/run-newer": _local_option("all/run-newer", det_path, reco_path),
            ModelSelectionOperations.DEFAULT_MODEL_KEY: _default_option(),
        }
        det, reco, reason = ModelSelectionOperations.pick_default_keys(options)
        assert det == "all/run-newer"
        assert reco == "all/run-newer"
        assert reason == "local-newer-than-hf"

    def test_returns_local_when_hf_unreachable(self, tmp_path):
        now = datetime.now(timezone.utc)
        det_path, reco_path = _make_local_pair(tmp_path, now)
        options = {
            ModelSelectionOperations.HF_LATEST_KEY: _hf_option(
                ModelSelectionOperations.HF_LATEST_KEY, last_modified=None
            ),
            "all/run-only-local": _local_option(
                "all/run-only-local", det_path, reco_path
            ),
            ModelSelectionOperations.DEFAULT_MODEL_KEY: _default_option(),
        }
        det, reco, reason = ModelSelectionOperations.pick_default_keys(options)
        assert det == "all/run-only-local"
        assert reason == "local-only-hf-unreachable"

    def test_returns_default_when_offline_and_no_local(self):
        options = {
            ModelSelectionOperations.HF_LATEST_KEY: _hf_option(
                ModelSelectionOperations.HF_LATEST_KEY, last_modified=None
            ),
            ModelSelectionOperations.DEFAULT_MODEL_KEY: _default_option(),
        }
        det, reco, reason = ModelSelectionOperations.pick_default_keys(options)
        assert det == ModelSelectionOperations.DEFAULT_MODEL_KEY
        assert reco == ModelSelectionOperations.DEFAULT_MODEL_KEY
        assert reason == "hf-unreachable-no-local"


class TestDiscoverModelOptions:
    def test_includes_hf_latest_and_default(self, monkeypatch, tmp_path):
        monkeypatch.setattr(
            ModelSelectionOperations,
            "fetch_hf_last_modified",
            classmethod(
                lambda cls, *, revision=None, timeout=5.0: datetime(
                    2026, 5, 1, tzinfo=timezone.utc
                )
            ),
        )
        monkeypatch.setattr(
            ModelSelectionOperations,
            "get_shared_models_root",
            classmethod(lambda cls: tmp_path / "missing"),
        )

        options, labels = ModelSelectionOperations.discover_model_options()

        assert ModelSelectionOperations.HF_LATEST_KEY in options
        assert ModelSelectionOperations.DEFAULT_MODEL_KEY in options
        assert options[ModelSelectionOperations.HF_LATEST_KEY].is_huggingface
        assert options[ModelSelectionOperations.HF_LATEST_KEY].hf_last_modified == (
            datetime(2026, 5, 1, tzinfo=timezone.utc)
        )
        # Labels contain both
        assert "hugging face" in labels[ModelSelectionOperations.HF_LATEST_KEY].lower()

    def test_includes_pinned_when_revision_supplied(self, monkeypatch, tmp_path):
        monkeypatch.setattr(
            ModelSelectionOperations,
            "fetch_hf_last_modified",
            classmethod(
                lambda cls, *, revision=None, timeout=5.0: datetime(
                    2026, 5, 1, tzinfo=timezone.utc
                )
            ),
        )
        monkeypatch.setattr(
            ModelSelectionOperations,
            "get_shared_models_root",
            classmethod(lambda cls: tmp_path / "missing"),
        )

        options, _labels = ModelSelectionOperations.discover_model_options(
            hf_pinned_revision="v1.2.3"
        )

        pinned_key = ModelSelectionOperations.hf_pinned_key("v1.2.3")
        assert pinned_key in options
        pinned = options[pinned_key]
        assert pinned.hf_revision == "v1.2.3"
        assert pinned.is_huggingface

    def test_skips_hf_metadata_when_probe_returns_none(self, monkeypatch, tmp_path):
        monkeypatch.setattr(
            ModelSelectionOperations,
            "fetch_hf_last_modified",
            classmethod(lambda cls, *, revision=None, timeout=5.0: None),
        )
        monkeypatch.setattr(
            ModelSelectionOperations,
            "get_shared_models_root",
            classmethod(lambda cls: tmp_path / "missing"),
        )

        options, _ = ModelSelectionOperations.discover_model_options()
        assert options[ModelSelectionOperations.HF_LATEST_KEY].hf_last_modified is None


class TestFetchHfLastModified:
    def test_returns_none_when_huggingface_hub_missing(self, monkeypatch):
        import builtins

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "huggingface_hub":
                raise ImportError("not installed")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        result = ModelSelectionOperations.fetch_hf_last_modified()
        assert result is None

    def test_returns_none_on_network_error(self, monkeypatch):
        class _BoomApi:
            def model_info(self, *args, **kwargs):
                raise OSError("offline")

        fake_module = type("M", (), {"HfApi": _BoomApi})
        import sys

        monkeypatch.setitem(sys.modules, "huggingface_hub", fake_module)
        assert ModelSelectionOperations.fetch_hf_last_modified() is None


class TestDownloadHfWeights:
    def test_raises_for_non_hf_option(self):
        opt = _default_option()
        with pytest.raises(ValueError):
            ModelSelectionOperations.download_hf_weights(opt)

    def test_raises_when_pd_book_tools_hf_missing(self, monkeypatch):
        # Canonical HF download helpers live in ``pd_book_tools.hf``; the
        # labeler wraps that import so an out-of-date pd-book-tools surfaces
        # as a RuntimeError with a clear remediation message.
        import builtins

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "pd_book_tools.hf" or name.startswith("pd_book_tools.hf."):
                raise ImportError("not installed")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        opt = _hf_option(
            ModelSelectionOperations.HF_LATEST_KEY,
            last_modified=datetime.now(timezone.utc),
        )
        with pytest.raises(RuntimeError):
            ModelSelectionOperations.download_hf_weights(opt)

    def test_pulls_arch_and_vocab_sidecars_for_both_roles(self, monkeypatch, tmp_path):
        """Ensure ``.arch`` and ``.vocab`` are attempted for both .pt files.

        pd_book_tools reads sidecar files from the same directory as the .pt
        file, so we need to fetch them so they land in the same HF snapshot
        directory.
        """
        # Pre-create cache files so .read_text in download_hf_weights works.
        det_path = tmp_path / "detection" / "x.pt"
        reco_path = tmp_path / "recognition" / "x.pt"
        det_path.parent.mkdir(parents=True)
        reco_path.parent.mkdir(parents=True)
        det_path.write_bytes(b"")
        reco_path.write_bytes(b"")
        (reco_path.with_suffix(".vocab")).write_text("abc", encoding="utf-8")

        downloaded: list[str] = []

        class _FakeNotFound(Exception):
            pass

        def fake_hf_hub_download(*, repo_id, filename, revision=None):
            downloaded.append(filename)
            if filename.endswith(".arch"):
                # Simulate sidecar absent for the detection role only.
                if filename.startswith("detection/"):
                    raise _FakeNotFound("no arch")
            if filename == "detection/x.pt":
                return str(det_path)
            if filename == "recognition/x.pt":
                return str(reco_path)
            if filename == "recognition/x.vocab":
                return str(reco_path.with_suffix(".vocab"))
            if filename == "recognition/x.arch":
                # Simulate the sidecar landing in the same directory.
                arch_path = reco_path.with_suffix(".arch")
                arch_path.write_text("crnn_vgg16_bn", encoding="utf-8")
                return str(arch_path)
            if filename == "detection/x.vocab":
                # Simulate detection .vocab missing.
                raise _FakeNotFound("no vocab for detection")
            raise AssertionError(f"unexpected download: {filename}")

        fake_hf_module = type(
            "M", (), {"hf_hub_download": staticmethod(fake_hf_hub_download)}
        )
        fake_hf_utils = type("U", (), {"EntryNotFoundError": _FakeNotFound})
        import sys

        monkeypatch.setitem(sys.modules, "huggingface_hub", fake_hf_module)
        monkeypatch.setitem(sys.modules, "huggingface_hub.utils", fake_hf_utils)

        option = OCRModelOption(
            key=ModelSelectionOperations.HF_LATEST_KEY,
            label="hf",
            detection_weights_path=None,
            recognition_weights_path=None,
            hf_repo=HF_DEFAULT_REPO,
            hf_detection_filename="detection/x.pt",
            hf_recognition_filename="recognition/x.pt",
        )

        det, reco, vocab = ModelSelectionOperations.download_hf_weights(option)

        # .pt files always fetched
        assert "detection/x.pt" in downloaded
        assert "recognition/x.pt" in downloaded
        # Both sidecars attempted for both roles
        assert "detection/x.arch" in downloaded
        assert "detection/x.vocab" in downloaded
        assert "recognition/x.arch" in downloaded
        assert "recognition/x.vocab" in downloaded
        # vocab text returned from the recognition .vocab file we created
        assert vocab == "abc"
        assert det == det_path
        assert reco == reco_path
