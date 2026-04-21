"""Custom AceStep web interface — FastAPI + vanilla HTML/CSS/JS.

Run via: ``uv run acestep-custom --port 8090``

No framework constraints, no CSS hacks. Dark theme, two-column layout,
full control over everything. Includes model initialization, training, and
batch generation controls from the original UI.

Architecture:
    This file is the backend core (model init, generation handler, CLI entry).
    Frontend assets are extracted into sibling modules to reduce context pressure:

    - ``custom_interface_html.py``  - HTML body template constant (FRONTEND_BODY_HTML)
    - ``custom_interface_css.py``   - Stylesheet constant (STYLES_CSS)
    - ``custom_interface_js.py``    - Client-side JavaScript constant (CLIENT_JS)
    - ``custom_interface_routes.py``- FastAPI app + all API route handlers

HTML is reconstructed at runtime via f-string interpolation of the extracted
constants, preserving the original single-file deployment model while keeping
source files modular.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

from acestep.audio_utils import save_audio
from acestep.inference import format_sample
from loguru import logger

# Import extracted frontend assets (reconstructed into HTML constant)
from .custom_interface_html import FRONTEND_BODY_HTML  # noqa: F401
from .custom_interface_css import STYLES_CSS  # noqa: F401
from .custom_interface_js import CLIENT_JS  # noqa: F401

# Import shared routes infrastructure
from .custom_interface_routes import (  # noqa: F401
    WORKSPACE_DIR,
    AUDIO_EXTS,
    app,
    _audio_mounts,
    lifespan,
)

# Reconstruct the full HTML at runtime from extracted constants.
HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ACE-Step</title>
<style>
{STYLES_CSS}
</style>
</head><body>{FRONTEND_BODY_HTML}<script>{CLIENT_JS}</script></body></html>"""

# ---------------------------------------------------------------------------
# Global state (model handlers, init status)
# ---------------------------------------------------------------------------

_handler: Any = None
_llm_handler: Any = None
_init_done: bool = False
_init_params: dict[str, Any] = {}


def _get_project_root() -> str:
    """Return the repository root directory."""
    return str(Path(__file__).resolve().parent.parent.parent)


# ---------------------------------------------------------------------------
# BPM detection for Complete mode
# ---------------------------------------------------------------------------

def _detect_bpm_from_audio(audio_path: str) -> int | None:
    """Estimate BPM from an audio file using librosa onset-based tempo estimation.

    Returns None if librosia is unavailable or detection fails — the caller
    will fall back to ACE-Step's internal auto-BPM estimation (bpm=None).
    """
    import os as _os

    if not audio_path or not _os.path.isfile(audio_path) or _os.path.getsize(audio_path) < 44:
        return None

    try:
        import librosa
    except ImportError:
        logger.warning("[custom_ui] BPM detection skipped — librosia not installed. "
                       "Install with: pip install librosa")
        return None

    try:
        y, _ = librosa.load(audio_path, sr=None, mono=False)
        if y.ndim > 1:
            y = y.mean(axis=0)

        onset_env = librosa.onset.onset_strength(y=y, sr=None)
        onsets = librosa.onset.onset_detect(onset_envelope=onset_env, sr=None)

        if len(onsets) < 4:
            return None

        tempograms = librosa.feature.tempo_aggregate(
            onset_envelope=onset_env, sr=None, aggregation=librosa.tempogram.onset_hops,
        )
        tempo = librosa.beat.tempo(
            onset_envelope=onset_env, sr=None, aggregate=tempograms,
            max_bpm=300, min_bpm=30,
        )

        estimated = int(round(tempo[0])) if isinstance(tempo, (list, tuple)) else int(round(float(tempo)))
        return max(30, min(300, estimated))

    except Exception:
        logger.warning("[custom_ui] BPM detection failed for %s", audio_path)
        return None


# ---------------------------------------------------------------------------
# Model initialization helpers
# ---------------------------------------------------------------------------

