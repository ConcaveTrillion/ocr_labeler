# OCR Labeler TODOs

## Overview

This document outlines the development roadmap for the OCR Labeler application, organized into phases for incremental delivery. The application is a NiceGUI-based web interface for processing public domain book scans with OCR capabilities and ground truth comparison features.

## High-Level Feature Areas

The complete feature set includes:
- Full multi-page navigation with page indexing and bounds checking
- OCR processing with optional predictor injection, reset capabilities, and per-page JSON import/export
- Training/validation export for converting pages to training set files
- Rich page image overlay generation (paragraphs, lines, words, mismatches)
- Bulk operations for bbox expansion, refinement, and image regeneration
- Line filtering (all/mismatches/unvalidated) with visual state indicators
- Per-line rich editor with cropped images and OCR vs GT comparison
- Word-level editing table with thumbnails, inline editing, and bbox operations
- Consistent project naming and font styling

## Current Implementation Gaps

The NiceGUI implementation currently has these limitations:
- Basic project/page loading (single page only) with placeholder OCR dialogs
- No training/validation export integration
- No persistence for Save/Reload OCR operations (buttons are placeholders)
- No bbox operations (expand/refine/reset/crop) implemented
- No word-level editing UI (only whole-line GT text fields)
- No line image thumbnails or state-based border colors
- No split/merge/bbox editing capabilities
- No unmatched ground truth word handling
- No page overlay regeneration after edits
- Limited navigation refinements needed
- No per-page save naming with export prefix scheme
- No font injection implementation
- Incomplete filtering for native OCR lines
- Non-persistent validation state tracking

---

## Development Phases

### Phase 1: Foundational Data & Persistence
**Priority: Critical** | **Tasks: 1-4, 7-8, 35**

#### Data Persistence
1. **OCR Document Save** ✅: Serialize current native Page/PageVM into JSON + copy image (mirror IpynbLabeler.export_ocr_document). Add project/page ID strategy derived from directory name or configurable source.

2. **OCR Document Load** ✅: Implement import functionality for current page index; populate PageVM or native Page fields (import_ocr_document).

3. **Export Prefix Logic** ✅: Add project_id + page index naming with configurable project_id in AppState.

4. **GT Modifications Persistence** ✅: Persist validated line + word-level ground truth modifications back into JSON on save.

#### OCR & Page Management
7. **Reset OCR Logic** ✅: Add reset_ocr functionality to re-run docTR OCR for current image and discard manual edits for that page.

8. **Force Refresh Support** ✅: Support force_refresh flag in run_doctr_ocr_on_images for per-page refresh capabilities.

#### Error Handling
35. **User Notifications** ✅: Add user notifications (toast/snackbar) for save/load success/failure states.

### Phase 2: Basic Operations & Filtering
**Priority: High** | **Tasks: 9-12, 20, 25** | **Status: ✅ Complete**

#### Bounding Box Operations
9. **Refine All Bboxes** ✅: Implement refine_all_bboxes for native Page using page.refine_bounding_boxes(padding_px=2) and refresh overlays.

10. **Expand and Refine** ✅: Implement expand_and_refine_all_bboxes by iterating words → crop_bottom + expand_to_content then page.refine_bounding_boxes.

11. **Refresh Page Images** ✅: Implement refresh_page_images using page.refresh_page_images() and clear image cache.

12. **Refresh Line Images** ✅: Implement refresh_all_line_images for per-line thumbnails regeneration.

#### Line Filtering & Styling
20. **Mismatch Filtering** ✅: Apply mismatch filtering for native line Blocks (compute exact/validated similarly to notebook implementation).

25. **Font Injection** ✅: Inject custom monospace font (if path provided) into NiceGUI using global `<style>` tag.

### Phase 3: Word-Level Editing Core
**Priority: High** | **Tasks: 13-19, 23, 30, 32-33**

#### Word Editing Infrastructure
13. **Word VM Abstraction**: Introduce WordVM abstraction or adapt native Page usage in document mode to expose word operations.

14. **Per-Line Advanced Editor**: Add per-line collapsible advanced editor (similar to IpynbLineEditor) with:
    - Line image thumbnail
    - Word table (image + OCR + GT + buttons)
    - Copy line OCR→GT button
    - Delete line, Mark validated actions

15. **Word Actions**: Implement word delete, merge_left, merge_right actions modifying native line object.

16. **Word Split UI**: Implement word split UI with pixel slider + char index; call underlying split_word and recompute matches.

17. **Edit Bbox UI**: Implement edit bbox UI with margin adjustments, refine, crop top/bottom/all, save functionality.

18. **Quick Crop Buttons**: Add quick crop buttons CT/CB/CA per word row.

19. **Post-Edit Refresh**: After each structural word edit, trigger page.refresh_page_images and image cache invalidation.

#### Ground Truth & State
23. **Fuzz Score Recompute**: Implement per-word fuzz score recompute on GT edit (word.fuzz_score_against).

30. **Cache Invalidation**: Invalidate per-page image cache on any bbox/word edit.

32. **State Persistence**: Persist line validated state & word ground_truth_text in save JSON.

