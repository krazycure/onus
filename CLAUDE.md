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

## Feature Backlog (from gap analysis vs ACE-Step tutorial)

These are known feature gaps between what the ACE-Step tutorial describes and what the custom UI currently exposes. Prioritized by severity.

**Upstream Gradio source reference:** All original Gradio UI code lives in `acestep/ui/gradio/` of the upstream [ACE-Step-1.5](https://github.com/ace-step/ACE-Step-1.5) repo. Key files:
- `acestep/constants.py` — TASK_TYPES, MODE_TO_TASK_TYPE, BPM_MIN/MAX, DURATION_MIN/MAX, VALID_TIME_SIGNATURES
- `acestep/inference.py` — GenerationParams dataclass (all param defaults & docstrings)
- `acestep/ui/gradio/interfaces/generation_advanced_dit_controls.py` — DiT sliders/dropdowns (P2/P4)
- `acestep/ui/gradio/interfaces/generation_advanced_primary_controls.py` — LM hyperparams panel (P3)
- `acestep/ui/gradio/interfaces/generation_advanced_output_controls.py` — cover strength controls (P5-D)
- `acestep/ui/gradio/interfaces/generation_tab_secondary_controls.py` — BPM range, time sig dropdown, duration sliders (P5-A/B/C)
- `acestep/ui/gradio/interfaces/generation_defaults.py` — init defaults, model resolution chain (P1-C)
- `acestep/ui/gradio/events/generation/model_config.py` — base model detection / config handling
- `acestep/ui/gradio/events/generation/mode_ui.py` — mode visibility / UI update logic

### P1 — Core Task Coverage
- **P1-A: Add "Complete" task mode** — UI skeleton done (pill, taskTypeMap, src-audio visibility, CSS accent `#b388ff`, track selector). Does NOT work yet. See "Complete Mode Known Gaps" below for what's missing vs upstream Gradio and why results are noisy/incoherent.
  - Upstream Gradio ref: `acestep/constants.py:90` (TASK_TYPES), `acestep/constants.py:106-114` (MODE_TO_TASK_TYPE), `acestep/ui/gradio/events/generation/mode_ui.py` (mode visibility logic)
- **P1-B: Add "base" DiT model to init modal** — Tutorial says base model required for extract/lego/complete tasks. Init modal only offers sft/turbo/xl-turbo. Add `<option value="acestep-v15-base">` to `init-config_path` select.
  - Upstream Gradio ref: `acestep/ui/gradio/events/generation/model_config.py` (base model detection), `acestep/constants.py:97` (TASK_TYPES_BASE)
- **P1-C: Default DiT → turbo (not sft)** — Tutorial states default should be `turbo + 1.7B LM`. Init modal defaults to SFT (50 steps). Move `selected` from sft option to turbo; update JS fallback in `runInit()`.
  - Upstream Gradio ref: `acestep/ui/gradio/interfaces/generation_defaults.py:82-96` (resolve_is_pure_base_model default chain), `acestep/inference.py:157` (lm_temperature=0.85)

### P2 — DiT Inference Parameters
- **Shift slider** (range 0.5–5.0, default 1.0) — controls attention allocation during denoising
  - Upstream Gradio ref: `acestep/ui/gradio/interfaces/generation_advanced_dit_controls.py:94` (Slider def), `acestep/inference.py:72,136` (dataclass field + docstring)
- **CFG interval start/end** (range 0.0–1.0) — which diffusion stages apply CFG
  - Upstream Gradio ref: `acestep/ui/gradio/interfaces/generation_advanced_dit_controls.py:108,118` (Slider defs), `acestep/inference.py:70-71,134-135` (dataclass fields)
- **infer_method dropdown** (ode/sde) — deterministic vs random denoising
  - Upstream Gradio ref: `acestep/ui/gradio/interfaces/generation_advanced_dit_controls.py:52` (Dropdown def), `acestep/inference.py:75,137` (dataclass field)
- Wire through HTML advanced panel → JS body dict → backend `GenerationParams`

### P3 — LM Hyperparameters Panel (9 params from Gradio parity)
All defined in upstream `generation_advanced_primary_controls.py:build_lm_controls()`:
| Param | Upstream file:line | Dataclass default (`inference.py`) |
|-------|-------------------|-------------------------------------|
| Temperature | `generation_advanced_primary_controls.py:63-71` | `lm_temperature: float = 0.85` (:157) |
| LM CFG scale | `generation_advanced_primary_controls.py:72-80` | `lm_cfg_scale: float = 2.0` (:158) |
| Top-K | `generation_advanced_primary_controls.py:81-89` | `lm_top_k: int = 0` (:159) |
| Top-P | `generation_advanced_primary_controls.py:90-98` | `lm_top_p: float = 0.9` (:160) |
| Negative prompt | `generation_advanced_primary_controls.py:99-107` | `lm_negative_prompt: str = "NO USER INPUT"` (:161) |
| CoT Metas checkbox | `generation_advanced_primary_controls.py:111-117` | `use_cot_metas: bool = True` (:162) |
| CoT Language checkbox | `generation_advanced_primary_controls.py:118-124` | `use_cot_language: bool = True` (:165) |
| CoT Caption checkbox | `generation_advanced_primary_controls.py:142-148` | `use_cot_caption: bool = True` (:163) |
| Batch LM checkbox | `generation_advanced_primary_controls.py:135-141` | `lm_batch_chunk_size: int = 8` (GenerationConfig:204) |
| Debug Decode checkbox | `generation_advanced_primary_controls.py:129-135` | `constrained_decoding_debug: bool = False` (:205) |

### P4 — Additional DiT Params
All defined in upstream `generation_advanced_dit_controls.py`:
- **Sampler mode dropdown** (euler/heun) — `generation_advanced_dit_controls.py:61`, dataclass default `"euler"` at `inference.py:138`
- **velocity_norm_threshold slider** (0.0–5.0) — `generation_advanced_dit_controls.py:70`, dataclass default `0.0` at `inference.py:139` (comment: "Clamp velocity prediction norms")
- **velocity_ema_factor slider** (0.0–0.5) — `generation_advanced_dit_controls.py:79`, dataclass default `0.0` at `inference.py:140` (comment: "Velocity EMA smoothing")
- **MLX VAE chunk size slider** (192–2048, MPS-only visibility) — `generation_advanced_dit_controls.py:144`

### P5 — UX Polish
- **P5-A:** BPM range validation on `bpm-custom` input (`min="30" max="300"`)
  - Upstream Gradio ref: `acestep/constants.py:50-51` (BPM_MIN=30, BPM_MAX=300), `generation_tab_secondary_controls.py` (BPM range UI)
- **P5-B:** Add missing time signature options: 9/8, 12/8 to dropdown
  - Upstream Gradio ref: `acestep/constants.py:62` (VALID_TIME_SIGNATURES=[2,3,4,6]), `generation_tab_secondary_controls.py` (time sig dropdown)
- **P5-C:** Duration range hints on duration-custom input (`min="10" max="600"`)
  - Upstream Gradio ref: `acestep/constants.py:79-80` (DURATION_MIN=10, DURATION_MAX=600), `generation_tab_secondary_controls.py` (duration sliders)
- **P5-D:** Cover strength default → 1.0 (HTML + JS + backend). Current 0.75 was a workaround for model bug producing identical output at 1.0 — may be fixed now.
  - Upstream Gradio ref: `generation_advanced_output_controls.py` (build_cover_strength_controls, default=1.0), dataclass default `audio_cover_strength: float = 1.0` at `inference.py:152`

### Complete Mode Known Gaps

Complete mode (`task_type="complete"`) uploads a single-track source audio and asks the model to generate full accompaniment around it. It works in upstream Gradio but our custom UI produces noisy/incoherent results because several critical pieces are missing.

**What we have today:**
- Mode pill + visibility logic (js_modes.js) — working
- Track selector dropdown ("Focus") — sends single instrument name as `global_caption` / `{TRACK_CLASSES}` placeholder in prompt template (`constants.py:173`)
- BPM auto-detection from source audio via librosa (`custom_interface.py:_detect_bpm_from_audio()`) — graceful fallback to ACE-Step internal estimation if librosa unavailable
- Track name → global_caption for both lego and complete tasks (fixed in this session)

**What upstream Gradio has that we're missing:**

1. **`complete_track_classes` CheckboxGroup** — multi-select telling the model *which tracks are already present* in the source audio. This is the critical gap: without it, the model doesn't know what's there and may duplicate or ignore existing content.
   - Upstream ref: `acestep/ui/gradio/interfaces/generation_tab_source_controls.py:65` (CheckboxGroup def), `acestep/ui/gradio/events/generation/mode_ui.py:145` (visibility wiring)

2. **`complete_help_group`** — contextual help button explaining Complete mode semantics
   - Upstream ref: `generation_tab_source_controls.py:63` (gr.Group with help button)

3. **Auto-BPM forced for Complete in upstream?** — No. The upstream Gradio forces `auto_bpm=True` only for Extract/Lego modes (`mode_ui.py:105`). For Complete, the model is expected to analyze source audio internally. Our BPM detection is a bonus but not a substitute for `complete_track_classes`.

**Why results are noisy/incoherent:**
- Without `complete_track_classes`, the prompt template `"Complete the input track with {TRACK_CLASSES}:"` only tells the model *what to add*, not what's already there. The model may duplicate existing content or generate conflicting layers.
- Single-track focus (our dropdown) is insufficient — Complete mode needs multi-select to describe the full source composition.

**Next steps for Complete mode parity:**
1. Add `complete_track_classes` checkbox group to Complete mode UI (P2 priority)
2. Wire it through JS → backend → GenerationParams (new field needed in dataclass?)
3. Test with base model (per P1-B: Complete requires base DiT, not SFT/turbo)
4. Consider adding a "What's in my track?" label/tooltip for UX clarity
