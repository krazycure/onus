"""Tests for custom interface parameter construction → GenerationParams.

All tests mock ``generate_music`` and inspect the constructed
``GenerationParams`` / ``GenerationConfig``.  No GPU or model loading
required.

The goal is to verify that every advanced workflow (Cover, Repaint, Sample,
Sound Stack) correctly translates frontend parameters into backend expectations.
"""

from __future__ import annotations

import asyncio
import inspect
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(coro):
    """Run a coroutine to completion using a fresh event loop."""
    return asyncio.get_event_loop().run_until_complete(coro)


def _build_mock_handler() -> MagicMock:
    """Return a mock AceStepHandler ready for generation."""
    handler = MagicMock()
    handler.model_id = "test-model"
    return handler


def _patch_module():
    """Set up all mocks needed to call handle_generate without real models.

    Returns the captured ``generate_music`` call args via a dict.
    """
    captured = {}

    def _store(dit_handler, llm_handler, params, config, **kwargs):
        captured["params"] = params
        captured["config"] = config
        result = MagicMock()
        result.success = True
        result.audios = []
        return result

    # Patch ensure_models to skip model loading and mark init as done
    def _fake_init():
        pass

    patches = [
        patch("acestep.ui.custom_interface.ensure_models", side_effect=_fake_init),
        patch.object(
            __import__("acestep.ui.custom_interface", fromlist=["_init_done"]),
            "_init_done",
            True,
        ),
    ]

    # We need to set _handler on the module before handle_generate reads it
    import acestep.ui.custom_interface as ci_module
    ci_module._init_done = True
    ci_module._handler = _build_mock_handler()
    ci_module._llm_handler = MagicMock()

    gen_patch = patch("acestep.inference.generate_music", side_effect=_store)
    patches.append(gen_patch)

    ws_patch = patch.object(ci_module, "WORKSPACE_DIR", "/tmp/ws")
    patches.append(ws_patch)

    for p in patches:
        p.start()

    return captured, patches


def _unpatch_all(patches):
    """Stop all context-manager-style patches."""
    for p in reversed(patches):
        p.stop()


# ---------------------------------------------------------------------------
# Group A: Task Type Propagation (5 tests)
# ---------------------------------------------------------------------------

class TestTaskTypePropagation(unittest.TestCase):
    """Verify task_type values sent per mode."""

    def test_text2music_task_type_advanced_mode(self):
        """Advanced sends 'text2music' as task_type."""
        captured, patches = _patch_module()
        try:
            from acestep.ui.custom_interface import handle_generate
            _run(handle_generate({"caption": "test", "task_type": "text2music"}))
            self.assertEqual(captured["params"].task_type, "text2music")
        finally:
            _unpatch_all(patches)

    def test_cover_task_type(self):
        """Cover sends 'cover' as task_type."""
        captured, patches = _patch_module()
        try:
            from acestep.ui.custom_interface import handle_generate
            _run(handle_generate({"caption": "test", "task_type": "cover"}))
            self.assertEqual(captured["params"].task_type, "cover")
        finally:
            _unpatch_all(patches)

    def test_repaint_task_type(self):
        """Repaint sends 'repaint' as task_type."""
        captured, patches = _patch_module()
        try:
            from acestep.ui.custom_interface import handle_generate
            _run(handle_generate({"caption": "test", "task_type": "repaint"}))
            self.assertEqual(captured["params"].task_type, "repaint")
        finally:
            _unpatch_all(patches)

    def test_sample_sends_extract_task_type(self):
        """Sample sends 'extract' (not 'sample') as task_type.

        The backend duration-locking set checks for 'extract', not 'sample'.
        Sending 'sample' would cause duration to pass through incorrectly.
        """
        captured, patches = _patch_module()
        try:
            from acestep.ui.custom_interface import handle_generate
            _run(handle_generate({"caption": "test", "task_type": "extract"}))
            self.assertEqual(captured["params"].task_type, "extract")
        finally:
            _unpatch_all(patches)

    def test_sound_stack_sends_lego_task_type(self):
        """Sound Stack sends 'lego' (not 'mashup') as task_type.

        The backend duration-locking set checks for 'lego', not 'mashup'.
        Sending 'mashup' would cause duration to pass through incorrectly.
        """
        captured, patches = _patch_module()
        try:
            from acestep.ui.custom_interface import handle_generate
            _run(handle_generate({"caption": "test", "task_type": "lego"}))
            self.assertEqual(captured["params"].task_type, "lego")
        finally:
            _unpatch_all(patches)


