# GPU Deployment Paths

A thorough breakdown of both deployment scenarios for running the labeler with GPU-backed OCR.

## Current Architecture, Summarized

The app is a **NiceGUI web server** (Python, Starlette/Uvicorn) with no containerization. OCR is **lazy-triggered on page navigation** — the first time a user visits a page, it runs DocTR synchronously in-process (wrapped in `run.io_bound()` to avoid blocking the UI), then caches the result. Subsequent visits load from cache.

The key insertion point for any GPU work is `operations/ocr/page_operations.py` → `_parse_page()` → `OCRService`.

---

## Path 1: Full GPU Server Deployment

This is simpler — just run the whole app on a GPU instance.

**What's needed:**
1. A `Dockerfile` with a CUDA base image (`nvidia/cuda:12.x-runtime-ubuntu22.04`), installs Python 3.13 + uv, syncs the project
2. DocTR automatically detects and uses the GPU via PyTorch/CUDA — no code changes needed
3. Expose port 8080 and serve with `pd-ocr-labeler-ui` as-is

**Tradeoff:** A GPU instance runs 24/7 even when nobody is doing OCR. For a labeling tool with sporadic usage, this wastes money.

---

## Path 2: Split Architecture — CPU Web App + On-Demand GPU OCR

This is the more interesting design. The idea: the web UI runs cheaply on a CPU server, and OCR jobs are dispatched to a GPU worker that starts on demand and shuts down when idle.

```
┌─────────────────────────────────┐        ┌────────────────────────────────────┐
│  CPU Server (always-on, cheap)  │        │  GPU Worker (on-demand, expensive) │
│                                 │        │                                    │
│  NiceGUI Web UI                 │        │  DocTR OCR process                 │
│  + State/ViewModel/Views        │──job──▶│  + CUDA/PyTorch                    │
│  + Persistence/Cache            │◀─result│  + pd-book-tools                   │
│                                 │        │  + Fine-tuned model weights        │
└─────────────────────────────────┘        └────────────────────────────────────┘
          │                  ▲                          │            ▲
          └──── enqueue ─────┘                          └─ spin up ──┘
                    via queue/broker                       auto-scaling
```

The app already caches OCR results to disk, so the GPU is only hit **once per page**, which makes this very efficient.

### Three concrete options, ordered by implementation effort:

---

### Option A: Modal (least effort — recommended for getting started)