async def ensure_models():
    """Lazy-initialize AceStep models on first generation request.

    On first call, detects GPU tier, auto-selects an LM model from
    ``checkpoints/``, and initializes both DiT/VAE (AceStepHandler) and
    LLM (LLMHandler). Subsequent calls are no-ops.
    """
    global _handler, _llm_handler, _init_done

    if _init_done:
        return

    from acestep.handler import AceStepHandler
    from acestep.llm_inference import LLMHandler
    from acestep.gpu_config import get_gpu_config

    gpu = get_gpu_config()
    has_gpu = gpu.tier == "unlimited" or gpu.tier.startswith("tier")

    _handler = AceStepHandler()
    status_msg, ok = _handler.initialize_service(
        project_root=_get_project_root(),
        config_path="acestep-v15-turbo",
        device="auto" if has_gpu else "cpu",
        use_flash_attention=has_gpu,
        compile_model=False,
        offload_to_cpu=gpu.gpu_memory_gb < 16,
        offload_dit_to_cpu=False,
    )
    if not ok:
        raise RuntimeError(f"DiT/VAE init failed: {status_msg}")

    # Auto-detect available LM model in checkpoints
    ckpt_dir = os.path.join(_get_project_root(), "checkpoints")
    lm_model_path = None
    if os.path.isdir(ckpt_dir):
        for name in os.listdir(ckpt_dir):
            full = os.path.join(ckpt_dir, name)
            if os.path.isdir(full) and "5Hz-lm" in name:
                lm_model_path = name
                break
    # Fallback to 1.7B (default model)
    if not lm_model_path:
        lm_model_path = "acestep-5Hz-lm-1.7B"

    _llm_handler = LLMHandler()
    llm_status, llm_ok = _llm_handler.initialize(
        checkpoint_dir=ckpt_dir,
        lm_model_path=lm_model_path,
        backend="vllm" if has_gpu else "pt",
        device="auto" if has_gpu else "cpu",
        offload_to_cpu=False,
    )

    logger.info("[custom_ui] LLM init: model=%s ok=%s status='%s'", lm_model_path, llm_ok, llm_status)

    _init_done = True


async def initialize_service(params: dict[str, Any]) -> dict[str, Any]:
    """Initialize models with user-specified config. Returns status dict."""
    global _handler, _llm_handler, _init_done, _init_params

    from acestep.handler import AceStepHandler
    from acestep.llm_inference import LLMHandler
    from acestep.gpu_config import get_gpu_config

    # Tear down existing handlers to allow re-initialization (e.g., model switch)
    if _init_done:
        logger.info("[custom_ui] Re-initializing — tearing down existing handlers")
        if _llm_handler is not None and hasattr(_llm_handler, "cleanup"):
            try:
                _llm_handler.cleanup()
            except Exception as e:
                logger.warning("[custom_ui] LLM cleanup error: %s", e)
        if _handler is not None and hasattr(_handler, "cleanup"):
            try:
                _handler.cleanup()
            except Exception as e:
                logger.warning("[custom_ui] DiT/VAE cleanup error: %s", e)
        _llm_handler = None
        _handler = None
        _init_done = False

    gpu = get_gpu_config()
    has_gpu = gpu.tier == "unlimited" or gpu.tier.startswith("tier")
    device = params.get("device", "auto")
    if device == "auto":
        device = "auto" if has_gpu else "cpu"
    is_cpu = device == "cpu"

    config_path = params.get("config_path", "acestep-v15-turbo")
    quantization = params.get("quantization")
    compile_model = bool(params.get("compile_model", False))
    offload_to_cpu = bool(params.get("offload_to_cpu", gpu.gpu_memory_gb < 16))
    offload_dit_to_cpu = bool(params.get("offload_dit_to_cpu", False))

    _handler = AceStepHandler()
    status_msg, ok = _handler.initialize_service(
        project_root=_get_project_root(),
        config_path=config_path,
        device=device,
        use_flash_attention=not is_cpu,
        compile_model=compile_model,
        offload_to_cpu=offload_to_cpu,
        offload_dit_to_cpu=offload_dit_to_cpu,
        quantization=quantization,
    )

    if not ok:
        return {"status": "error", "message": f"DiT/VAE init failed: {status_msg}"}

    # Initialize LM if requested — auto-detect available model
    lm_model_path = params.get("lm_model_path", None)
    if not lm_model_path:
        ckpt_dir = os.path.join(_get_project_root(), "checkpoints")
        if os.path.isdir(ckpt_dir):
            for name in os.listdir(ckpt_dir):
                full = os.path.join(ckpt_dir, name)
                if os.path.isdir(full) and "5Hz-lm" in name:
                    lm_model_path = name
                    break
    if not lm_model_path:
        lm_model_path = "acestep-5Hz-lm-1.7B"

    backend = params.get("backend", "vllm" if not is_cpu else "pt")
    init_llm = bool(params.get("init_llm", True))

    _llm_handler = LLMHandler()
    llm_status, llm_ok = _llm_handler.initialize(
        checkpoint_dir=os.path.join(_get_project_root(), "checkpoints"),
        lm_model_path=lm_model_path if init_llm else None,
        backend=backend,
        device=device,
        offload_to_cpu=False,
    )

    _init_done = True
    _init_params = {
        "config_path": config_path,
        "device": device,
        "lm_model_path": lm_model_path,
        "backend": backend,
        "quantization": quantization,
        "compile_model": compile_model,
        "offload_to_cpu": offload_to_cpu,
    }

    return {
        "status": "complete",
        "message": f"DiT: {config_path} | Device: {device}",
        "gpu_memory_gb": gpu.gpu_memory_gb,
        "tier": gpu.tier,
        "llm_available": init_llm and llm_ok,
    }


