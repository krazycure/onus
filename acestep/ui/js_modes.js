const MODES = ["Advanced", "Cover", "Edit", "Inspiration", "Sound Stack", "Complete"];
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

// ── Mode pills ────────────────────────────────────────────────────────────────

// Pure base model detection (mirrors upstream Gradio `is_pure_base_model`).
// "base" must appear as a delimited token AND neither "sft" nor "turbo" may be present.
function isPureBaseModel(configPath) {
    const p = configPath.toLowerCase();
    return /(^|[\/._-])base($|[\/._-])/.test(p) && !/sft/.test(p) && !/turbo/.test(p);
}

const MODE_TITLES = {
    "Advanced": "Full manual control over caption, lyrics, BPM, key, and all generation parameters. Use when you know exactly what you want.",
    "Cover": "Generate new music using a reference audio for timbre/style transfer. Upload reference + source audio to control what gets generated.",
    "Edit": "Open your source audio in an editor to modify specific regions. Choose intensity (Subtle Blend/Moderate Blend/Full Replace) and set start/end times. Prompt drives the regenerated content.",    "Inspiration": "Use source audio as a vibe reference to generate entirely new music in the same style. Choose a Focus (instrument/stem) and Style, then write a prompt for what you want.",
    "Sound Stack": "Start with a vocal or instrument layer and build a full track on top of it. Add drums, bass, harmonies — anything you can imagine. Upload your starting layer as reference audio.",
    "Complete": "Upload a single vocal or instrument track. The model generates the full accompaniment around it — drums, bass, harmonies, everything else.",
};

function renderModePills() {
    const pillsEl = document.getElementById("mode-pills");
    if (!pillsEl) return;
    pillsEl.innerHTML = "";

    // Complete mode only available with pure base DiT model (per upstream Gradio).
    const isBase = isPureBaseModel(document.getElementById("init-config_path")?.value || "");
    const visibleModes = isBase ? MODES : MODES.filter(m => m !== "Complete");

    // If current mode is Complete but not available, switch to Advanced.
    if (currentMode === "Complete" && !isBase) {
        currentMode = "Advanced";
    }

    for (const mode of visibleModes) {
        const btn = document.createElement("button");
        btn.className = "mode-pill" + (mode === currentMode ? " active" : "");
        btn.textContent = mode;
        if (MODE_TITLES[mode]) btn.title = MODE_TITLES[mode];
        btn.onclick = () => setMode(mode);
        pillsEl.appendChild(btn);
    }

    // Re-sync visibility for the new pill set.
    updateVisibility();
}

// Initial render on page load (reads default from DOM).
renderModePills();

// Watch config_path changes — re-render pills when user switches models via reinit modal.
const initConfigSelect = document.getElementById("init-config_path");
if (initConfigSelect) initConfigSelect.addEventListener("change", renderModePills);

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
    const showLyrics = currentMode !== "Inspiration" && currentMode !== "Sound Stack" && currentMode !== "Complete";
    const showSrcAudio = ["Cover", "Edit", "Inspiration", "Sound Stack", "Complete"].includes(currentMode);
    const showRefAudio = ["Cover", "Edit", "Sound Stack"].includes(currentMode);
    const showCoverControls = currentMode === "Cover";
    const showInspirationControls = currentMode === "Inspiration";
    const showCustom = currentMode === "Advanced" || currentMode === "Inspiration";
    const showEdit = currentMode === "Edit" || currentMode === "Sound Stack";
    const showTrackSelect = currentMode === "Inspiration" || currentMode === "Sound Stack" || currentMode === "Complete";
    const showCompleteClasses = currentMode === "Complete";

    document.getElementById("lyrics-field").classList.toggle("hidden", !showLyrics);
    document.getElementById("src-audio-field").classList.toggle("hidden", !showSrcAudio);
    document.getElementById("ref-audio-field").classList.toggle("hidden", !showRefAudio);
    document.getElementById("complete-track-classes-field").classList.toggle("hidden", !showCompleteClasses);
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

    // Dynamic labels for track selector in Sound Stack vs Inspiration vs Complete modes
    const trackSelectorLabel = document.getElementById("track-selector-label");
    if (currentMode === "Sound Stack") {
        if (trackSelectorLabel) trackSelectorLabel.textContent = "Layer";
    } else if (currentMode === "Inspiration" && trackSelectorLabel) {
        trackSelectorLabel.textContent = "Focus";
    } else if (currentMode === "Complete" && trackSelectorLabel) {
        trackSelectorLabel.textContent = "Instruments";
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

    // Dynamic labels for track selector in Sound Stack vs Inspiration vs Complete modes (tooltip)
    const trackSelector = document.getElementById("track-selector");
    if (currentMode === "Sound Stack" && trackSelector) {
        trackSelector.title = "Which layer to generate. 'All / Auto' lets the model decide generically. Specific instruments tell the model which one to add to your source audio.";
    } else if (currentMode === "Inspiration" && trackSelector) {
        trackSelector.title = "Which instrument/stem to isolate. 'All / Auto' lets the model decide generically. Specific instruments tell the model which one to generate from your source audio.";
    } else if (currentMode === "Complete" && trackSelector) {
        trackSelector.title = "Instruments to include in the accompaniment. 'All / Auto' lets the model decide. Specific instruments add them on top of your source audio.";
    }

    // Render Complete mode track classes checkboxes
    if (currentMode === "Complete") {
        renderCompleteTrackClasses();
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

// ── Complete mode: track classes checkbox group ────────────────────────────────
const COMPLETE_TRACK_CLASSES = ["vocals", "backing_vocals", "guitar", "bass", "drums", "percussion", "keyboard", "strings", "synth", "woodwinds", "brass", "fx"];

function renderCompleteTrackClasses() {
    const container = document.getElementById("complete-track-classes");
    if (!container) return;
    // Only populate once
    if (container.dataset.rendered === "1") return;
    container.dataset.rendered = "1";
    container.innerHTML = COMPLETE_TRACK_CLASSES.map(name =>
        `<label class="track-class-chip"><input type="checkbox" value="${name}"> ${name}</label>`
    ).join("");
}

function getCompleteTrackClasses() {
    const checked = document.querySelectorAll("#complete-track-classes input[type=checkbox]:checked");
    return Array.from(checked).map(cb => cb.value);
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

