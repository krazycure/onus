# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Onus — a custom FastAPI + vanilla HTML/CSS/JS frontend plugin for [ACE-Step 1.5](https://github.com/ace-step/ACE-Step-1.5). Replaces the default Gradio UI. Zero Gradio dependency.

## Architecture

The codebase is split into two layers:

**Backend core** (`acestep/ui/custom_interface.py`): Model initialization, generation handler, CLI entry point (`acestep-custom`). Reconstructs the full HTML at runtime via f-string interpolation of extracted frontend constants.

**Extracted frontend assets** (sibling modules in `acestep/ui/`):
- `custom_interface_html.py` — `FRONTEND_BODY_HTML`: body template constant
- `custom_interface_css.py` — `STYLES_CSS`: stylesheet constant
- `custom_interface_js.py` — thin facade that reads 3 chunk files at import time:
  - `js_modes.js` — mode system, visibility logic, prompt library (~693 lines)
  - `js_results.js` — init flow, generation, results rendering, workspaces (~766 lines)
  - `js_settings.js` — settings persistence, presets, waveform, toast notifications (~595 lines)

**API routes** (`acestep/ui/custom_interface_routes.py`): FastAPI app with all API endpoints (init, generate, upload, workspaces, results, LM model management, prompt enhancement). Uses `_parent()` lazy import to avoid circular imports back to `custom_interface.py`.

**Modified upstream modules**: `constants.py`, `inference.py`, and `llm_inference.py` are patched versions of the ACE-Step originals (add INSPIRATION_PRESETS, Edit mode, inspiration task type, system_instruction param).

## Running

```bash
uv run acestep-custom --port 8090
```

The server starts on `127.0.0.1:8090` by default. Models lazy-initialize on first generation request.

## Making changes

- Brand text (top-left "ACE-STEP"): `acestep/ui/custom_interface_html.py:89` (`<span class="brand">`)
- Page title ("ACE-Step"): `acestep/ui/custom_interface.py:55` (`<title>`)
- API app title: `acestep/ui/custom_interface_routes.py:79` (FastAPI `title=` kwarg)

## Git / GitHub

Remote `origin` is configured (`git@github.com:krazycure/onus.git`). Push with:

```bash
git push -u origin main
```

## Deployment to existing ACE-Step install

Copy these files into `/home/admin/ACE-Step-1.5/`:
- `acestep/constants.py`
- `acestep/inference.py`
- `acestep/llm_inference.py`
- `acestep/ui/custom_interface*.py` (all 6 files)

Then run:
```bash
cd /home/admin/ACE-Step-1.5 && uv sync && uv run acestep-custom --port 8090
```

## Development Workflow
- **Git Safety:** Always check `git status` before big edits.
- **Commits:** After completing a working feature, run `git add .` and `git commit -m "feat: [description]"`.
- **Remote:** Push to GitHub after every major milestone.
- **Rollback:** If a refactor fails or logic becomes circular, use the `/undo` command or `git reset --hard HEAD`.
- **Complex string manipulation:** When you need to extract/manipulate content that contains triple-quotes (`"""`) or other complex delimiters, write a temp `.py` script file and run it — never try inline `-c` code or heredocs. The quoting boundaries will always conflict with the Python parser. Use `git show HEAD:file | sed -n 'X,Yp' > target_file` for line-range extraction as an alternative that avoids Python entirely.

## File size guidelines

- **Soft cap: 800 lines per file.** When a file approaches this threshold, split it — ideally by extracting logical chunks (e.g., route groups, JS modules) rather than arbitrary line counts.
- **Raw string assets** (`*.py` files that are single f-string constants for HTML/CSS/JS) should be treated as monoliths until they become unwieldy; prefer the plain-text chunk pattern used for `js_*.js`.

## Modularity going forward

- Split when a file has clearly separable concerns (e.g., route groups, feature modules), not just because it's long.
- Don't over-split — one file per logical concern is fine. No need to extract every function or small group into its own module.
- When adding new routes or features to `custom_interface_routes.py`, watch for natural grouping boundaries (init/generate vs workspaces vs LM models, etc.) and split proactively before it hits 800 lines.

## Resolved: splitting custom_interface_js.py monolith

`acestep/ui/custom_interface_js.py` was split from a 2070-line raw string into three plain-text chunk files + thin facade (see Architecture section above). The chunks are stored as `.js` files on disk and read at import time, avoiding the triple-quote boundary issues that plagued earlier attempts.
