// ── Prompt Library event listeners ──
document.getElementById("lib-save-btn").onclick = saveToPromptLibrary;
document.getElementById("lib-close-btn").onclick = dismissPromptLibModal;
document.getElementById("lib-manage-btn-inline").onclick = openPromptLibModal;
document.getElementById("prompt-lib-modal").onclick = (e) => {
    if (e.target.id === "prompt-lib-modal") dismissPromptLibModal();
};

// ── DiT model availability + on-demand download ────────────────────────────────
let _ditModelsInstalled = new Set(); // track which models are installed

function showDitDownloadArea() {
    const area = document.getElementById("dit-download-area");
    if (area) area.classList.remove("hidden");
}
function hideDitDownloadArea() {
    const area = document.getElementById("dit-download-area");
    if (area) area.classList.add("hidden");
}
function setDitDownloadProgress(pct, text) {
    const bar = document.getElementById("dit-download-bar");
    const status = document.getElementById("dit-download-status");
    if (bar) bar.style.width = pct + "%";
    if (status) status.textContent = text;
}

// Check selected DiT model and show download UI if missing.
function checkDitModelAndShowDownload() {
    const select = document.getElementById("init-config_path");
    if (!select) return;
    const modelId = select.value;

    // If fetch hasn't completed yet, conservatively show download for non-default models.
    if (!_ditFetchDone && _ditModelsInstalled.size === 0) {
        if (modelId !== "acestep-v15-sft") {
            showDitDownloadArea();
            setDitDownloadProgress(0, "Checking availability...");
        } else {
            hideDitDownloadArea();
        }
        return;
    }

    if (_ditModelsInstalled.has(modelId)) {
        hideDitDownloadArea();
        return;
    }
    showDitDownloadArea();
    setDitDownloadProgress(0, "Ready to download: " + modelId);
}

// Download a DiT model on demand.
async function downloadDitModel(modelName) {
    const btn = document.getElementById("dit-download-btn");
    if (btn) btn.disabled = true;

    try {
        setDitDownloadProgress(10, "Starting download...");
        const resp = await fetch("/api/dit-model/download", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({model: modelName}),
        });

        if (!resp.ok) {
            const err = await resp.json().catch(() => ({message: "Download failed"}));
            setDitDownloadProgress(0, "Error: " + (err.message || "download failed"));
            return false;
        }

        const data = await resp.json();
        if (data.status === "complete") {
            _ditModelsInstalled.add(modelName);
            setDitDownloadProgress(100, "Done! — " + data.message);
            setTimeout(hideDitDownloadArea, 2000);
            return true;
        } else {
            setDitDownloadProgress(0, "Error: " + (data.message || "unknown error"));
            return false;
        }
    } catch (e) {
        setDitDownloadProgress(0, "Error: " + e.message);
        return false;
    } finally {
        if (btn) btn.disabled = false;
    }
}

// Fetch installed DiT models on page load.
let _ditFetchDone = false;
fetch("/api/dit-models/available").then(r => r.json()).then(data => {
    for (const m of data.models) {
        if (m.installed) _ditModelsInstalled.add(m.id);
    }
    _ditFetchDone = true;
    checkDitModelAndShowDownload();
}).catch(() => {}); // If API unavailable, assume all installed — graceful degradation.

// Wire config_path select change → show download area if needed.
(function() {
    const select = document.getElementById("init-config_path");
    if (select) select.addEventListener("change", checkDitModelAndShowDownload);
})();

// Wire download button click.
(function() {
    const btn = document.getElementById("dit-download-btn");
    if (!btn) return;
    btn.onclick = async () => {
        const select = document.getElementById("init-config_path");
        if (!select) return;
        await downloadDitModel(select.value);
    };
})();

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
        const taskTypeMap = { Advanced: "text2music", Cover: "cover", Edit: "repaint", Inspiration: "inspiration", ["Sound Stack"]: "lego", Complete: "complete" };
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

        // Track selector for Inspiration/Sound Stack/Complete modes
        if (currentMode === "Inspiration" || currentMode === "Sound Stack" || currentMode === "Complete") {
            const trackVal = document.getElementById("track-selector")?.value;
            if (trackVal) body.track_name = trackVal;
        }

        // Complete mode: collect selected track classes
        if (currentMode === "Complete") {
            const trackClassesEl = document.querySelectorAll("#complete-track-classes input[type=checkbox]:checked");
            const trackClasses = Array.from(trackClassesEl).map(cb => cb.value);
            if (trackClasses.length > 0) body.complete_track_classes = trackClasses;
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
        case "Complete": return "accent-track"; // purple — single track → full accompaniment
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
        const modeMap = {"text2music": "Advanced", "cover": "Cover", "repaint": "Edit", "extract": "Inspiration", "lego": "Sound Stack", "complete": "Complete"};
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

