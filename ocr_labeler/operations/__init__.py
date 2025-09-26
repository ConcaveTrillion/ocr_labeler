"""Operations for the OCR labeler."""

from .ocr import LineOperations, PageOperations
from .persistence import ProjectOperations

__all__ = ["PageOperations", "LineOperations", "ProjectOperations"]
