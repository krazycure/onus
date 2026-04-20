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