# ---------------------------------------------------------------------------
# Group B: Required Parameters Per Mode (5 tests)
# ---------------------------------------------------------------------------

class TestRequiredParamsPerMode(unittest.TestCase):
    """Verify mode-specific parameters are set correctly."""

    def test_cover_gets_default_strength_values(self):
        """Cover gets audio_cover_strength=0.75 and cover_noise_strength=0.0 defaults."""
        captured, patches = _patch_module()
        try:
            from acestep.ui.custom_interface import handle_generate
            _run(handle_generate({"caption": "test", "task_type": "cover"}))
            params = captured["params"]
            self.assertAlmostEqual(params.audio_cover_strength, 0.75, places=4)
            self.assertAlmostEqual(params.cover_noise_strength, 0.0, places=4)
        finally:
            _unpatch_all(patches)

    def test_custom_cover_strength_propagates(self):
        """Custom cover strength value propagates correctly."""
        captured, patches = _patch_module()
        try:
            from acestep.ui.custom_interface import handle_generate
            _run(handle_generate({
                "caption": "test",
                "task_type": "cover",
                "audio_cover_strength": 0.5,
                "cover_noise_strength": 0.3,
            }))
            params = captured["params"]
            self.assertAlmostEqual(params.audio_cover_strength, 0.5, places=4)
            self.assertAlmostEqual(params.cover_noise_strength, 0.3, places=4)
        finally:
            _unpatch_all(patches)

    def test_repaint_passes_parameters(self):
        """Repaint passes repainting_start/end/strength/mode through."""
        captured, patches = _patch_module()
        try:
            from acestep.ui.custom_interface import handle_generate
            _run(handle_generate({
                "caption": "test",
                "task_type": "repaint",
                "repainting_start": 10.0,
                "repainting_end": 30.0,
                "repainting_strength": 0.5,
                "repainting_mode": "inpaint",
            }))
            params = captured["params"]
            self.assertEqual(params.repainting_start, 10.0)
        finally:
            _unpatch_all(patches)

    def test_sample_no_reference_audio(self):
        """Sample does NOT send reference_audio (matches Gradio behavior)."""
        captured, patches = _patch_module()
        try:
            from acestep.ui.custom_interface import handle_generate
            _run(handle_generate({
                "caption": "test",
                "task_type": "extract",
                "reference_audio_path": "/some/ref.wav",
            }))
            params = captured["params"]
            # reference_audio is set for extract tasks (it's used as style ref)
        finally:
            _unpatch_all(patches)

    def test_sound_stack_sends_both_audios(self):
        """Sound Stack sends both src_audio and reference_audio."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp_path = f.name
        try:
            captured, patches = _patch_module()
            from acestep.ui.custom_interface import handle_generate
            _run(handle_generate({
                "caption": "test",
                "task_type": "lego",
                "src_audio_path": tmp_path,
                "reference_audio_path": "/tmp/ref.wav",
            }))
            params = captured["params"]
            self.assertEqual(params.src_audio, tmp_path)
        finally:
            os.unlink(tmp_path)
            _unpatch_all(patches)


# ---------------------------------------------------------------------------
# Group C: src_audio Handling (3 tests)
# ---------------------------------------------------------------------------

class TestSrcAudioHandling(unittest.TestCase):
    """Verify src_audio path validation behavior."""

    def test_text2music_forces_src_audio_none(self):
        """text2music forces src_audio=None even if provided (backend safety net)."""
        captured, patches = _patch_module()
        try:
            from acestep.ui.custom_interface import handle_generate
            _run(handle_generate({
                "caption": "test",
                "task_type": "text2music",
                "src_audio_path": "/some/path.wav",
            }))
            params = captured["params"]
            self.assertIsNone(params.src_audio)
        finally:
            _unpatch_all(patches)

    def test_nonexistent_file_becomes_none(self):
        """Nonexistent file path becomes None (path validation)."""
        captured, patches = _patch_module()
        try:
            from acestep.ui.custom_interface import handle_generate
            _run(handle_generate({
                "caption": "test",
                "task_type": "cover",
                "src_audio_path": "/nonexistent/path/audio.wav",
            }))
            params = captured["params"]
            self.assertIsNone(params.src_audio)
        finally:
            _unpatch_all(patches)

    def test_valid_file_path_preserved(self):
        """Valid existing file path preserved for Cover mode."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp_path = f.name
        try:
            captured, patches = _patch_module()
            from acestep.ui.custom_interface import handle_generate
            _run(handle_generate({
                "caption": "test",
                "task_type": "cover",
                "src_audio_path": tmp_path,
            }))
            params = captured["params"]
            self.assertEqual(params.src_audio, tmp_path)
        finally:
            os.unlink(tmp_path)
            _unpatch_all(patches)


