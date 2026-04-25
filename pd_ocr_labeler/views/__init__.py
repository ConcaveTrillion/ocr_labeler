"""Modular view components for the OCR Labeler UI.

This package contains the individual UI components that make up the main interface:
- main_view.LabelerView: Main orchestrator with header + content composition
- header.HeaderBar: Project controls and navigation
- content.ContentArea: Main content splitter with image/text tabs
- image_tabs.ImageTabs: Overlay image variants display
- text_tabs.TextTabs: OCR vs ground truth text comparison
- word_match.WordMatchView: Word-level matching with color coding
- project_navigation_controls.ProjectNavigationControls: Project navigation controls
- project_load_controls.ProjectLoadControls: Project directory selection
"""

from .main_view import LabelerView

__all__ = ["LabelerView"]
