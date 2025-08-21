High‑level feature areas in notebook:

Full multi‑page navigation + page index display + go-to (#) with bounds.
OCR run (with optional injected predictor), reset, import/export per-page JSON + image copy.
Training / validation export (convert page to training set files).
Rich page image set regeneration (paragraph, line, word, mismatches overlays).
Bulk operations: expand & refine all word bboxes; refine only; refresh page images; refresh all line images.
Line filtering (all / mismatches / unvalidated mismatches) – already partially in NiceGUI.
Per-line rich editor:
Visual cropped line image.
OCR vs GT text display with coloring for exact vs mismatch.
Actions: Copy line OCR→GT, delete line, mark validated.
State-based border colors (gray exact, red mismatch, green validated).
Word-level table per line:
Cropped word image thumbnails.
Color-coded OCR & GT tokens (red/blue/gray).
Inline GT editing with recompute of match score & rematch logic.
Unmatched ground-truth token insertion handling.
Word-level actions: delete word, merge left/right, split word (interactive pixel + char index), edit bbox (margins, refine, crop top/bottom/both), quick crop buttons (CT/CB/CA).
Post-edit line/page image refresh hooks.
Line-level recomputation & page image refresh after structural edits (split/merge/delete/crop/refine).
Export/import Document (single page) with consistent prefix naming scheme projectid_pageidx.
Font injection / consistent monospace styling.
Current NiceGUI gaps:

Only prototype project/page loading (single page) & simplistic OCR run dialog; no per-page JSON import/export integration.
No training/validation export wiring.
No actual persistence for Save/Reload OCR; buttons are placeholders.
No bbox operations (expand/refine/reset/crop) implemented.
No word-level editing UI (only whole-line GT text field; no word segmentation actions).
No line image thumbnails or border color state (validated/exact mismatch styling minimal).
No split / merge / bbox edit tasks.
No unmatched GT word handling (LineVM lacks fine-grained word model).
No page overlay regeneration triggered by word/line edits (only passive caching).
No refresh all line images functionality.
Limited navigation (has prev/next + number input, but no direct go-to button or max clamp text; acceptable but can be refined).
No per-page save naming with export_prefix scheme (project_id missing context).
Font injection not implemented (relying on default CSS).
Filtering for native OCR lines not applying mismatch rules yet (TODO noted).
Validation logic for native lines only tracked via set of ids (not persisted).
Actionable task list (ordered for incremental delivery):

Foundational Data & Persistence

Implement OCR document save: serialize current native Page (or PageVM) into JSON + copy image (mirror IpynbLabeler.export_ocr_document). Add project/page id strategy (derive project_id from directory name or configurable).
Implement OCR document load (import) for current page index; populate PageVM or native Page fields (import_ocr_document).
Add export_prefix logic (project_id + page index) with configurable project_id in AppState.
Persist validated line + word-level GT modifications back into JSON on save.
Training / Validation Export 5. Implement export_training and export_validation operations using native Page.convert_to_training_set equivalent if available; fallback to placeholder and log if pd_book_tools missing. 6. Hook these to buttons (currently no-ops).

OCR & Page Management 7. Add reset_ocr logic: re-run docTR OCR for current image and discard manual edits for that page. 8. Support force_refresh flag in run_doctr_ocr_on_images / per-page refresh.

Bounding Box Operations 9. Implement refine_all_bboxes for native Page: call page.refine_bounding_boxes(padding_px=2) and refresh overlays. 10. Implement expand_and_refine_all_bboxes: iterate words -> crop_bottom + expand_to_content then page.refine_bounding_boxes. 11. Implement refresh_page_images: call page.refresh_page_images() and clear image cache. 12. Implement refresh_all_line_images: (if per-line thumbnails added) regenerate those; placeholder now.

Line & Word Editing UI 13. Introduce a WordVM abstraction or adapt native Page usage when in document mode to expose word operations. 14. Add per-line collapsible advanced editor (similar to IpynbLineEditor) with: - Line image thumbnail. - Word table (image + OCR + GT + buttons). - Copy line OCR→GT button. - Delete line, Mark validated. 15. Implement word delete, merge_left, merge_right actions modifying native line object. 16. Implement word split UI: pixel slider + char index; call underlying split_word and recompute matches. 17. Implement edit bbox UI: margin adjustments, refine, crop top/bottom/all, save. 18. Add quick crop buttons CT/CB/CA per word row. 19. After each structural word edit, trigger page.refresh_page_images and image cache invalidation.

Line Filtering & Styling 20. Apply mismatch filtering for native line Blocks (compute exact / validated similarly to notebook). 21. Add border color classes to line containers based on status (exact/validated/mismatch). 22. Provide toggle to hide validated lines when mismatch filter enabled (already partially implemented via enum; extend native path).

Ground Truth Matching & Scores 23. Implement per-word fuzz score recompute on GT edit (word.fuzz_score_against). 24. Handle unmatched ground truth words (simulate insertion placeholders) and editing / merging behavior.

Font & Styling 25. Inject custom monospace font (if path provided) into NiceGUI (add <style> tag globally). 26. Consistent monospace class for OCR/GT text.

Navigation & UX Enhancements 27. Add Go To Page button (or immediate on enter already done) plus input bounds enforcement (some exists; ensure consistent). 28. Display current page name (already present) but include index and total in a single label for clarity. 29. Add loading / busy indicators during OCR operations (disable buttons while running).

Caching & Performance 30. Invalidate per-page image cache on any bbox/word edit. 31. Optional: Debounce frequent GT edits before recompute overlays.

Validation & State Persistence 32. Persist line validated state & word ground_truth_text in save JSON. 33. Reapply validated flags on load (mapping native Block objects—store by text+index or stable id hash). 34. Add global tally of validated vs total mismatched lines.

Error Handling & Logging 35. Add user notifications (toast/snackbar) for save/load success/failure. 36. Graceful fallback if pd_book_tools or cv2 not installed (disable relevant buttons).

Project Loading Expansion 37. Support loading multiple pages (not just first) with pagination integration (remove intentional limitation). 38. Support loading all JSON files merging pages (with index offsets). 39. Add PGDP loader to incorporate ground truth (pages.json) and then run OCR to match lines (like notebook adds ground truth to page).

Image Variants 40. Add words-with-GT-text overlay generation (cv2_numpy_page_image_word_with_bboxes_and_gt_text) if underlying library supports; else fallback. 41. Generate mismatches overlay highlighting mismatched words similarly to notebook (cv2_numpy_page_image_matched_word_with_colors).

Testing & Automation 42. Add unit tests for save/load round trip of a simple page with GT edits. 43. Add test for word split merging correctness (token counts). 44. Add test for bbox refine logic updates (ensuring dimensions change). 45. Add test for filtering logic across matching modes.

Documentation 46. Update README (NiceGUI labeler) with new features & key shortcuts. 47. Provide developer guide for extending word-level UI. 48. Add troubleshooting section (missing overlays, predictor failure, font not loading).

Incremental Delivery Plan (suggested phases): Phase 1 (Persistence & Basic Ops): Tasks 1–12, 20, 25, 35. Phase 2 (Word-Level Editing Core): Tasks 13–19, 23, 30, 32–33. Phase 3 (Overlays & Matching Enhancements): Tasks 21–22, 24, 34, 40–41. Phase 4 (Navigation & Multi-Page): Tasks 27–29, 37–39. Phase 5 (Testing & Docs): Tasks 42–48. Phase 6 (Polish & Performance): Tasks 26, 31, 36, 43–45 refinement loops.

Let me know if you’d like me to start implementing Phase 1 (I can scaffold save/load + bbox ops next).