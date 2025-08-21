"""Backward compatible shim for modularized views.

The monolithic implementation was split into smaller components under
``ocr_labeler.views``. Import and re-export the new ``LabelerView`` so existing
imports (``from ocr_labeler.view import LabelerView``) keep working.
"""

from .views.main_view import LabelerView  # noqa: F401

