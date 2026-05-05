# Installing pd-ocr-labeler

The OCR Labeler is a NiceGUI web app. After install, run
`pd-ocr-labeler-ui .` from any project directory and open the URL it
prints in your browser.

## Prerequisites

- Python 3.13 or newer (the install scripts will provision one via `uv`
  if needed).
- `git` (only required for installing from source).
- Optional: NVIDIA GPU + CUDA Toolkit for GPU-accelerated OCR. The
  install scripts auto-detect this via `nvidia-smi` and install a
  matching PyTorch wheel.

## Option A — One-line install (recommended for end users)

Linux / macOS:

```sh
curl -sSL https://raw.githubusercontent.com/ConcaveTrillion/pd-ocr-labeler/main/install.sh | sh
```

Windows (PowerShell):

```powershell
irm https://raw.githubusercontent.com/ConcaveTrillion/pd-ocr-labeler/main/install.ps1 | iex
```

The script will:

1. Install [`uv`](https://docs.astral.sh/uv/) if it isn't already on
   your system.
2. Auto-detect NVIDIA CUDA (Linux/Windows) or Apple Silicon and select
   the right PyTorch wheel.
3. Resolve the latest released tag from GitHub and install it as a
   `uv tool`.

After the script finishes you'll have two commands on your PATH:

- `pd-ocr-labeler-ui` — launches the labeler web UI.
- `pd-ocr-labeler-export` — exports labeled pages for downstream use.

If the commands aren't found, add `uv`'s tool bin directory to your
PATH. On Linux / macOS:

```sh
export PATH="$HOME/.local/bin:$PATH"
```

On Windows, run `uv tool update-shell` once.

## Option B — Install from a local clone (for developers)

If you've cloned the repo and want a global install built from your
local source (with CUDA auto-detect):

```sh
git clone https://github.com/ConcaveTrillion/pd-ocr-labeler.git
cd pd-ocr-labeler
make install
```

To remove it later:

```sh
make uninstall
```

`make install` here means *install the global `pd-ocr-labeler-ui` tool
on your PATH*. It does **not** set up a development environment — for
that, use `make setup` (see [`DEVELOPMENT.md`](../../DEVELOPMENT.md)).

## GPU acceleration

The install scripts handle the GPU/CPU split automatically:

- **NVIDIA on Linux or Windows:** if `nvidia-smi` reports a CUDA
  version, the matching `cuXXX` PyTorch wheel index is used.
- **Apple Silicon Mac (M1/M2/M3/M4):** MPS acceleration kicks in
  automatically with the default wheels.
- **No GPU:** CPU-only PyTorch is installed and the labeler works fine
  — first-page OCR is slower but everything else is responsive.

GPU mostly helps when you're processing many pages back-to-back.

### Forcing CPU or a specific CUDA tag (dev installs)

If you're installing from a clone via `make install`, you can override
the auto-detect:

```sh
make install GPU=cpu      # force CPU even on a GPU box
make install GPU=cu124    # force a specific CUDA index (e.g. cu118, cu121, cu124)
```

The same `GPU=` arg works on `make setup` and `make upgrade-deps`.

## Running the app

From any directory containing page images (`.png`, `.jpg`, `.jpeg`):

```sh
pd-ocr-labeler-ui .
```

Then open the URL printed in your terminal (default
`http://127.0.0.1:8080/`).

For other launch options (host/port, project chooser, verbose logging),
see [How to Label a Page](how-to-label-a-page.md) and
`pd-ocr-labeler-ui --help`.

## Updating

Re-run the one-line install command — it always installs the latest
released tag and `uv tool install --reinstall` replaces the existing
copy.

## Uninstalling

```sh
uv tool uninstall pd-ocr-labeler
```

(or `make uninstall` from a repo clone).
