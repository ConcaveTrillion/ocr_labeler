"""Shared constants for the OCR labeler application."""

from __future__ import annotations

# Word label keys used in word_labels lists and word_attributes persistence.
WORD_LABEL_ITALIC = "italic"
WORD_LABEL_SMALL_CAPS = "small_caps"
WORD_LABEL_BLACKLETTER = "blackletter"
WORD_LABEL_FOOTNOTE = "footnote"
WORD_LABEL_LEFT_FOOTNOTE = "left_footnote"
WORD_LABEL_RIGHT_FOOTNOTE = "right_footnote"
WORD_LABEL_VALIDATED = "validated"

# Supported image file extensions for page images.
IMAGE_EXTS = (".png", ".jpg", ".jpeg")