[Modal](https://modal.com) is a serverless GPU platform. You define a function with a GPU, and it spins up in seconds only when called.

**Changes required:** Minimal — just swap out `_parse_page()` in `operations/ocr/page_operations.py` to call a Modal remote function instead of running locally.

```python
# modal_ocr.py (new file, deployed separately)
import modal

app = modal.App("pd-ocr")
image = modal.Image.debian_slim().pip_install("doctr", "pd-book-tools", ...)

@app.function(gpu="T4", image=image, timeout=120)
def run_ocr(image_bytes: bytes, engine: str = "doctr") -> dict:
    from doctr... import ...
    # run OCR, return serialized Page dict
    ...
```

```python
# In page_operations.py _parse_page():
import modal
run_ocr = modal.Function.lookup("pd-ocr", "run_ocr")
result = run_ocr.remote(image_bytes)  # blocks until GPU finishes
```

- **Cold start:** ~5–15 seconds for Modal to boot the container
- **Cost:** Pay only for actual GPU compute seconds
- **Scaling:** Modal handles it automatically

---

### Option B: Celery + Redis + Docker Compose (self-hosted, full control)

Best if you want to self-host everything or avoid vendor lock-in.

**New components:**
- Redis as the job broker
- A `celery_worker.py` that imports DocTR and processes OCR jobs
- Docker Compose: three services — `web` (CPU), `redis`, `worker` (GPU, optional separate host)

```yaml
# docker-compose.yml
services:
  web:
    build: { context: ., dockerfile: Dockerfile.cpu }
    environment: [CELERY_BROKER_URL=redis://redis:6379/0]
    ports: ["8080:8080"]

  redis:
    image: redis:7-alpine

  worker:
    build: { context: ., dockerfile: Dockerfile.gpu }
    environment: [CELERY_BROKER_URL=redis://redis:6379/0]
    deploy:
      resources:
        reservations:
          devices: [{ driver: nvidia, count: 1, capabilities: [gpu] }]
```

**Changes to the app:** `_parse_page()` submits a Celery task and polls for the result (or uses a callback into NiceGUI's async loop). The existing `run.io_bound()` wrapper makes this straightforward.

For **scale-to-zero**, the GPU worker container can be on a separate machine managed by an AWS Auto Scaling Group or GCP Managed Instance Group with a zero-minimum — it boots when a job arrives in the queue and terminates after an idle timeout.

---

### Option C: AWS Batch / GCP Cloud Run Jobs (cloud-native managed)

If you're already on a cloud provider, both AWS Batch and GCP Cloud Run Jobs support GPU and **scale to zero between jobs**.

- The web app submits an OCR job (image path in S3/GCS + job parameters)
- AWS Batch / Cloud Run Jobs spins up a GPU container, runs DocTR, writes the result back to shared storage
- The web app polls or gets notified (SNS, Pub/Sub, or just polling the output path)

This requires more infrastructure plumbing but has no always-on worker cost.

---

## Key Design Considerations

| Concern | Notes |
|---|---|
| **Cold start latency** | GPU containers take 10–120 seconds to boot. The UI already runs OCR in a background task, so you can show a spinner. Consider pre-warming the worker if users are active. |
| **The cache is your friend** | The existing page-image-cache means OCR runs once per page. The GPU cost is a one-time hit per page, not per visit. |
| **Model weights** | Fine-tuned `.pt` files in `~/.local/share/pd-ml-models` need to be bundled into the GPU container image or fetched from S3 on startup. |
| **Serialization** | `pd-book-tools`' `Page` / `Document` objects need to be serialized over the wire (JSON or pickle). The existing export logic may cover this. |
| **Shared filesystem** | If web and worker run on different machines, the page image files and cache directory need to be on shared storage (NFS, S3, GCS) rather than local disk. |

---

## Recommended Starting Point

If you want the lowest friction path: **Modal + a CPU-only Docker deployment for the web app**. The code change is localized to `_parse_page()` in `page_operations.py`, and Modal handles all GPU lifecycle management. Once that's working, you can migrate to a fully self-hosted Celery setup if needed.

Want me to sketch out the actual code changes for any of these options?


Let me look at how model loading works in the current codebase.

Good question — this is the main practical hurdle. Here's the full picture based on the actual code.

## What the app currently does

Models live at `~/.local/share/pd-ml-models/<profile>/detection/*.pt` and `recognition/*.pt`. The paths are resolved at runtime and passed as filesystem `Path` objects to `get_finetuned_torch_doctr_predictor(detection_path, recognition_path, vocab)`. The selected model key (e.g. `"mymodel/v1.0"`) and its paths are stored in `AppState` and passed through `PageOperations.configure_doctr_weights()`.



## Three options for Modal

---

### Option 1: Modal Volume (best fit)

Modal has a persistent cloud volume you manage separately from your function containers. You upload your `.pt` files once, and the function mounts them on every run.

```bash
# One-time upload (run from your machine)
modal volume create pd-ml-models
modal volume put pd-ml-models ~/.local/share/pd-ml-models/ /
```

```python
# modal_ocr.py
import modal
from pathlib import Path

volume = modal.Volume.from_name("pd-ml-models")
app = modal.App("pd-ocr")

@app.function(
    gpu="T4",
    image=...,
    volumes={"/root/pd-ml-models": volume},  # mounted here
)
def run_ocr(
    image_bytes: bytes,
    detection_weights_key: str | None,   # e.g. "mymodel/v1.0-detection.pt"
    recognition_weights_key: str | None, # e.g. "mymodel/v1.0-recognition.pt"
    vocab: str = "",
) -> dict:
    model_root = Path("/root/pd-ml-models")
    det_path = model_root / detection_weights_key if detection_weights_key else None
    rec_path = model_root / recognition_weights_key if recognition_weights_key else None
    # call get_finetuned_torch_doctr_predictor(det_path, rec_path, vocab)
    # or get_default_doctr_predictor() if both None
    ...
```

When you update a model, run `modal volume put` again — no container rebuild needed. The `OCRModelOption` already carries the relative paths; you'd strip the local prefix and send the relative key to Modal.

---

### Option 2: Bake models into the image

If the models rarely change and you want zero cold-start I/O:

```python
image = (
    modal.Image.debian_slim()
    .pip_install("doctr", ...)
    .copy_local_dir(
        Path.home() / ".local/share/pd-ml-models",
        "/root/pd-ml-models"
    )
)
```

Simple, but requires a full image rebuild (minutes) whenever you retrain or add a model profile.

---

### Option 3: Pull from S3/GCS on cold start

Upload `.pt` files to a private S3 bucket, download them inside the function. Works, but adds 10–30 seconds to cold starts depending on model size. Only worth it if you already have cloud storage infrastructure.

---

## How the web app passes the model selection

The web app already knows the selected model's paths via `AppState.selected_ocr_model_key` and the `OCRModelOption`. When submitting the OCR job to Modal, you'd send the relative path keys rather than absolute local paths:

```python
# In page_operations.py, when building the remote call:
model = self._selected_model_option  # OCRModelOption

result = run_ocr.remote(
    image_bytes=open(image_path, "rb").read(),
    detection_weights_key=str(model.detection_weights_path.relative_to(model_store_root))
                          if model.detection_weights_path else None,
    recognition_weights_key=str(model.recognition_weights_path.relative_to(model_store_root))
                            if model.recognition_weights_path else None,
    vocab=model.vocab or "",
)
```

**Modal Volume is the right default** — it decouples model updates from deployments and directly mirrors the existing `pd-ml-models` directory structure.



Yes, exactly — the server becomes a thin data layer, and the client owns all the interactive complexity. That's actually what makes the API so simple, but it also means the frontend is the real work.

## What runs client-side

Everything that currently lives in the NiceGUI state/viewmodel/view layers:

- Rendering the page image + all bbox overlays on a canvas
- Pan/zoom with coordinate transforms (screen coords ↔ image coords)
- Click-to-select words, lines, paragraphs
- Drag to rebox (resize/reposition bounding boxes)
- Merge/split logic (word and paragraph operations)
- Validation state rollup (word → line → paragraph)
- Tag editing, per-word GT comparison display
- Undo/redo history
- Navigation state

The server just does: serve image, serve OCR JSON, accept saved labels.

## The hard part is the canvas, not the framework

This is fundamentally an **image annotation tool** — the bbox overlays, drag interactions, and coordinate math are the real complexity regardless of what framework you pick. That work exists in any choice.

**Konva.js** is the right library for this layer. It gives you a scene graph on top of canvas — shapes, groups, layers, drag events, transforms — which maps directly onto words/lines/paragraphs as grouped bounding boxes. It has first-class React and Vue bindings.

```
┌─ App Framework (React / Vue / Svelte) ──────────┐
│  navigation, page list, text panels, dialogs    │
│                                                  │
│  ┌─ Konva Stage ──────────────────────────────┐ │
│  │  Layer: page image                         │ │
│  │  Layer: paragraph rects                    │ │
│  │  Layer: line rects                         │ │
│  │  Layer: word rects (selectable, draggable) │ │
│  │  Layer: selection handles / rebox UI       │ │
│  └────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────┘
```

## Framework options

**React + Konva (react-konva)** — largest ecosystem, best tooling, most examples of annotation UIs built this way. If you're comfortable with React, this is the default choice.

**Svelte** — genuinely lighter, less boilerplate, compiles to minimal JS. Would use konva directly (no official Svelte binding, but konva is plain JS so it integrates fine). Good choice if you want a clean small codebase.

**Vue + vue-konva** — works well, similar story to React. Slightly less ecosystem for annotation specifically.

The framework matters less than you'd think here. Pick what you know.

## Worth knowing about OpenSeadragon

If the page images are large/high-resolution, [OpenSeadragon](https://openseadragon.github.io/) handles deep-zoom tiling natively and was built specifically for document/museum images. It has an annotation plugin ecosystem. Might be a better base for the image viewer layer than raw Konva if resolution is a concern.

## Honest take on the effort

The NiceGUI app has a lot of accumulated editing logic — word merge/split, bbox refinement, per-word validation state, paragraph operations. Rebuilding that faithfully in JS is probably **4–8 weeks of focused frontend work** depending on how much of the feature set you need. It's not a weekend project.

If you're doing this solo on a free project, Option A (keep NiceGUI, pre-populate cache, run on a $4 Hetzner box) is probably the right call until there's a reason to invest in the rewrite.


That changes the picture significantly — the hard work is already done in pd-book-tools, and your scripts are essentially the pipeline logic. The new app is really just an **orchestration layer and UI on top of what you've already built**.

That makes this a much better fit for a simple web UI than the labeling tool, because there's no complex canvas annotation to reimplement. The frontend just needs to handle:

- Specify input (upload images, or point to a local/S3 directory)
- Configure the run (model selection, any preprocessing options)
- Trigger the batch OCR job
- Show progress
- Download or access the PGDP-ready output

There's no bbox editing, no canvas, no per-word state — it's a **pipeline UI**, not an annotation tool.

## What this might look like

```
┌─ Web UI (simple) ─────────────────────────────────┐
│  1. Select project images                          │
│  2. Choose OCR model                               │
│  3. [ Run OCR ]  → submits batch job              │
│  4. Progress / status display                      │
│  5. [ Download PGDP package ]                      │
└────────────────────────────────────────────────────┘
         │ job submission
         ▼
┌─ API (FastAPI, thin) ──────────────────────────────┐
│  wraps your existing pd-book-tools scripts         │
│  manages job state (running / done / failed)       │
└────────────────────────────────────────────────────┘
         │ dispatches to
         ▼
┌─ GPU batch worker ─────────────────────────────────┐
│  Modal / Spot EC2                                  │
│  runs your OCR + PGDP packaging scripts            │
│  writes output to S3                              │
└────────────────────────────────────────────────────┘
```

## Stack that fits this well

Since you're already in Python and the logic is in pd-book-tools, **FastAPI + HTMX** is worth considering. HTMX lets you write a fully dynamic UI (progress polling, form submission, result display) in plain HTML with small `hx-` attributes — no JS framework, no build step. The backend is just FastAPI endpoints that call your existing script functions.

Alternatively, **NiceGUI again** — you already know it, and for a pipeline UI (not a canvas annotation tool) it's actually a good fit. Much less complexity than the labeling app.

## The key question to figure out

How much of your existing scripts is reusable as-is versus needing to be refactored to work in a web/async context? If they're synchronous CLI scripts today, wrapping them in a FastAPI + background job pattern is straightforward, but it's worth mapping out which pd-book-tools functions they call and whether those have any side effects or assumptions about the local filesystem that would need to change for S3-based storage.

What does the current script workflow look like — are they mostly sequential steps, or is there branching/decisions between steps?

