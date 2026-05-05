# OCR Model Selection

Describes how the labeler discovers, selects, and applies DocTR detection +
recognition model pairs for OCR.

Status: validated against current code on 2026-05-04.

## Sources

The labeler picks DocTR weights from three sources, in priority order:

1. **Hugging Face — published default repo** (`CT2534/pd-ocr-models`). Always
   present in the option list. When the network probe succeeds, the option
   carries an `hf_last_modified` timestamp. Optionally pinned to a specific
   revision (tag / branch / commit SHA).
2. **Local fine-tuned models** discovered under the OS-aware shared models
   root (`pd-ml-models`), one option per `<profile>/<signature>` pair found.
3. **Built-in DocTR fallback** (`DEFAULT_MODEL_KEY = "default"`) — falls back
   to `pd_book_tools.ocr.doctr_support.get_default_doctr_predictor()` (stock
   Mindee weights). Used only when neither HF nor local is available.

## Components

- Discovery, picker, and HF download:
  `pd_ocr_labeler/operations/ocr/model_selection_operations.py`
  - `OCRModelOption` (frozen dataclass): `key`, `label`, optional
    `detection_weights_path` / `recognition_weights_path` / `vocab` for
    local pairs, plus `hf_repo`, `hf_detection_filename`,
    `hf_recognition_filename`, `hf_revision`, `hf_last_modified` for HF
    options.
  - `ModelSelectionOperations.discover_model_options(...)` returns the full
    option dict + label map; accepts `hf_pinned_revision` to add a pinned
    HF option alongside the latest entry.
  - `fetch_hf_last_modified(...)` probes HF for `last_modified`; returns
    `None` on missing dep, network error, or timeout.
  - `download_hf_weights(option)` downloads the `.pt` files plus `.arch`
    and `.vocab` sidecars (pd-book-tools reads sidecars from the same
    directory as the `.pt` file via `_read_arch_sidecar` /
    `_read_vocab_sidecar`).
  - `pick_default_keys(options)` chooses `(detection_key, recognition_key,
    reason)` per the priority rules below.
- Application state:
  `pd_ocr_labeler/state/app_state.py`
  - `available_ocr_models: dict[str, OCRModelOption]`
  - `ocr_detection_model_options`, `ocr_recognition_model_options`
    (dropdown maps).
  - `selected_ocr_detection_model_key`, `selected_ocr_recognition_model_key`,
    `hf_pinned_revision`.
  - `_announce_selection_reason(reason)` queues a notification when the
    auto-pick reason changes (e.g. HF unreachable → falling back to local).
  - `set_hf_pinned_revision(revision)` updates the pin and triggers
    `refresh_ocr_models`.
- ViewModel surface:
  `pd_ocr_labeler/viewmodels/app/app_state_view_model.py`
  - Exposes the model option maps, selected keys, and `hf_pinned_revision`.
  - Commands: `command_refresh_ocr_models`,
    `command_set_selected_ocr_models`, `command_set_hf_pinned_revision`.
- View:
  `pd_ocr_labeler/views/header/ocr_config_modal.py`
  - Detection + recognition selectors, revision-pin input, Rescan / Cancel
    / Apply.
- Predictor wiring:
  `pd_ocr_labeler/operations/ocr/page_operations.py`
  - `HuggingFaceWeightsDescriptor` (frozen dataclass): repo, filename,
    revision, role.
  - `configure_doctr_weights(...)` accepts both local paths and HF
    descriptors; either pair populates `_detection_weights_path` /
    `_recognition_weights_path` (for local) or schedules a lazy download
    (for HF).
  - `_resolve_pending_hf_weights()` downloads HF `.pt` + `.arch` + `.vocab`
    on first use.
  - `_get_or_create_predictor()` builds the predictor lazily after
    resolving any HF descriptors. Uses
    `pd_book_tools.ocr.doctr_support.get_finetuned_torch_doctr_predictor`
    when paths are set; otherwise falls back to
    `get_default_doctr_predictor()`.

## Default Selection Priority

`ModelSelectionOperations.pick_default_keys(options)` returns the chosen
keys plus a `reason` string used to drive notifications:

