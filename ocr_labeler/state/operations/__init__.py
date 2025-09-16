"""Operations module for OCR labeling tasks.

This module contains all I/O and persistence operations, separated from
state management to maintain clear architectural boundaries.
"""

from .line_operations import LineOperations
from .page_operations import PageOperations
from .project_operations import ProjectOperations

__all__ = ["LineOperations", "PageOperations", "ProjectOperations"]
