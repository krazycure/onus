"""Custom AceStep UI — API routes + FastAPI app.

Route Map:
    GET  /                    -> index()              Serve frontend HTML
    GET  /api/config          -> config()             GPU/status config
    POST /api/init            -> api_init()           Model initialization
    POST /api/generate        -> api_generate()       Music generation
    POST /api/upload          -> api_upload()         Audio file upload
    GET  /api/audio           -> get_audio()          Serve audio files
    GET  /api/workspaces      -> get_workspaces()     List workspaces
    POST /api/workspace/create-> create_workspace()   Create workspace dir
    GET  /api/results         -> get_results()        Scan results for workspace
    DELETE /api/result/delete -> delete_result()      Delete result + sidecar
    GET  /api/dit-models/available -> get_available_dit_models() List DiT models
    POST /api/dit-model/download   -> download_dit_model()        Download DiT model
    GET  /api/lm-models/available -> get_available_lm_models() List LM models
    POST /api/lm-model/download   -> download_lm_model()       Download LM model
    POST /api/lm/enhance      -> lm_enhance()         Prompt enhancement via LM
    POST /api/interpret       -> interpret_prompt()     Inspiration mode prompt interpretation

Exports:
    app: FastAPI application instance
    _audio_mounts: list of mounted audio directories (for dynamic StaticFiles)
    WORKSPACE_DIR: base directory for generated audio files
    AUDIO_EXTS: set of recognized audio file extensions
    lifespan: startup/shutdown lifecycle context manager
"""

import asyncio
import json
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger


# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

WORKSPACE_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "generated"
)
AUDIO_EXTS = {".wav", ".flac", ".mp3", ".ogg", ".m4a"}


def _parent():
    """Resolve the sibling module (custom_interface.py) at call time.

    Avoids circular import: routes.py is imported by custom_interface.py,
    so we can't import back at module level.
    """
    # __name__ = 'acestep.ui.custom_interface_routes' → strip last segment to get package,
    # then grab the sibling 'custom_interface' from that package's sys.modules entry.
    parent_name = __name__.rsplit(".", 1)[0] + ".custom_interface"
    return sys.modules[parent_name]


# ---------------------------------------------------------------------------
# FastAPI app + lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    yield  # No heavy startup — models load lazily on first request
    p = _parent()
    if p._handler is not None and hasattr(p._handler, "cleanup"):
        try:
            p._handler.cleanup()
        except Exception:
            pass


app = FastAPI(title="ACE-Step Custom UI", version="1.0", lifespan=lifespan)

# Serve static audio files from temp dirs (mounted at runtime)
_audio_mounts: list[str] = []