# ---------------------------------------------------------------------------
# Generation handler
# ---------------------------------------------------------------------------

async def handle_generate(data: dict[str, Any]) -> dict[str, Any]:
    """Run a generation and return results.

    Parses request fields into ``GenerationParams``/``GenerationConfig``,
    invokes the ``generate_music`` pipeline, saves sidecar metadata JSONs,
    and returns serialized audio paths with timing info.
    """
    global _handler, _llm_handler

    from acestep.inference import generate_music, GenerationParams, GenerationConfig

    # Lazy init
    await ensure_models()

    if not _init_done or _handler is None:
        return {"status": "error", "message": "Models failed to initialize"}

    # Parse request fields with defaults matching Gradio UI
    caption = data.get("caption", "")
    lyrics = data.get("lyrics", "[Instrumental]")
    task_type = data.get("task_type", "text2music")
    inference_steps = int(data.get("inference_steps", 8))
    guidance_scale = float(data.get("guidance_scale", 7.0))
    seed = int(data.get("seed", -1))
    batch_size = max(1, min(8, int(data.get("batch_size", 2))))
    duration = data.get("duration", None)
    if duration is not None and str(duration).strip():
        try:
            duration = float(duration)
        except (ValueError, TypeError):
            duration = None
    _raw_bpm = data.get("bpm", None)
    try:
        bpm = int(_raw_bpm) if _raw_bpm is not None and str(_raw_bpm).strip() else None
    except (ValueError, TypeError):
        bpm = None
    keyscale = data.get("keyscale", "")
    timesignature = data.get("timesignature", "")
    vocal_language = data.get("vocal_language", "en")
    thinking = bool(data.get("thinking", True))

    # CoT (Chain-of-Thought) flags — read from request or default based on
    # thinking value. For Complete mode, force all to False below.
    def _bool_val(key: str, default: bool = True) -> bool:
        raw = data.get(key)
        if raw is None:
            return default
        if isinstance(raw, bool):
            return raw
        return str(raw).lower() in ("true", "1")

    use_cot_caption = _bool_val("use_cot_caption", True)
    use_cot_metas = _bool_val("use_cot_metas", True)
    use_cot_language = _bool_val("use_cot_language", True)

    # Complete mode: disable thinking + all CoT flags. The LLM has no knowledge
    # of complete_track_classes (that field only reaches DiT via instruction),
    # so the LLM generates audio codes for its own full arrangement, and DiT
    # tries to blend it with the source — producing a muddy multi-instrument
    # mess. Forcing thinking=False sends caption + instruction straight to DiT,
    # which is what Complete mode actually intends.
    if task_type == "complete":
        thinking = False
        use_cot_caption = False
        use_cot_metas = False
        use_cot_language = False
    use_random_seed = bool(data.get("use_random_seed", True))
    audio_format = data.get("audio_format", "mp3")
    reference_audio = data.get("reference_audio_path") or data.get("reference_audio")
    src_audio = data.get("src_audio_path") or data.get("src_audio")
    track_name = data.get("track_name") or data.get("name")  # frontend sends "track_name" (js_results.js), legacy "name" kept for compat
    complete_track_classes = data.get("complete_track_classes", [])  # Complete mode: tracks present in source audio

    # Build instruction with track classes substitution for Complete mode.
    # Without this, the prompt template has an unfilled {TRACK_CLASSES} placeholder
    # which confuses the model and produces noisy/incoherent output.
    complete_instruction = None
    if task_type == "complete" and complete_track_classes:
        complete_instruction = f'Complete the input track with {", ".join(complete_track_classes)}:'

    # Cover mode: default strength 0.75 (not Gradio's 1.0). During initial dev,
    # setting cover strength to 1.0 produced output identical to the input audio
    # (likely a model bug). The workaround was to use 0.75 as the default. This
    # may be adjusted back to 1.0 after confirming covers work correctly.
    audio_cover_strength = float(data.get("audio_cover_strength", 0.75))
    cover_noise_strength = float(data.get("cover_noise_strength", 0.0))
    inspiration_preset = data.get("inspiration_preset", None)

    # Edit mode: time range mask and strength
    repainting_start = float(data.get("repainting_start", 0.0))
    repainting_end_raw = data.get("repainting_end", "-1")
    try:
        repainting_end = float(repainting_end_raw) if repainting_end_raw is not None else -1.0
    except (ValueError, TypeError):
        repainting_end = -1.0
    repaint_mode = str(data.get("repaint_mode", "balanced"))
    repaint_strength = float(data.get("repaint_strength", 0.5))

    # When a non-default time range is set, use explicit mask so the backend
    # only regenerates within that window (default auto lets model decide).
    # For lego/Sound Stack, always force explicit so Mask Control: true is used.
    if task_type == "lego":
        chunk_mask_mode = "explicit"
    elif repainting_end > 0:
        chunk_mask_mode = "explicit"
    else:
        chunk_mask_mode = "auto"

    # Complete mode: auto-detect BPM from source audio if not explicitly provided.
    # Without this, the model generates at a random/default tempo — producing
    # "toddlers with noise makers" regardless of instrument selection.
    if task_type == "complete" and bpm is None and src_audio:
        detected = _detect_bpm_from_audio(src_audio)
        if detected is not None:
            bpm = detected
            logger.info("[custom_ui] Complete mode: auto-detected BPM=%d from source audio", detected)

    # Validate src_audio file exists before passing to generation pipeline
    if src_audio and task_type != "text2music":
        if not Path(src_audio).is_file():
            logger.warning("[custom_ui] src_audio path does not exist: %s", src_audio)
            src_audio = None

    # Log cover mode params for debugging
    if task_type == "cover":
        logger.info(
            "[custom_ui] Cover mode: audio_cover_strength=%.2f cover_noise=%.2f src_audio=%s",
            audio_cover_strength, cover_noise_strength, src_audio,
        )
        if audio_cover_strength >= 1.0:
            logger.info(
                "[custom_ui] Cover mode: audio_cover_strength=1.0 = full timbre coverage "
                "(output will closely match source timbre). Reduce for more variation."
            )

    # Build params
    params = GenerationParams(
        caption=caption,
        lyrics=lyrics,
        task_type=task_type,
        inference_steps=inference_steps,
        guidance_scale=guidance_scale,
        seed=seed,
        duration=duration,
        bpm=bpm if str(bpm).strip() else None,
        keyscale=keyscale if keyscale.strip() else "",
        timesignature=str(timesignature).strip() if str(timesignature).strip() else "",
        vocal_language=vocal_language,
        thinking=thinking,
        use_cot_caption=use_cot_caption,
        use_cot_metas=use_cot_metas,
        use_cot_language=use_cot_language,
        instruction=complete_instruction,
        global_caption=track_name if (task_type in ("lego", "complete")) and track_name and str(track_name).strip() else "",
        reference_audio=reference_audio if task_type != "text2music" else None,
        src_audio=src_audio if task_type != "text2music" else None,
        audio_cover_strength=audio_cover_strength,
        cover_noise_strength=cover_noise_strength if task_type == "cover" else 0.0,
        repainting_start=repainting_start,
        repainting_end=repainting_end,
        repaint_mode=repaint_mode,
        repaint_strength=repaint_strength,
        chunk_mask_mode=chunk_mask_mode,
        inspiration_preset=inspiration_preset if task_type == "inspiration" else None,
    )

    config = GenerationConfig(
        batch_size=batch_size,
        use_random_seed=use_random_seed,
        audio_format=audio_format,
    )

    logger.info(f"[custom_ui] task_type={task_type} src_audio={src_audio} ref_audio={reference_audio} cover_strength={audio_cover_strength} noise={cover_noise_strength}")

    # Log edit mode params for debugging
    if task_type == "repaint":
        logger.info("[custom_ui] Edit mode: start=%.2f end=%.2f mode=%s strength=%.2f", repainting_start, repainting_end, repaint_mode, repaint_strength)

    # Determine workspace output directory
    ws = data.get("workspace", "__root__")
    if ws and ws != "__root__":
        output_dir = os.path.join(WORKSPACE_DIR, ws)
    else:
        output_dir = WORKSPACE_DIR
    os.makedirs(output_dir, exist_ok=True)

    result = generate_music(
        dit_handler=_handler,
        llm_handler=_llm_handler,
        params=params,
        config=config,
        save_dir=output_dir,
    )

    if not result.success:
        msg = result.error or "Generation failed"
        # Enhance source-audio-specific errors with actionable guidance
        if "source audio" in (msg or "").lower():
            msg += (
                ". Verify the uploaded file is a valid audible audio file (WAV/FLAC/MP3/OGG). "
                "Silent or corrupted files will be rejected."
            )
        return {"status": "error", "message": msg}

    # Serialize results and save sidecar metadata per file
    audios = []
    for audio in result.audios:
        orig_path = audio.get("path", "")
        key = audio.get("key", "unknown")
        stat_info = None
        if orig_path:
            try:
                stat_info = os.stat(orig_path)
            except OSError:
                pass
        audios.append({
            "path": orig_path,
            "key": key,
            "sample_rate": audio.get("sample_rate", 48000),
            "prompt": audio.get("params", {}).get("caption", "") or params.caption or "",
            "size": stat_info.st_size if stat_info else None,
            "modified": stat_info.st_mtime if stat_info else None,
        })

    # Save sidecar JSON for each result file so we can restore metadata on reload
    extra = result.extra_outputs or {}
    time_costs = extra.get("time_costs", {})
    llm_interpretation = extra.get("phase1_reasoning")
    meta_blob = {
        "prompt": params.caption,
        "lyrics": params.lyrics,
        "task_type": params.task_type,
        "inference_steps": inference_steps,
        "guidance_scale": guidance_scale,
        "seed": seed,
        "batch_size": batch_size,
        "duration": duration,
        "track_name": track_name if track_name and str(track_name).strip() else None,
        "bpm": bpm if str(bpm).strip() else None,
        "keyscale": keyscale if keyscale.strip() else "",
        "timesignature": str(timesignature).strip() if str(timesignature).strip() else "",
        "vocal_language": vocal_language,
        "thinking": thinking,
        "use_random_seed": use_random_seed,
        "audio_format": audio_format,
        "time_costs": {k: round(v, 2) for k, v in time_costs.items()},
    }
    for audio in audios:
        orig_path = audio.get("path", "")
        if orig_path:
            sidecar = orig_path.rsplit(".", 1)[0] + ".json"
            try:
                with open(sidecar, "w") as f:
                    json.dump(meta_blob, f, indent=2)
            except OSError:
                pass

    first_prompt = ""
    if audios:
        p = audios[0].get("params", {}).get("caption", "") or params.caption or ""
        first_prompt = p

    return {
        "status": "complete",
        "audios": audios,
        "metadata": {
            "bpm": audios[0].get("params", {}).get("bpm") if audios else None,
            "keyscale": audios[0].get("params", {}).get("keyscale") if audios else None,
            "duration": audios[0].get("params", {}).get("duration") if audios else None,
            "track_name": track_name if track_name and str(track_name).strip() else None,
            "time_costs": {k: round(v, 2) for k, v in time_costs.items()},
        },
        "prompt": first_prompt,
        "llm_interpretation": llm_interpretation if llm_interpretation else None,
        "_params": {
            "caption": params.caption,
            "lyrics": params.lyrics,
            "task_type": params.task_type,
            "inference_steps": inference_steps,
            "guidance_scale": guidance_scale,
            "seed": seed,
            "batch_size": batch_size,
            "duration": duration,
            "bpm": bpm if str(bpm).strip() else None,
            "keyscale": keyscale,
            "timesignature": timesignature if str(timesignature).strip() else "",
            "vocal_language": vocal_language,
            "thinking": thinking,
            "use_random_seed": use_random_seed,
            "audio_format": audio_format,
            "track_name": track_name if track_name and str(track_name).strip() else None,
        },
    }


# ---------------------------------------------------------------------------
# CLI entry point (re-exported from routes for pyproject.toml target)
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
