# UI Action Buttons Inventory

Complete inventory of every actionable button and interactive control in the
OCR Labeler UI, organised by view component. Used to track browser-test
coverage and plan new tests.

---

## 1. Header — Project Load Controls

**Source:** `pd_ocr_labeler/views/header/project_load_controls.py`

### Main Controls

| # | Label / Icon | Handler | Description | Browser-Tested |
| --- | --- | --- | --- | --- |
| 1 | **LOAD** | `_load_selected_project` | Load selected project | Yes — click + assertions |
| 2 | 📁 `folder_open` icon | `_open_source_folder_dialog` | Open source folder picker dialog | No |

### Source Folder Dialog

| # | Label | Handler | Description | Browser-Tested |
| --- | --- | --- | --- | --- |
| 3 | **Home** | `_path_picker_go_home` | Navigate picker to home directory | No |
| 4 | **Up** | `_path_picker_go_up` | Navigate picker to parent directory | No |
| 5 | **Open Typed Path** | `_open_typed_source_path` | Open path typed in input field | No |
| 6 | **Use Current** | `_use_current_folder` | Use current folder as source | No |
| 7 | **Cancel** | `dialog.close` | Close dialog without saving | No |
| 8 | **Apply** | `_apply_source_folder` | Apply selected source folder | No |

### Source Folder Dialog Keyboard Shortcuts

| # | Event | Handler | Description | Browser-Tested |
| --- | --- | --- | --- | --- |
| 9 | `Enter` in path input | `_on_source_path_enter` | Navigate to typed path | No |

---

## 1b. Header — OCR Configuration Modal

**Source:** `pd_ocr_labeler/views/header/ocr_config_modal.py`

The trigger is rendered alongside the project load controls
(`project_load_controls.py` instantiates `OCRConfigModal` and calls
`build()`). Disabled state is bound from
`ProjectStateViewModel.is_controls_disabled`.

### Header Trigger

| # | Label / Icon | Handler | Description | Browser-Tested |
| --- | --- | --- | --- | --- |
| 109 | `tune` icon | `_open` | Open OCR Configuration dialog (rescans available models on open) | No |

### Dialog Buttons

| # | Label | Handler | Description | Browser-Tested |
| --- | --- | --- | --- | --- |
| 110 | **Rescan Models** | `_rescan_models` | Re-scan local trainer outputs and HF cache; refreshes both selects | No |
| 111 | **Cancel** | `_close` | Close dialog without applying changes | No |
| 112 | **Apply** | `_apply_selection` | Apply HF revision pin (if changed) then commit selected detection / recognition pair | No |

### Dialog Inputs (non-button)

| # | Type | Handler / Binding | Description | Browser-Tested |
| --- | --- | --- | --- | --- |
| 113 | **Detection model** (`ui.select`, `with_input=True`) | bound to `AppStateViewModel.ocr_detection_model_options`; applied via `command_set_selected_ocr_models` | Pick detection weights (HF default + local trainer outputs) | No |
| 114 | **Recognition model** (`ui.select`, `with_input=True`) | bound to `AppStateViewModel.ocr_recognition_model_options`; applied via `command_set_selected_ocr_models` | Pick recognition weights (HF default + local trainer outputs) | No |
| 115 | **Hugging Face revision pin** (`ui.input`) | applied via `command_set_hf_pinned_revision` | Optional revision/tag/commit SHA pinning the HF download (empty = latest) | No |

---

## 2. Project Navigation Controls

**Source:** `pd_ocr_labeler/views/projects/project_navigation_controls.py`

| # | Label | Handler | Description | Browser-Tested |
| --- | --- | --- | --- | --- |
| 10 | **Prev** | `_on_prev` | Navigate to previous page | Yes — click + disabled state |
| 11 | **Next** | `_on_next` | Navigate to next page | Yes — click + disabled state |
| 12 | **Go To:** | `_on_goto` | Navigate to specific page number | Yes — fill + click |

### Navigation Keyboard Shortcuts

| # | Event | Handler | Description | Browser-Tested |
| --- | --- | --- | --- | --- |
| 13 | `Enter` in page input | `_on_goto` | Go to page on Enter | No |

