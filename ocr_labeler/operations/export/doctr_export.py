"""DocTR training dataset export operations.

This module builds DocTR-format detection and recognition training datasets
from labeled OCR data.  It delegates low-level image writing, polygon/crop
generation, and label-JSON accumulation to the
:class:`~pd_book_tools.ocr.page.Page` export methods while orchestrating page
loading, validation gating, GT-first resolution, and optional word filtering.

It can produce:

* **Standard** datasets (detection polygons + recognition word crops for every
  word on validated pages).
* **Labeled / filtered** datasets where only words carrying a specific
  ``text_style_label`` (e.g. *italics*, *small caps*, *blackletter*) or
  ``word_component`` are included — useful for training specialised recognition
  models.
* **Classification** datasets where each recognition label is a dict
  containing the ground-truth text *and* a boolean map of all tracked
  style/component flags.

Ground-truth text and bounding boxes are resolved with **GT-first** semantics:
``word.ground_truth_text`` (falling back to ``word.text``) and
``word.ground_truth_bounding_box`` (falling back to ``word.bounding_box``).

Pages are only exported when they pass a configurable validation predicate –
the default requires every word to have ``"validated"`` in its
``word_labels``.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Sequence

from cv2 import imread as cv2_imread
from pd_book_tools.ocr.page import Page
from pd_book_tools.ocr.word import Word

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExportStats:
    """Summary statistics for an export run."""

    pages_scanned: int = 0
    pages_exported: int = 0
    pages_skipped_no_image: int = 0
    pages_skipped_not_validated: int = 0
    words_exported_detection: int = 0
    words_exported_recognition: int = 0
    words_skipped_no_text: int = 0

    def summary(self) -> str:
        lines = [
            f"Pages scanned:       {self.pages_scanned}",
            f"Pages exported:      {self.pages_exported}",
            f"  skipped (no image):       {self.pages_skipped_no_image}",
            f"  skipped (not validated):  {self.pages_skipped_not_validated}",
            f"Words (detection):   {self.words_exported_detection}",
            f"Words (recognition): {self.words_exported_recognition}",
            f"  skipped (no text):        {self.words_skipped_no_text}",
        ]
        return "\n".join(lines)


@dataclass
class _MutableStats:
    """Internal mutable accumulator used while building an export."""

    pages_scanned: int = 0
    pages_exported: int = 0
    pages_skipped_no_image: int = 0
    pages_skipped_not_validated: int = 0
    words_exported_detection: int = 0
    words_exported_recognition: int = 0
    words_skipped_no_text: int = 0

    def freeze(self) -> ExportStats:
        return ExportStats(
            **{k: getattr(self, k) for k in ExportStats.__dataclass_fields__}
        )


@dataclass(frozen=True)
class WordFilter:
    """Predicate for selecting words to include in a labeled export.

    When *style_labels* is non-empty, only words whose ``text_style_labels``
    intersect with the requested set are included.  When *word_components* is
    non-empty a similar check is performed against ``word_components``.

    An empty filter (the default) matches **all** words.
    """

    style_labels: frozenset[str] = field(default_factory=frozenset)
    word_components: frozenset[str] = field(default_factory=frozenset)

    def matches(self, word: Word) -> bool:  # type: ignore[override]
        if not self.style_labels and not self.word_components:
            return True

        if self.style_labels:
            word_styles = set(getattr(word, "text_style_labels", None) or [])
            if not word_styles & self.style_labels:
                return False

        if self.word_components:
            word_comps = set(getattr(word, "word_components", None) or [])
            if not word_comps & self.word_components:
                return False

        return True


# ---------------------------------------------------------------------------
# Classification label helpers
# ---------------------------------------------------------------------------

#: The full set of style labels tracked for multivariate classification.
CLASSIFICATION_STYLE_LABELS: tuple[str, ...] = (
    "italics",
    "small caps",
    "blackletter",
    "bold",
    "all caps",
    "underline",
    "strikethrough",
    "monospace",
    "handwritten",
)

CLASSIFICATION_WORD_COMPONENTS: tuple[str, ...] = (
    "superscript",
    "subscript",
    "footnote marker",
    "drop cap",
)


def _word_classification_dict(word: Word) -> dict[str, bool]:
    """Return a {label: bool} mapping of all classification attributes."""
    word_styles = set(getattr(word, "text_style_labels", None) or [])
    word_comps = set(getattr(word, "word_components", None) or [])
    result: dict[str, bool] = {}
    for label in CLASSIFICATION_STYLE_LABELS:
        result[label] = label in word_styles
    for comp in CLASSIFICATION_WORD_COMPONENTS:
        result[comp] = comp in word_comps
    return result


def _classification_label_formatter(word: Word) -> dict[str, Any]:
    """Label formatter for classification export mode.

    Used as the *label_formatter* callback for
    :meth:`Page.generate_doctr_recognition_training_set`.
    """
    return {
        "text": word.ground_truth_text or word.text or "",
        "labels": _word_classification_dict(word),
    }


# ---------------------------------------------------------------------------
# Validation predicates
# ---------------------------------------------------------------------------


def page_is_validated(page: Page) -> bool:
    """Default validation predicate: True when ALL words carry 'validated'.

    A page with no words is considered not validated.
    """
    words = page.words
    if not words:
        return False
    return all("validated" in (getattr(w, "word_labels", None) or []) for w in words)


def page_always_valid(_page: Page) -> bool:
    """Permissive predicate that accepts every page (useful for bulk exports)."""
    return True


def page_has_ground_truth(page: Page) -> bool:
    """True when at least one word has non-empty ground_truth_text."""
    for word in page.words:
        if getattr(word, "ground_truth_text", None):
            return True
    return False


# ---------------------------------------------------------------------------
# Export status helpers
# ---------------------------------------------------------------------------


class ExportStatus:
    """Status of the DocTR export for a page."""

    NOT_EXPORTED = "not_exported"
    EXPORTED = "exported"
    STALE = "stale"  # exported but page was modified since


def check_page_export_status(
    output_dir: Path,
    prefix: str,
    page_index: int,
    saved_json_path: Path | None = None,
) -> str:
    """Check whether export data exists for a page and if it's current.

    Parameters
    ----------
    output_dir : Path
        The project-scoped export output directory.
    prefix : str
        The prefix used in export filenames (typically project_id).
    page_index : int
        The page index (used by pd-book-tools in filenames).
    saved_json_path : Path | None
        Path to the saved labeled JSON for this page.  When provided and
        its mtime is newer than the export image, the export is ``STALE``.

    Returns
    -------
    str
        One of :attr:`ExportStatus.NOT_EXPORTED`,
        :attr:`ExportStatus.EXPORTED`, or :attr:`ExportStatus.STALE`.
    """
    detection_image = output_dir / "detection" / "images" / f"{prefix}_{page_index}.png"
    if not detection_image.exists():
        return ExportStatus.NOT_EXPORTED

    if saved_json_path is not None and saved_json_path.exists():
        export_mtime = detection_image.stat().st_mtime
        saved_mtime = saved_json_path.stat().st_mtime
        if saved_mtime > export_mtime:
            return ExportStatus.STALE

    return ExportStatus.EXPORTED


# ---------------------------------------------------------------------------
# GT-first preparation
# ---------------------------------------------------------------------------


def _prepare_page_gt_first(page: Page) -> None:
    """Resolve GT-first text and bounding boxes on all words **in place**.

    After this call every word's ``ground_truth_text`` is set (falling back to
    OCR ``text``) and ``bounding_box`` is replaced with
    ``ground_truth_bounding_box`` where available.
    """
    for word in page.words:
        if not word.ground_truth_text:
            word.ground_truth_text = word.text or ""
        gt_bbox = getattr(word, "ground_truth_bounding_box", None)
        if gt_bbox is not None:
            word.bounding_box = gt_bbox


# ---------------------------------------------------------------------------
# Main export class
# ---------------------------------------------------------------------------


class DocTRExportOperations:
    """Build DocTR-format training datasets from labeled OCR pages.

    Low-level image writing, polygon/crop generation, and label-JSON
    accumulation are delegated to
    :meth:`~pd_book_tools.ocr.page.Page.generate_doctr_detection_training_set`
    and
    :meth:`~pd_book_tools.ocr.page.Page.generate_doctr_recognition_training_set`.

    Parameters
    ----------
    labeled_data_dir : Path
        Directory containing ``<project_id>_<n>.json`` / ``.png`` pairs.
    output_dir : Path
        Root output directory for the generated dataset.
    validation_predicate : callable, optional
        ``(Page) -> bool`` — only pages that pass are exported.
        Defaults to :func:`page_is_validated`.
    train_val_split : float, optional
        Fraction of pages directed to the *training* set.  The remainder goes
        to the *validation* set.  Set to ``1.0`` to export everything as
        training data.  Default ``1.0`` (caller manages split externally).
    """

    def __init__(
        self,
        labeled_data_dir: Path,
        output_dir: Path,
        *,
        validation_predicate: Callable[[Page], bool] | None = None,
        train_val_split: float = 1.0,
    ):
        self.labeled_data_dir = Path(labeled_data_dir)
        self.output_dir = Path(output_dir)
        self.validation_predicate = validation_predicate or page_is_validated
        self.train_val_split = max(0.0, min(1.0, train_val_split))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def export_standard(
        self,
        *,
        prefix: str = "",
        detection: bool = True,
        recognition: bool = True,
    ) -> ExportStats:
        """Export standard detection + recognition datasets (all words).

        Parameters
        ----------
        prefix : str
            Optional prefix prepended to exported image filenames.
        detection : bool
            Whether to generate detection data.
        recognition : bool
            Whether to generate recognition data.
        """
        return self._run_export(
            word_filter=None,
            prefix=prefix,
            detection=detection,
            recognition=recognition,
            classification=False,
        )

    def export_labeled(
        self,
        *,
        style_labels: Sequence[str] = (),
        word_components: Sequence[str] = (),
        prefix: str = "",
        detection: bool = True,
        recognition: bool = True,
    ) -> ExportStats:
        """Export datasets containing only words that match the given labels.

        This is for training specialised recognition models (e.g. italic-only).
        Words that do not match the filter are excluded from both detection
        polygons and recognition crops.

        Parameters
        ----------
        style_labels : sequence of str
            Text style labels to match (e.g. ``["italics"]``).
        word_components : sequence of str
            Word components to match (e.g. ``["footnote marker"]``).
        prefix : str
            Optional filename prefix.
        detection : bool
            Whether to generate detection data.
        recognition : bool
            Whether to generate recognition data.
        """
        wf = WordFilter(
            style_labels=frozenset(style_labels),
            word_components=frozenset(word_components),
        )
        return self._run_export(
            word_filter=wf,
            prefix=prefix,
            detection=detection,
            recognition=recognition,
            classification=False,
        )

    def export_classification(
        self,
        *,
        prefix: str = "",
    ) -> ExportStats:
        """Export recognition dataset with multivariate classification labels.

        Each word receives a label dict of all tracked style/component flags.
        This produces a recognition ``labels.json`` whose values are dicts
        instead of plain strings::

            {
              "image.png": {
                "text": "word",
                "labels": {"italics": true, "small caps": false, ...}
              }
            }

        Detection data is also generated (plain polygon format).
        """
        return self._run_export(
            word_filter=None,
            prefix=prefix,
            detection=True,
            recognition=True,
            classification=True,
        )

    # ------------------------------------------------------------------
    # Internal: orchestration
    # ------------------------------------------------------------------

    def _run_export(
        self,
        *,
        word_filter: WordFilter | None,
        prefix: str,
        detection: bool,
        recognition: bool,
        classification: bool,
    ) -> ExportStats:
        stats = _MutableStats()
        json_files = sorted(self.labeled_data_dir.glob("*.json"))
        if not json_files:
            logger.warning("No JSON files found in %s", self.labeled_data_dir)
            return stats.freeze()

        self.output_dir.mkdir(parents=True, exist_ok=True)

        for json_path in json_files:
            stats.pages_scanned += 1
            try:
                page, image_path = self._load_labeled_page(json_path)
            except Exception:
                logger.warning("Failed to load %s", json_path, exc_info=True)
                continue

            if page is None:
                continue

            # Validation gate
            if not self.validation_predicate(page):
                stats.pages_skipped_not_validated += 1
                logger.debug("Skipping non-validated page: %s", json_path.name)
                continue

            # Load image
            if image_path is None or not image_path.exists():
                stats.pages_skipped_no_image += 1
                logger.warning("No image for %s", json_path.name)
                continue

            cv2_image = cv2_imread(str(image_path))
            if cv2_image is None:
                stats.pages_skipped_no_image += 1
                logger.warning("cv2 failed to load image: %s", image_path)
                continue

            page.cv2_numpy_page_image = cv2_image

            # Resolve GT-first text and bboxes on all words
            _prepare_page_gt_first(page)

            # Build the prefix incorporating the JSON stem for uniqueness
            page_prefix = json_path.stem
            if prefix:
                page_prefix = f"{prefix}_{page_prefix}"

            # Build word-filter callable for pd-book-tools
            wf_callable: Callable[[Word], bool] | None = None
            if word_filter is not None:
                wf_callable = word_filter.matches

            # Pre-compute stats (pd-book-tools methods don't return counts)
            words = page.words
            if wf_callable is not None:
                filtered_words = [w for w in words if wf_callable(w)]
            else:
                filtered_words = words

            if not filtered_words:
                logger.debug("No matching words on page %s", json_path.name)
                stats.pages_exported += 1
                continue

            words_with_text = [w for w in filtered_words if w.ground_truth_text]
            no_text_count = len(filtered_words) - len(words_with_text)

            # --- Detection (delegated to pd-book-tools) ---
            if detection:
                page.generate_doctr_detection_training_set(
                    output_path=self.output_dir,
                    prefix=page_prefix,
                    word_filter=wf_callable,
                )
                stats.words_exported_detection += len(filtered_words)

            # --- Recognition (delegated to pd-book-tools) ---
            if recognition:
                label_formatter = (
                    _classification_label_formatter if classification else None
                )
                page.generate_doctr_recognition_training_set(
                    output_path=self.output_dir,
                    prefix=page_prefix,
                    word_filter=wf_callable,
                    label_formatter=label_formatter,
                )
                stats.words_exported_recognition += len(words_with_text)
                stats.words_skipped_no_text += no_text_count

            stats.pages_exported += 1

        return stats.freeze()

    # ------------------------------------------------------------------
    # Internal: page loading
    # ------------------------------------------------------------------

    def _load_labeled_page(self, json_path: Path) -> tuple[Page | None, Path | None]:
        """Load a Page object and resolve its source image path.

        Labels (``text_style_labels``, ``word_components``, ``word_labels``)
        are restored directly from the serialised page dict via
        ``Page.from_dict()``.
        """
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            logger.warning("Invalid JSON structure in %s", json_path)
            return None, None

        page_dict = self._extract_page_dict(data)
        if page_dict is None:
            return None, None

        page = Page.from_dict(page_dict)

        # Resolve image path
        image_path = self._resolve_image_path(json_path, data)
        return page, image_path

    def _extract_page_dict(self, data: dict[str, Any]) -> dict[str, Any] | None:
        """Extract the page dictionary from either format.

        Supports both the ``ocr_labeler.user_page`` envelope schema and the
        older ``{"pages": [...]}`` layout.
        """
        if _is_envelope(data):
            payload = data.get("payload", {})
            if isinstance(payload, dict):
                page = payload.get("page")
                if isinstance(page, dict):
                    return page
            return None

        pages = data.get("pages")
        if isinstance(pages, list) and pages and isinstance(pages[0], dict):
            return pages[0]
        return None

    def _resolve_image_path(self, json_path: Path, data: dict[str, Any]) -> Path | None:
        """Find the PNG/JPG image corresponding to a labeled JSON file.

        Priority:
        1. Same-directory image with matching stem (``<stem>.png``, ``.jpg``)
        2. Source path recorded in the JSON metadata (relative to labeled dir)
        """
        stem = json_path.stem
        parent = json_path.parent
        for ext in (".png", ".jpg", ".jpeg"):
            candidate = parent / f"{stem}{ext}"
            if candidate.exists():
                return candidate

        # Fallback: source_path / source.image_path
        source_path_str = None
        if _is_envelope(data):
            source = data.get("source", {})
            if isinstance(source, dict):
                source_path_str = source.get("image_path")
        else:
            source_path_str = data.get("source_path")

        if source_path_str:
            candidate = parent / Path(source_path_str).name
            if candidate.exists():
                return candidate

        return None


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _is_envelope(data: dict[str, Any]) -> bool:
    schema = data.get("schema")
    return isinstance(schema, dict) and schema.get("name") == "ocr_labeler.user_page"


def _resolve_text(word: Word) -> str:
    """Return GT text if present, else OCR text."""
    gt = getattr(word, "ground_truth_text", None)
    if gt:
        return gt
    return getattr(word, "text", "") or ""


def _resolve_bbox(word: Word):
    """Return GT bbox if present, else OCR bbox."""
    gt_bbox = getattr(word, "ground_truth_bounding_box", None)
    if gt_bbox is not None:
        return gt_bbox
    return getattr(word, "bounding_box", None)


# ---------------------------------------------------------------------------
# In-memory single-page export (used by the GUI)
# ---------------------------------------------------------------------------


def export_page_to_doctr(
    page: Page,
    image_path: Path,
    output_dir: Path,
    *,
    prefix: str = "",
    detection: bool = True,
    recognition: bool = True,
    word_filter: WordFilter | None = None,
    label_formatter: Callable[[Word], Any] | None = None,
) -> ExportStats:
    """Export a single in-memory page to DocTR training format.

    This bypasses the directory-scan workflow used by
    :class:`DocTRExportOperations` and is designed for interactive GUI use
    where the ``Page`` object is already loaded.

    The caller is responsible for any validation checks *before* calling
    this function (i.e. it does **not** apply a validation predicate).
    """
    stats = _MutableStats(pages_scanned=1)

    cv2_image = cv2_imread(str(image_path))
    if cv2_image is None:
        logger.warning("cv2 failed to load image: %s", image_path)
        stats.pages_skipped_no_image += 1
        return stats.freeze()

    page.cv2_numpy_page_image = cv2_image
    _prepare_page_gt_first(page)

    output_dir.mkdir(parents=True, exist_ok=True)

    page_prefix = prefix or image_path.stem

    words = page.words
    if not words:
        stats.pages_exported += 1
        return stats.freeze()

    # Build word_filter callable for pd-book-tools if a WordFilter is given
    _wf_callable = word_filter.matches if word_filter else None

    words_with_text = [w for w in words if w.ground_truth_text]
    if word_filter:
        words = [w for w in words if word_filter.matches(w)]
        words_with_text = [w for w in words if w.ground_truth_text]
    no_text_count = len(words) - len(words_with_text)

    if detection:
        page.generate_doctr_detection_training_set(
            output_path=output_dir,
            prefix=page_prefix,
            word_filter=_wf_callable,
        )
        stats.words_exported_detection += len(words)

    if recognition:
        page.generate_doctr_recognition_training_set(
            output_path=output_dir,
            prefix=page_prefix,
            word_filter=_wf_callable,
            label_formatter=label_formatter,
        )
        stats.words_exported_recognition += len(words_with_text)
        stats.words_skipped_no_text += no_text_count

    stats.pages_exported += 1
    return stats.freeze()
