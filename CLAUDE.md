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

## Git / GitHub

This repo has **no remote configured by default**. To push:

```bash
git remote add origin https://github.com/krazycure/onus.git
# Fix broken global URL rewrite rule first (converts git@ to https:// without .com):
git config --global --unset 'url.https://.insteadof'
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

## Known struggles — splitting custom_interface_js.py (2070-line monolith)

### Goal
Split `acestep/ui/custom_interface_js.py` (~2070 lines of JS in one raw string) into chunk modules + thin facade. Each chunk exports `_chunk = r"""..."""`. Facade concatenates them into `CLIENT_JS`.

### What went wrong — repeated failures to get byte-exact reconstruction
Every attempt failed verification: the reconstructed JS never matched the original byte-for-byte. The core issue is **triple-quote boundary confusion** in Python string manipulation:

1. **The original file uses `r"""..."""` delimiters.** Extracting content requires finding the opening and closing triple-quotes reliably.
2. **When writing chunk files, each also uses `r"""..."""`.** My extraction logic (`content.rindex('"""')`) should find the last occurrence (the closing delimiter), but when I pass Python code containing `"""` as string literals to write these files, the escaping gets mangled — especially in heredocs and `-c` one-liners.
3. **Trailing blank lines get lost.** `'\n'.join()` strips trailing empty elements. The original has a blank line separator between chunks (index 706) that keeps getting dropped or duplicated during reconstruction.
4. **The leading `\n` after `r"""`.** In the original, `CLIENT_JS = r"""` is followed by a newline before the first JS line (`const MODES`). My extraction consistently missed this because I was slicing at wrong indices.

### Key insight: the tools are fighting triple-quotes
When writing Python code that contains `"""` (to produce chunk files with `r"""..."""`) inside another string literal or heredoc, the boundaries get confused. This is a fundamental limitation of trying to manipulate triple-quote-delimited content through Python string APIs in one-liners and heredocs.

### What would work
- **Use `git show HEAD:file | sed -n 'X,Yp'` piped directly to files** — avoids all Python quoting issues by using shell tools for extraction
- **Store chunks as plain text files on disk, read at runtime** — no string escaping needed because content lives in real files
- **Write a temp script file (not inline code)** that reads the original by line number and writes chunks directly

### Resolution (Option B: plain text chunk files)
Done. Three `.js` files store raw JS content on disk, read at import time:
- `acestep/ui/js_modes.js` — mode system, visibility logic, prompt library (~693 lines)
- `acestep/ui/js_results.js` — init flow, generation, results rendering, workspaces (~766 lines)  
- `acestep/ui/js_settings.js` — settings persistence, presets, waveform, toast notifications (~595 lines)

The facade (`custom_interface_js.py`) reads these at import time and concatenates them into `CLIENT_JS`. Byte-exact match verified against git HEAD.