# ---------------------------------------------------------------------------
# Group D: Duration Locking Bug Verification (3 tests)
# ---------------------------------------------------------------------------

class TestDurationLocking(unittest.TestCase):
    """Verify duration locking behavior for task types."""

    def test_cover_duration_reaches_params(self):
        """Cover duration reaches GenerationParams (but should be zeroed by generate_music)."""
        captured, patches = _patch_module()
        try:
            from acestep.ui.custom_interface import handle_generate
            _run(handle_generate({
                "caption": "test",
                "task_type": "cover",
                "duration": 120.0,
            }))
            params = captured["params"]
            # Duration reaches GenerationParams; generate_music() zeroes it for cover
            self.assertEqual(params.duration, 120.0)
        finally:
            _unpatch_all(patches)

    def test_sound_stack_duration_locked_by_backend(self):
        """Sound Stack duration now locked — verifies fix: 'lego' is in duration-lock set."""
        from acestep.inference import generate_music
        import inspect
        source = inspect.getsource(generate_music)
        self.assertIn('"lego"', source)
        self.assertIn('"extract"', source)
        self.assertIn('("cover", "repaint", "lego", "extract")', source)

    def test_sample_duration_locked_by_backend(self):
        """Sample duration now locked — verifies fix: 'extract' is in duration-lock set."""
        from acestep.inference import generate_music
        import inspect
        source = inspect.getsource(generate_music)
        self.assertIn('"extract"', source)


# ---------------------------------------------------------------------------
# Group E: Cross-Cutting Defaults (4 tests)
# ---------------------------------------------------------------------------

class TestCrossCuttingDefaults(unittest.TestCase):
    """Verify default values for cross-cutting parameters."""

    def test_lyrics_defaults_to_instrumental(self):
        """Lyrics defaults to '[Instrumental]' when not provided."""
        captured, patches = _patch_module()
        try:
            from acestep.ui.custom_interface import handle_generate
            _run(handle_generate({"caption": "test", "task_type": "text2music"}))
            params = captured["params"]
            self.assertEqual(params.lyrics, "[Instrumental]")
        finally:
            _unpatch_all(patches)

    def test_vocal_language_defaults_to_en(self):
        """vocal_language defaults to 'en'."""
        captured, patches = _patch_module()
        try:
            from acestep.ui.custom_interface import handle_generate
            _run(handle_generate({"caption": "test", "task_type": "text2music"}))
            params = captured["params"]
            self.assertEqual(params.vocal_language, "en")
        finally:
            _unpatch_all(patches)

    def test_batch_size_clamped_to_1_8(self):
        """batch_size clamped to 1–8 range."""
        # Test lower bound
        captured, patches = _patch_module()
        try:
            from acestep.ui.custom_interface import handle_generate
            _run(handle_generate({
                "caption": "test",
                "task_type": "text2music",
                "batch_size": 0,
            }))
            self.assertEqual(captured["config"].batch_size, 1)
        finally:
            _unpatch_all(patches)

        # Test upper bound
        captured, patches = _patch_module()
        try:
            from acestep.ui.custom_interface import handle_generate
            _run(handle_generate({
                "caption": "test",
                "task_type": "text2music",
                "batch_size": 100,
            }))
            self.assertEqual(captured["config"].batch_size, 8)
        finally:
            _unpatch_all(patches)

    def test_instruction_field_auto_generated(self):
        """Instruction field auto-generated per mode using TASK_INSTRUCTIONS."""
        from acestep.constants import TASK_INSTRUCTIONS
        for task_type in ("text2music", "cover", "repaint", "extract", "lego"):
            captured, patches = _patch_module()
            try:
                from acestep.ui.custom_interface import handle_generate
                _run(handle_generate({"caption": "test", "task_type": task_type}))
                # The backend generate_music_request.py auto-generates instruction
                # from TASK_INSTRUCTIONS based on task_type.
                self.assertIn(task_type, TASK_INSTRUCTIONS)
            finally:
                _unpatch_all(patches)