---

## 3. Page Actions

**Source:** `pd_ocr_labeler/views/projects/pages/page_actions.py`

| # | Label | Handler | Tooltip | Browser-Tested |
| --- | --- | --- | --- | --- |
| 14 | **Reload OCR** | `_on_reload_ocr` | — | Visibility only |
| 15 | **Save Page** | `_on_save_page` | — | Yes — click + notification |
| 16 | **Load Page** | `_on_load_page` | — | Visibility only |
| 17 | **Rematch GT** | `_on_rematch_gt` | "Re-run ground truth matching from source text, replacing any per-word GT edits" | No |

---

## 4. Word Match Toolbar — Scope Action Grid

**Source:** `pd_ocr_labeler/views/projects/pages/word_match_toolbar.py`

Each row shares the same column layout. Columns with "—" indicate the
operation is not applicable at that scope.

### 4a. Page Row

| # | Icon | Tooltip | Handler | Browser-Tested |
| --- | --- | --- | --- | --- |
| 18 | `auto_fix_high` 🔧 | "Refine all bounding boxes on this page" | `_on_refine_bboxes` | No |
| 19 | `zoom_out_map` | "Expand then refine all bounding boxes on this page" | `_on_expand_refine_bboxes` | No |
| 20 | `content_copy` (flipped) | "Copy all ground truth text to OCR on this page" | `_handle_copy_page_gt_to_ocr` | No |
| 21 | `content_copy` | "Copy all OCR text to ground truth on this page" | `_handle_copy_page_ocr_to_gt` | No |
| 22 | `check_circle` ✓ | "Validate all words on this page" | `_handle_validate_page` | No |
| 23 | `unpublished` | "Unvalidate all words on this page" | `_handle_unvalidate_page` | No |

### 4b. Paragraph Row

| # | Icon | Tooltip | Handler | Browser-Tested |
| --- | --- | --- | --- | --- |
| 24 | `call_merge` | "Merge selected paragraphs" | `_handle_merge_selected_paragraphs` | Yes |
| 25 | `auto_fix_high` | "Refine selected paragraphs" | `_handle_refine_selected_paragraphs` | Yes |
| 26 | `zoom_out_map` | "Expand then refine selected paragraphs" | `_handle_expand_then_refine_selected_paragraphs` | Yes |
| 27 | `call_split` | "Split the containing paragraph immediately after the selected line" | `_handle_split_paragraph_after_selected_line` | Yes |
| 28 | `content_copy` (flipped) | "Copy ground truth text to OCR for selected paragraphs" | `_handle_copy_selected_paragraphs_gt_to_ocr` | Yes |
| 29 | `content_copy` | "Copy OCR text to ground truth for selected paragraphs" | `_handle_copy_selected_paragraphs_ocr_to_gt` | Yes |
| 30 | `check_circle` | "Validate all words in selected paragraphs" | `_handle_validate_selected_paragraphs` | Yes |
| 31 | `unpublished` | "Unvalidate all words in selected paragraphs" | `_handle_unvalidate_selected_paragraphs` | Yes |
| 32 | `delete` | "Delete selected paragraphs" | `_handle_delete_selected_paragraphs` | Yes |

### 4c. Line Row

| # | Icon | Tooltip | Handler | Browser-Tested |
| --- | --- | --- | --- | --- |
| 33 | `call_merge` | "Merge selected lines into the first selected line" | `_handle_merge_selected_lines` | No |
| 34 | `auto_fix_high` | "Refine selected lines" | `_handle_refine_selected_lines` | No |
| 35 | `zoom_out_map` | "Expand then refine selected lines" | `_handle_expand_then_refine_selected_lines` | No |
| 36 | `call_split` | "Split the selected line immediately after the selected word" | `_handle_split_line_after_selected_word` | No |
| 37 | `vertical_split` | "Split line(s) into selected and unselected words" | `_handle_split_lines_into_selected_unselected_words` | No |
| 38 | `subject` | "Select lines to form a new paragraph" | `_handle_split_paragraph_by_selected_lines` | No |
| 39 | `content_copy` (flipped) | "Copy ground truth text to OCR for selected lines" | `_handle_copy_selected_lines_gt_to_ocr` | No |
| 40 | `content_copy` | "Copy OCR text to ground truth for selected lines" | `_handle_copy_selected_lines_ocr_to_gt` | No |
| 41 | `check_circle` | "Validate all words in selected lines" | `_handle_validate_selected_lines` | No |
| 42 | `unpublished` | "Unvalidate all words in selected lines" | `_handle_unvalidate_selected_lines` | No |
| 43 | `delete` | "Delete selected lines" | `_handle_delete_selected_lines` | No |

