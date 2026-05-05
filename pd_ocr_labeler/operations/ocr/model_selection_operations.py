"""Discover selectable OCR model pairs from Hugging Face and trainer outputs."""

from __future__ import annotations

import logging
import os
import platform
import re
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


HF_DEFAULT_REPO = "CT2534/pd-ocr-models"
HF_DEFAULT_DETECTION_FILENAME = "detection/pd-all-detection-model-finetuned.pt"
HF_DEFAULT_RECOGNITION_FILENAME = "recognition/pd-all-recognition-model-finetuned.pt"


@dataclass(frozen=True)
class OCRModelOption:
    """Resolved OCR model pair for one selectable option.

    Local options carry resolved ``.pt`` paths in
    ``detection_weights_path`` / ``recognition_weights_path``. Hugging Face
    options leave those as ``None`` until the weights are downloaded; the
    ``hf_*`` fields describe what to fetch.
    """

    key: str
    label: str
    detection_weights_path: Path | None
    recognition_weights_path: Path | None
    vocab: str | None = None
    hf_repo: str | None = None
    hf_detection_filename: str | None = None
    hf_recognition_filename: str | None = None
    hf_revision: str | None = None
    hf_last_modified: datetime | None = None

    @property
    def is_huggingface(self) -> bool:
        return bool(self.hf_repo)


