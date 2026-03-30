"""Callback type definitions for the OCR labeler views."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable, Optional

from nicegui import events

PageActionEvent = events.ClickEventArguments | None
PageActionCallback = Callable[[PageActionEvent], Awaitable[None]]
ProjectNavigateCallback = Callable[[PageActionEvent], Awaitable[None]]
ProjectGotoCallback = Callable[
    [object, events.GenericEventArguments | None], Awaitable[None]
]


@dataclass
class PageActionCallbacks:
    """Structured async callbacks for page-level action workflows."""

    save_page: Optional[PageActionCallback] = None
    load_page: Optional[PageActionCallback] = None
    refine_bboxes: Optional[PageActionCallback] = None
    expand_refine_bboxes: Optional[PageActionCallback] = None
    reload_ocr: Optional[PageActionCallback] = None
    rematch_gt: Optional[PageActionCallback] = None
