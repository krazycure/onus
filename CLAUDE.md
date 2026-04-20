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
- `custom_interface_js.py` — `CLIENT_JS`: client-side JavaScript constant

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