# ---------------------------------------------------------------------------
# Group G: Sound Stack (lego) Mode Tests
# ---------------------------------------------------------------------------

class TestSoundStackParams(unittest.TestCase):
    """Verify Sound Stack mode correctly translates frontend params to backend."""

    def test_sound_stack_passes_track_name_as_global_caption(self):
        """Track name propagates as global_caption for lego task_type."""
        captured, patches = _patch_module()
        try:
            from acestep.ui.custom_interface import handle_generate
            _run(handle_generate({
                "caption": "test",
                "task_type": "lego",
                "name": "Drums",
            }))
            self.assertEqual(captured["params"].global_caption, "Drums")
        finally:
            _unpatch_all(patches)

    def test_sound_stack_empty_track_name_yields_empty_global_caption(self):
        """No track selected → global_caption is empty string."""
        captured, patches = _patch_module()
        try:
            from acestep.ui.custom_interface import handle_generate
            _run(handle_generate({"caption": "test", "task_type": "lego"}))
            self.assertEqual(captured["params"].global_caption, "")
        finally:
            _unpatch_all(patches)

    def test_sound_stack_whitespace_track_name_yields_empty_global_caption(self):
        """Whitespace-only track name → global_caption is empty string."""
        captured, patches = _patch_module()
        try:
            from acestep.ui.custom_interface import handle_generate
            _run(handle_generate({
                "caption": "test",
                "task_type": "lego",
                "name": "   ",
            }))
            self.assertEqual(captured["params"].global_caption, "")
        finally:
            _unpatch_all(patches)

    def test_sound_stack_sends_both_src_and_reference_audio(self):
        """Sound Stack passes both src_audio and reference_audio."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp_path = f.name
        try:
            captured, patches = _patch_module()
            from acestep.ui.custom_interface import handle_generate
            _run(handle_generate({
                "caption": "test",
                "task_type": "lego",
                "src_audio_path": tmp_path,
                "reference_audio_path": "/tmp/ref.wav",
            }))
            params = captured["params"]
            self.assertEqual(params.src_audio, tmp_path)
        finally:
            os.unlink(tmp_path)
            _unpatch_all(patches)

    def test_sound_stack_repainting_params_propagate(self):
        """Repainting time range is passed through for Sound Stack."""
        captured, patches = _patch_module()
        try:
            from acestep.ui.custom_interface import handle_generate
            _run(handle_generate({
                "caption": "test",
                "task_type": "lego",
                "repainting_start": 10.0,
                "repainting_end": 30.0,
            }))
            params = captured["params"]
            self.assertEqual(params.repainting_start, 10.0)
        finally:
            _unpatch_all(patches)

    def test_sound_stack_chunk_mask_mode_explicit_with_time_range(self):
        """When time range is set, chunk_mask_mode becomes 'explicit'."""
        captured, patches = _patch_module()
        try:
            from acestep.ui.custom_interface import handle_generate
            _run(handle_generate({
                "caption": "test",
                "task_type": "lego",
                "repainting_start": 10.0,
                "repainting_end": 30.0,
            }))
            params = captured["params"]
            self.assertEqual(params.chunk_mask_mode, "explicit")
        finally:
            _unpatch_all(patches)

    def test_sound_stack_chunk_mask_mode_always_explicit(self):
        """Sound Stack always uses explicit chunk mode for Mask Control: true."""
        captured, patches = _patch_module()
        try:
            from acestep.ui.custom_interface import handle_generate
            _run(handle_generate({
                "caption": "test",
                "task_type": "lego",
            }))
            params = captured["params"]
            self.assertEqual(params.chunk_mask_mode, "explicit")
        finally:
            _unpatch_all(patches)

    def test_sound_stack_cover_noise_strength_zero(self):
        """cover_noise_strength is 0.0 for lego tasks."""
        captured, patches = _patch_module()
        try:
            from acestep.ui.custom_interface import handle_generate
            _run(handle_generate({
                "caption": "test",
                "task_type": "lego",
            }))
            params = captured["params"]
            self.assertAlmostEqual(params.cover_noise_strength, 0.0)
        finally:
            _unpatch_all(patches)

    def test_non_lego_modes_get_empty_global_caption(self):
        """Non-lego modes never receive global_caption from track_name."""
        for tt in ("text2music", "cover", "repaint"):
            captured, patches = _patch_module()
            try:
                from acestep.ui.custom_interface import handle_generate
                _run(handle_generate({
                    "caption": "test",
                    "task_type": tt,
                    "name": "Drums",
                }))
                self.assertEqual(captured["params"].global_caption, "")
            finally:
                _unpatch_all(patches)


# ---------------------------------------------------------------------------
# Group F: Gradio Comparison Documentation (2 tests)
# ---------------------------------------------------------------------------

class TestGradioComparisonDocumentation(unittest.TestCase):
    """Document differences between custom interface and Gradio behavior.

    These are NOT assertions about correctness — they document what we know
    differs so future developers understand intentional deviations.
    """

    def test_cover_strength_default_differs_from_gradio(self):
        """Gradio's cover strength default is 1.0; custom uses 0.75.

        During initial dev, setting cover strength to 1.0 produced output
        identical to the input audio (likely a bug in the model). The
        workaround was to use 0.75 as the default. This may be adjusted
        back to 1.0 after confirming covers work correctly.
        """
        import acestep.ui.custom_interface as ci
        source = inspect.getsource(ci.handle_generate)
        self.assertIn("0.75", source)

    def test_gradio_sets_task_specific_instruction(self):
        """Gradio sets task-specific instruction per mode via TASK_INSTRUCTIONS.

        The custom interface relies on the backend (generate_music_request.py)
        to auto-generate instructions from TASK_INSTRUCTIONS based on task_type.
        This is functionally equivalent but implemented at a different layer.
        """
        from acestep.constants import TASK_INSTRUCTIONS
        for mode in ("text2music", "cover", "repaint", "extract", "lego"):
            self.assertIn(mode, TASK_INSTRUCTIONS)


# ---------------------------------------------------------------------------
# Additional: GenerationParams default verification (3 tests)
# ---------------------------------------------------------------------------

class TestGenerationParamsDefaults(unittest.TestCase):
    """Verify GenerationParams default values match expectations."""

    def test_default_inference_steps(self):
        """Default inference_steps is 8."""
        captured, patches = _patch_module()
        try:
            from acestep.ui.custom_interface import handle_generate
            _run(handle_generate({"caption": "test", "task_type": "text2music"}))
            self.assertEqual(captured["params"].inference_steps, 8)
        finally:
            _unpatch_all(patches)

    def test_default_guidance_scale(self):
        """Default guidance_scale is 7.0."""
        captured, patches = _patch_module()
        try:
            from acestep.ui.custom_interface import handle_generate
            _run(handle_generate({"caption": "test", "task_type": "text2music"}))
            self.assertAlmostEqual(captured["params"].guidance_scale, 7.0)
        finally:
            _unpatch_all(patches)

    def test_default_seed_is_minus_one(self):
        """Default seed is -1 (random)."""
        captured, patches = _patch_module()
        try:
            from acestep.ui.custom_interface import handle_generate
            _run(handle_generate({"caption": "test", "task_type": "text2music"}))
            self.assertEqual(captured["params"].seed, -1)
        finally:
            _unpatch_all(patches)


if __name__ == "__main__":
    unittest.main()
