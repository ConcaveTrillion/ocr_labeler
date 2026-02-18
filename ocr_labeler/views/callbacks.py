"""Callback type definitions for the OCR labeler views."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable, Optional


@dataclass
class PageActionCallbacks:
    """Structured async callbacks for page-level action workflows."""

    save_page: Optional[Callable[[], Awaitable[None]]] = None
    load_page: Optional[Callable[[], Awaitable[None]]] = None
    refine_bboxes: Optional[Callable[[], Awaitable[None]]] = None
    expand_refine_bboxes: Optional[Callable[[], Awaitable[None]]] = None
    reload_ocr: Optional[Callable[[], Awaitable[None]]] = None
