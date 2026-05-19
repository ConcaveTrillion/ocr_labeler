# Dev-Local Upgrade Flow (Spec)

Status: **spec only — not yet implemented.** Workspace-wide standard,
authored 2026-05-07. Tracked in
[`docs/planning/roadmap/overview.md`](planning/roadmap/overview.md).

## Repo-specific status

**Applicable, deferred-pending-deprecation.** This repo (legacy NiceGUI
labeler) is being phased out in favor of
[`pd-ocr-labeler-spa`](../../pd-ocr-labeler-spa/) (FastAPI + React port).
However, while the migration is in flight the legacy labeler still
receives dependency updates — most notably via `make upgrade-pd-book-tools`
and `make upgrade-deps` — and a developer running it against an editable
sibling `pd-book-tools` checkout is squarely in the hazard zone described
below. The fix should land here whenever the workspace-wide rollout
reaches this repo; it does not need to wait for SPA cutover.

This repo does **not currently** expose a `dev-local` mode (no
editable-sibling target, no `dev-local` marker file, no `PD_DEV_LOCAL`
handling). The hazard is therefore latent: any contributor who *manually*
swaps in editable `pd-book-tools` (e.g. `uv pip install -e
../pd-book-tools`) will silently lose that swap on the next
`make upgrade-deps`.

## The hazard

`make upgrade-deps` ends with:

```makefile
uv lock --upgrade
uv sync --group all-dev
```

`uv sync` reconciles the venv to match `uv.lock` exactly. Any
out-of-band editable installs (sibling pd-* checkouts, doctr-from-git,
GPU-specific torch wheels) that are not represented in the lockfile are
silently reverted to the canonical published baseline. The developer
gets no warning; the next test run may pass or fail in surprising ways
because the imported `pd_book_tools` is no longer the one they were
editing.

## Required behavior (workspace-wide contract)

1. **Detect dev-local vs canonical** before any `uv sync` triggered by
   `upgrade-deps` (or any sibling target that re-syncs).
2. **Detection cascade:**
   1. Probe `uv pip show pd-book-tools` for an `Editable project
      location:` line. This is the cross-repo contract — anchored in
      pd-book-tools because every other pd-* repo depends on it. If
      present, the venv is in dev-local mode.
   2. Fallback: presence of a marker file in `.venv/` (e.g.
      `.venv/.pd-dev-local`) written by whichever target enabled
      dev-local mode.
   3. Last-resort opt-in: environment variable `PD_DEV_LOCAL=1`.
3. **UX:**
   - **Default `upgrade-deps` in dev-local mode: refuse with a
     message.** The message must name the detected editable package(s)
     and point the user at `upgrade-deps-local`. Refusing is preferred
     over auto-restoring because the restore step depends on knowing
     *which* siblings to re-link, and that intent belongs to the human.
   - **Sibling target `upgrade-deps-local`:** runs `uv lock --upgrade`,
     `uv sync --group all-dev`, then re-applies the editable
     sibling installs and any GPU/torch overrides recorded for the
     venv. This is the dev-local-aware equivalent.
4. **Canonical-mode behavior unchanged.** When detection finds no
   editable siblings and no marker/env opt-in, `upgrade-deps` runs
   exactly as it does today.
5. **Cross-platform.** Detection and refusal must work on macOS, Linux,
   and Windows (PowerShell). `uv pip show` parsing is portable; marker
   file and env var are trivially portable.

## Implementation notes for this repo (when picked up)

- This repo has no `dev-local` setup target today — implementing the
  refusal does not require first building one. The detection cascade
  works against any manually-applied editable install.
- If a `dev-local` setup target is added later (mirroring whatever
  pattern the workspace settles on, likely seeded from `pd-ocr-cli`),
  it must write the `.venv/.pd-dev-local` marker so the fallback
  detection works even when `uv pip show` parsing is brittle.
- `make upgrade-pd-book-tools` also ends in `uv sync --group all-dev`
  and has the same hazard. Apply the same refusal there, or document
  why it's exempt (it explicitly bumps the canonical pin, so arguably
  the user *wants* canonical mode — but they'd still lose any *other*
  editable siblings).

## References

- Workspace decision: 2026-05-07, applied across all pd-* repos.
- Cross-repo anchor: `pd-book-tools` is the foundation library every
  other pd-* depends on, so `uv pip show pd-book-tools` is the
  reliable detection probe.