### 4d. Word Row

| # | Icon | Tooltip | Handler | Browser-Tested |
| --- | --- | --- | --- | --- |
| 44 | `call_merge` | "Merge selected words on the same line" | `_handle_merge_selected_words` | No |
| 45 | `auto_fix_high` | "Refine selected words" | `_handle_refine_selected_words` | No |
| 46 | `zoom_out_map` | "Expand then refine selected words" | `_handle_expand_then_refine_selected_words` | No |
| 47 | `short_text` | "Form one new line from selected words" | `_handle_split_line_by_selected_words` | No |
| 48 | `format_paragraph` | "Select words to form a new paragraph (one new line per source line)" | `_handle_group_selected_words_into_new_paragraph` | No |
| 49 | `content_copy` (flipped) | "Copy ground truth text to OCR for selected words" | `_handle_copy_selected_words_gt_to_ocr` | No |
| 50 | `content_copy` | "Copy OCR text to ground truth for selected words" | `_handle_copy_selected_words_ocr_to_gt` | No |
| 51 | `check_circle` | "Validate selected words" | `_handle_validate_selected_words` | No |
| 52 | `unpublished` | "Unvalidate selected words" | `_handle_unvalidate_selected_words` | No |
| 53 | `delete` | "Delete selected words" | `_handle_delete_selected_words` | No |

### 4e. Apply Style / Component Toolbar

| # | Label | Handler | `data-testid` | Browser-Tested |
| --- | --- | --- | --- | --- |
| 54 | **Apply Style** | `_apply_selected_style` | `apply-style-button` | Yes — click after selection |
| 55 | **Apply Component** | `_apply_selected_component` | `apply-component-button` | Yes — click after selection |
| 56 | **Clear Component** | `_clear_selected_component` | `clear-component-button` | No |

---

## 5. Word Match Renderer — Per-Line and Per-Word Buttons

**Source:** `pd_ocr_labeler/views/projects/pages/word_match_renderer.py`

### Paragraph Expander

| # | Icon | Handler | Browser-Tested |
| --- | --- | --- | --- |
| 57 | `expand_more` / `chevron_right` | `_toggle_paragraph_expanded` | No |

### Line Card Action Buttons (rendered per line)

| # | Label / Icon | Tooltip | Handler | Browser-Tested |
| --- | --- | --- | --- | --- |
| 58 | **GT→OCR** `content_copy` | "Copy ground truth text to OCR text for all words in this line" | `_handle_copy_gt_to_ocr` | No |
| 59 | **OCR→GT** `content_copy` | "Copy OCR text to ground truth text for all words in this line" | `_handle_copy_ocr_to_gt` | No |
| 60 | **Validate** / **Unvalidate** (`check_circle` / `unpublished`) | Dynamic tooltip with validation count | `_handle_validate_line` | No |
| 61 | `delete` | "Delete this line" | `_handle_delete_line` | No |

### Per-Word Buttons (rendered per word)

| # | Icon | Tooltip | Handler | `data-testid` | Browser-Tested |
| --- | --- | --- | --- | --- | --- |
| 62 | `edit` | "Edit word actions" | `_open_word_edit_dialog` | `edit-word-button` | Yes — opens dialog |
| 63 | `check` | "Validated" / "Mark as validated" | `_handle_toggle_word_validated` | — | No |

### Tag Chip Clear Buttons (rendered per tag)

| # | Icon | Handler | `data-testid` | Browser-Tested |
| --- | --- | --- | --- | --- |
| 64 | `close` | `_clear_word_tag` | `word-tag-clear-button` | No |