# ---------------------------------------------------------------------------
# Core endpoints
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the main HTML page."""
    return HTMLResponse(_parent().HTML)


@app.get("/api/config")
async def config():
    """Return app status and available modes."""
    from acestep.gpu_config import get_gpu_config

    p = _parent()
    gpu = get_gpu_config()
    has_gpu = gpu.tier == "unlimited" or gpu.tier.startswith("tier")
    llm_available = (
        p._init_done
        and hasattr(p._llm_handler, "llm_initialized")
        and getattr(p._llm_handler, "llm_initialized", False)
    )
    return {
        "ready": p._init_done,
        "gpu": "cuda" if has_gpu else "cpu",
        "gpu_memory_gb": getattr(gpu, 'gpu_memory_gb', 0),
        "tier": getattr(gpu, 'tier', 0),
        "llm_available": llm_available,
    }


@app.post("/api/init")
async def api_init(req: dict[str, Any]):
    """Initialize models with user-specified config."""
    try:
        result = await _parent().initialize_service(req)
        return JSONResponse(result)
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error(f"Init failed:\n{tb}")
        return JSONResponse({"status": "error", "message": str(e), "traceback": tb}, status_code=500)


@app.post("/api/generate")
async def api_generate(req: dict[str, Any]):
    """Run generation and return results."""
    try:
        result = await _parent().handle_generate(req)
        if result.get("status") == "complete" and result.get("audios"):
            for audio in result["audios"]:
                path = audio.get("path", "")
                if path and Path(path).exists():
                    mount_dir = str(Path(path).parent)
                    if mount_dir not in _audio_mounts:
                        try:
                            app.mount("/tmp_audio", StaticFiles(directory=mount_dir), name="tmp_audio")
                            _audio_mounts.append(mount_dir)
                        except Exception:
                            pass
        return JSONResponse(result)
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ---------------------------------------------------------------------------
# File upload and audio serving
# ---------------------------------------------------------------------------

_UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "_uploads")
os.makedirs(_UPLOAD_DIR, exist_ok=True)


@app.post("/api/upload")
async def api_upload(file: UploadFile):
    """Upload an audio file and return its path."""
    import shutil
    ext = Path(file.filename or "audio").suffix.lower() if file.filename else ".wav"
    if ext not in {".wav", ".flac", ".mp3", ".ogg", ".m4a", ".aac"}:
        ext = ".wav"
    fname = f"{id(file)}{ext}"
    dst = os.path.join(_UPLOAD_DIR, fname)
    with open(dst, "wb") as f:
        content = await file.read()
        f.write(content)
    return {"path": dst}


@app.get("/api/audio")
async def get_audio(path: str):
    """Serve a generated audio file."""
    from fastapi.responses import FileResponse

    if not path or not Path(path).exists():
        return JSONResponse({"error": "File not found"}, status_code=404)
    return FileResponse(path, media_type="audio/flac")


# ---------------------------------------------------------------------------
# Workspace endpoints
# ---------------------------------------------------------------------------


@app.get("/api/workspaces")
async def get_workspaces():
    """List available workspaces (subdirs of generated/ + 'My Experiments')."""
    os.makedirs(WORKSPACE_DIR, exist_ok=True)
    ws = [{"name": "__root__", "label": "My Experiments"}]
    try:
        for entry in sorted(os.listdir(WORKSPACE_DIR)):
            full = os.path.join(WORKSPACE_DIR, entry)
            if os.path.isdir(full):
                count = len([f for f in os.listdir(full) if Path(f).suffix.lower() in AUDIO_EXTS])
                ws.append({"name": entry, "label": entry, "count": count})
    except OSError:
        pass
    return {"workspaces": ws}


@app.post("/api/workspace/create")
async def create_workspace(req: dict):
    """Create a new workspace directory."""
    name = req.get("name", "")
    if not name or not name.strip():
        return JSONResponse({"status": "error", "message": "Name required"}, status_code=400)
    name = name.strip().replace("/", "_").replace("\\", "_")[:64]
    path = os.path.join(WORKSPACE_DIR, name)
    if os.path.exists(path):
        return JSONResponse({"status": "error", "message": "Workspace already exists"}, status_code=409)
    os.makedirs(path, exist_ok=True)
    return {"status": "ok", "name": name}


@app.get("/api/results")
async def get_results(workspace: str = "__root__"):
    """Scan workspace directory for audio files."""
    if workspace == "__root__":
        base = WORKSPACE_DIR
    else:
        base = os.path.join(WORKSPACE_DIR, workspace)
    if not os.path.isdir(base):
        return {"results": []}

    results = []
    try:
        for f in sorted(os.listdir(base), reverse=True):
            full = os.path.join(base, f)
            if not os.path.isfile(full):
                continue
            ext = Path(f).suffix.lower()
            if ext not in AUDIO_EXTS:
                continue
            stat = os.stat(full)
            meta = {}
            try:
                with open(full.rsplit(".", 1)[0] + ".json") as sf:
                    meta = json.load(sf)
            except (OSError, json.JSONDecodeError):
                pass
            results.append({
                "path": full,
                "name": f,
                "size": stat.st_size,
                "modified": stat.st_mtime,
                "meta": meta,
            })
    except OSError as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

    return {"results": results}


@app.delete("/api/result/delete")
async def delete_result(path: str = Body(..., embed=True)):
    """Delete a result file and its sidecar JSON from disk."""
    p = Path(path)
    if not p.exists():
        return JSONResponse({"status": "error", "message": "File not found"}, status_code=404)
    try:
        sidecar = str(p).rsplit(".", 1)[0] + ".json"
        sc = Path(sidecar)
        if sc.exists():
            sc.unlink()
        p.unlink()
        return {"status": "ok"}
    except OSError as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ---------------------------------------------------------------------------
# LM model management endpoints
# ---------------------------------------------------------------------------

_AVAILABLE_LM_MODELS = [
    {"id": "acestep-5Hz-lm-0.6B", "label": "0.6B (fastest, ~3GB VRAM)", "vram_gb": 3},
    {"id": "acestep-5Hz-lm-1.7B", "label": "1.7B (balanced, ~8GB VRAM)", "vram_gb": 8},
    {"id": "acestep-5Hz-lm-4B",   "label": "4B (best quality, ~12GB VRAM)", "vram_gb": 12},
]

# Known DiT model config paths — used to populate the init dropdown and check availability.
_AVAILABLE_DIT_MODELS = [
    "acestep-v15-sft",
    "acestep-v15-turbo",
    "acestep-v15-base",
    "acestep-v15-xl-turbo",
]


def _check_dit_installed(model_id: str) -> bool:
    """Check if a DiT model directory exists in checkpoints."""
    ckpt_dir = os.path.join(
        os.path.dirname(__file__), "..", "..", "checkpoints"
    )
    return os.path.isdir(os.path.join(ckpt_dir, model_id))


@app.get("/api/dit-models/available")
async def get_available_dit_models():
    """Return all known DiT models with installed status."""
    results = []
    for m in _AVAILABLE_DIT_MODELS:
        results.append({"id": m, "installed": _check_dit_installed(m)})
    return {"models": results}


@app.post("/api/dit-model/download")
async def download_dit_model(req: dict):
    """Download a DiT model checkpoint. Runs blocking I/O in threadpool."""
    model_name = req.get("model", "")
    if not model_name:
        return JSONResponse({"status": "error", "message": "No model specified"}, status_code=400)

    from concurrent.futures import ThreadPoolExecutor
    def _do_download():
        from acestep.model_downloader import ensure_dit_model
        ckpt_dir = os.path.join(
            os.path.dirname(__file__), "..", "..", "checkpoints"
        )
        return ensure_dit_model(model_name=model_name, checkpoints_dir=Path(ckpt_dir))

    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        success, msg = await loop.run_in_executor(pool, _do_download)

    if success:
        logger.info("[custom_ui] DiT model downloaded: %s", model_name)
        return {"status": "complete", "message": msg}
    else:
        return JSONResponse({"status": "error", "message": msg}, status_code=500)


def _check_lm_installed(model_id: str) -> bool:
    """Check if an LM model directory exists in checkpoints."""
    ckpt_dir = os.path.join(
        os.path.dirname(__file__), "..", "..", "checkpoints"
    )
    return os.path.isdir(os.path.join(ckpt_dir, model_id))


@app.get("/api/lm-models/available")
async def get_available_lm_models():
    """Return all known LM models with installed status."""
    results = []
    for m in _AVAILABLE_LM_MODELS:
        results.append({**m, "installed": _check_lm_installed(m["id"])})
    return {"models": results}


@app.post("/api/lm-model/download")
async def download_lm_model(req: dict):
    """Download an LM model. Runs blocking I/O in threadpool."""
    model_name = req.get("model", "")
    if not model_name:
        return JSONResponse({"status": "error", "message": "No model specified"}, status_code=400)

    from concurrent.futures import ThreadPoolExecutor
    def _do_download():
        from acestep.model_downloader import ensure_lm_model
        ckpt_dir = os.path.join(
            os.path.dirname(__file__), "..", "..", "checkpoints"
        )
        return ensure_lm_model(model_name=model_name, checkpoints_dir=Path(ckpt_dir))

    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        success, msg = await loop.run_in_executor(pool, _do_download)

    if success:
        logger.info("[custom_ui] LM model downloaded: %s", model_name)
        return {"status": "ok", "message": msg}
    else:
        return JSONResponse({"status": "error", "message": msg}, status_code=500)


# ---------------------------------------------------------------------------
# LLM prompt enhancement endpoint
# ---------------------------------------------------------------------------

_ENHANCE_SYSTEM_PROMPTS = {
    "enhance": (
        "You are a music production assistant. The user will give you a brief description of the music they want. "
        "Expand it into a detailed, structured prompt suitable for a music generation model. Include:\n"
        "- Genre and style descriptors\n"
        "- Instrumentation (specific instruments, not just 'orchestra')\n"
        "- Mood and atmosphere\n"
        "- Tempo feel and energy level\n"
        "- Song structure suggestions (intro, verse, chorus, bridge, outro)\n"
        "- Production notes (reverb, compression, stereo width)\n"
        "Write in the same format as a music generation caption: descriptive, comma-separated phrases. "
        "Keep it under 200 characters if possible. Do NOT add section headers — just write it as a flowing description."
    ),
    "lyrics": (
        "You are a songwriting assistant. The user will give you a brief idea for a song. "
        "Create a complete song structure with lyrics. Include:\n"
        "- Song title\n"
        "- Genre and style note\n"
        "- Full lyrics organized by section: [Intro], [Verse 1], [Chorus], [Verse 2], [Chorus], [Bridge], [Final Chorus], [Outro]\n"
        "- Instrumentation notes per section in brackets, e.g., [guitar solo], [soft piano]\n"
        "Write lyrics that are evocative and specific. Avoid clichés when possible.\n"
        "Format the output as a structured music generation prompt:\n"
        "Title: <title>\n"
        "Style: <genre description>\n"
        "[Intro]\n"
        "<instrumental notes>\n"
        "[Verse 1]\n"
        "<lyrics>\n"
        "... etc.\n"
        "Keep the total under 300 words. Write in English unless the user's input is clearly in another language."
    ),
}


@app.post("/api/lm/enhance")
async def lm_enhance(req: dict):
    """Enhance caption or lyrics via the 5Hz LM using free-form generation (no constrained decoding)."""
    p = _parent()
    if not p._init_done or p._llm_handler is None:
        return JSONResponse(
            {"status": "error", "message": "Models not initialized. Please initialize first."},
            status_code=503,
        )

    if not hasattr(p._llm_handler, "llm_initialized") or not p._llm_handler.llm_initialized:
        return JSONResponse(
            {"status": "error", "message": "LM not available. Initialize with an LM model to use this feature."},
            status_code=400,
        )

    caption = req.get("caption", "").strip()
    lyrics = req.get("lyrics", "").strip()
    mode = req.get("mode", "enhance")  # "enhance" or "lyrics"

    if not caption and not lyrics:
        return JSONResponse(
            {"status": "error", "message": "Provide a caption or lyrics to enhance."},
            status_code=400,
        )

    system_prompts = {
        "enhance": (
            "You are a creative writing assistant for music generation. "
            "Rewrite the user's input into a richer, more detailed musical description. "
            "Preserve the original intent and style but expand on instrumentation, mood, structure, and production details. "
            "Return ONLY the enhanced text — no labels, no explanations."
        ),
        "lyrics": (
            "You are a creative lyricist for music generation. "
            "Write lyrics based on the provided caption description. "
            "Include structural section tags like [Verse], [Chorus], [Bridge]. "
            "Return ONLY the lyrics — no labels, no explanations."
        ),
    }
    system_prompt = system_prompts.get(mode, system_prompts["enhance"])

    def _do_enhance():
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Caption: {caption if caption else '[Instrumental]'}\nLyrics: {lyrics}"},
        ]
        formatted = p._llm_handler.llm_tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True,
        )
        output_text, status_msg = p._llm_handler.generate_from_formatted_prompt(
            formatted_prompt=formatted,
            cfg={"temperature": 0.85},
            use_constrained_decoding=False,
        )
        if not output_text:
            raise RuntimeError(status_msg or "LM returned no output")
        return output_text.strip()

    from concurrent.futures import ThreadPoolExecutor
    loop = asyncio.get_event_loop()
    result_text = await loop.run_in_executor(None, _do_enhance)

    if mode == "lyrics":
        return {"status": "ok", "result": result_text}
    else:
        return {"status": "ok", "result": result_text}


# ---------------------------------------------------------------------------
# Inspiration prompt interpretation endpoint
# ---------------------------------------------------------------------------

@app.post("/api/interpret")
async def interpret_prompt(req: dict):
    """Run Phase 1 (CoT) of the LLM pipeline with a style preset and return the interpreted caption.

    Used in Inspiration mode to iteratively refine prompts before generation.
    """
    p = _parent()
    if not p._init_done or p._llm_handler is None:
        return JSONResponse(
            {"status": "error", "message": "Models not initialized. Please initialize first."},
            status_code=503,
        )

    if not hasattr(p._llm_handler, "llm_initialized") or not p._llm_handler.llm_initialized:
        return JSONResponse(
            {"status": "error", "message": "LM not available. Initialize with an LM model to use this feature."},
            status_code=400,
        )

    caption = req.get("caption", "").strip()
    lyrics = req.get("lyrics", "").strip()
    preset_key = req.get("preset", "detailed")  # style preset key

    if not caption:
        return JSONResponse(
            {"status": "error", "message": "Provide a caption to interpret."},
            status_code=400,
        )

    from acestep.constants import INSPIRATION_PRESETS, DEFAULT_LM_INSPIRED_INSTRUCTION

    system_instruction = INSPIRATION_PRESETS.get(preset_key, DEFAULT_LM_INSPIRED_INSTRUCTION)

    def _do_interpret():
        import random as _random

        # Inject a random seed into the prompt so repeated calls produce different outputs.
        random_seed = _random.randint(0, 2**31 - 1)

        # Build Phase 1 prompt with the style preset as system instruction.
        # For inspiration mode we must NOT present the original text in a structured
        # format that mirrors the constrained output (i.e. not "# Caption\n...").
        # If we do, the model pattern-matches and copies it verbatim into its own
        # "caption:" field regardless of the system instruction.  Instead we frame
        # the original as raw inspiration material with explicit anti-copying cues.
        user_content = (
            f"=== ORIGINAL INPUT (do NOT copy or reuse phrases from this) ===\n"
            f"{caption}\n"
            f"=== END OF ORIGINAL INPUT ===\n"
            f"[Random seed: {random_seed}]"
        )
        if lyrics:
            user_content += f"\n\nLyrics:\n{lyrics}"

        formatted_prompt = p._llm_handler.llm_tokenizer.apply_chat_template(
            [
                {"role": "system", "content": f"# Instruction\n{system_instruction}\n\n"},
                {"role": "user", "content": user_content},
            ],
            tokenize=False,
            add_generation_prompt=True,
        )
        cot_output_text, status_msg = p._llm_handler.generate_from_formatted_prompt(
            formatted_prompt=formatted_prompt,
            cfg={"temperature": 0.95},
            use_constrained_decoding=True,
            stop_at_reasoning=True,
        )
        if not cot_output_text:
            raise RuntimeError(status_msg or "LM returned no output")

        # Extract raw reasoning text first (needed for fallback caption extraction)
        import re as _re
        reasoning = None
        for pat in [r'<antThinking>(.*?)</antThinking>', r'<reasoning>(.*?)</reasoning>']:
            m = _re.search(pat, cot_output_text, _re.DOTALL)
            if m:
                reasoning = m.group(1).strip()
                break
        if not reasoning:
            fallback = cot_output_text.split('<|audio_code_')[0]
            if fallback.strip():
                reasoning = fallback.strip()

        # Parse metadata from CoT output to extract the interpreted caption
        metadata, _ = p._llm_handler.parse_lm_output(cot_output_text)
        interpreted_caption = metadata.get("caption", "")

        # If parse_lm_output didn't find a caption (e.g., model used <antThinking> tags),
        # try to extract it from the reasoning text directly.
        if not interpreted_caption and reasoning:
            cap_match = _re.search(r'^caption:\s*(.+)', reasoning, _re.MULTILINE)
            if cap_match:
                interpreted_caption = cap_match.group(1).strip()

        logger.info(f"[interpret] input caption={caption!r} | output caption={interpreted_caption!r} | metadata keys={list(metadata.keys())}")

        return {
            "interpreted_caption": interpreted_caption,
            "metadata": metadata,
            "reasoning": reasoning,
        }

    from concurrent.futures import ThreadPoolExecutor
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, _do_interpret)

    if not result.get("interpreted_caption"):
        return JSONResponse(
            {"status": "error", "message": "Interpretation produced no caption. Try again."},
            status_code=502,
        )
    return {"status": "ok", **result}


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    """CLI entry point — launches the FastAPI server."""
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser(description="ACE-Step Custom UI")
    parser.add_argument("--host", default="127.0.0.1", help="Server host")
    parser.add_argument("--port", type=int, default=8090, help="Server port")
    args = parser.parse_args()

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
