# OCR Labeler TODOs

## Overview

Development roadmap for the OCR Labeler application. The application is a NiceGUI-based web interface for processing public domain book scans with OCR capabilities and ground truth comparison features.

## Completed Features

✅ **Phase 1**: Foundational data persistence, OCR save/load, export naming, reset OCR, user notifications
✅ **Phase 2**: Bounding box operations (refine, expand, refresh), line filtering, font injection


## Development Phases

** Rotate Page Left/Right Buttons **
Transform OCR bboxes as well as part of rotation
Should this be part of the Page Class itself?

### Phase 3: Word & Line-Level Editing Core
**Priority: High** | **Status: In Progress**

### Block grouping operations
using the nice gui ui component that lets you click in an image, i want to be able to pick top left / bottom right and then have the lines within form a paragraph block

#### Line-Level Operations
**Merge Lines Button**: Create checkbox-based multi-line selection UI with "Merge Lines" button. When checkboxes are displayed next to each line, user can select multiple lines and click "Accept" to merge them into a single line. Should handle:
    - Checkbox UI state (show/hide)
    - Line selection tracking
    - Line merging logic (concatenate text, merge bboxes)
    - Ground truth preservation/merging
    - Post-merge refresh and state update

**Delete Line**: Add ability to delete a selected line from the page. Should handle:
    - Line deletion from page structure
    - Ground truth cleanup
    - Page bbox recalculation
    - Image overlay regeneration
    - Undo capability consideration

#### Word Editing Infrastructure
13. **Word VM Abstraction**: Introduce WordVM abstraction or adapt native Page usage in document mode to expose word operations.

14. **Per-Line Advanced Editor**: Add per-line collapsible advanced editor (similar to IpynbLineEditor) with:
    - Line image thumbnail
    - Word table (image + OCR + GT + buttons)
    - Copy line OCR→GT button
    - Delete line, Mark validated actions

15. **Word Actions**: Implement word delete, merge_left, merge_right actions modifying native line object.

16. **Word Split UI**: Implement word split UI with pixel slider + char index; call underlying split_word and recompute matches.
Make it so you can just "click" in the image (nicegui has a image overlay tool which should enable this)

17. **Edit Bbox UI**: Implement edit bbox UI with margin adjustments, refine, crop top/bottom/all, save functionality.

18. **Quick Crop Buttons**: Add quick crop buttons CT/CB/CA per word row.

19. **Post-Edit Refresh**: After each structural word edit, trigger page.refresh_page_images and image cache invalidation.

#### Ground Truth & State
23. **Fuzz Score Recompute**: Implement per-word fuzz score recompute on GT edit (word.fuzz_score_against).

30. **Cache Invalidation**: Invalidate per-page image cache on any bbox/word edit.

32. **State Persistence**: Persist line validated state & word ground_truth_text in save JSON.

33. **State Restoration**: Reapply validated flags on load (mapping native Block objects by text+index or stable ID hash).


### Phase 4: Enhanced UI & Matching
**Priority: Medium**

#### Visual Enhancements & Ground Truth
24. **Unmatched GT Handling**: Handle unmatched ground truth words with insertion placeholders and editing/merging behavior. Implement edit/merge tooling.

26. **Consistent Styling**: Add consistent monospace class for OCR/GT text across all UI components.

#### Image Overlays
40. **GT Text Overlays**: Add words-with-GT-text overlay generation (cv2_numpy_page_image_word_with_bboxes_and_gt_text) with fallback support.

41. **Mismatch Overlays**: Generate mismatches overlay highlighting mismatched words similarly to notebook implementation.

### Phase 5: Navigation & Multi-Page Support
**Priority: Medium**

#### Multi-Page Support
37. **Multiple Page Loading**: Support loading multiple pages (not just first) with pagination integration (remove intentional limitation).

38. **JSON File Merging**: Support loading all JSON files merging pages with index offsets.

39. **PGDP Loader**: Add PGDP loader to incorporate ground truth (pages.json) and run OCR to match lines.

### Phase 6: Performance & Polish
**Priority: Low**

31. **Debounced Updates**: Optional debouncing of frequent GT edits before recompute overlays.

36. **Graceful Fallbacks**: Graceful fallback if pd_book_tools or cv2 not installed (disable relevant buttons).

### Phase 7: Testing & Documentation
**Priority: Medium**

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
**Priority: Medium**

5. **Export Operations**: Implement export_training and export_validation operations using native Page.convert_to_training_set equivalent; fallback to placeholder if pd_book_tools missing.

6. **Export Integration**: Hook export operations to buttons (currently no-ops).

---

## Distribution & Deployment (Future)

### Phase 9: Distribution Strategy
**Priority: Future**

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

**Current Priority**: Phase 3 (Word & Line-Level Editing) is the active development focus.

**Dependencies**: Most tasks depend on proper integration with the `pd-book-tools` library for OCR functionality and the NiceGUI framework for UI components.

**Testing Strategy**: Each phase should include corresponding tests to ensure reliability and prevent regressions.

**Performance Considerations**: Image caching and overlay generation should be optimized to prevent UI blocking during operations.

---

## Quick Reference: Task Summary by Phase

### ✅ Phase 1-2 (Complete)
Foundation: Save/load, OCR reset, bbox operations, filtering, fonts

### Phase 3 (High Priority - In Progress)
Core editing: Word-level UI, line merge operations, ground truth, state persistence

### Phase 4 (Medium Priority)
Enhanced UI: Visual styling, overlays, matching improvements

### Phase 5 (Medium Priority)
Navigation: Multi-page support, enhanced navigation

### Phase 6 (Low Priority)
Performance: Optimizations and graceful fallbacks

### Phase 7 (Medium Priority)
Quality: Testing suite and documentation

### Phase 8 (Medium Priority)
Export: Training and validation data export

### Phase 9 (Future)
Distribution: Deployment and packaging solutions