---

## 6. Word Edit Dialog

**Source:** `pd_ocr_labeler/views/projects/pages/word_edit_dialog.py`

### Dialog Header

| # | Icon | Tooltip | Handler | Browser-Tested |
| --- | --- | --- | --- | --- |
| 65 | `check` ✓ | "Apply and close" | `_apply_and_close` | No |
| 66 | `close` | "Close without saving" | `dialog.close` | No |

### Style / Component Controls (in dialog)

| # | Label | Handler | Browser-Tested |
| --- | --- | --- | --- |
| 67 | **Apply Style** | `_apply_selected_style_from_dialog` | Yes — click |
| 68 | **Apply Component** | `_apply_selected_component_from_dialog(enabled=True)` | Yes — click |
| 69 | **Clear Component** | `_apply_selected_component_from_dialog(enabled=False)` | No |

### Tag Chip Clear (in dialog)

| # | Icon | Handler | `data-testid` | Browser-Tested |
| --- | --- | --- | --- | --- |
| 70 | `close` | `_clear_word_tag` | `word-edit-tag-clear-button` | Yes — click + chip count |

### Merge / Split / Delete Operations

| # | Label / Icon | Tooltip | Handler | Browser-Tested |
| --- | --- | --- | --- | --- |
| 71 | **Merge Prev** `call_merge` | "Merge current word into previous word" | `_handle_merge_word_left` | No |
| 72 | **Merge Next** `call_merge` | "Merge with next word" | `_handle_merge_word_right` | No |
| 73 | **H** `call_split` | "Split horizontally at marker (H-split: vertical line)" | `_handle_split_word` | No |
| 74 | **V** `call_split` | "Split vertically at marker (V-split: horizontal line, assign to closest line)" | `_handle_split_word_vertical_closest_line` | No |
| 75 | `delete` | "Delete word" | `_handle_delete_single_word` | No |

### Bounding Box Cropping

| # | Label | Tooltip | Handler | Browser-Tested |
| --- | --- | --- | --- | --- |
| 76 | **Crop Above** | "Stage removal above horizontal marker" | `_stage_crop_to_marker("above")` | No |
| 77 | **Crop Below** | "Stage removal below horizontal marker" | `_stage_crop_to_marker("below")` | No |
| 78 | **Crop Left** | "Stage removal left of vertical marker" | `_stage_crop_to_marker("left")` | No |
| 79 | **Crop Right** | "Stage removal right of vertical marker" | `_stage_crop_to_marker("right")` | No |

### Bounding Box Refinement

| # | Label / Icon | Tooltip | Handler | Browser-Tested |
| --- | --- | --- | --- | --- |
| 80 | **Refine** `auto_fix_high` | "Preview refine (stage without applying)" | `_stage_refine_preview(expand=False)` | No |
| 81 | **Expand + Refine** `unfold_more` | "Preview expand then refine (stage without applying)" | `_stage_refine_preview(expand=True)` | No |

### Fine-Tune Nudge Buttons

| # | Label | Edge | Direction | Handler | Browser-Tested |
| --- | --- | --- | --- | --- | --- |
| 82 | **X−** | Left | ← shrink | `_accumulate_bbox_nudge(left_units=-1)` | No |
| 83 | **X+** | Left | → expand | `_accumulate_bbox_nudge(left_units=1)` | No |
| 84 | **X−** | Right | ← shrink | `_accumulate_bbox_nudge(right_units=-1)` | No |
| 85 | **X+** | Right | → expand | `_accumulate_bbox_nudge(right_units=1)` | No |
| 86 | **Y−** | Top | ↑ shrink | `_accumulate_bbox_nudge(top_units=-1)` | No |
| 87 | **Y+** | Top | ↓ expand | `_accumulate_bbox_nudge(top_units=1)` | No |
| 88 | **Y−** | Bottom | ↑ shrink | `_accumulate_bbox_nudge(bottom_units=-1)` | No |
| 89 | **Y+** | Bottom | ↓ expand | `_accumulate_bbox_nudge(bottom_units=1)` | No |

### Apply / Reset Bbox Edits

