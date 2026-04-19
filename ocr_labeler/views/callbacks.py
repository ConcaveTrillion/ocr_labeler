"""Callback type definitions for the OCR labeler views."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable

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

    save_page: PageActionCallback | None = None
    save_project: PageActionCallback | None = None
    load_page: PageActionCallback | None = None
    refine_bboxes: PageActionCallback | None = None
    expand_refine_bboxes: PageActionCallback | None = None
    reload_ocr: PageActionCallback | None = None
    rematch_gt: PageActionCallback | None = None
