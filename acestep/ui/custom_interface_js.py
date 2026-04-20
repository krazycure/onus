"""Custom AceStep UI — Client-side JavaScript.

Exports:
    CLIENT_JS: The full JavaScript for the main interface page.

See Also:
    custom_interface.py      - Backend core (init, generate, CLI)
    custom_interface_css.py  - Stylesheet (STYLES_CSS)
    custom_interface_html.py - HTML body template (FRONTEND_BODY_HTML)
    custom_interface_routes.py - API routes + FastAPI app
"""

CLIENT_JS = r"""
const MODES = ["Advanced", "Cover", "Edit", "Inspiration", "Sound Stack"];
let currentMode = "Advanced";
let modelsReady = false;
let llmReady = false;
let resultsStore = []; // track result cards for clearing
let _toastCountdown = 0; // auto-dismiss countdown (updated each interval tick)
let currentCoverNoisePreset = "0.0"; // tracks selected cover noise preset value
let currentEditPreset = "0.5"; // tracks selected Edit strength preset value
const SETTINGS_KEY = "acestep_settings_v1";
const DIVIDER_KEY = "acestep_divider_width";

// ── GPU info on load ──
fetch("/api/config").then(r => r.json()).then(data => {
    if (data.gpu) {
        document.getElementById("gpu-info").textContent = `${data.gpu} | ${data.gpu_memory_gb || '?'}GB VRAM | Tier ${data.tier || '?'}`;
    } else {
        document.getElementById("gpu-info").textContent = "GPU info unavailable";
    }
}).catch(() => {
    document.getElementById("gpu-info").textContent = "Could not detect GPU";
});

// ── Inspiration style preview ────────────────────────────────────────────────
const INSPIRATION_STYLE_DESCS = {
    detailed: "The LLM will expand your caption into a more detailed musical description, then generate audio codes guided by the source audio's style.",
    lyrics: "The LLM will write complete song lyrics with structure tags ([Verse], [Chorus], etc.), then use those lyrics to guide generation.",
    conductor: "The LLM will create structural arrangement notes (instrument cues per section) for an instrumental piece, guiding the DiT model's output.",
    mood: "The LLM will describe the mood, atmosphere, instrumentation, and production style in vivid detail before generating audio codes.",
};

function updateInspirationStylePreview() {
    const el = document.getElementById("inspiration-style-preview");
    if (!el) return;
    const preset = document.getElementById("inspiration_style")?.value;
    if (preset && INSPIRATION_STYLE_DESCS[preset]) {
        el.textContent = INSPIRATION_STYLE_DESCS[preset];
        el.style.display = "block";
    } else {
        el.style.display = "none";
    }
}

// ── Inspiration strength slider init ─────────────────────────────────────────
(function() {
    const slider = document.getElementById("inspiration_strength");
    if (slider) updateInspirationStrength(slider);
})();

// ── Mode pills ──
const MODE_TITLES = {
    "Advanced": "Full manual control over caption, lyrics, BPM, key, and all generation parameters. Use when you know exactly what you want.",
    "Cover": "Generate new music using a reference audio for timbre/style transfer. Upload reference + source audio to control what gets generated.",
    "Edit": "Open your source audio in an editor to modify specific regions. Choose intensity (Subtle Blend/Moderate Blend/Full Replace) and set start/end times. Prompt drives the regenerated content.",    "Inspiration": "Use source audio as a vibe reference to generate entirely new music in the same style. Choose a Focus (instrument/stem) and Style, then write a prompt for what you want.",
    "Sound Stack": "Start with a vocal or instrument layer and build a full track on top of it. Add drums, bass, harmonies — anything you can imagine. Upload your starting layer as reference audio.",
};
const pillsEl = document.getElementById("mode-pills");
MODES.forEach(mode => {
    const btn = document.createElement("button");
    btn.className = "mode-pill" + (mode === currentMode ? " active" : "");
    btn.textContent = mode;
    if (MODE_TITLES[mode]) btn.title = MODE_TITLES[mode];
    btn.onclick = () => setMode(mode);
    pillsEl.appendChild(btn);
});

function setMode(mode) {
    currentMode = mode;
    document.querySelectorAll(".mode-pill").forEach(p => p.classList.toggle("active", p.textContent === mode));
    updateVisibility();
}

// ── Toggle custom input visibility for dropdowns ──
function toggleCustomInput(field, value, selectId) {
    const selectEl = document.getElementById(selectId || field + "-select");
    const customEl = document.getElementById(field + "-custom");
    if (!selectEl) return;
    if (value === "custom") {
        selectEl.style.display = "none";
        if (customEl) customEl.style.display = "";
        customEl && customEl.focus();
    } else {
        selectEl.style.display = "";
        if (customEl) customEl.style.display = "none";
    }
}

function getCustomValue(field, selectId) {
    const selectEl = document.getElementById(selectId || field + "-select");
    const customEl = document.getElementById(field + "-custom");
    if (!selectEl || selectEl.style.display === "none" || selectEl.value === "custom") {
        return customEl ? customEl.value.trim() || null : null;
    }
    return selectEl.value || null;
}

function restoreDropdownValue(field, value, selectId) {
    const selectEl = document.getElementById(selectId || field + "-select");
    const customEl = document.getElementById(field + "-custom");
    if (!selectEl || !customEl) return;
    // Try to find matching option
    const opt = Array.from(selectEl.options).find(o => o.value === value);
    if (opt) {
        selectEl.value = value;
        toggleCustomInput(field, value, selectId);
    } else if (value) {
        // Value not in dropdown — use custom input
        customEl.value = value;
        toggleCustomInput(field, "custom", selectId);
    }
}

// ── Randomize ────────────────────────────────────────────────────────────────
const KEYS = ["C major","C minor","D major","D minor","E major","E minor","F major","F minor","G major","G minor","A major","A minor","B major","B minor"];
const SIGS = ["2/4","3/4","4/4","5/4","6/8","7/4"];

function randomize() {
    // BPM: 60–180, snap to preset or custom
    const bpmPreset = [60,80,100,120,130,140,150,160,180];
    const bpmVal = bpmPreset[Math.floor(Math.random() * bpmPreset.length)];
    document.getElementById("bpm-select").value = String(bpmVal);
    toggleCustomInput("bpm", String(bpmVal));

    // Key
    document.getElementById("keyscale-select").value = KEYS[Math.floor(Math.random() * KEYS.length)];
    toggleCustomInput("key", document.getElementById("keyscale-select").value);

    // Time signature
    const sigVal = SIGS[Math.floor(Math.random() * SIGS.length)];
    document.getElementById("timesignature-select").value = sigVal;
    toggleCustomInput("time", sigVal);

    // Duration: 90–300 seconds (1.5–5 minutes)
    const dur = Math.round(90 + Math.random() * 210);
    document.getElementById("duration-custom").value = dur;

    // Steps: 4–32
    const steps = [4,6,8,12,16,24,32][Math.floor(Math.random() * 7)];
    document.getElementById("inference_steps").value = steps;

    // Guidance: 3.0–10.0
    const guidance = (3 + Math.random() * 7).toFixed(1);
    document.getElementById("guidance_scale").value = guidance;

    // Seed: random positive integer
    document.getElementById("seed").value = String(Math.floor(Math.random() * 999999));

    saveSettings();
}

document.getElementById("randomize-btn").onclick = randomize;

// ── Reset to defaults ────────────────────────────────────────────────────────
function resetToDefaults() {
    // BPM → Auto
    document.getElementById("bpm-select").value = "";
    toggleCustomInput("bpm", "");

    // Key → Auto
    document.getElementById("keyscale-select").value = "";
    toggleCustomInput("key", "", "keyscale-select");

    // Sig → Auto
    document.getElementById("timesignature-select").value = "";
    toggleCustomInput("time", "", "timesignature-select");

    // Duration → empty
    document.getElementById("duration-custom").value = "";

    // Batch → 1
    document.getElementById("batch-custom").value = "1";

    // Steps → 8 (turbo default)
    document.getElementById("inference_steps").value = "8";

    // Guidance → 7.0
    document.getElementById("guidance_scale").value = "7.0";

    // Seed → -1, Random checked
    document.getElementById("seed").value = "-1";
    document.getElementById("use_random_seed").checked = true;

    saveSettings();
}

document.getElementById("reset-btn").onclick = resetToDefaults;

// ── Auto-resize textarea (min rows → maxLines, capped) ────────────────────────
function autoResizeTextarea(el, maxLines) {
    el.style.height = "auto";
    const lineHeight = parseInt(getComputedStyle(el).lineHeight) || 20;
    const cap = maxLines * lineHeight;
    el.style.height = Math.min(el.scrollHeight, cap) + "px";
}

// ── Lyrics input — auto-off instrumental toggle when user types ────────────────
function onLyricsInput() {
    const lyricsEl = document.getElementById("lyrics");
    const toggle = document.getElementById("instrumental-toggle");
    if (toggle.checked && lyricsEl.value.trim() !== "[Instrumental]") {
        toggle.checked = false;
    }
}

// ── Mode pills / visibility ────────────────────────────────────────────────────
function updateVisibility() {
    // Lyrics: shown for all modes except Inspiration and Sound Stack (per Gradio design)
    const showLyrics = currentMode !== "Inspiration" && currentMode !== "Sound Stack";
    const showSrcAudio = ["Cover", "Edit", "Inspiration", "Sound Stack"].includes(currentMode);
    const showRefAudio = ["Cover", "Edit", "Sound Stack"].includes(currentMode);
    const showCoverControls = currentMode === "Cover";
    const showInspirationControls = currentMode === "Inspiration";
    const showCustom = currentMode === "Advanced" || currentMode === "Inspiration";
    const showEdit = currentMode === "Edit" || currentMode === "Sound Stack";
    const showTrackSelect = currentMode === "Inspiration" || currentMode === "Sound Stack";

    document.getElementById("lyrics-field").classList.toggle("hidden", !showLyrics);
    document.getElementById("src-audio-field").classList.toggle("hidden", !showSrcAudio);
    document.getElementById("ref-audio-field").classList.toggle("hidden", !showRefAudio);
    document.getElementById("cover-controls-field").classList.toggle("hidden", !showCoverControls);
    document.getElementById("inspiration-controls-field").classList.toggle("hidden", !showInspirationControls);
    document.getElementById("custom-fields").classList.toggle("hidden", !showCustom);
    document.getElementById("repaint-controls-field").classList.toggle("hidden", !showEdit);
    document.getElementById("track-select-field").classList.toggle("hidden", !showTrackSelect);

    // Interpret button: only visible in Inspiration mode
    document.getElementById("interpret-btn").classList.toggle("hidden", currentMode !== "Inspiration");

    // Dynamic labels for Edit vs Sound Stack modes
    if (currentMode === "Sound Stack") {
        document.getElementById("repaint-section-label").textContent = "Layer Region Controls";
    } else {
        document.getElementById("repaint-section-label").textContent = "Edit Region Controls";
    }

    // Dynamic labels for Edit vs Sound Stack time inputs
    if (currentMode === "Sound Stack") {
        document.getElementById("repainting_start").title = "Start time of the new stem area in seconds";
        document.getElementById("repainting_end").title = "End time of the new stem area (-1 = to end)";
    } else {
        document.getElementById("repainting_start").title = "Start time (in seconds) of the region to regenerate. Use 0.0 to start from the beginning of the audio.";
        document.getElementById("repainting_end").title = "End time (in seconds) of the region to regenerate. Use -1 to extend to the end of the audio.";
    }

    // Dynamic labels for track selector in Sound Stack vs Inspiration modes
    const trackSelectorLabel = document.getElementById("track-selector-label");
    if (currentMode === "Sound Stack") {
        if (trackSelectorLabel) trackSelectorLabel.textContent = "Layer";
    } else if (currentMode === "Inspiration" && trackSelectorLabel) {
        trackSelectorLabel.textContent = "Focus";
    }

    // Inspiration style preview descriptions
    const STYLE_PREVIEWS = {
        detailed: "The LLM will expand your caption into a more detailed musical description, then generate audio codes guided by the source audio's style.",
        lyrics: "The LLM will write complete song lyrics with structure tags ([Verse], [Chorus], etc.), then use those lyrics to guide generation.",
        conductor: "The LLM will create structural arrangement notes (instrument cues per section) for an instrumental piece, guiding the DiT model's output.",
        mood: "The LLM will describe the mood, atmosphere, instrumentation, and production style in vivid detail before generating audio codes.",
    };
    const stylePreview = document.getElementById("inspiration-style-preview");
    if (stylePreview) {
        const preset = document.getElementById("inspiration_style")?.value;
        if (preset && STYLE_PREVIEWS[preset]) {
            stylePreview.textContent = STYLE_PREVIEWS[preset];
            stylePreview.style.display = "block";
        } else {
            stylePreview.style.display = "none";
        }
    }

    // Dynamic labels for track selector in Sound Stack vs Inspiration modes (tooltip)
    const trackSelector = document.getElementById("track-selector");
    if (currentMode === "Sound Stack" && trackSelector) {
        trackSelector.title = "Which layer to generate. 'All / Auto' lets the model decide generically. Specific instruments tell the model which one to add to your source audio.";
    } else if (currentMode === "Inspiration" && trackSelector) {
        trackSelector.title = "Which instrument/stem to isolate. 'All / Auto' lets the model decide generically. Specific instruments tell the model which one to generate from your source audio.";
    }

    // Update approach label for Edit mode only (in Sound Stack it stays as "Approach")
    const repaintModeLabel = document.querySelector("#repaint-controls-field .field-row:nth-child(4) span");
    if (repaintModeLabel) {
        if (currentMode === "Edit") {
            repaintModeLabel.textContent = "Approach";
            repaintModeLabel.title = "Regeneration approach. Subtle Blend preserves more of the original audio, Full Replace regenerates everything.";
        } else {
            repaintModeLabel.textContent = "Edit Approach";
            repaintModeLabel.title = "How the new stem is generated. Subtle Blend preserves more of the original audio, Full Replace regenerates everything.";
        }
    }

    // Update strength label for Sound Stack mode
    const strengthLabel = document.querySelector("#repaint-controls-field .field-row:nth-child(5) span:first-of-type");
    if (currentMode === "Sound Stack" && strengthLabel) {
        strengthLabel.textContent = "Blend";
        strengthLabel.title = "How much new content to blend. 0 = keep original, 1 = fully replace.";
    } else if (strengthLabel) {
        strengthLabel.textContent = "Strength";
        strengthLabel.title = "How much of the region gets regenerated. 0 = minimal change, 1 = full regeneration.";
    }

    // Dynamic button label for Sound Stack mode
    const genBtn = document.getElementById("generate-btn");
    if (genBtn) {
        genBtn.textContent = currentMode === "Sound Stack" ? "ADD LAYER" : "GENERATE";
    }

    // Waveform visibility & render for Edit mode
    const waveformContainer = document.getElementById("waveform-container");
    if (currentMode === "Edit" && waveformContainer) {
        updateWaveform();
    } else if (waveformContainer) {
        waveformContainer.classList.add("hidden");
    }
}

// ── Bidirectional sync: strength slider ↔ preset cards ──
function onRepaintStrengthChange() {
    const strengthSlider = document.getElementById("repaint_strength");
    if (!strengthSlider) return;
    const strength = parseFloat(strengthSlider.value);
    // Sync preset card selection
    let closestPreset = "0.5";
    let minDiff = Math.abs(strength - 0.5);
    const candidates = [
        { value: "0.2", label: "Conservative" },
        { value: "0.5", label: "Balanced" },
        { value: "1.0", label: "Full Replace" },
    ];
    for (const c of candidates) {
        const diff = Math.abs(strength - parseFloat(c.value));
        if (diff < minDiff) {
            minDiff = diff;
            closestPreset = c.value;
        }
    }
    currentEditPreset = closestPreset;
    document.querySelectorAll(".strength-preset-card").forEach(card => {
        card.classList.toggle("selected", card.dataset.value === closestPreset);
    });

}

// Derive repaint_mode string from a numeric strength value.
function computeRepaintModeFromStrength(strength) {
    if (strength < 0.35) return "conservative";
    if (strength < 0.75) return "balanced";
    return "aggressive";
}

// ── Inspiration strength slider: gradient + dynamic value color ────────────────
function updateInspirationStrength(el) {
    const val = parseFloat(el.value);
    // Compute interpolated color between prompt (amber #f59e0b) and source (blue #3b82f6)
    const r = Math.round(245 + (59 - 245) * val);
    const g = Math.round(158 + (130 - 158) * val);
    const b = Math.round(11 + (246 - 11) * val);
    const color = `rgb(${r},${g},${b})`;

    // Gradient background on the slider track
    el.style.backgroundImage = `linear-gradient(to right, #f59e0b ${val * 100}%, #3b82f6 ${val * 100}%)`;

    // Color the numeric value to match
    const valEl = document.getElementById("inspiration-strength-val");
    if (valEl) valEl.style.color = color;

    // Update label emphasis based on which side is dominant
    const leftLabel = document.getElementById("inspiration-label-left");
    const rightLabel = document.getElementById("inspiration-label-right");
    if (leftLabel && rightLabel) {
        const dimmed = "rgba(148, 163, 184, 0.5)"; // slate-400 muted
        if (val < 0.4) {
            leftLabel.style.color = "#f59e0b";
            rightLabel.style.color = dimmed;
        } else if (val > 0.6) {
            leftLabel.style.color = dimmed;
            rightLabel.style.color = "#3b82f6";
        } else {
            leftLabel.style.color = "#f59e0b";
            rightLabel.style.color = "#3b82f6";
        }
    }

    // Format to 2 decimal places
    if (valEl) valEl.textContent = val.toFixed(2);
}

// ── Instrumental toggle — auto-fills [Instrumental] into lyrics ──
document.getElementById("instrumental-toggle").onchange = () => {
    const lyricsEl = document.getElementById("lyrics");
    if (document.getElementById("instrumental-toggle").checked) {
        lyricsEl.value = "[Instrumental]";
    } else if (lyricsEl.value.trim() === "[Instrumental]") {
        lyricsEl.value = "";
    }
};

// ── Clear file input ──
function clearFileInput(id) {
    const el = document.getElementById(id);
    el.value = "";
}

// ── Prompt Library ──
const PROMPT_LIB_KEY = "acestep_prompt_library";

function loadPromptLib() {
    try {
        const raw = localStorage.getItem(PROMPT_LIB_KEY);
        if (!raw) return {};
        const lib = JSON.parse(raw);
        // Ensure pinned array exists (backward compat)
        if (!Array.isArray(lib.pinned)) lib.pinned = [];
        return lib;
    } catch { return { pinned: [] }; }
}
function savePromptLib(lib) { localStorage.setItem(PROMPT_LIB_KEY, JSON.stringify(lib)); }

function renderPromptLibrary() {
    const lib = loadPromptLib();
    const row = document.getElementById("prompt-library-row");
    const list = document.getElementById("prompt-lib-list");
    const pinned = lib.pinned || [];
    // Filter to only existing entries (in case deleted)
    const validPinned = pinned.filter(n => n && lib[n] && !lib[n].pinned);
    const nonPinnedEntries = Object.entries(lib).filter(([name, entry]) => name !== "pinned" && !entry.pinned);

    // Render pinned buttons
    const pinnedContainer = document.getElementById("pinned-prompts");
    if (validPinned.length > 0) {
        pinnedContainer.innerHTML = validPinned.map(name =>
            `<button class="pinned-btn" data-name="${name}" title="Click to load · Right-click or press × to unpin">` +
            esc((lib[name] && lib[name].name) || name) +
            `<span class="unpin-btn" data-unpin="${name}">&times;</span></button>`
        ).join("");
        pinnedContainer.querySelectorAll(".pinned-btn").forEach(btn => {
            btn.onclick = (e) => {
                if (e.target.classList.contains("unpin-btn")) return;
                loadPromptFromLib(btn.dataset.name);
            };
        });
        pinnedContainer.querySelectorAll(".unpin-btn").forEach(btn => {
            btn.onclick = (e) => { e.stopPropagation(); togglePinPrompt(btn.dataset.unpin); };
        });
    } else {
        pinnedContainer.innerHTML = "";
    }

    // Populate dropdown with non-pinned entries
    const dropdown = document.getElementById("prompt-lib-dropdown");
    if (dropdown) {
        dropdown.innerHTML = '<option value="">-- Load Prompt --</option>' +
            nonPinnedEntries.map(([name, entry]) =>
                `<option value="${esc(name)}">${esc((entry.name || name).slice(0, 40))}</option>`
            ).join("");
    }

    // Modal list (show all entries including pinned)
    const allEntries = Object.entries(lib).filter(([name]) => name !== "pinned");
    if (allEntries.length === 0) {
        list.innerHTML = '<div style="font-size:12px;color:var(--text-2);text-align:center;padding:20px;">No saved prompts yet.</div>';
    } else {
        list.innerHTML = allEntries.map(([name, entry]) => {
            const isPinned = (lib.pinned || []).includes(name);
            return `<div class="prompt-lib-item" data-name="${name}">` +
                `<span class="lib-name">${esc(entry.name || name)}</span>` +
                `<span class="lib-preview">${esc((entry.caption || "").slice(0, 40))}</span>` +
                (isPinned ? '<span style="font-size:10px;color:var(--text-2);">★</span>' : '') +
                `<button class="lib-delete" data-name="${name}">&#10005;</button></div>`;
        }).join("");

        list.querySelectorAll(".prompt-lib-item").forEach(item => {
            item.onclick = (e) => {
                if (e.target.classList.contains("lib-delete")) return;
                loadPromptFromLib(item.dataset.name);
                dismissPromptLibModal();
            };
        });
        list.querySelectorAll(".lib-delete").forEach(btn => {
            btn.onclick = (e) => { e.stopPropagation(); deletePromptFromLib(btn.dataset.name); };
        });
    }
}

function togglePinPrompt(name) {
    const lib = loadPromptLib();
    if (!Array.isArray(lib.pinned)) lib.pinned = [];
    const idx = lib.pinned.indexOf(name);
    if (idx >= 0) {
        lib.pinned.splice(idx, 1);
    } else {
        lib.pinned.push(name);
    }
    savePromptLib(lib);
    renderPromptLibrary();
}

function esc(s) { const d = document.createElement("div"); d.textContent = s; return d.innerHTML; }

function saveToPromptLibrary() {
    const caption = document.getElementById("caption").value.trim();
    const lyrics = document.getElementById("lyrics").value.trim();
    if (!caption && !lyrics) { alert("Nothing to save — add a prompt or lyrics first."); return; }
    const name = document.getElementById("lib-name").value.trim() || caption.slice(0, 30) || "untitled";
    const lib = loadPromptLib();
    // Check pin checkbox state
    const pinChecked = document.getElementById("lib-pin-checkbox") && document.getElementById("lib-pin-checkbox").checked;

    lib[name] = { caption, lyrics, mode: currentMode, savedAt: new Date().toISOString() };
    if (pinChecked && !lib.pinned.includes(name)) lib.pinned.push(name);
    savePromptLib(lib);
    document.getElementById("lib-name").value = "";
    renderPromptLibrary();
}

function deletePromptFromLib(name) {
    if (!confirm(`Delete "${name}" from library?`)) return;
    const lib = loadPromptLib();
    delete lib[name];
    if (Array.isArray(lib.pinned)) lib.pinned = lib.pinned.filter(n => n !== name);
    savePromptLib(lib);
    renderPromptLibrary();
}

function loadPromptFromLib(name) {
    const lib = loadPromptLib();
    const entry = lib[name];
    if (!entry) return;
    document.getElementById("caption").value = entry.caption || "";
    if (entry.lyrics) {
        document.getElementById("lyrics").value = entry.lyrics;
        // Restore instrumental toggle state
        document.getElementById("instrumental-toggle").checked = (entry.lyrics.trim() === "[Instrumental]");
    }
    // Reset pin checkbox on load
    const pinCb = document.getElementById("lib-pin-checkbox");
    if (pinCb) pinCb.checked = false;
    renderPromptLibrary();
}

function handlePromptLibSelect(value) {
    if (value) {
        loadPromptFromLib(value);
        document.getElementById("prompt-lib-dropdown").value = "";
    }
}

function openPromptLibModal() {
    document.getElementById("prompt-lib-modal").classList.remove("hidden");
    renderPromptLibrary();
}
function dismissPromptLibModal() {
    document.getElementById("prompt-lib-modal").classList.add("hidden");
}

// ── Accordion toggle ──
function toggleAccordion(bodyId, chevronId) {
    const body = document.getElementById(bodyId);
    const chev = document.getElementById(chevronId);
    if (body.classList.contains("collapsed")) {
        body.style.maxHeight = body.scrollHeight + 200 + "px";
        setTimeout(() => body.classList.remove("collapsed"), 10);
        chev.classList.add("open");
    } else {
        body.style.maxHeight = body.scrollHeight + "px";
        requestAnimationFrame(() => {
            body.classList.add("collapsed");
            chev.classList.remove("open");
        });
    }
}

// ── Training tabs ──
function switchTrainTab(tab) {
    document.querySelectorAll(".training-tab").forEach(t => t.classList.remove("active"));
    document.querySelectorAll(".training-panel").forEach(p => p.classList.remove("active"));
    event.target.classList.add("active");
    document.getElementById("train-" + tab).classList.add("active");
}

// ── Show init modal on first load if not ready ──
(function() {
    fetch("/api/config").then(r => r.json()).then(data => {
        if (!data.ready) {
            const m = document.getElementById("init-modal");
            if (m) m.classList.remove("hidden");
        }
    }).catch(() => {
        const m = document.getElementById("init-modal");
        if (m) m.classList.remove("hidden");
    });
})();

// ── Init modal button ──
function resetModalButton() {
    const btn = document.getElementById("modal-init-btn");
    if (!btn) return;
    btn.disabled = false;
    btn.textContent = "INITIALIZE";
}

document.getElementById("modal-init-btn").onclick = async () => {
    const box = document.querySelector("#init-modal .modal-box");
    if (box) box.classList.add("initing");
    await runInit();
};

// Skip button dismisses the modal
document.getElementById("modal-skip-btn").onclick = () => dismissModal();

// ── Reinitialize flow ──
function triggerReinit() {
    resetModalButton();
    const m = document.getElementById("init-modal");
    if (!m) return;
    // Reset init state from any previous session
    m.querySelector(".modal-box")?.classList.remove("initing");
    _stopInitDots();
    m.classList.remove("hidden");
}

function dismissModal() {
    resetModalButton();
    const link = document.getElementById("reinit-link");
    if (link) link.classList.remove("hidden");
    const m = document.getElementById("init-modal");
    if (m) m.classList.add("hidden");
}

// ── LM model selector ────────────────────────────────────────────────────────
let selectedFormLmModel = localStorage.getItem("lm_model_form") || "acestep-5Hz-lm-1.7B";

async function renderLMModelSelector(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    let models;
    try {
        const resp = await fetch("/api/lm-models/available");
        models = (await resp.json()).models || [];
    } catch {
        // Fallback to defaults if API unavailable
        models = [
            {id:"acestep-5Hz-lm-0.6B", label:"0.6B (fastest, ~3GB VRAM)", vram_gb:3, installed:true},
            {id:"acestep-5Hz-lm-1.7B", label:"1.7B (balanced, ~8GB VRAM)", vram_gb:8, installed:true},
            {id:"acestep-5Hz-lm-4B",   label:"4B (best quality, ~12GB VRAM)", vram_gb:12, installed:false},
        ];
    }

    container.innerHTML = models.map(m => `
        <div class="lm-option${m.id === selectedFormLmModel ? ' selected' : ''}" data-model="${m.id}">
            <div class="lm-radio"></div>
            <div class="lm-info" style="flex:1;min-width:0;">
                <div class="lm-name">${m.label}</div>
                <div class="lm-meta">${m.vram_gb}GB VRAM · ${m.installed ? 'Installed' : 'Not installed'}</div>
            </div>
            ${!m.installed ? `<button class="lm-download-btn" onclick="event.stopPropagation();downloadLMModel('${m.id}',this)">Download</button>` : '<span class="lm-installed">&#10003;</span>'}
        </div>`).join('');

    container.querySelectorAll(".lm-option").forEach(el => {
        el.onclick = () => {
            container.querySelector(".selected")?.classList.remove("selected");
            el.classList.add("selected");
            selectedFormLmModel = el.dataset.model;
            localStorage.setItem("lm_model_form", el.dataset.model);
        };
    });
}

async function downloadLMModel(modelName, btnEl) {
    btnEl.textContent = "Downloading...";
    btnEl.classList.add("downloading");
    try {
        const resp = await fetch("/api/lm-model/download", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({model: modelName}),
        });
        const data = await resp.json();
        if (data.status === "ok") {
            btnEl.textContent = "Installed";
            btnEl.classList.remove("downloading");
            btnEl.style.display = "none";
            // Re-render to show checkmark
            renderLMModelSelector("lm-list");
        } else {
            btnEl.textContent = "Download";
            btnEl.classList.remove("downloading");
            alert("Download failed: " + (data.message || "unknown error"));
        }
    } catch (e) {
        btnEl.textContent = "Download";
        btnEl.classList.remove("downloading");
        alert("Download failed: " + e.message);
    }
}

// ── Prompt Library event listeners ──
document.getElementById("lib-save-btn").onclick = saveToPromptLibrary;
document.getElementById("lib-close-btn").onclick = dismissPromptLibModal;
document.getElementById("lib-manage-btn-inline").onclick = openPromptLibModal;
document.getElementById("prompt-lib-modal").onclick = (e) => {
    if (e.target.id === "prompt-lib-modal") dismissPromptLibModal();
};

// Shared init runner for the form button
let _initStatusTimer = null;

function _setInitStatus(text) {
    const statusBar = document.getElementById("status-bar");
    const statusText = document.getElementById("status-text");
    if (!statusBar || !statusText) return;
    statusBar.className = "status generating";
    statusText.textContent = text;
}

function _startInitDots() {
    let count = 0;
    _setInitStatus("Initializing, please wait" + ".".repeat(count % 4));
    _initStatusTimer = setInterval(() => {
        count++;
        _setInitStatus("Initializing, please wait" + ".".repeat(count % 4));
    }, 500);
}

function _stopInitDots() {
    if (_initStatusTimer) {
        clearInterval(_initStatusTimer);
        _initStatusTimer = null;
    }
}

async function runInit() {
    const btn = document.getElementById("modal-init-btn");
    if (!btn) return;
    btn.disabled = true;
    btn.textContent = "Initializing...";

    // Hide init modal and reinit link so user can interact with the UI during init
    const initModalEl = document.getElementById("init-modal");
    if (initModalEl) initModalEl.classList.add("hidden");
    const reinitLink = document.getElementById("reinit-link");
    if (reinitLink) reinitLink.classList.add("hidden");

    _startInitDots();

    try {
        // Read config from modal inputs (prefixed with "init-")
        const getConfig = (id) => { const el = document.getElementById("init-" + id); return el ? el.value : null; };
        const getCheck = (id) => { const el = document.getElementById("init-" + id); return el ? el.checked : false; };

        const resp = await fetch("/api/init", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                config_path: getConfig("config_path") || "acestep-v15-sft",
                device: getConfig("device") || "auto",
                quantization: (getConfig("quantization") && getConfig("quantization") !== "") ? getConfig("quantization") : null,
                compile_model: getCheck("compile_model"),
                offload_dit_to_cpu: getCheck("offload_dit_to_cpu"),
                lm_model_path: selectedFormLmModel,
                backend: getConfig("lm_backend") || "vllm",
                init_llm: getCheck("init_llm"),
            }),
        });
        const data = await resp.json();

        if (data.status === "complete") {
            _stopInitDots();
            resetModalButton();
            modelsReady = true;
            llmReady = data.llm_available || false;
            setStatus("ready", "Ready");
            document.getElementById("generate-btn").disabled = false;
            const link = document.getElementById("reinit-link");
            if (link) link.classList.remove("hidden");
        } else {
            _stopInitDots();
            resetModalButton();
            setStatus("error", (data.traceback || data.message || "Init failed").substring(0, 200));
            const link = document.getElementById("reinit-link");
            if (link) link.classList.remove("hidden");
        }
    } catch (e) {
        _stopInitDots();
        resetModalButton();
        setStatus("error", e.message);
        const link = document.getElementById("reinit-link");
        if (link) link.classList.remove("hidden");
    }
}

// ── Inspiration Interpret (lightbulb) ────────────────────────────────────────

async function handleInterpret() {
    const captionEl = document.getElementById("caption");
    const btn = document.getElementById("interpret-btn");
    const originalTitle = btn.title;
    const svg = btn.querySelector("svg");

    // Loading state
    btn.disabled = true;
    btn.style.color = "#f5a623";
    btn.title = "Interpreting...";
    setStatus("generating", "Interpreting prompt with LLM...");

    try {
        const resp = await fetch("/api/interpret", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                caption: captionEl.value.trim(),
                lyrics: document.getElementById("lyrics").value.trim(),
                preset: document.getElementById("inspiration_style")?.value || "detailed",
            }),
        });

        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            throw new Error(err.message || `Interpret failed (${resp.status})`);
        }

        const data = await resp.json();
        if (data.status !== "ok") {
            throw new Error(data.message || "Interpret returned no result");
        }

        const interpretedCaption = data.interpreted_caption || "";
        captionEl.value = interpretedCaption;
        autoResizeTextarea(captionEl, 10);

        if (data.reasoning) {
            setStatus("complete", `Prompt interpreted — edit and generate when ready.`);
        } else {
            setStatus("error", "Interpretation produced no reasoning. Try again.");
        }
    } catch (e) {
        console.error("[interpret] error:", e);
        setStatus("error", e.message || "Interpret failed");
    } finally {
        btn.disabled = false;
        btn.style.color = "";
        btn.title = originalTitle;
    }
}

// ── Generate ──
document.getElementById("generate-btn").onclick = doGenerate;

async function doGenerate() {
    const caption = document.getElementById("caption").value.trim();
    if (!caption) { alert("Please enter a prompt."); return; }

    const btn = document.getElementById("generate-btn");
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Generating...';
    // Show placeholder result card in results area
    setStatus("generating", "Generating...");
    showGeneratingPlaceholder();

    // Upload audio files if present
    let srcAudioPath = null;
    let refAudioPath = null;
    try {
        const srcFile = document.getElementById("src-audio").files[0];
        if (srcFile) {
            const uf = new FormData();
            uf.append("file", srcFile);
            const sr = await fetch("/api/upload", { method: "POST", body: uf });
            if (sr.ok) { const sd = await sr.json(); srcAudioPath = sd.path; }
        }
    } catch {}
    try {
        const refFile = document.getElementById("ref-audio").files[0];
        if (refFile) {
            const uf = new FormData();
            uf.append("file", refFile);
            const sr = await fetch("/api/upload", { method: "POST", body: uf });
            if (sr.ok) { const sd = await sr.json(); refAudioPath = sd.path; }
        }
    } catch {}

    try {
        // Map UI mode names to backend task_type values.
        // Note: "Inspiration" → "extract", "Sound Stack" → "lego" (backend duration-locking set).
        const taskTypeMap = { Advanced: "text2music", Cover: "cover", Edit: "repaint", Inspiration: "inspiration", ["Sound Stack"]: "lego" };
        const taskType = taskTypeMap[currentMode] || currentMode.toLowerCase();
        const body = {
            caption,
            task_type: taskType,
            lyrics: document.getElementById("instrumental-toggle").checked ? "[Instrumental]" : (document.getElementById("lyrics").value.trim() || "[Instrumental]"),
            inference_steps: parseInt(document.getElementById("inference_steps").value),
            guidance_scale: parseFloat(document.getElementById("guidance_scale").value),
            seed: parseInt(document.getElementById("seed").value),
            batch_size: Math.max(1, Math.min(8, parseInt(document.getElementById("batch-custom").value) || 1)),
            duration: (document.getElementById("duration-custom").value.trim() ? parseFloat(document.getElementById("duration-custom").value) : null),
            bpm: getCustomValue("bpm") || null,
            keyscale: getCustomValue("key", "keyscale-select") || "",
            timesignature: getCustomValue("time", "timesignature-select") || "",
            thinking: document.getElementById("thinking").checked,
            use_random_seed: document.getElementById("use_random_seed").checked,
            workspace: currentWorkspace,
            audio_format: document.getElementById("output_format").value || "mp3",
            name: (document.getElementById("track-name")?.value?.trim() || null),
        };

        // Cover-mode specific params
        if (currentMode === "Cover") {
            body.audio_cover_strength = parseFloat(document.getElementById("audio_cover_strength").value);
            body.cover_noise_strength = isCoverNoiseCustom() ? parseFloat(document.getElementById("cover_noise_strength").value) : parseFloat(currentCoverNoisePreset);
        }

        // Inspiration-mode strength (uses audio_cover_strength under the hood)
        if (currentMode === "Inspiration") {
            body.audio_cover_strength = parseFloat(document.getElementById("inspiration_strength").value);
            const preset = document.getElementById("inspiration_style")?.value;
            if (preset && preset !== "detailed") body.inspiration_preset = preset;
        }

        // Edit/Sound Stack-mode specific params
        if (currentMode === "Edit" || currentMode === "Sound Stack") {
            body.repainting_start = parseFloat(document.getElementById("repainting_start").value) || 0;
            body.repainting_end = parseFloat(document.getElementById("repainting_end").value) || -1;
            body.repaint_mode = computeRepaintModeFromStrength(parseFloat(document.getElementById("repaint_strength").value) || 0.5);
            body.repaint_strength = parseFloat(document.getElementById("repaint_strength").value) || 0.5;
        }

        // Track selector for Inspiration/Sound Stack modes
        if (currentMode === "Inspiration" || currentMode === "Sound Stack") {
            const trackVal = document.getElementById("track-selector")?.value;
            if (trackVal) body.track_name = trackVal;
        }

        // Audio paths for non-text2music modes
        if (srcAudioPath) body.src_audio_path = srcAudioPath;
        if (refAudioPath) body.reference_audio_path = refAudioPath;

        // Inspiration and Sound Stack modes require source audio
        if (currentMode === "Inspiration" && !srcAudioPath) {
            setStatus("error", "Please upload a source audio file before generating in Inspiration mode.");
            return;
        }
        if (currentMode === "Sound Stack" && !srcAudioPath) {
            setStatus("error", "Please upload a source audio file before generating in Sound Stack mode.");
            return;
        }

        const resp = await fetch("/api/generate", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(body),
        });

        const data = await resp.json();
        if (data.status === "error") throw new Error(data.message);

        renderResults(data.audios, data.metadata, data.prompt || "", data._params, data.llm_interpretation);
        saveSettings();
        updateClearResultsVisibility();
        loadWorkspaces(); // refresh workspace counts / trigger UI update
        removeGeneratingPlaceholder();
    } catch (e) {
        setStatus("error", e.message || "Generation failed");
    } finally {
        btn.disabled = false;
        btn.textContent = "GENERATE";
        removeGeneratingPlaceholder();
        document.getElementById("status-bar").classList.remove("generating");
    }
}

// ── Generating placeholder ───────────────────────────────────────────────────

let _generatingPlaceholder = null; // keep reference to remove later

function showGeneratingPlaceholder() {
    const scroll = document.getElementById("results-scroll");
    if (!scroll) return;
    // Remove any existing empty state
    let es = document.getElementById("empty-state");
    if (es) es.remove();

    const accent = resultAccentClass();
    const card = document.createElement("div");
    card.className = "result-card" + (accent ? " " + accent : "") + " generating";
    card.id = "generating-placeholder";
    card.innerHTML = '<span class="spinner"></span> Generating...';
    // Prepend for newest-first sort; move to top if already present
    const firstCard = scroll.querySelector(".result-card");
    if (firstCard) {
        scroll.insertBefore(card, firstCard);
    } else {
        scroll.appendChild(card);
    }
    _generatingPlaceholder = card;
}

function removeGeneratingPlaceholder() {
    if (_generatingPlaceholder) {
        _generatingPlaceholder.remove();
        _generatingPlaceholder = null;
    }
}

// ── Results rendering ────────────────────────────────────────────────────────

function resultAccentClass() {
    switch (currentMode) {
        case "Simple": case "Advanced": case "Inspiration": return "accent-inspiration"; // teal — vibe reference + prompt
        case "Cover": return "accent-source";          // blue  — reference audio
        case "Edit": return "accent-edit";             // green — edit region
        case "Sound Stack": return "accent-stack";         // amber — layer building
        default: return "";
    }
}

function renderResults(audios, metadata, prompt, genParams, llmInterpretation) {
    const scroll = document.getElementById("results-scroll");
    const empty = document.getElementById("empty-state");
    if (empty) empty.remove();

    // Remove placeholder before adding real results
    removeGeneratingPlaceholder();

    // Capture scroll state BEFORE appending cards — the DOM mutation will change scrollHeight
    let userIsNearBottom = true;
    if (scroll) {
        const distanceFromTop = scroll.scrollTop;
        const maxScroll = scroll.scrollHeight - scroll.clientHeight;
        userIsNearBottom = maxScroll <= 0 || distanceFromTop < Math.max(maxScroll - 150, 0);
    }

    const accent = resultAccentClass();
    audios.forEach((audio, i) => {
        const card = document.createElement("div");
        card.className = "result-card" + (accent ? " " + accent : "");
        card.dataset.timestamp = audio.modified ? String(audio.modified * 1000) : String(Date.now());
        resultsStore.push(card);

        // Store full generation params on the card for reuse
        if (genParams) {
            try { card.dataset.params = JSON.stringify(genParams); } catch {}
        } else if (audio.params) {
            try { card.dataset.params = JSON.stringify(audio.params); } catch {}
        }

        const metaStr = [];
        if (metadata) {
            if (metadata.bpm) metaStr.push(`BPM: ${metadata.bpm}`);
            if (metadata.keyscale) metaStr.push(`Key: ${metadata.keyscale}`);
            if (metadata.duration) metaStr.push(`Dur: ${metadata.duration}s`);
        }

        // File info
        let fileSize = "";
        let fileDate = "";
        if (audio.size != null) {
            fileSize = Math.round(audio.size / 1024) + " KB";
        }
        if (audio.modified != null) {
            const d = new Date(audio.modified * 1000);
            fileDate = d.toLocaleDateString() + " " + d.toLocaleTimeString();
        }

        // Use prompt as label, truncated for display
        let label = "Track";
        const p = (audio.prompt && audio.prompt.trim()) ? audio.prompt : (prompt && prompt.trim()) ? prompt : "";
        // If a track name is provided in metadata, use it as the label instead of caption
        const displayName = metadata?.track_name || p;
        if (displayName) {
            const short = displayName.replace(/\s+/g, ' ').trim().slice(0, 60);
            label = '"' + short + (displayName.length > 60 ? '…"' : '"');
        }

        const showSrc = ["Cover", "Edit", "Inspiration", "Sound Stack"].includes(currentMode);
        const showRef = ["Cover", "Edit", "Sound Stack"].includes(currentMode);
        const auxBtns = [];
        if (showSrc) auxBtns.push('<button class="result-use-src" title="Use as source audio">&#9654;</button>');
        if (showRef) auxBtns.push('<button class="result-use-ref" title="Use as reference audio">&#9654;</button>');

        card.innerHTML = `
            <div class="result-header">
                <span class="result-key" title="${p.replace(/"/g, '&quot;')}">${label}</span>
                ${auxBtns.join('')}
                <button class="btn-sm result-delete" title="Delete">&#128465;</button>
                <button class="btn-sm result-reuse" title="Reuse prompt and settings">&#8635;</button>
            </div>
            <audio controls src="/api/audio?path=${encodeURIComponent(audio.path)}"></audio>
            ${llmInterpretation ? `<details class="llm-interpretation"><summary>LLM Interpretation</summary><pre>${llmInterpretation.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</pre></details>` : ''}
            ${metaStr.length || fileSize || fileDate ? `<div class="result-meta">${metaStr.map(m => '<span>' + m + '</span>').join('')}${fileSize ? '<span>' + fileSize + '</span>' : ''}${fileDate ? '<span>' + fileDate + '</span>' : ''}<span style="margin-left:auto;"><a class="btn-sm result-download" href="/api/audio?path=${encodeURIComponent(audio.path)}" download>Download</a></span></div>` : ''}
            ${!metaStr.length && !fileSize && !fileDate ? `<div class="result-actions"><a class="btn-sm" href="/api/audio?path=${encodeURIComponent(audio.path)}" download>Download</a></div>` : ''}`;

        card.querySelector(".result-delete").onclick = (e) => {
            e.stopPropagation();
            deleteResultFile(card, audio.path);
        };

        card.querySelector(".result-reuse").onclick = (e) => {
            e.stopPropagation();
            reuseResult(card);
        };

        if (showSrc) {
            card.querySelector(".result-use-src").onclick = (e) => {
                e.stopPropagation();
                useAsSource(audio.path);
            };
        }

        if (showRef) {
            card.querySelector(".result-use-ref").onclick = (e) => {
                e.stopPropagation();
                useAsReference(audio.path);
            };
        }

        scroll.appendChild(card);
    });

    // Smart scroll: only auto-scroll if user was near the top of results before we appended cards.
    // If they've scrolled down to review old tracks, show a toast instead.
    const rs = document.getElementById("results-scroll");
    if (userIsNearBottom && rs) {
        rs.scrollTop = rs.scrollHeight;
    } else if (!userIsNearBottom) {
        _showToast(audios.length + " new generation" + (audios.length > 1 ? "s" : "") + " ready", "Go to top");
    }

    // Stop any other audio when one starts playing
    rs.addEventListener("play", function(e) {
        if (e.target.tagName === "AUDIO") stopAllAudios(e.target);
    }, true);

    applyResultsSort();
    setStatus("ready", "Complete");
}

function reuseResult(card) {
    let params;
    try { params = JSON.parse(card.dataset.params || '{}'); } catch { return; }
    if (!params || !Object.keys(params).length) return;

    // Mode tab — restore first so the right controls become visible before populating values
    if (params.task_type) {
        const modeMap = {"text2music": "Advanced", "cover": "Cover", "repaint": "Edit", "extract": "Inspiration", "lego": "Sound Stack"};
        const mode = modeMap[params.task_type];
        if (mode) setMode(mode);
    }

    // Populate caption and lyrics
    const captionEl = document.getElementById("caption");
    if (captionEl && params.caption != null) captionEl.value = params.caption;

    const lyricsEl = document.getElementById("lyrics");
    if (lyricsEl && params.lyrics != null) {
        lyricsEl.value = params.lyrics;
        // Sync instrumental toggle
        const instrToggle = document.getElementById("instrumental-toggle");
        if (instrToggle) instrToggle.checked = false;
    }

    // Track name
    const trackNameEl = document.getElementById("track-name");
    if (trackNameEl && params.track_name) trackNameEl.value = params.track_name;

    // Settings
    if (params.inference_steps != null) document.getElementById("inference_steps").value = params.inference_steps;
    if (params.guidance_scale != null) document.getElementById("guidance_scale").value = params.guidance_scale;
    if (params.seed != null) document.getElementById("seed").value = params.seed;
    if ("use_random_seed" in params) document.getElementById("use_random_seed").checked = params.use_random_seed;
    if (params.batch_size != null) document.getElementById("batch-custom").value = params.batch_size;
    if (params.duration != null) document.getElementById("duration-custom").value = params.duration;

    // Dropdown-based custom values
    if (params.bpm != null) restoreDropdownValue("bpm", String(params.bpm));
    if (params.keyscale != null && String(params.keyscale).trim()) restoreDropdownValue("key", params.keyscale, "keyscale-select");
    if (params.timesignature != null && String(params.timesignature).trim()) restoreDropdownValue("time", params.timesignature, "timesignature-select");

    // Toggles and format
    if ("thinking" in params) document.getElementById("thinking").checked = params.thinking;
    if (params.audio_format) document.getElementById("output_format").value = params.audio_format;

    // Scroll to top so user sees the populated fields
    window.scrollTo({ top: 0, behavior: "smooth" });
}

// ── Use result audio as source / reference ──
async function useAsSource(audioPath) {
    try {
        const resp = await fetch(`/api/audio?path=${encodeURIComponent(audioPath)}`);
        if (!resp.ok) throw new Error("Failed to fetch audio");
        const blob = await resp.blob();
        const file = new File([blob], "source_audio.wav", { type: blob.type });
        const input = document.getElementById("src-audio");
        if (!input) return;
        const dt = new DataTransfer();
        dt.items.add(file);
        input.files = dt.files;
        input.dispatchEvent(new Event("change", { bubbles: true }));
    } catch (e) {
        console.error("useAsSource failed:", e);
        alert("Failed to load audio as source.");
    }
}

async function useAsReference(audioPath) {
    try {
        const resp = await fetch(`/api/audio?path=${encodeURIComponent(audioPath)}`);
        if (!resp.ok) throw new Error("Failed to fetch audio");
        const blob = await resp.blob();
        const file = new File([blob], "reference_audio.wav", { type: blob.type });
        const input = document.getElementById("ref-audio");
        if (!input) return;
        const dt = new DataTransfer();
        dt.items.add(file);
        input.files = dt.files;
        input.dispatchEvent(new Event("change", { bubbles: true }));
    } catch (e) {
        console.error("useAsReference failed:", e);
        alert("Failed to load audio as reference.");
    }
}

// ── Results sorting ──
const RESULTS_SORT_KEY = "acestep_results_sort";

function sortResults(order) {
    const scroll = document.getElementById("results-scroll");
    if (!scroll) return;
    // Only reorder actual result-card elements (skip empty state and header bar)
    const cards = Array.from(scroll.querySelectorAll(".result-card"));
    if (cards.length <= 1) return;

    cards.sort((a, b) => {
        const ta = parseInt(a.dataset.timestamp || "0", 10);
        const tb = parseInt(b.dataset.timestamp || "0", 10);
        return order === "asc" ? ta - tb : tb - ta;
    });
    cards.forEach(card => scroll.appendChild(card));

    // Update dropdown to match
    const sel = document.getElementById("results-sort");
    if (sel) sel.value = order;
    localStorage.setItem(RESULTS_SORT_KEY, order);
}

function loadResultsSortOrder() {
    return localStorage.getItem(RESULTS_SORT_KEY) || "desc";
}

function applyResultsSort() {
    sortResults(loadResultsSortOrder());
}

function setStatus(type, text) {
    const bar = document.getElementById("status-bar");
    const txt = document.getElementById("status-text");
    bar.className = "status" + (type === "ready" ? " ready" : type === "error" ? " error" : "");
    txt.textContent = text;
}

// ── Workspaces ──
let currentWorkspace = "__root__"; // default "My Experiments"

function renderWorkspaces(workspaces) {
    const bar = document.getElementById("workspace-bar");
    if (!bar) return;
    let html = workspaces.map(ws =>
        `<span class="ws-pill${ws.name === currentWorkspace ? ' active' : ''}" data-ws="${ws.name}">${ws.label}${ws.count != null ? ` (${ws.count})` : ''}</span>`
    ).join("");
    html += '<button class="ws-add" title="New workspace">+</button>';
    bar.innerHTML = html;

    bar.querySelectorAll(".ws-pill").forEach(pill => {
        pill.onclick = () => switchWorkspace(pill.dataset.ws);
    });
    bar.querySelector(".ws-add").onclick = createWorkspace;
}

async function loadWorkspaces() {
    try {
        const r = await fetch("/api/workspaces");
        const data = await r.json();
        renderWorkspaces(data.workspaces || []);
    } catch {}
}

function switchWorkspace(name) {
    currentWorkspace = name;
    localStorage.setItem("acestep_current_workspace", name);
    loadWorkspaces(); // re-render pills
    loadResultsForWorkspace();
}

async function createWorkspace() {
    const name = prompt("New workspace name:");
    if (!name || !name.trim()) return;
    try {
        const r = await fetch("/api/workspace/create", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({name: name.trim()}),
        });
        const data = await r.json();
        if (data.status === "error") { alert(data.message); return; }
        switchWorkspace(data.name);
    } catch (e) { alert("Failed to create workspace"); }
}

// ── Load results from disk for current workspace ──
async function loadResultsForWorkspace() {
    const scroll = document.getElementById("results-scroll");
    // Clear existing result cards (not empty state or clear button)
    resultsStore.forEach(card => card.remove());
    resultsStore.length = 0;

    try {
        const r = await fetch(`/api/results?workspace=${encodeURIComponent(currentWorkspace)}`);
        const data = await r.json();
        const results = data.results || [];

        // Remove empty state if visible
        let es = document.getElementById("empty-state");
        if (es) es.remove();

        if (results.length === 0) {
            // Ensure empty state is visible
            es = document.getElementById("empty-state");
            if (!es) {
                es = document.createElement("div");
                es.id = "empty-state";
                es.className = "empty-state";
                scroll.appendChild(es);
            }
            es.classList.remove("hidden");
            return;
        }

        results.forEach(audio => {
            const card = document.createElement("div");
            const accent = resultAccentClass();
            card.className = "result-card" + (accent ? " " + accent : "");
            card.dataset.timestamp = String(audio.modified * 1000);
            resultsStore.push(card);

            // Store sidecar meta on the card for reuse
            if (audio.meta) {
                try { card.dataset.params = JSON.stringify(audio.meta); } catch {}
            }

            const date = new Date(audio.modified * 1000);
            const sizeKB = Math.round(audio.size / 1024);
            // Use prompt from sidecar as label, fall back to filename
            let label = escFilename(audio.name);
            if (audio.meta && audio.meta.prompt) {
                const short = audio.meta.prompt.replace(/\s+/g, ' ').trim().slice(0, 60);
                label = '"' + short + (audio.meta.prompt.length > 60 ? '…"' : '"');
            }

            const showSrc = ["Cover", "Edit", "Inspiration", "Sound Stack"].includes(currentMode);
            const showRef = ["Cover", "Edit", "Sound Stack"].includes(currentMode);
            const auxBtns = [];
            if (showSrc) auxBtns.push('<button class="result-use-src" title="Use as source audio">&#9654;</button>');
            if (showRef) auxBtns.push('<button class="result-use-ref" title="Use as reference audio">&#9654;</button>');

            card.innerHTML = `
                <div class="result-header">
                    <span class="result-key">${label}</span>
                    ${auxBtns.join('')}
                    <button class="btn-sm result-delete" title="Delete">&#128465;</button>
                    <button class="btn-sm result-reuse" title="Reuse prompt and settings">&#8635;</button>
                </div>
                <audio controls src="/api/audio?path=${encodeURIComponent(audio.path)}"></audio>
                <div class="result-meta"><span>${sizeKB} KB</span><span>${date.toLocaleDateString()} ${date.toLocaleTimeString()}</span><a class="btn-sm result-download" href="/api/audio?path=${encodeURIComponent(audio.path)}" download style="margin-left:auto;">Download</a></div>`;

            card.querySelector(".result-delete").onclick = (e) => {
                e.stopPropagation();
                deleteResultFile(card, audio.path);
            };

            card.querySelector(".result-reuse").onclick = (e) => {
                e.stopPropagation();
                reuseResult(card);
            };

            if (showSrc) {
                card.querySelector(".result-use-src").onclick = (e) => {
                    e.stopPropagation();
                    useAsSource(audio.path);
                };
            }

            if (showRef) {
                card.querySelector(".result-use-ref").onclick = (e) => {
                    e.stopPropagation();
                    useAsReference(audio.path);
                };
            }

            scroll.appendChild(card);
        });
        // Stop any other audio when one starts playing
        scroll.addEventListener("play", function(e) {
            if (e.target.tagName === "AUDIO") stopAllAudios(e.target);
        }, true);
        applyResultsSort();
    } catch {}
}

function escFilename(name) {
    const d = document.createElement("div");
    d.textContent = name;
    return d.innerHTML;
}

// Stop all playing audio except the target when any one starts
function stopAllAudios(exceptEl) {
    document.querySelectorAll("#results-scroll audio").forEach(a => { if (a !== exceptEl && !a.paused) a.pause(); });
}

async function deleteResultFile(card, path) {
    let existing = card.querySelector(".confirm-inline");
    if (existing) return; // already showing

    const trashBtn = card.querySelector(".result-delete");
    if (!trashBtn) return;

    // Hide trash icon, show inline X/check buttons in its place
    trashBtn.style.display = "none";

    const container = document.createElement("div");
    container.className = "confirm-inline";
    container.innerHTML = `
        <button class="confirm-cancel" title="Cancel">&#10005;</button>
        <button class="confirm-ok" title="Delete">&#10003;</button>`;

    trashBtn.parentNode.insertBefore(container, trashBtn);

    container.querySelector(".confirm-cancel").onclick = () => {
        container.remove();
        trashBtn.style.display = "";
    };
    container.querySelector(".confirm-ok").onclick = async () => {
        container.remove();
        try {
            const r = await fetch("/api/result/delete", {
                method: "DELETE",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({path: path}),
            });
            if (r.ok) {
                card.remove();
                resultsStore.splice(resultsStore.indexOf(card), 1);
                updateClearResultsVisibility();
                loadWorkspaces(); // refresh counts
                if (resultsStore.length === 0) loadResultsForWorkspace(); // re-show empty state
            } else {
                alert("Failed to delete file");
            }
        } catch { alert("Failed to delete file"); }
    };
}

// ── Settings persistence (save after every generation, load on startup) ──
function getSettingsFields() {
    return {
        mode: currentMode,
        caption: document.getElementById("caption").value,
        lyrics: document.getElementById("lyrics").value,
        inference_steps: document.getElementById("inference_steps").value,
        guidance_scale: document.getElementById("guidance_scale").value,
        seed: document.getElementById("seed").value,
        use_random_seed: document.getElementById("use_random_seed").checked,
        batch_size: document.getElementById("batch-custom").value,
        duration: document.getElementById("duration-custom").value,
        bpm: getCustomValue("bpm"),
        keyscale: getCustomValue("key", "keyscale-select"),
        timesignature: getCustomValue("time", "timesignature-select"),
        thinking: document.getElementById("thinking").checked,
        instrumental: document.getElementById("instrumental-toggle").checked,
        cover_strength: document.getElementById("audio_cover_strength").value,
        cover_noise_preset: currentCoverNoisePreset,
        cover_noise_custom: isCoverNoiseCustom() ? parseFloat(document.getElementById("cover_noise_strength").value) : null,
        inspiration_strength: document.getElementById("inspiration_strength")?.value,
        inspiration_style: document.getElementById("inspiration_style")?.value,
        edit_preset: currentEditPreset,
        output_format: document.getElementById("output_format").value || "mp3",
        track_name: (document.getElementById("track-name")?.value?.trim() || null),
        repainting_start: document.getElementById("repainting_start")?.value,
        repainting_end: document.getElementById("repainting_end")?.value,
        repaint_strength: document.getElementById("repaint_strength")?.value,
        track_selector: document.getElementById("track-selector")?.value,
    };
}

function saveSettings() {
    try { localStorage.setItem(SETTINGS_KEY, JSON.stringify(getSettingsFields())); } catch {}
}

function loadSettings() {
    try {
        const s = JSON.parse(localStorage.getItem(SETTINGS_KEY));
        if (!s) return;
        // Restore mode (set first since it drives visibility)
        // Migrate old mode names to new Suno-parity naming.
        let savedMode = s.mode;
        if (savedMode === "Text2Music") savedMode = "Advanced";
        else if (savedMode === "Repaint") savedMode = "Edit";
        else if (savedMode === "Sample" || savedMode === "Isolate") savedMode = "Inspiration";
        else if (savedMode === "Lego") savedMode = "Sound Stack";
        currentMode = savedMode || "Advanced";
        document.querySelectorAll(".mode-pill").forEach(p => p.classList.toggle("active", p.textContent === currentMode));
        updateVisibility();
        // Restore fields
        if (s.caption != null) document.getElementById("caption").value = s.caption;
        if (s.lyrics != null) document.getElementById("lyrics").value = s.lyrics;
        if (s.inference_steps !== undefined) document.getElementById("inference_steps").value = s.inference_steps;
        if (s.guidance_scale !== undefined) document.getElementById("guidance_scale").value = s.guidance_scale;
        if (s.seed !== undefined) document.getElementById("seed").value = s.seed;
        if ("use_random_seed" in s) document.getElementById("use_random_seed").checked = s.use_random_seed;
        if (s.batch_size !== undefined) document.getElementById("batch-custom").value = s.batch_size;
        if (s.duration !== undefined) document.getElementById("duration-custom").value = s.duration;
        if (s.bpm !== undefined) restoreDropdownValue("bpm", s.bpm);
        if (s.keyscale !== undefined) restoreDropdownValue("key", s.keyscale, "keyscale-select");
        if (s.timesignature !== undefined) restoreDropdownValue("time", s.timesignature, "timesignature-select");
        if ("thinking" in s) document.getElementById("thinking").checked = s.thinking;
        if ("instrumental" in s && s.instrumental) {
            document.getElementById("instrumental-toggle").checked = true;
            if (!document.getElementById("lyrics").value.trim()) {
                document.getElementById("lyrics").value = "[Instrumental]";
            }
        }
        if (s.cover_strength !== undefined) document.getElementById("audio_cover_strength").value = s.cover_strength;
        if (s.cover_noise_preset !== undefined) {
            currentCoverNoisePreset = String(s.cover_noise_preset);
            const presetCard = document.querySelector(`.preset-card[data-value="${currentCoverNoisePreset}"]`);
            if (presetCard) highlightPreset(presetCard);
        }
        if (s.cover_noise_custom !== null && s.cover_noise_custom !== undefined) {
            if (s.cover_noise_custom !== null) {
                showCoverNoiseCustom(s.cover_noise_custom);
            } else {
                hideCoverNoiseCustom();
            }
        }
        if (s.inspiration_strength !== undefined) document.getElementById("inspiration_strength").value = s.inspiration_strength;
        if (s.inspiration_style !== undefined) document.getElementById("inspiration_style").value = s.inspiration_style;
        if (s.output_format !== undefined) document.getElementById("output_format").value = s.output_format;
        if (s.track_name != null) { const tnEl = document.getElementById("track-name"); if (tnEl && s.track_name) tnEl.value = s.track_name; }
        // Repainting controls
        if (s.repainting_start !== undefined) document.getElementById("repainting_start").value = s.repainting_start;
        if (s.repainting_end !== undefined) document.getElementById("repainting_end").value = s.repainting_end;
        if (s.repaint_strength !== undefined) {
            document.getElementById("repaint_strength").value = s.repaint_strength;
            const sv = document.getElementById("repaint-strength-val");
            if (sv) sv.textContent = s.repaint_strength;
        }
        // Edit strength preset
        if (s.edit_preset !== undefined) {
            currentEditPreset = s.edit_preset;
            const card = document.querySelector(`.strength-preset-card[data-value="${currentEditPreset}"]`);
            if (card) selectEditPreset(card);
        }
        // Track selector
        if (s.track_selector !== undefined) {
            const tsEl = document.getElementById("track-selector");
            if (tsEl && tsEl.querySelector(`option[value="${s.track_selector}"]`)) {
                tsEl.value = s.track_selector;
            }
        }
        // Restore sort order and apply to existing cards
        const sortOrder = localStorage.getItem(RESULTS_SORT_KEY) || "desc";
        const sortSel = document.getElementById("results-sort");
        if (sortSel) sortSel.value = sortOrder;
    } catch {}
}

// ── Clear results ──
document.getElementById("clear-results-btn").onclick = () => {
    const scroll = document.getElementById("results-scroll");
    resultsStore.forEach(card => card.remove());
    resultsStore.length = 0;
    document.getElementById("clear-results-btn").style.display = "none";
    const emptyClone = document.getElementById("empty-state").cloneNode(true);
    emptyClone.classList.remove("hidden");
    scroll.appendChild(emptyClone);
};

function updateClearResultsVisibility() {
    document.getElementById("clear-results-btn").style.display = resultsStore.length > 0 ? "" : "none";
}

// ── GPU info on load ──
fetch("/api/config").then(r => r.json()).then(data => {
    if (data.gpu) {
        document.getElementById("gpu-info").textContent = data.gpu + " | " + (data.gpu_memory_gb || "?") + "GB VRAM | Tier " + (data.tier || "?");
    } else {
        document.getElementById("gpu-info").textContent = "GPU info unavailable";
    }
}).catch(() => {
    document.getElementById("gpu-info").textContent = "Could not detect GPU";
});

// ── Render LM model selector on load (both modal and accordion) ──────────────
renderLMModelSelector("lm-list-modal");
renderLMModelSelector("lm-list");

// ── Check model status on load ──
fetch("/api/config").then(r => r.json()).then(data => {
    if (data.ready) {
        setStatus("ready", "Ready");
        document.getElementById("generate-btn").disabled = false;
        modelsReady = true;
        llmReady = data.llm_available || false;
        const link = document.getElementById("reinit-link");
        if (link) link.classList.remove("hidden");
    }
}).catch(() => {});

// ── Load saved settings on startup ──
loadSettings();

// ── Cover noise preset cards ──
function highlightPreset(card) {
    document.querySelectorAll(".preset-card").forEach(c => c.classList.remove("selected"));
    card.classList.add("selected");
}

(function() {
    const container = document.getElementById("cover-noise-presets");
    if (!container) return;
    container.addEventListener("click", (e) => {
        const card = e.target.closest(".preset-card");
        if (!card) return;
        currentCoverNoisePreset = card.dataset.value;
        highlightPreset(card);
    });
})();

function isCoverNoiseCustom() {
    return document.getElementById("cover-noise-custom") && !document.getElementById("cover-noise-custom").classList.contains("hidden");
}

function toggleCoverNoiseCustom() {
    const slider = document.getElementById("cover_noise_strength");
    if (!slider) return;
    // Set slider to current preset value before showing
    slider.value = currentCoverNoisePreset;
    showCoverNoiseCustom(parseFloat(currentCoverNoisePreset));
}

function showCoverNoiseCustom(value) {
    const presetsDiv = document.getElementById("cover-noise-presets");
    const customDiv = document.getElementById("cover-noise-custom");
    if (!customDiv) return;
    if (presetsDiv) presetsDiv.classList.add("hidden");
    customDiv.classList.remove("hidden");
    document.getElementById("cover_noise_strength").value = value;
    // Swap toggle buttons: hide Custom, show Return to Presets
    document.getElementById("cover-noise-custom-btn").classList.add("hidden");
}

function hideCoverNoiseCustom() {
    const presetsDiv = document.getElementById("cover-noise-presets");
    const customDiv = document.getElementById("cover-noise-custom");
    if (customDiv) customDiv.classList.add("hidden");
    if (presetsDiv) presetsDiv.classList.remove("hidden");
    // Swap toggle buttons: show Custom, hide Return to Presets
    document.getElementById("cover-noise-custom-btn").classList.remove("hidden");
}

function resetCoverNoiseToPresets() {
    hideCoverNoiseCustom();
}

// ── Edit strength preset cards ──
function selectEditPreset(card) {
    document.querySelectorAll(".strength-preset-card").forEach(c => c.classList.remove("selected"));
    card.classList.add("selected");
    currentEditPreset = card.dataset.value;
    const slider = document.getElementById("repaint_strength");
    if (slider) {
        slider.value = currentEditPreset;
        const sv = document.getElementById("repaint-strength-val");
        if (sv) sv.textContent = currentEditPreset;
    }
}

(function() {
    const container = document.getElementById("edit-strength-presets");
    if (!container) return;
    container.addEventListener("click", (e) => {
        const card = e.target.closest(".strength-preset-card");
        if (!card) return;
        selectEditPreset(card);
    });
})();

// ── Waveform region selector ────────────────────────────────────────────────
let _waveformBuffer = null;
let _waveformDuration = 0;
let _waveformReady = false;

function decodeAudioFile(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = async (e) => {
            try {
                const ctx = new (window.AudioContext || window.webkitAudioContext)();
                const audioBuffer = await ctx.decodeAudioData(e.target.result);
                resolve({ buffer: audioBuffer, context: ctx });
            } catch (err) { reject(err); }
        };
        reader.onerror = () => reject(new Error("Failed to read file"));
        reader.readAsArrayBuffer(file);
    });
}

function renderWaveform() {
    const canvas = document.getElementById("waveform-canvas");
    if (!canvas || !_waveformReady) return;
    const ctx = canvas.getContext("2d");
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);
    const W = rect.width, H = rect.height;
    const data = _waveformBuffer.getChannelData(0);
    const step = Math.max(1, Math.floor(data.length / W));
    const mid = H / 2;

    // Background waveform (dim)
    ctx.fillStyle = "rgba(148,163,184,0.5)";
    for (let i = 0; i < W; i++) {
        let max = 0;
        for (let j = 0; j < step; j++) {
            const idx = i * step + j;
            if (idx < data.length) max = Math.max(max, Math.abs(data[idx]));
        }
        const h = max * H * 0.85;
        ctx.fillRect(i, mid - h / 2, 1, h);
    }

    // Selected region overlay
    const startSec = parseFloat(document.getElementById("repainting_start").value) || 0;
    const startPx = (startSec / _waveformDuration) * W;
    const endVal = document.getElementById("repainting_end").value;
    let endSec = parseFloat(endVal);
    if (endSec <= 0 || isNaN(endSec)) endSec = _waveformDuration;
    const endPx = Math.min((endSec / _waveformDuration) * W, W - 14);

    ctx.fillStyle = "rgba(124,204,255,0.08)";
    ctx.fillRect(startPx, 0, endPx - startPx, H);

    // Region edge lines
    ctx.strokeStyle = "rgba(124,204,255,0.35)";
    ctx.lineWidth = 1;
    [startPx, endPx].forEach(x => {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, H);
        ctx.stroke();
    });

    updateWaveformHandles();
}

function updateWaveformHandles() {
    const canvas = document.getElementById("waveform-canvas");
    if (!canvas) return;
    const W = canvas.getBoundingClientRect().width;
    const startSec = parseFloat(document.getElementById("repainting_start").value);
    const endVal = document.getElementById("repainting_end").value;
    let endSec = parseFloat(endVal);

    const startHandle = document.getElementById("waveform-start-handle");
    const endHandle = document.getElementById("waveform-end-handle");

    // Show handles only when values are valid (not -1)
    if (!isNaN(startSec) && startSec >= 0) {
        startHandle.style.display = "block";
        startHandle.style.left = Math.max(0, (startSec / _waveformDuration) * W - 3) + "px";
    } else {
        startHandle.style.display = "none";
    }

    if (!isNaN(endSec) && endSec > 0) {
        endHandle.style.display = "block";
        const clampedEnd = Math.min(endSec, _waveformDuration);
        endHandle.style.right = Math.max(0, W - (clampedEnd / _waveformDuration * W)) + 3 + "px";
    } else {
        endHandle.style.display = "none";
    }
}

// ── Waveform play/pause from selected region ────────────────────────────────
let _waveformAudio = null;
let _isWaveformPlaying = false;
let _stopTimeout = null;

function toggleWaveformPlay() {
    if (_isWaveformPlaying) {
        stopWaveformPlay();
    } else {
        startWaveformPlay();
    }
}

function startWaveformPlay() {
    const srcFile = document.getElementById("src-audio")?.files[0];
    const refFile = document.getElementById("ref-audio")?.files[0];
    const file = srcFile || refFile;
    if (!file) return;

    // Stop any existing playback
    stopWaveformPlay();

    const url = URL.createObjectURL(file);
    _waveformAudio = new Audio(url);
    _waveformAudio.addEventListener("ended", () => {
        _isWaveformPlaying = false;
        updatePlayButton();
        URL.revokeObjectURL(url);
    });

    const startSec = parseFloat(document.getElementById("repainting_start").value) || 0;
    const endVal = document.getElementById("repainting_end").value;
    let endSec = parseFloat(endVal);
    if (endSec <= 0 || isNaN(endSec)) endSec = _waveformDuration;

    _waveformAudio.currentTime = Math.max(0, startSec);
    // Use audioContext to stop at end time since HTML5 Audio has no built-in end
    scheduleWaveformStop();
    _waveformAudio.play();
    _isWaveformPlaying = true;
    updatePlayButton();
}

function scheduleWaveformStop() {
    if (!_waveformAudio) return;
    const endVal = document.getElementById("repainting_end").value;
    let endSec = parseFloat(endVal);
    if (endSec <= 0 || isNaN(endSec)) endSec = _waveformDuration;

    const remaining = Math.max(0.01, endSec - _waveformAudio.currentTime);
    setTimeout(() => {
        if (_waveformAudio && _isWaveformPlaying) {
            _waveformAudio.pause();
            _waveformAudio.currentTime = 0;
            URL.revokeObjectURL(_waveformAudio.src);
            _waveformAudio = null;
            _isWaveformPlaying = false;
            updatePlayButton();
        }
    }, remaining * 1000);
}

function stopWaveformPlay() {
    if (_waveformAudio) {
        clearTimeout(_stopTimeout);
        _waveformAudio.pause();
        URL.revokeObjectURL(_waveformAudio.src);
        _waveformAudio = null;
    }
    _isWaveformPlaying = false;
    updatePlayButton();
}

function updatePlayButton() {
    const btn = document.getElementById("waveform-play-btn");
    if (!btn) return;
    btn.innerHTML = _isWaveformPlaying ? "&#9646;&#9646; Pause" : "&#9654; Play";
}

function initWaveformDrag() {
    const canvas = document.getElementById("waveform-canvas");
    if (!canvas) return;
    let dragging = null;

    function pxToTime(px) {
        const W = canvas.getBoundingClientRect().width;
        return Math.max(0, Math.min(_waveformDuration, (px / W) * _waveformDuration));
    }

    function snap(v) { return Math.round(v * 10) / 10; }

    canvas.addEventListener("mousedown", (e) => {
        if (!_waveformReady) return;
        const rect = canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const W = rect.width;
        const startSec = parseFloat(document.getElementById("repainting_start").value) || 0;
        const endVal = document.getElementById("repainting_end").value;
        let endSec = parseFloat(endVal);
        if (endSec <= 0 || isNaN(endSec)) endSec = _waveformDuration;
        const startPx = (startSec / _waveformDuration) * W;
        const endPx = (endSec / _waveformDuration) * W;

        if (Math.abs(x - startPx) < 14) { dragging = "start"; }
        else if (Math.abs(x - endPx) < 14) { dragging = "end"; }
    });

    document.addEventListener("mousemove", (e) => {
        if (!dragging || !_waveformReady) return;
        const t = pxToTime(e.clientX - canvas.getBoundingClientRect().left);
        const startEl = document.getElementById("repainting_start");
        const endEl = document.getElementById("repainting_end");

        if (dragging === "start") {
            startEl.value = snap(t);
            renderWaveform();
        } else if (dragging === "end") {
            endEl.value = snap(Math.max(t, (parseFloat(startEl.value) || 0) + 0.5));
            renderWaveform();
        }
    });

    document.addEventListener("mouseup", () => { dragging = null; });
}

function resetWaveformRegion() {
    if (!_waveformReady) return;
    document.getElementById("repainting_start").value = "0.0";
    document.getElementById("repainting_end").value = "-1";
    renderWaveform();
}

async function updateWaveform() {
    const container = document.getElementById("waveform-container");
    if (!container) return;
    const srcFile = document.getElementById("src-audio")?.files[0];
    const refFile = document.getElementById("ref-audio")?.files[0];
    const file = srcFile || refFile;
    if (!file) { container.classList.add("hidden"); return; }

    try {
        const result = await decodeAudioFile(file);
        _waveformBuffer = result.buffer;
        _waveformDuration = result.buffer.sampleRate > 0 ? result.buffer.duration : 0;
        _waveformReady = true;

        // Default to inner 50% selection when no explicit values set yet
        const startEl = document.getElementById("repainting_start");
        const endEl = document.getElementById("repainting_end");
        if (startEl.value === "-1" && endEl.value === "-1") {
            const quarter = _waveformDuration * 0.25;
            startEl.value = String(quarter);
            endEl.value = String(_waveformDuration - quarter);
        }

        container.classList.remove("hidden");
        // Defer render to next frame so hidden→shown transition completes
        requestAnimationFrame(() => requestAnimationFrame(renderWaveform));
    } catch {
        _waveformReady = false;
        container.classList.add("hidden");
    }
}

// ── Draggable divider between controls and results ──
(function() {
    const divider = document.getElementById("content-divider");
    if (!divider) return;
    let isDragging = false;

    // Restore saved width
    const saved = localStorage.getItem(DIVIDER_KEY);
    if (saved) {
        const w = Math.max(200, Math.min(1200, parseInt(saved, 10)));
        document.getElementById("controls").style.width = w + "px";
    }

    divider.addEventListener("mousedown", (e) => {
        isDragging = true;
        divider.classList.add("dragging");
        e.preventDefault();
    });

    document.addEventListener("mousemove", (e) => {
        if (!isDragging) return;
        const controls = document.getElementById("controls");
        const newWidth = Math.max(200, Math.min(1200, e.clientX));
        controls.style.width = newWidth + "px";
    });

    document.addEventListener("mouseup", () => {
        if (!isDragging) return;
        isDragging = false;
        divider.classList.remove("dragging");
        const w = parseInt(document.getElementById("controls").style.width, 10);
        localStorage.setItem(DIVIDER_KEY, String(w));
    });
})();

// ── Waveform drag init + file input listeners ────────────────────────────────
initWaveformDrag();
["src-audio", "ref-audio"].forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    el.addEventListener("change", () => {
        if (currentMode === "Edit") updateWaveform();
    });
});

// ── Restore current workspace from localStorage ──
const savedWs = localStorage.getItem("acestep_current_workspace");
if (savedWs && savedWs !== "undefined") {
    currentWorkspace = savedWs;
} else {
    currentWorkspace = "__root__";
    localStorage.setItem("acestep_current_workspace", "__root__");
}

// ── Load workspaces and results on startup ──
loadWorkspaces();
loadResultsForWorkspace();

// ── Toast notifications ──

function _showToast(message, actionLabel) {
    const container = document.getElementById("toast-container");
    if (!container) return;

    // Remove any existing toast (coalesce rapid fire)
    const existing = container.querySelector(".toast");
    if (existing) existing.remove();

    const toast = document.createElement("div");
    toast.className = "toast";
    toast.innerHTML = `
        <span class="toast-text">${message}</span>
        ${actionLabel ? `<button class="toast-go">${actionLabel}</button>` : ""}`;

    if (actionLabel) {
        toast.querySelector(".toast-go").onclick = () => {
            toast.remove();
            _scrollResultsToTop();
        };
    }

    container.appendChild(toast);
    _toastCountdown = 5;

    setTimeout(() => {
        if (toast.parentNode) {
            toast.classList.add("hiding");
            setTimeout(() => toast.remove(), 200);
        }
    }, 4500);
}

function _scrollResultsToTop() {
    const rs = document.getElementById("results-scroll");
    if (rs) rs.scrollTo({ top: 0, behavior: "smooth" });
}

// ── Render prompt library chips from localStorage ──
renderPromptLibrary();
"""