| Reason | Trigger | Notification kind |
| --- | --- | --- |
| `hf-latest` | HF probe succeeded AND (HF mtime ≥ newest local mtime OR no local) | info |
| `hf-only` | HF probe succeeded, no local fine-tuned models | info |
| `local-newer-than-hf` | HF reachable but local mtime is strictly newer | info |
| `local-only-hf-unreachable` | HF unreachable, latest local present | warning |
| `hf-unreachable-no-local` | HF unreachable, no local — falls back to stock Mindee | negative |
| `stock-fallback` | No HF option, no local — last-resort Mindee | warning |

Per user spec, **HF is preferred when its timestamp is later than or equal
to the latest local model's mtime**. Stock Mindee is reached only when
neither HF nor local is usable.

## Shared Models Root

`ModelSelectionOperations.get_shared_models_root()` resolves the OS-aware
parent directory containing the `pd-ml-models` subtree:

| OS | Default root |
| --- | --- |
| Linux | `$XDG_DATA_HOME/pd-ml-models` (default `~/.local/share/pd-ml-models`) |
| macOS | `~/Library/Application Support/pd-ml-models` |
| Windows | `%APPDATA%/pd-ml-models` |

Inside the dev container this resolves to
`/home/vscode/.local/share/pd-ml-models/`, which is also the named volume
written by `pd-ocr-trainer`.

## Profile Layout (Local)

Each profile directory (e.g. `base-ocr`, `italics`) has parallel
`detection/` and `recognition/` subdirectories containing `.pt`
checkpoints. Optional sidecar files:

- `<stem>.arch` — doctr architecture name (preferred over heuristics).
- `<stem>.vocab` — recognition vocab string.

Detection and recognition `.pt` files are paired by their normalized
"signature" (filename stem with `-detection-` or `-recognition-` removed).
Each unique signature becomes one selectable option keyed
`<profile>/<signature>` with label `<profile>: <signature>`.

## Hugging Face Pinning

The OCR config modal includes a free-form revision input. Setting it adds
a second HF option keyed `huggingface@<revision>` so the user can switch
between `latest` and the pinned commit/tag. The pin applies on Apply.
Clearing the input restores latest-only behavior.

## Apply Flow

1. User edits the revision pin and/or picks detection + recognition options
   in the modal.
2. `_apply_selection` calls `command_set_hf_pinned_revision` (if changed),
   which triggers `AppState.set_hf_pinned_revision` →
   `refresh_ocr_models`.
3. `command_set_selected_ocr_models` calls
   `AppState.set_selected_ocr_models(...)`.
4. `_apply_selected_ocr_model_to_project_state` invokes
   `page_ops.configure_doctr_weights(...)` on every loaded `ProjectState`
   plus `_default_project_state` if present, passing either local paths
   or HF descriptors per role.
5. `configure_doctr_weights` clears the cached predictor; the next OCR
   call rebuilds it. For HF descriptors, the rebuild downloads the `.pt`
   plus `.arch` and `.vocab` sidecars before constructing the predictor.
6. Provenance `source_lib` is `"doctr-pd-huggingface"` when either side is
   HF, `"doctr-pd-finetuned"` for local fine-tuned, and
   `"doctr-pd-labeled"` for stock Mindee fallback.

## UI Behavior

- The OCR config trigger button is disabled while project controls are
  disabled (`is_controls_disabled`).
- Re-opening the modal triggers `command_refresh_ocr_models` so the
  dropdown reflects newly trained models or a fresh HF probe.
- Applying a different model pair clears the lazy predictor cache, so the
  next OCR call uses the new weights (and downloads them, if HF).

## Failure Modes

- **HF unreachable on probe** — `fetch_hf_last_modified` returns `None`;
  the picker falls back to local-latest (if present) and queues a warning
  notification (`local-only-hf-unreachable` /
  `hf-unreachable-no-local`).
- **HF unreachable on download** — `hf_hub_download` raises; the exception
  propagates from `_get_or_create_predictor` so the failure is visible.
  When a cached snapshot already exists, hf_hub_download returns it
  without hitting the network.
- **Sidecars missing in HF repo** — caught as `EntryNotFoundError`; the
  finetuned predictor's heuristic detection (`_detect_recognition_arch` /
  `_detect_detection_arch`) and default vocab kick in.