class ModelSelectionOperations:
    """Locate OCR model pairs for the labeler's predictor wiring.

    Sources, in priority order:
    - Hugging Face: a published default repo (``HF_DEFAULT_REPO``) plus any
      pinned-revision options the user has configured.
    - Local: ``.pt`` pairs produced by ``pd-ocr-trainer`` under the OS-aware
      shared models root (``pd-ml-models``).
    - Built-in: the ``"default"`` key, which falls back to
      ``get_default_doctr_predictor()`` (stock Mindee weights).
    """

    DEFAULT_MODEL_KEY = "default"
    DEFAULT_MODEL_LABEL = "Built-in DocTR (stock Mindee fallback)"
    HF_LATEST_KEY = "huggingface"
    HF_PINNED_KEY_PREFIX = "huggingface@"
    MODEL_STORE_DIRNAME = "pd-ml-models"
    PREFERRED_ALL_PROFILES = {"all", "base-ocr"}
    TIMESTAMP_SUFFIX_PATTERN = re.compile(r"(\d{10})$")

    @classmethod
    def hf_pinned_key(cls, revision: str) -> str:
        return f"{cls.HF_PINNED_KEY_PREFIX}{revision.strip()}"

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
                if not option.is_huggingface
                and key != cls.DEFAULT_MODEL_KEY
                and option.detection_weights_path is not None
            ]
        elif component == "recognition":
            keys = [
                key
                for key, option in options.items()
                if not option.is_huggingface
                and key != cls.DEFAULT_MODEL_KEY
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
    def _build_hf_option(
        cls,
        *,
        key: str,
        label: str,
        revision: str | None,
        last_modified: datetime | None,
    ) -> OCRModelOption:
        return OCRModelOption(
            key=key,
            label=label,
            detection_weights_path=None,
            recognition_weights_path=None,
            hf_repo=HF_DEFAULT_REPO,
            hf_detection_filename=HF_DEFAULT_DETECTION_FILENAME,
            hf_recognition_filename=HF_DEFAULT_RECOGNITION_FILENAME,
            hf_revision=revision,
            hf_last_modified=last_modified,
        )

    @classmethod
    def fetch_hf_last_modified(
        cls, *, revision: str | None = None, timeout: float = 5.0
    ) -> datetime | None:
        """Return the published HF model's last-modified timestamp.

        Returns ``None`` when ``huggingface_hub`` is unavailable, the network
        is unreachable, or the repository has no ``last_modified`` metadata.
        Logs the failure but never raises.
        """
        try:
            from huggingface_hub import HfApi
        except ImportError:
            logger.debug("huggingface_hub not installed; skipping HF probe")
            return None

        try:
            info = HfApi().model_info(
                HF_DEFAULT_REPO,
                revision=revision,
                timeout=timeout,
            )
        except Exception as exc:
            logger.info(
                "HF probe failed for %s@%s: %s",
                HF_DEFAULT_REPO,
                revision or "main",
                exc,
            )
            return None

        last_modified = getattr(info, "last_modified", None)
        if last_modified is None:
            return None
        if isinstance(last_modified, datetime) and last_modified.tzinfo is None:
            last_modified = last_modified.replace(tzinfo=timezone.utc)
        return last_modified

    @classmethod
    def download_hf_weights(
        cls, option: OCRModelOption
    ) -> tuple[Path, Path, str | None]:
        """Download HF detection + recognition weights and any vocab sidecar.

        Returns ``(detection_path, recognition_path, vocab_text)``. Raises
        ``RuntimeError`` if ``huggingface_hub`` is missing or the download
        fails (caller is expected to surface a notification).
        """
        if not option.is_huggingface:
            raise ValueError(
                f"download_hf_weights called on non-HF option {option.key!r}"
            )
        if not option.hf_detection_filename or not option.hf_recognition_filename:
            raise ValueError(
                f"HF option {option.key!r} is missing detection/recognition filenames"
            )

        try:
            from pd_book_tools.hf import OCR_MODEL_SIDECARS, hf_download
        except ImportError as exc:
            raise RuntimeError(
                "pd_book_tools.hf is required to download published OCR models. "
                "Install/upgrade pd-book-tools via `make setup`."
            ) from exc

        det_path = hf_download(
            option.hf_repo,  # type: ignore[arg-type]
            option.hf_detection_filename,
            option.hf_revision,
            sidecars=OCR_MODEL_SIDECARS,
        )
        reco_path = hf_download(
            option.hf_repo,  # type: ignore[arg-type]
            option.hf_recognition_filename,
            option.hf_revision,
            sidecars=OCR_MODEL_SIDECARS,
        )

        vocab_path = reco_path.with_suffix(".vocab")
        vocab_text: str | None = None
        if vocab_path.is_file():
            try:
                vocab_text = vocab_path.read_text(encoding="utf-8")
            except OSError:
                vocab_text = None

        return det_path, reco_path, vocab_text

    @classmethod
    def discover_local_models(cls) -> dict[str, OCRModelOption]:
        """Return locally-discovered OCR options keyed by ``profile/signature``."""
        options: dict[str, OCRModelOption] = {}
        root = cls.get_shared_models_root()
        if not root.exists() or not root.is_dir():
            return options

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
        return options

    @classmethod
    def latest_local_mtime(cls, options: dict[str, OCRModelOption]) -> datetime | None:
        """Return the most recent mtime across local detection/recognition files."""
        latest: datetime | None = None
        for option in options.values():
            if option.is_huggingface:
                continue
            for path in (
                option.detection_weights_path,
                option.recognition_weights_path,
            ):
                if path is None or not path.is_file():
                    continue
                try:
                    mtime = datetime.fromtimestamp(
                        path.stat().st_mtime, tz=timezone.utc
                    )
                except OSError:
                    continue
                if latest is None or mtime > latest:
                    latest = mtime
        return latest

    @classmethod
    def discover_model_options(
        cls,
        *,
        hf_pinned_revision: str | None = None,
        hf_probe_timeout: float = 5.0,
    ) -> tuple[dict[str, OCRModelOption], dict[str, str]]:
        """Return all selectable model options keyed by option id.

        Always includes:
        - ``HF_LATEST_KEY`` — the published HF repo at ``main`` (latest).
          When the network probe succeeds, ``hf_last_modified`` is populated.
        - ``DEFAULT_MODEL_KEY`` — stock Mindee fallback.
        - All locally-discovered fine-tuned options.

        When ``hf_pinned_revision`` is given, an additional pinned HF option
        keyed ``huggingface@<revision>`` is included so the user can switch
        between ``latest`` and the pinned revision in the UI.
        """
        options: dict[str, OCRModelOption] = {}

        hf_latest_modified = cls.fetch_hf_last_modified(timeout=hf_probe_timeout)
        options[cls.HF_LATEST_KEY] = cls._build_hf_option(
            key=cls.HF_LATEST_KEY,
            label=f"Hugging Face: {HF_DEFAULT_REPO} (latest)",
            revision=None,
            last_modified=hf_latest_modified,
        )

        if hf_pinned_revision:
            pinned_key = cls.hf_pinned_key(hf_pinned_revision)
            pinned_modified = cls.fetch_hf_last_modified(
                revision=hf_pinned_revision, timeout=hf_probe_timeout
            )
            options[pinned_key] = cls._build_hf_option(
                key=pinned_key,
                label=f"Hugging Face: {HF_DEFAULT_REPO}@{hf_pinned_revision}",
                revision=hf_pinned_revision,
                last_modified=pinned_modified,
            )

        options.update(cls.discover_local_models())

        options[cls.DEFAULT_MODEL_KEY] = OCRModelOption(
            key=cls.DEFAULT_MODEL_KEY,
            label=cls.DEFAULT_MODEL_LABEL,
            detection_weights_path=None,
            recognition_weights_path=None,
        )

        labels = {key: option.label for key, option in options.items()}
        return options, labels

    @classmethod
    def update_hf_last_modified(
        cls,
        options: dict[str, OCRModelOption],
        *,
        hf_probe_timeout: float = 5.0,
    ) -> dict[str, OCRModelOption]:
        """Re-probe HF for any HF option and return an updated dict."""
        updated = dict(options)
        for key, option in options.items():
            if not option.is_huggingface:
                continue
            last_modified = cls.fetch_hf_last_modified(
                revision=option.hf_revision, timeout=hf_probe_timeout
            )
            updated[key] = replace(option, hf_last_modified=last_modified)
        return updated

    @classmethod
    def find_preferred_all_model_key(
        cls, options: dict[str, OCRModelOption]
    ) -> str | None:
        """Return the latest preferred fine-tuned local key for the all profile."""
        keys = [
            key
            for key, option in options.items()
            if not option.is_huggingface
            and key != cls.DEFAULT_MODEL_KEY
            and cls._is_preferred_profile_key(key)
            and option.detection_weights_path is not None
            and option.recognition_weights_path is not None
        ]
        return cls._latest_key(keys)

    @classmethod
    def find_latest_detection_model_key(
        cls, options: dict[str, OCRModelOption]
    ) -> str | None:
        """Return the latest available local detection model key."""
        return cls._latest_key(cls._candidate_keys_for_component(options, "detection"))

    @classmethod
    def find_latest_recognition_model_key(
        cls, options: dict[str, OCRModelOption]
    ) -> str | None:
        """Return the latest available local recognition model key."""
        return cls._latest_key(
            cls._candidate_keys_for_component(options, "recognition")
        )

    @classmethod
    def pick_default_keys(
        cls, options: dict[str, OCRModelOption]
    ) -> tuple[str, str, str]:
        """Pick default detection / recognition keys plus a status reason.

        Priority (per user spec):
        1. HF latest if reachable AND (no local OR HF >= newest local mtime).
        2. Latest local fine-tuned model.
        3. HF latest if reachable but with an older timestamp than local — the
           user explicitly asked HF to be preferred when "latest or equal";
           we still fall through to local when the local copy is strictly
           newer.
        4. Stock Mindee fallback (``DEFAULT_MODEL_KEY``).

        Returns ``(detection_key, recognition_key, reason)`` where ``reason``
        is a short string suitable for telemetry / logging / notifications.
        """
        hf_latest = options.get(cls.HF_LATEST_KEY)
        latest_local_detection = cls.find_latest_detection_model_key(options)
        latest_local_recognition = cls.find_latest_recognition_model_key(options)
        local_mtime = cls.latest_local_mtime(options)

        hf_available = hf_latest is not None and hf_latest.hf_last_modified is not None

        if hf_available:
            assert hf_latest is not None  # for type-checkers
            if (
                local_mtime is None
                or hf_latest.hf_last_modified is None
                or hf_latest.hf_last_modified >= local_mtime
            ):
                return cls.HF_LATEST_KEY, cls.HF_LATEST_KEY, "hf-latest"

        if latest_local_detection is not None and latest_local_recognition is not None:
            return (
                latest_local_detection,
                latest_local_recognition,
                "local-newer-than-hf" if hf_available else "local-only-hf-unreachable",
            )

        if hf_latest is not None and not hf_available:
            return (
                cls.DEFAULT_MODEL_KEY,
                cls.DEFAULT_MODEL_KEY,
                "hf-unreachable-no-local",
            )

        if hf_available:
            return cls.HF_LATEST_KEY, cls.HF_LATEST_KEY, "hf-only"

        return cls.DEFAULT_MODEL_KEY, cls.DEFAULT_MODEL_KEY, "stock-fallback"