33. **State Restoration**: Reapply validated flags on load (mapping native Block objects by text+index or stable ID hash).

### Phase 4: Enhanced UI & Matching
**Priority: Medium** | **Tasks: 21-22, 24, 26, 34, 40-41**

#### Visual Enhancements
24. **Unmatched GT Handling**: Handle unmatched ground truth words with insertion placeholders and editing/merging behavior. Still need to implement edit/merge tooling.

26. **Consistent Styling**: Add consistent monospace class for OCR/GT text. This is not yet done.

#### Image Overlays
40. **GT Text Overlays**: Add words-with-GT-text overlay generation (cv2_numpy_page_image_word_with_bboxes_and_gt_text) with fallback support.

41. **Mismatch Overlays**: Generate mismatches overlay highlighting mismatched words similarly to notebook implementation.

### Phase 5: Navigation & Multi-Page Support
**Priority: Medium** | **Tasks: 27-29, 37-39**

#### Navigation Enhancements
None currently in the pipeline

#### Multi-Page Support
37. **Multiple Page Loading**: Support loading multiple pages (not just first) with pagination integration (remove intentional limitation).

38. **JSON File Merging**: Support loading all JSON files merging pages with index offsets.

39. **PGDP Loader**: Add PGDP loader to incorporate ground truth (pages.json) and run OCR to match lines.

### Phase 6: Performance & Polish
**Priority: Low** | **Tasks: 31, 36**

31. **Debounced Updates**: Optional debouncing of frequent GT edits before recompute overlays.

36. **Graceful Fallbacks**: Graceful fallback if pd_book_tools or cv2 not installed (disable relevant buttons).

### Phase 7: Testing & Documentation
**Priority: Medium** | **Tasks: 42-48**

#### Testing
42. **Save/Load Tests**: Add unit tests for save/load round trip of simple page with GT edits.

43. **Word Operations Tests**: Add test for word split merging correctness (token counts).

44. **Bbox Logic Tests**: Add test for bbox refine logic updates (ensuring dimensions change).

45. **Filtering Tests**: Add test for filtering logic across matching modes.

#### Documentation
46. **README Updates**: Update README with new NiceGUI labeler features & key shortcuts.

47. **Developer Guide**: Provide developer guide for extending word-level UI.

48. **Troubleshooting**: Add troubleshooting section (missing overlays, predictor failure, font not loading).

### Phase 8: Training & Validation Export
**Priority: Medium** | **Tasks: 5-6**

5. **Export Operations**: Implement export_training and export_validation operations using native Page.convert_to_training_set equivalent; fallback to placeholder if pd_book_tools missing.

6. **Export Integration**: Hook export operations to buttons (currently no-ops).

---

## Distribution & Deployment (Future)

### Phase 9: Distribution Strategy
**Priority: Future** | **Tasks: 49-56**

49. **GPU Support Strategy**: Implement GPU detection and runtime backend selection with CPU fallback and Docker GPU variant.

50. **Standalone Executables**: Create PyInstaller/Nuitka builds bundling Python runtime and dependencies.

51. **Docker Solutions**: Containerized approach with CPU and GPU variants using NVIDIA Container Toolkit.

52. **Platform Installers**: Create platform-specific executables (.exe, .app, AppImage) requiring zero user setup.

53. **Distribution System**: Complete PyInstaller build system with auto-browser opening, icons, splash screens, system tray integration.

54. **Multi-Platform Builds**: GitHub Actions for automated Windows/Mac/Linux distribution creation.

55. **User Documentation**: User-friendly installation and usage instructions for non-technical users.

56. **Release Process**: Automated release pipeline with version tagging and asset distribution.

---

## Implementation Notes

**Current Priority**: Phase 1 (Persistence & Basic Ops) should be implemented first to establish the foundation for all subsequent features.

**Dependencies**: Most tasks depend on proper integration with the `pd-book-tools` library for OCR functionality and the NiceGUI framework for UI components.

**Testing Strategy**: Each phase should include corresponding tests to ensure reliability and prevent regressions.

**Performance Considerations**: Image caching and overlay generation should be optimized to prevent UI blocking during operations.

---

## Quick Reference: Task Summary by Phase

### Phase 1 (Critical): Tasks 1-4, 7-8, 35 ✅ Complete
Foundation: Save/load, OCR reset, notifications

### Phase 2 (High): Tasks 9-12, 20, 25 ✅ Complete
Basic ops: Bbox operations, filtering, fonts

### Phase 3 (High): Tasks 13-19, 23, 30, 32-33
Core editing: Word-level UI, ground truth, state persistence

### Phase 4 (Medium): Tasks 21-22, 24, 26, 34, 40-41
Enhanced UI: Visual styling, overlays, matching improvements

### Phase 5 (Medium): Tasks 27-29, 37-39
Navigation: Multi-page support, enhanced navigation

### Phase 6 (Low): Tasks 31, 36
Performance: Optimizations and graceful fallbacks

### Phase 7 (Medium): Tasks 42-48
Quality: Testing suite and documentation

### Phase 8 (Medium): Tasks 5-6
Export: Training and validation data export

### Phase 9 (Future): Tasks 49-56
Distribution: Deployment and packaging solutions
