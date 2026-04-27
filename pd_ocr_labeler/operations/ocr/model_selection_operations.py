"""Discover selectable OCR model pairs from trainer output directories."""

from __future__ import annotations

import os
import platform
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class OCRModelOption:
    """Resolved OCR model pair for one selectable option."""

    key: str
    label: str
    detection_weights_path: Path | None
    recognition_weights_path: Path | None
    vocab: str | None = None


class ModelSelectionOperations:
    """Locate OCR model pairs produced by pd-ocr-trainer."""

    DEFAULT_MODEL_KEY = "default"
    DEFAULT_MODEL_LABEL = "Built-in DocTR (default)"
    MODEL_STORE_DIRNAME = "pd-ml-models"

    @staticmethod
    def _stem_signature(stem: str) -> str:
        """Normalize model filename stems to a shared run signature."""
        if "-detection-" in stem:
            return stem.replace("-detection-", "-", 1)
        if "-recognition-" in stem:
            return stem.replace("-recognition-", "-", 1)
        return stem

    @classmethod
    def get_shared_models_root(cls) -> Path:
        """Return OS-aware root where trainer stores fine-tuned models."""
        system_name = platform.system()

        if system_name == "Linux":
            data_home = os.getenv("XDG_DATA_HOME")
            base_dir = (
                Path(data_home).expanduser()
                if data_home
                else Path.home() / ".local" / "share"
            )
        elif system_name == "Darwin":
            base_dir = Path.home() / "Library" / "Application Support"
        elif system_name == "Windows":
            appdata = os.getenv("APPDATA")
            base_dir = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
        else:
            base_dir = Path.home() / ".local" / "share"

        return base_dir / cls.MODEL_STORE_DIRNAME

    @classmethod
    def discover_model_options(cls) -> tuple[dict[str, OCRModelOption], dict[str, str]]:
        """Return model option metadata and labels keyed by selectable option id."""
        options: dict[str, OCRModelOption] = {
            cls.DEFAULT_MODEL_KEY: OCRModelOption(
                key=cls.DEFAULT_MODEL_KEY,
                label=cls.DEFAULT_MODEL_LABEL,
                detection_weights_path=None,
                recognition_weights_path=None,
            )
        }

        root = cls.get_shared_models_root()
        if not root.exists() or not root.is_dir():
            return options, {k: v.label for k, v in options.items()}

        for profile_dir in sorted(
            (p for p in root.iterdir() if p.is_dir()), key=lambda p: p.name.lower()
        ):
            detection_dir = profile_dir / "detection"
            recognition_dir = profile_dir / "recognition"
            if not detection_dir.is_dir() or not recognition_dir.is_dir():
                continue

            detection_by_signature = {
                cls._stem_signature(p.stem): p
                for p in detection_dir.glob("*.pt")
                if p.is_file()
            }
            recognition_by_signature = {
                cls._stem_signature(p.stem): p
                for p in recognition_dir.glob("*.pt")
                if p.is_file()
            }

            for signature in sorted(
                set(detection_by_signature).intersection(recognition_by_signature)
            ):
                key = f"{profile_dir.name}/{signature}"
                label = f"{profile_dir.name}: {signature}"
                recognition_path = recognition_by_signature[signature]
                vocab_path = recognition_path.with_suffix(".vocab")
                vocab_chars: str | None = None
                if vocab_path.is_file():
                    try:
                        vocab_chars = vocab_path.read_text(encoding="utf-8")
                    except OSError:
                        vocab_chars = None
                options[key] = OCRModelOption(
                    key=key,
                    label=label,
                    detection_weights_path=detection_by_signature[signature],
                    recognition_weights_path=recognition_path,
                    vocab=vocab_chars,
                )

        labels = {k: option.label for k, option in options.items()}
        return options, labels
