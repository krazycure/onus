# Onus — ACE-Step Custom Interface

A plugin for [ACE-Step 1.5](https://github.com/ace-step/ACE-Step-1.5) that replaces the default Gradio UI with a custom FastAPI + vanilla HTML/CSS/JS frontend. Zero Gradio dependency.

## Installation (on top of existing ACE-Step install)

```bash
# Run the installer, pointing to your ACE-Step directory:
./install.sh /path/to/ACE-Step-1.5

# Then start the server:
cd /path/to/ACE-Step-1.5 && uv sync && uv run acestep-custom --port 8090
```

## Files

| File | Purpose |
|------|---------|
| `acestep/constants.py` | Modified — adds INSPIRATION_PRESETS, "Edit" mode, "inspiration" task type |
| `acestep/inference.py` | Modified — adds inspiration_preset to GenerationParams, cfg_scale param |
| `acestep/llm_inference.py` | Modified — adds system_instruction param for LLM |
| `acestep/ui/custom_interface.py` | Backend core + CLI entry point (`acestep-custom`) |
| `acestep/ui/custom_interface_html.py` | HTML template constant |
| `acestep/ui/custom_interface_css.py` | CSS stylesheet constant |
| `acestep/ui/custom_interface_js.py` | Client-side JavaScript constant |
| `acestep/ui/custom_interface_routes.py` | FastAPI app + API routes |
| `acestep/ui/custom_interface_generate_params_test.py` | Unit tests |
