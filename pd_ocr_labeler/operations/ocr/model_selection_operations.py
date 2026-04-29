"""Discover selectable OCR model pairs from trainer output directories."""

from __future__ import annotations

import os
import platform
import re
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
    PREFERRED_ALL_PROFILES = {"all", "base-ocr"}
    TIMESTAMP_SUFFIX_PATTERN = re.compile(r"(\d{10})$")

    @classmethod
    def _is_preferred_profile_key(cls, key: str) -> bool:
        profile_name = key.split("/", 1)[0].strip().lower()
        return profile_name in cls.PREFERRED_ALL_PROFILES

    @classmethod
    def _latest_key(cls, keys: list[str]) -> str | None:
        if not keys:
            return None

        def sort_key(key: str) -> tuple[int, str, str]:
            signature = key.split("/", 1)[1] if "/" in key else key
            match = cls.TIMESTAMP_SUFFIX_PATTERN.search(signature)
            timestamp = match.group(1) if match else ""
            return (1 if match else 0, timestamp, key)

        return max(keys, key=sort_key)

    @classmethod
    def _candidate_keys_for_component(
        cls,
        options: dict[str, OCRModelOption],
        component: str,
    ) -> list[str]:
        if component == "detection":
            keys = [
                key
                for key, option in options.items()
                if key != cls.DEFAULT_MODEL_KEY
                and option.detection_weights_path is not None
            ]
        elif component == "recognition":
            keys = [
                key
                for key, option in options.items()
                if key != cls.DEFAULT_MODEL_KEY
                and option.recognition_weights_path is not None
            ]
        else:
            raise ValueError(f"Unknown component '{component}'")

        preferred = [key for key in keys if cls._is_preferred_profile_key(key)]
        return preferred or keys

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

    @classmethod
    def find_preferred_all_model_key(
        cls, options: dict[str, OCRModelOption]
    ) -> str | None:
        """Return the latest preferred fine-tuned key for the global/all profile."""
        keys = [
            key
            for key, option in options.items()
            if key != cls.DEFAULT_MODEL_KEY
            and cls._is_preferred_profile_key(key)
            and option.detection_weights_path is not None
            and option.recognition_weights_path is not None
        ]
        return cls._latest_key(keys)

    @classmethod
    def find_latest_detection_model_key(
        cls, options: dict[str, OCRModelOption]
    ) -> str | None:
        """Return the latest available detection model key (prefer all/base-ocr profiles)."""
        return cls._latest_key(cls._candidate_keys_for_component(options, "detection"))

    @classmethod
    def find_latest_recognition_model_key(
        cls, options: dict[str, OCRModelOption]
    ) -> str | None:
        """Return the latest available recognition model key (prefer all/base-ocr profiles)."""
        return cls._latest_key(
            cls._candidate_keys_for_component(options, "recognition")
        )