| # | Label | Tooltip | Handler | Browser-Tested |
| --- | --- | --- | --- | --- |
| 90 | **Reset** | "Reset pending bbox edits" | `_reset_pending_bbox_nudges` | No |
| 91 | **Apply** | "Apply pending bbox edits" | `_apply_pending_bbox_nudges(refine_after=False)` | No |
| 92 | **Apply + Refine** | "Apply pending bbox edits and refine" | `_apply_pending_bbox_nudges(refine_after=True)` | No |

### Keyboard Shortcuts (in dialog)

| # | Event | Handler | Description | Browser-Tested |
| --- | --- | --- | --- | --- |
| 93 | `Enter` in GT input | `_commit_word_gt_input_change` | Commit ground truth text edit | No |

---

## 7. Other Interactive Controls (non-button)

These are not buttons but have meaningful UI interactions.

| # | Type | Location | Description | Browser-Tested |
| --- | --- | --- | --- | --- |
| 94 | **Project dropdown** (`ui.select`) | Header | Select project to load | Yes |
| 95 | **Show Paragraphs** checkbox | Image Tabs | Toggle paragraph overlay layer | Yes — toggled |
| 96 | **Show Lines** checkbox | Image Tabs | Toggle line overlay layer | Visibility only |
| 97 | **Show Words** checkbox | Image Tabs | Toggle word overlay layer | Visibility only |
| 98 | **Selection Mode** radio | Image Tabs | Switch selection mode | Visibility only |
| 99 | **Matches** tab | Text Tabs | Show word match view | Yes — click + active state |
| 100 | **Ground Truth** tab | Text Tabs | Show GT text editor | Yes — click + content |
| 101 | **OCR** tab | Text Tabs | Show OCR text editor | Yes — click + content |
| 102 | **Filter toggle** (Unvalidated / Mismatched / All) | Word Match | Filter displayed lines | Yes — toggle through |
| 103 | **Style dropdown** (`ui.select`) | Toolbar | Select style to apply | Partial |
| 104 | **Scope dropdown** (`ui.select`) | Toolbar | Select scope (whole/part) | No |
| 105 | **Component dropdown** (`ui.select`) | Toolbar | Select component to apply | Yes — in dialog |
| 106 | **Word checkbox** | Word Match Renderer | Toggle word selection | Yes — checked |
| 107 | **Line checkbox** | Word Match Renderer | Toggle line selection | No |
| 108 | **GT text input** | Word Match Renderer | Edit per-word ground truth | No |

---

## Coverage Summary

| Area | Total | Browser-Tested | Coverage |
| --- | --- | --- | --- |
| Header / Load Controls | 9 | 1 | 11% |
| Header / OCR Config Modal | 7 | 0 | 0% |
| Navigation Controls | 4 | 3 | 75% |
| Page Actions | 4 | 2 (one partial) | 50% |
| Toolbar — Page Row | 6 | 0 | 0% |
| Toolbar — Paragraph Row | 9 | 0 | 0% |
| Toolbar — Line Row | 11 | 0 | 0% |
| Toolbar — Word Row | 10 | 0 | 0% |
| Toolbar — Style/Component | 3 | 2 | 67% |
| Renderer — Line Buttons | 4 | 0 | 0% |
| Renderer — Word Buttons | 3 | 1 | 33% |
| Word Edit Dialog | 29 | 3 | 10% |
| Other Interactive Controls | 15 | 9 | 60% |
| **TOTAL** | **114** | **21** | **18%** |

### Highest-Priority Gaps (by user-impact)

1. **Toolbar scope actions** (36 icon buttons) — 0% covered; core editing workflow
2. **Word edit dialog operations** (merge/split/crop/refine/nudge) — 0% covered
3. **Per-line action buttons** (GT→OCR, Validate, Delete) — 0% covered
4. **Source folder dialog** (6 buttons) — 0% covered
5. **Rematch GT button** — not tested at all
6. **Per-word validate toggle** — not tested
7. **Line/word selection checkboxes** — only word checkbox tested
8. **OCR Configuration modal** (trigger + Rescan/Cancel/Apply +
   detection/recognition/HF-revision inputs) — not tested
