"""Custom AceStep UI — Stylesheet.

Dark theme CSS for the FastAPI-based web interface. All styles are scoped to
the single-page app layout (topbar, controls left panel, results right panel).

Exports:
    STYLES_CSS: Raw CSS string (no <style> tags — embedded by caller).

See Also:
    custom_interface.py      - Backend core (init, generate, CLI)
    custom_interface_html.py - HTML body template (FRONTEND_BODY_HTML)
    custom_interface_js.py   - Client-side JavaScript (CLIENT_JS)
    custom_interface_routes.py - API routes + FastAPI app
"""

STYLES_CSS = r""":root {
    --bg-0: #0a0a0b; --bg-1: #121214; --bg-2: #17171a; --bg-3: #1e1e22;
    --border: #26262b; --border-strong: #33333a;
    --text-0: #ededef; --text-1: #a8a8ae; --text-2: #70707a;
    --accent: #e5e5e7; --ok: #6ed28a; --warn: #e5a87a;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body { height: 100%; overflow: hidden; background: var(--bg-0); color: var(--text-0); font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }

/* ── Layout ── */
.app { display: flex; flex-direction: column; height: 100vh; }
.topbar { display: flex; align-items: center; padding: 6px 16px; background: var(--bg-1); border-bottom: 1px solid var(--border); min-height: 38px; gap: 12px; }
.brand { font-family: 'JetBrains Mono', monospace; font-size: 13px; font-weight: 600; letter-spacing: .15em; color: var(--text-0); }
.status { margin-left: auto; display: flex; align-items: center; gap: 8px; font-size: 12px; color: var(--text-1); font-family: 'JetBrains Mono', monospace; }
.dot { width: 7px; height: 7px; border-radius: 50%; background: var(--warn); flex-shrink: 0; }
.status.ready .dot { background: var(--ok); }
.status.error .dot { background: #e57a7a; }
.status.generating .dot { animation: dotPulse 1.5s ease-in-out infinite; }
@keyframes dotPulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
}
.status.error #status-text {
    color: #e57a7a;
    animation: errorPulse 1s ease-in-out infinite, errorDrift 2s ease-in-out infinite;
}
@keyframes errorPulse {
    0%, 100% { opacity: 1; text-shadow: none; }
    50% { opacity: 0.6; text-shadow: 0 0 8px rgba(229, 122, 122, 0.6); }
}
@keyframes errorDrift {
    0%, 100% { transform: translateX(0); }
    50% { transform: translateX(3px); }
}

/* Placeholder result card shown during generation */
.result-card.generating {
    display: flex; align-items: center; justify-content: center; gap: 10px;
    min-height: 80px; padding: 24px; color: var(--text-2); font-size: 13px;
}

/* Workspace bar */
.workspace-bar { display: flex; align-items: center; gap: 4px; overflow-x: auto; max-width: 60vw; flex-shrink: 1; scrollbar-width: none; }
.workspace-bar::-webkit-scrollbar { display: none; }
.ws-pill { font-size: 10px; font-weight: 600; letter-spacing: .08em; text-transform: uppercase; padding: 3px 10px; border-radius: 4px; cursor: pointer; color: var(--text-2); background: transparent; border: 1px solid transparent; transition: all .12s; white-space: nowrap; flex-shrink: 0; }
.ws-pill:hover { color: var(--text-1); border-color: var(--border); }
.ws-pill.active { color: var(--bg-0); background: var(--accent); border-color: var(--accent); font-weight: 700; }
.ws-add { width: 22px; height: 22px; display: flex; align-items: center; justify-content: center; font-size: 16px; color: var(--text-2); background: transparent; border: 1px dashed var(--border); border-radius: 4px; cursor: pointer; transition: all .12s; padding: 0; flex-shrink: 0; }
.ws-add:hover { color: var(--text-0); border-color: var(--border-strong); background: var(--bg-3); }

.content { display: flex; flex: 1; overflow: hidden; min-height: 0; position: relative; }

/* ── Divider between controls and results ── */
.divider { width: 4px; height: 100%; cursor: col-resize; background: transparent; border-left: 1px solid var(--border); border-right: 1px solid var(--border); flex-shrink: 0; transition: background .12s; z-index: 5; }
.divider:hover, .divider.dragging { background: var(--accent); opacity: .3; }

/* ── Left panel: controls ── */
.controls { width: 420px; flex-shrink: 0; padding: 12px 14px; background: var(--bg-1); border-right: 1px solid var(--border); overflow-y: auto; display: flex; flex-direction: column; gap: 8px; scrollbar-width: thin; }
.controls::-webkit-scrollbar { width: 6px; }
.controls::-webkit-scrollbar-track { background: transparent; }
.controls::-webkit-scrollbar-thumb { background: var(--border-strong); border-radius: 3px; }

.section-label { font-size: 10px; font-weight: 600; letter-spacing: .14em; text-transform: uppercase; color: var(--text-2); margin-bottom: 4px; }
.section-header { display: flex; align-items: center; justify-content: space-between; cursor: pointer; padding: 4px 0; user-select: none; }
.section-header:hover .section-label { color: var(--text-1); }
.section-chevron { font-size: 10px; transition: transform .2s; color: var(--text-2); }
.section-chevron.open { transform: rotate(90deg); }

/* Accordion */
.accordion-body { overflow: hidden; transition: max-height .3s ease; }
.accordion-body.collapsed { max-height: 0 !important; }

/* Advanced grid: 2 fields per row */
.adv-grid, .custom-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }

/* Mode pills */
.mode-pills { display: flex; gap: 2px; background: var(--bg-2); border-radius: 8px; padding: 3px; }
.mode-pill { flex: 1; text-align: center; padding: 6px 4px; font-size: 11px; font-weight: 500; color: var(--text-1); background: transparent; border: none; border-radius: 6px; cursor: pointer; transition: all .12s; }
.mode-pill:hover { background: var(--bg-3); }
.mode-pill.active { background: var(--text-0); color: var(--bg-0); font-weight: 600; }
.mode-pill.pill-disabled { opacity: .45; cursor: not-allowed; pointer-events: none; }
/* Complete mode hidden — upstream bug (#803, #1088). Remove this rule to re-enable. */
.mode-pill-complete { display: none !important; }

/* Cover noise preset cards */
.cover-noise-presets { display: grid; grid-template-columns: 1fr 1fr; gap: 4px; margin-bottom: 4px; }
.preset-card { display: flex; flex-direction: column; gap: 2px; padding: 6px 8px; border: 1px solid var(--border); border-radius: 6px; cursor: pointer; transition: all .12s; background: var(--bg-2); }
.preset-card:hover { border-color: var(--border-strong); background: var(--bg-3); }
.preset-card.selected { border-color: var(--accent); background: var(--bg-3); box-shadow: 0 0 0 1px var(--accent); }
.preset-label { font-size: 11px; font-weight: 500; color: var(--text-1); }
.preset-stars { font-size: 10px; letter-spacing: 1px; }
.stars-prompt { color: #f5a623; }
.stars-source { color: #4fc3f7; }

/* Edit strength preset cards */
.edit-strength-presets { display: flex; gap: 4px; margin-bottom: 4px; }
.strength-preset-card { flex: 1; display: flex; flex-direction: column; gap: 2px; padding: 6px 8px; border: 1px solid var(--border); border-radius: 6px; cursor: pointer; transition: all .12s; background: var(--bg-2); text-align: center; }
.strength-preset-card:hover { border-color: var(--border-strong); background: var(--bg-3); }
/* Per-preset accent colors — blue → green → orange spectrum */
.strength-preset-card.preset-conservative.selected { border-color: #4fc3f7; background: linear-gradient(135deg, rgba(79,195,247,.08), rgba(245,166,35,.04)); box-shadow: 0 0 0 1px #4fc3f7; }
.strength-preset-card.preset-conservative .preset-label { color: #4fc3f7; }
.strength-preset-card.preset-balanced.selected { border-color: #6ed88a; background: linear-gradient(135deg, rgba(79,195,247,.06), rgba(110,216,138,.06)); box-shadow: 0 0 0 1px #6ed88a; }
.strength-preset-card.preset-balanced .preset-label { color: #6ed88a; }
.strength-preset-card.preset-full-replace.selected { border-color: #f5a623; background: linear-gradient(135deg, rgba(245,166,35,.08), rgba(79,195,247,.04)); box-shadow: 0 0 0 1px #f5a623; }
.strength-preset-card.preset-full-replace .preset-label { color: #f5a623; }
.preset-desc { font-size: 9px; color: var(--text-2); line-height: 1.3; }

/* Complete mode track classes chips */
.track-class-chip { display: inline-flex; align-items: center; gap: 3px; padding: 3px 8px; border: 1px solid var(--border); border-radius: 6px; cursor: pointer; font-size: 11px; color: var(--text-1); background: var(--bg-2); transition: all .12s; user-select: none; }
.track-class-chip:hover { border-color: #b388ff; background: var(--bg-3); }
.track-class-chip input[type=checkbox] { display: none; }
.track-class-chip:has(input:checked) { border-color: #b388ff; color: #b388ff; background: rgba(179, 136, 255, .08); }

/* Waveform region selector */
.waveform-container { position: relative; width: 100%; margin-bottom: 4px; border-radius: 6px; overflow: hidden; background: var(--bg-1); border: 1px solid var(--border); }
#waveform-canvas { display: block; width: 100%; height: 72px; cursor: crosshair; }
.waveform-handle { position: absolute; top: 0; bottom: 0; width: 6px; cursor: ew-resize; z-index: 3; transition: background .1s; }
.waveform-handle::after { content: ''; position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 6px; height: 48px; border-radius: 3px; background: #fff; opacity: .9; box-shadow: 0 0 6px rgba(0,0,0,.4); }
.waveform-handle:hover::after, .waveform-handle.active::after { opacity: 1; height: 56px; }
#waveform-start-handle { left: 0; background: linear-gradient(to right, rgba(255,255,255,.1), transparent); }
#waveform-end-handle { right: 0; background: linear-gradient(to left, rgba(255,255,255,.1), transparent); }
.waveform-times-row { display: flex; align-items: center; justify-content: center; gap: 6px; margin-top: 4px; font-size: 11px; color: var(--text-2); }
.waveform-times-row input[type="number"] { width: 58px; font-size: 11px; text-align: center; background: var(--bg-2); border: 1px solid var(--border); border-radius: 4px; color: var(--text-1); padding: 2px 4px; }
.waveform-times-row input[type="number"]:focus { outline: none; border-color: var(--accent); }
.waveform-play-btn { font-size: 12px; background: none; border: 1px solid var(--border); border-radius: 4px; padding: 2px 8px; cursor: pointer; color: var(--text-1); transition: all .1s; display: flex; align-items: center; gap: 3px; }
.waveform-play-btn:hover { border-color: var(--accent); background: var(--bg-3); }

/* Themed form focus states — prompt (amber) vs source (blue) */
textarea.theme-prompt:focus, input.theme-prompt:focus { border-color: var(--accent); box-shadow: 0 0 0 1px #f5a623; }
input.theme-source:focus { border-color: var(--accent); box-shadow: 0 0 0 1px #4fc3f7; }

/* Caption row with interpret button */
.caption-row { display:flex;flex-direction:column;gap:4px;position:relative; }
.caption-textarea { flex:1;min-width:0; }
.btn-interpret { position:absolute;top:8px;right:8px;width:28px;height:28px;display:flex;align-items:center;justify-content:center;background:var(--bg-3);border:1px solid var(--border);border-radius:6px;color:var(--text-2);cursor:pointer;transition:all .15s;padding:0;z-index:2; }
.btn-interpret:hover { border-color:#f5a623;color:#f5a623;background:var(--bg-2); }
.btn-interpret:active { transform:scale(.94); }
.btn-interpret svg { width:16px;height:16px;pointer-events:none; }

/* Themed form elements — persistent left accent border (must come after base textarea/input) */
.hidden-btn { display: none !important; }

.library-row { display: flex; gap: 4px; align-items: center; margin-top: 6px; flex-wrap: wrap; }
.lib-chip { font-size: 10px; font-weight: 600; letter-spacing: .08em; text-transform: uppercase; padding: 3px 8px; border-radius: 4px; cursor: pointer; color: var(--text-1); background: var(--bg-3); border: 1px solid var(--border); transition: all .12s; }
.lib-chip:hover { border-color: var(--border-strong); color: var(--text-0); }

/* Form elements */
.field { display: flex; flex-direction: column; gap: 4px; overflow: hidden; }
.field-row { display: flex; gap: 8px; align-items: center; }
textarea, input[type="text"], input[type="number"], select { box-sizing: border-box; background: var(--bg-2); border: 1px solid var(--border); color: var(--text-0); border-radius: 6px; padding: 8px 10px; font-family: inherit; font-size: 13px; transition: border-color .12s; max-width: 100%; }
textarea:focus, input:focus, select:focus { border-color: var(--border-strong); outline: none; }
select { cursor: pointer; appearance: none; background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%2370707a' d='M6 8L2 4h8z'/%3E%3C/svg%3E"); background-repeat: no-repeat; background-position: right 8px center; padding-right: 28px; }
textarea { resize: vertical; min-height: 120px; overflow-y: auto; }

/* Themed persistent left accent — prompt (amber) vs source (blue) */
textarea.theme-prompt, input.theme-source { border-left-width: 3px !important; }
textarea.theme-prompt { border-left-color: #f5a623 !important; }
input.theme-source { border-left-color: #4fc3f7 !important; }

/* Source-themed field container — wraps file inputs with blue accent */
.field-source { background: var(--bg-1); border: 1px solid var(--border); border-left: 3px solid #4fc3f7; border-radius: 6px; padding: 8px 10px; }

/* Clear button in source-themed areas */
.field-source .clear-btn:hover { color: #4fc3f7 !important; border-color: #4fc3f7 !important; background: rgba(79,195,247,.08) !important; }

/* Source-themed labels — blue text to match container accent */
.source-label { color: #4fc3f7 !important; }

/* Compact inputs */
.compact { max-width: 100px !important; width: 80px !important; text-align: center; padding: 6px 4px !important; font-size: 12px !important; }
select.compact { padding-right: 24px !important; }
.wide { flex: 1; min-width: 0; }

/* Toggle switch */
.toggle-row { display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 4px 0; }
.toggle-label { font-size: 12px; color: var(--text-1); white-space: nowrap; }
.toggle { position: relative; width: 36px; height: 20px; flex-shrink: 0; }
.toggle input { opacity: 0; width: 0; height: 0; }
.toggle .slider { position: absolute; inset: 0; background: var(--bg-3); border-radius: 10px; cursor: pointer; transition: .2s; border: 1px solid var(--border); }
.toggle .slider::before { content: ''; position: absolute; width: 14px; height: 14px; left: 2px; top: 2px; background: var(--text-1); border-radius: 50%; transition: .2s; }
.toggle input:checked + .slider { background: var(--ok); border-color: var(--ok); }
.toggle input:checked + .slider::before { transform: translateX(16px); background: #fff; }

/* Generate button */
#generate-btn { width: 100%; padding: 12px; font-size: 14px; font-weight: 600; letter-spacing: .04em; background: var(--text-0); color: var(--bg-0); border: none; border-radius: 8px; cursor: pointer; transition: background .12s; }
#generate-btn:hover:not(:disabled) { background: #fff; }
#generate-btn:disabled { opacity: .4; cursor: not-allowed; }

/* Init button */
#init-btn { width: 100%; padding: 8px; font-size: 12px; font-weight: 600; letter-spacing: .04em; background: var(--bg-3); color: var(--text-0); border: 1px solid var(--border); border-radius: 6px; cursor: pointer; transition: all .12s; }
#init-btn:hover:not(:disabled) { border-color: var(--border-strong); background: #24242a; }
#init-btn:disabled { opacity: .4; cursor: not-allowed; }

/* ── LM model selector ── */
.lm-option { display:flex;align-items:center;gap:8px;padding:6px 10px;border-radius:6px;border:1px solid var(--border);background:var(--bg-2);cursor:pointer;transition:all .12s;font-size:12px; }
.lm-option:hover { border-color: var(--border-strong); background: var(--bg-3); }
.lm-option.selected { border-color: var(--ok); background: #1f2a22; }
.lm-radio { width: 14px; height: 14px; border-radius: 50%; border: 1.5px solid var(--text-2); flex-shrink: 0; display:flex;align-items:center;justify-content:center;transition:all .12s; }
.lm-option.selected .lm-radio { border-color: var(--ok); }
.lm-option.selected .lm-radio::after { content:'';width:8px;height:8px;border-radius:50%;background:var(--ok); }
.lm-info { flex:1;min-width:0; }
.lm-name { color:var(--text-0);font-weight:500;font-family:'JetBrains Mono',monospace;font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis; }
.lm-meta { color:var(--text-2);font-size:11px;margin-top:1px; }
.lm-download-btn { padding:3px 8px;border-radius:5px;border:1px solid var(--border-strong);background:var(--bg-1);color:var(--text-1);cursor:pointer;font-size:11px;font-family:'JetBrains Mono',monospace;white-space:nowrap;transition:all .12s; }
.lm-download-btn:hover { background:var(--bg-3);color:var(--text-0);border-color:var(--text-2); }
.lm-download-btn.downloading { opacity:.5;pointer-events:none; }
.lm-installed { color:var(--ok);font-size:14px;flex-shrink:0; }

/* ── Right panel: results + training ── */
.results-pane { flex: 1; display: flex; flex-direction: column; padding: 12px 16px; background: var(--bg-0); min-width: 0; gap: 8px; }
.results-scroll { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 8px; min-height: 0; }
.results-header-bar { display: flex; align-items: center; justify-content: space-between; padding: 4px 0; gap: 8px; }
.results-header-bar select { font-size: 11px; background: var(--bg-3); color: var(--text-2); border: 1px solid var(--border); border-radius: 6px; padding: 4px 8px; cursor: pointer; }
.results-header-bar select option { background: var(--bg-2); color: var(--text-1); }

.result-card { position:relative; background: var(--bg-2); border: 1px solid var(--border); border-radius: 10px; padding: 12px 14px; transition: border-color .12s, background .12s; }
.result-card:hover { border-color: var(--border-strong); background: var(--bg-3); }

/* Mode-colored left accent on result cards */
.result-card.accent-prompt { border-left-width: 3px !important; border-left-color: #f5a623 !important; border-top-left-radius: 0; border-bottom-left-radius: 0; }
.result-card.accent-source { border-left-width: 3px !important; border-left-color: #4fc3f7 !important; border-top-left-radius: 0; border-bottom-left-radius: 0; }
.result-card.accent-edit   { border-left-width: 3px !important; border-left-color: #6ed88a !important; border-top-left-radius: 0; border-bottom-left-radius: 0; }
.result-card.accent-track   { border-left-width: 3px !important; border-left-color: #b388ff !important; border-top-left-radius: 0; border-bottom-left-radius: 0; }
.result-card.accent-inspiration { border-left-width: 3px !important; border-left-color: #26c6da !important; border-top-left-radius: 0; border-bottom-left-radius: 0; }
.result-card.accent-stack     { border-left-width: 3px !important; border-left-color: #ffb74d !important; border-top-left-radius: 0; border-bottom-left-radius: 0; }

.result-header { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; width: 100%; position: relative; }
.result-key { font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--text-2); }
.result-meta { font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--text-2); display: flex; align-items: center; gap: 12px; margin-top: 6px; }
.result-actions { display: flex; gap: 8px; margin-top: 8px; }
.result-delete { padding: 4px 8px; font-size: 16px; background: transparent; color: #e57a7a; border: none; cursor: pointer; transition: all .12s; opacity: .6; line-height: 1; }
.result-delete:hover { color:#ff9999; opacity: 1; transform: scale(1.1); }
.result-reuse { padding: 4px 8px; font-size: 14px; background: transparent; color: #7ab5e5; border: none; cursor: pointer; transition: all .12s; opacity: .6; line-height: 1; margin-left: 2px; }
.result-reuse:hover { color:#99ccff; opacity: 1; transform: scale(1.1); }
.result-use-src { padding: 4px 8px; font-size: 13px; background: transparent; color: #4fc3f7; border: none; cursor: pointer; transition: all .12s; opacity: .6; line-height: 1; margin-left: 2px; }
.result-use-src:hover { color:#80dfff; opacity: 1; transform: scale(1.1); }
.result-use-ref { padding: 4px 8px; font-size: 13px; background: transparent; color: #ce93d8; border: none; cursor: pointer; transition: all .12s; opacity: .6; line-height: 1; margin-left: 2px; }
.result-use-ref:hover { color:#e1bee7; opacity: 1; transform: scale(1.1); }

/* Inline delete confirmation — replaces trash icon in-place */
.confirm-inline { display:flex;align-items:center;gap:4px;flex-shrink:0; }
.confirm-inline button { width:24px;height:24px;border-radius:5px;border:none;cursor:pointer;font-size:13px;display:flex;align-items:center;justify-content:center;transition:all .12s;line-height:1; }
.confirm-cancel { background:#2a2025;color:#e57a7a !important; }
.confirm-cancel:hover { background:#3a3038;color:#ff9999 !important; }
.confirm-ok { background:#1f2a22;color:#6ed28a !important; }
.confirm-ok:hover { background:#2a3a2e;color:#8ee8a5 !important; }

.btn-sm { padding: 4px 10px; font-size: 11px; background: var(--bg-3); color: var(--text-0); border: 1px solid var(--border); border-radius: 6px; cursor: pointer; transition: all .12s; text-decoration: none; display: inline-block; }
.btn-sm:hover { border-color: var(--border-strong); background: #24242a; }

/* Clear button for file inputs */
.clear-btn { width: 22px; height: 22px; display: flex; align-items: center; justify-content: center; font-size: 16px; color: var(--text-2); background: transparent; border: 1px solid var(--border); border-radius: 4px; cursor: pointer; transition: all .12s; padding: 0; flex-shrink: 0; line-height: 1; }
.clear-btn:hover { color: #e57a7a; border-color: #e57a7a; background: rgba(229,122,122,.08); }

audio { width: 100%; margin-top: 6px; height: 32px; filter: invert(0.95); }

/* Prompt Library modal */
.modal-backdrop { position:fixed;inset:0;background:rgba(0,0,0,.6);display:flex;align-items:center;justify-content:center;z-index:1000;transition:opacity .15s; }
.prompt-lib-dialog { background:var(--bg-2);border:1px solid var(--border);border-radius:12px;padding:20px;width:480px;max-width:90vw;max-height:70vh;display:flex;flex-direction:column;gap:10px; }
.prompt-lib-list { overflow-y:auto;flex:1;display:flex;flex-direction:column;gap:6px;min-height:60px; }
.prompt-lib-item { display:flex;align-items:center;gap:8px;padding:8px 10px;background:var(--bg-3);border:1px solid var(--border);border-radius:6px;font-size:12px;cursor:pointer;transition:all .12s; }
.prompt-lib-item:hover { border-color:var(--border-strong);background:#24242a; }
.prompt-lib-item .lib-name { font-weight:600;color:var(--text-0);flex-shrink:0;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap; }
.prompt-lib-item .lib-preview { color:var(--text-2);font-size:11px;flex-shrink:0;max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap; }
.prompt-lib-item .lib-delete { background:none;border:none;color:var(--text-2);cursor:pointer;font-size:14px;padding:0 4px;flex-shrink:0;opacity:.5;transition:opacity .12s; }
.prompt-lib-item .lib-delete:hover { color:#e57a7a;opacity:1; }
.prompt-lib-actions { display:flex;gap:8px;justify-content:flex-end;padding-top:4px; }
.prompt-lib-actions button { padding:6px 16px;font-size:12px;background:var(--bg-3);color:var(--text-0);border:1px solid var(--border);border-radius:6px;cursor:pointer;transition:all .12s; }
.prompt-lib-actions button:hover { border-color:var(--border-strong);background:#24242a; }

/* Prompt library bar + pinned prompts */
.prompt-lib-bar { display:flex;flex-direction:column;gap:6px;margin-top:4px; }
.pinned-prompts { display:flex;flex-wrap:wrap;gap:6px;min-height:0; }
.pinned-btn { padding:3px 10px;font-size:11px;background:var(--bg-3);color:var(--text-1);border:1px solid var(--border-strong);border-radius:12px;cursor:pointer;white-space:nowrap;max-width:200px;overflow:hidden;text-overflow:ellipsis;transition:all .12s;display:flex;align-items:center;gap:4px; }
.pinned-btn:hover { background:#24242a;border-color:var(--border-strong); }
.pinned-btn .unpin-btn { font-size:10px;color:var(--text-2);cursor:pointer;padding:0 2px;line-height:1;opacity:.5;transition:opacity .12s; }
.pinned-btn .unpin-btn:hover { opacity:1;color:#e57a7a; }
#prompt-lib-dropdown { font-size:12px;background:var(--bg-3);color:var(--text-2);border:1px solid var(--border);border-radius:6px;padding:4px 8px;width:100%;cursor:pointer; }
#prompt-lib-dropdown option { background:var(--bg-2);color:var(--text-1); }
.pin-toggle { font-size:12px;color:var(--text-2);display:flex;align-items:center;gap:6px;cursor:pointer;padding:4px 0; }
.pin-toggle input { cursor:pointer;accent-color:var(--border-strong); }

/* Empty state */
.empty-state { flex: 1; display: flex; align-items: center; justify-content: center; color: var(--text-2); font-family: 'JetBrains Mono', monospace; font-size: 13px; text-align: center; gap: 8px; }

/* Training section */
.training-section { flex-shrink: 0; border-top: 1px solid var(--border); }
.training-body { overflow: hidden; transition: max-height .3s ease; }
.training-body.collapsed { max-height: 0 !important; }
.training-tabs { display: flex; gap: 2px; margin-bottom: 8px; background: var(--bg-2); border-radius: 6px; padding: 2px; }
.training-tab { padding: 5px 12px; font-size: 11px; color: var(--text-1); background: transparent; border: none; border-radius: 4px; cursor: pointer; transition: all .12s; white-space: nowrap; }
.training-tab:hover { background: var(--bg-3); }
.training-tab.active { background: var(--bg-3); color: var(--text-0); font-weight: 600; }
.training-panel { display: none; flex-direction: column; gap: 8px; }
.training-panel.active { display: flex; }

/* Training form */
.train-field { display: flex; flex-direction: column; gap: 3px; }
.train-row { display: flex; gap: 8px; align-items: center; }
.train-input { background: var(--bg-2); border: 1px solid var(--border); color: var(--text-0); padding: 6px 8px; border-radius: 4px; font-size: 12px; font-family: inherit; }
.train-input:focus { border-color: var(--border-strong); outline: none; }
.train-input.wide { flex: 1; min-width: 0; }

/* ── Loading spinner ── */
.spinner { width: 16px; height: 16px; border: 2px solid var(--border-strong); border-top-color: var(--text-0); border-radius: 50%; animation: spin .6s linear infinite; display: inline-block; }
@keyframes spin { to { transform: rotate(360deg); } }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: var(--bg-1); }
::-webkit-scrollbar-thumb { background: var(--border-strong); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: var(--text-2); }

/* ── Toast notifications ── */
.toast-container { position: fixed; top: 48px; left: 50%; transform: translateX(-50%); z-index: 900; display: flex; flex-direction: column; gap: 8px; pointer-events: none; }
.toast { pointer-events: auto; background: var(--bg-1); border: 1px solid var(--border-strong); border-radius: 10px; padding: 10px 16px; display: flex; align-items: center; gap: 12px; box-shadow: 0 8px 30px rgba(0,0,0,.45); backdrop-filter: blur(8px); animation: toastIn .25s ease-out; min-width: 260px; }
.toast.hiding { animation: toastOut .2s ease-in forwards; }
@keyframes toastIn { from { opacity: 0; transform: translateY(-12px); } to { opacity: 1; transform: translateY(0); } }
@keyframes toastOut { from { opacity: 1; transform: translateY(0); } to { opacity: 0; transform: translateY(-12px); } }
.toast-text { font-size: 13px; color: var(--text-1); flex: 1; }
.toast-go { padding: 5px 14px; font-size: 12px; font-weight: 600; background: var(--text-0); color: var(--bg-0); border: none; border-radius: 6px; cursor: pointer; white-space: nowrap; transition: background .12s; }
.toast-go:hover { background: #fff; }

/* ── Hidden utility ── */
.hidden { display: none !important; }


/* ── LLM section when models loaded but no LM configured ── */

/* ── Init status message ── */
.init-status { font-size: 11px; padding: 6px 8px; border-radius: 4px; background: var(--bg-2); color: var(--text-1); word-break: break-word; }

/* ── Modal overlay ── */
.modal-overlay {
    position: fixed; inset: 0; z-index: 1000;
    background: rgba(0,0,0,.65); backdrop-filter: blur(4px);
    display: flex; align-items: center; justify-content: center;
}
.modal-overlay.hidden { display: none !important; }
.modal-box {
    background: var(--bg-1); border: 1px solid var(--border-strong);
    border-radius: 12px; padding: 24px; max-width: 500px; width: 90%;
    box-shadow: 0 20px 60px rgba(0,0,0,.5);
}
.modal-title { font-size: 16px; font-weight: 700; color: var(--text-0); margin-bottom: 4px; }
.modal-subtitle { font-size: 12px; color: var(--text-1); margin-bottom: 16px; line-height: 1.5; }
.modal-box .field, .modal-box .toggle-row { max-width: 100%; }

/* Extra spacing for fields inside the modal to prevent overlap */
.modal-box .field { gap: 8px !important; }
.modal-box > .field,
.modal-box > .toggle-row,
.modal-box > div[style*="border-top"],
.modal-box > #modal-gpu-info {
    margin-bottom: 6px;
}
.modal-footer { display: flex; justify-content: flex-end; gap: 8px; margin-top: 16px; padding-top: 12px; border-top: 1px solid var(--border); }

/* Model availability warning inside init modal */
.model-warning {
    font-size: 11px; color: #f5a623; background: rgba(245,166,35,.08);
    border: 1px solid rgba(245,166,35,.25); border-radius: 6px;
    padding: 6px 8px; margin-top: 2px; line-height: 1.4;
}
.model-warning.hidden { display: none; }

/* Modal buttons */
.modal-footer button {
    padding: 7px 18px; font-size: 12px; font-weight: 600; letter-spacing: .04em;
    border-radius: 6px; cursor: pointer; transition: all .12s; border: none;
}
.modal-footer button:disabled { opacity: .5; cursor: wait; }
#modal-skip-btn {
    background: var(--bg-3); color: var(--text-1); border: 1px solid var(--border) !important;
}
#modal-skip-btn:hover:not(:disabled) { background: #24242a; color: var(--text-0); }
#modal-init-btn {
    background: var(--text-0); color: var(--bg-0);
}
#modal-init-btn:hover:not(:disabled) { background: #fff; }

/* Modal during init: dim non-button elements inside the modal box, animate button text */
.modal-box.initing .modal-subtitle,
.modal-box.initing #modal-gpu-info,
.modal-box.initing .toggle-row,
.modal-box.initing select,
.modal-box.initing .lm-option { opacity: .35; pointer-events: none; user-select: none; }
.modal-box.initing .modal-skip-btn { opacity: .4; pointer-events: none; }

/* Button shimmer during init */
@keyframes btn-shimmer {
    0%, 100% { background-position: -200% center; }
    50% { background-position: 200% center; }
}
.modal-box.initing #modal-init-btn {
    background: linear-gradient(90deg, rgba(255,255,255,.06) 40%, rgba(255,255,255,.18) 50%, rgba(255,255,255,.06) 60%) !important;
    background-size: 300% auto !important;
    animation: btn-shimmer 2s ease-in-out infinite;
    cursor: wait;
}

/* Reinitialize link */
.reinit-link {
    font-size: 12px; color: var(--accent); text-align: center; display: block;
    padding: 8px 0 4px; cursor: pointer; text-decoration: underline; opacity: .7;
}
.reinit-link:hover { opacity: 1; }

/* LLM Interpretation (CoT reasoning preview) */
.llm-interpretation {
    margin: 6px 0 0; border-top: 1px solid var(--border);
}
.llm-interpretation[open] {
    max-height: none;
}
.llm-interpretation summary {
    font-size: 11px; color: var(--text-2); cursor: pointer; padding: 4px 0;
    user-select: none; letter-spacing: .03em; text-transform: uppercase;
}
.llm-interpretation summary:hover { color: var(--text-1); }
.llm-interpretation pre {
    margin: 6px 8px; padding: 8px 10px; font-size: 12px; line-height: 1.5;
    background: var(--bg-3); border-radius: 4px; color: var(--text-1);
    max-height: 300px; overflow-y: auto; white-space: pre-wrap; word-break: break-word;
    font-family: 'JetBrains Mono', monospace, sans-serif;
}
"""
