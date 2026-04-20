"""Custom AceStep UI — HTML body template.

Exports:
    FRONTEND_BODY_HTML: The <body> content for the main interface page.

See Also:
    custom_interface.py      - Backend core (init, generate, CLI)
    custom_interface_css.py  - Stylesheet (STYLES_CSS)
    custom_interface_js.py   - Client-side JavaScript (CLIENT_JS)
    custom_interface_routes.py - API routes + FastAPI app
"""

FRONTEND_BODY_HTML = r"""
<!-- ── Initialization modal (first run only) ── -->
<div class="modal-overlay hidden" id="init-modal">
    <div class="modal-box">
        <div class="modal-title">Initialize Models</div>
        <div class="modal-subtitle">Configure and initialize the models before generating music. This modal will disappear once initialization starts.</div>

        <div class="field">
            <label class="section-label">DiT Model</label>
            <select id="init-config_path">
                <option value="acestep-v15-sft" selected>acestep-v15-sft (recommended)</option>
                <option value="acestep-v15-turbo">acestep-v15-turbo</option>
                <option value="acestep-v15-xl-turbo">acestep-v15-xl-turbo</option>
            </select>
        </div>

        <div class="field">
            <label class="section-label">Device</label>
            <select id="init-device">
                <option value="auto" selected>Auto-detect</option>
                <option value="cuda">CUDA (NVIDIA GPU)</option>
                <option value="mps">MPS (Apple Silicon)</option>
                <option value="xpu">Intel XPU</option>
                <option value="cpu">CPU only</option>
            </select>
        </div>

        <div class="field">
            <label class="section-label">Quantization</label>
            <select id="init-quantization">
                <option value="" selected>None (FP16)</option>
                <option value="nf4">NF4 (4-bit)</option>
                <option value="fp8">FP8</option>
                <option value="int8">INT8</option>
            </select>
        </div>

        <div class="toggle-row">
            <span class="toggle-label">Compile model</span>
            <label class="toggle"><input type="checkbox" id="init-compile_model" checked><span class="slider"></span></label>
        </div>
        <div class="toggle-row">
            <span class="toggle-label">Offload DiT to CPU</span>
            <label class="toggle"><input type="checkbox" id="init-offload_dit_to_cpu"><span class="slider"></span></label>
        </div>

        <!-- LM section -->
        <div style="margin-top:8px; padding-top:6px; border-top:1px solid var(--border);">
            <div class="section-label" style="margin-bottom:4px;">Language Model</div>
            <div id="lm-list-modal" style="display:flex;flex-direction:column;gap:4px;margin-top:4px;"></div>
        </div>

        <div class="field">
            <label class="section-label">LM Backend</label>
            <select id="init-lm_backend">
                <option value="vllm" selected>vLLM (fast)</option>
                <option value="pt">PyTorch (fallback)</option>
            </select>
        </div>
        <div class="toggle-row">
            <span class="toggle-label">Initialize LM</span>
            <label class="toggle"><input type="checkbox" id="init-init_llm" checked><span class="slider"></span></label>
        </div>

        <div id="modal-gpu-info" style="font-size:11px;color:var(--text-2);padding:6px 0;font-family:'JetBrains Mono',monospace;">Detecting...</div>

        <div class="modal-footer">
            <button id="modal-skip-btn" class="modal-skip-btn">Skip</button>
            <button id="modal-init-btn">INITIALIZE</button>
        </div>
    </div>
</div>

<div class="app">
    <!-- Top bar -->
    <div class="topbar">
        <span class="brand">ONUS</span>
        <div class="workspace-bar" id="workspace-bar"></div>
        <div class="status" id="status-bar"><span class="dot"></span><span id="status-text">Not initialized</span></div>
    </div>

    <!-- Content: controls left + results right -->
    <div class="content">
        <!-- Left: Controls -->
        <div class="controls" id="controls">
            <!-- ── Mode selector ── -->
            <div class="section-label" style="margin-top:4px;">Mode</div>
            <div class="mode-pills" id="mode-pills"></div>

            <!-- Language selector -->
            <div class="field" style="margin-bottom:8px;">
                <label class="section-label" for="lang-select">Language</label>
                <select id="lang-select" style="width:100%;box-sizing:border-box;">
                    <option value="">Auto-detect</option>
                    <option value="en" selected>English</option>
                    <option value="zh">Chinese</option>
                    <option value="ja">Japanese</option>
                    <option value="ko">Korean</option>
                    <option value="fr">French</option>
                    <option value="de">German</option>
                    <option value="es">Spanish</option>
                    <option value="it">Italian</option>
                    <option value="pt">Portuguese</option>
                    <option value="ru">Russian</option>
                    <option value="hi">Hindi</option>
                    <option value="ar">Arabic</option>
                    <option value="he">Hebrew</option>
                    <option value="nl">Dutch</option>
                    <option value="pl">Polish</option>
                    <option value="ro">Romanian</option>
                    <option value="sv">Swedish</option>
                    <option value="tr">Turkish</option>
                </select>
            </div>

            <!-- Prompt -->
            <div class="field">
                <div style="display:flex;align-items:center;margin-bottom:4px;">
                    <label class="section-label" title="Describe the music you want to generate. Include genre, mood, instrumentation, and style details for better results. The LLM planner will expand this into detailed generation instructions." style="margin:0;">Prompt / Caption</label>
                </div>
                <div class="caption-row">
                    <textarea id="caption" class="theme-prompt caption-textarea" rows="4" placeholder="Describe the music you want to generate..." oninput="autoResizeTextarea(this, 10)"></textarea>
                    <button id="interpret-btn" class="btn-interpret hidden" title="Interpret prompt with selected style preset (Inspiration mode only)" onclick="handleInterpret()">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18h6"/><path d="M10 22h4"/></svg>
                    </button>
                </div>
                <input type="text" id="track-name" placeholder="Track name (optional)" style="font-size:12px;width:100%;box-sizing:border-box;">
                <div class="prompt-lib-bar" id="prompt-library-row">
                    <div class="pinned-prompts" id="pinned-prompts"></div>
                    <select id="prompt-lib-dropdown" onchange="handlePromptLibSelect(this.value)">
                        <option value="">-- Load Prompt --</option>
                    </select>
                </div>
                <button id="lib-manage-btn-inline" class="btn-sm" style="font-size:10px;padding:3px 8px;margin-top:2px;" onclick="openPromptLibModal()">MANAGE</button>
            </div>

            <!-- Prompt Library modal -->
            <div class="modal-backdrop hidden" id="prompt-lib-modal">
                <div class="prompt-lib-dialog">
                    <h3 style="margin:0 0 12px 0;font-size:14px;color:var(--text-0);">Prompt Library</h3>
                    <input type="text" id="lib-name" placeholder="Save as name..." style="width:100%;box-sizing:border-box;">
                    <label class="pin-toggle"><input type="checkbox" id="lib-pin-checkbox"> Pin this prompt (show as quick-access button)</label>
                    <div class="prompt-lib-list" id="prompt-lib-list"></div>
                    <div class="prompt-lib-actions">
                        <button id="lib-save-btn">SAVE CURRENT</button>
                        <button id="lib-close-btn">CLOSE</button>
                    </div>
                </div>
            </div>

            <!-- Lyrics (shown for Advanced/Cover/Edit — hidden for Inspiration/Sound Stack) -->
            <div class="field hidden" id="lyrics-field">
                <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px;">
                    <label class="section-label" title="Enter lyrics for vocal generation, or leave as [Instrumental] for instrumental music. In Edit mode, this defines what replaces the masked region of the source audio." style="margin:0;">Lyrics</label>
                    <div style="display:flex;align-items:center;gap:4px;">
                        <label class="toggle"><input type="checkbox" id="instrumental-toggle"><span class="slider"></span></label>
                        <span style="font-size:11px;color:var(--text-2);white-space:nowrap;">Instrumental</span>
                    </div>
                </div>
                <textarea id="lyrics" class="theme-prompt" rows="4" placeholder="[Instrumental] or enter lyrics..." oninput="onLyricsInput()"></textarea>
            </div>

            <!-- Source audio (shown for Cover/Edit/Inspiration/Sound Stack) -->
            <div class="field field-source hidden" id="src-audio-field">
                <label class="section-label source-label" title="The source audio to use as a base. In Cover mode, its timbre provides context hints. In Edit mode, specific regions are masked and regenerated based on your prompt. In Inspiration mode, the entire track's vibe is used as a style reference for new generation." style="margin:0;">Source Audio</label>
                <div style="display:flex;align-items:center;gap:6px;">
                    <input type="file" id="src-audio" accept="audio/*" style="font-size:12px;flex:1;">
                    <button class="clear-btn source-clear" onclick="clearFileInput('src-audio')" title="Clear file">×</button>
                </div>
            </div>

            <!-- Reference audio (shown for Cover/Edit/Sound Stack) -->
            <div class="field field-source hidden" id="ref-audio-field">
                <label class="section-label source-label" title="Audio whose timbre/style will be transferred to the generated output. The model extracts vocal characteristics and uses them as conditioning throughout generation. Works best with clear, clean audio." style="margin:0;">Reference Audio</label>
                <div style="display:flex;align-items:center;gap:6px;">
                    <input type="file" id="ref-audio" accept="audio/*" style="font-size:12px;flex:1;">
                    <button class="clear-btn source-clear" onclick="clearFileInput('ref-audio')" title="Clear file">×</button>
                </div>
            </div>

            <!-- Cover strength (shown for Cover mode) -->
            <div class="field hidden" id="cover-controls-field">
                <label class="section-label">Cover Settings</label>
                <div class="field-row">
                    <span style="font-size:11px;color:var(--text-2);width:90px;" title="What fraction of diffusion steps use the source audio's structure as guidance. 1.0 = all steps reference source (faithful cover). Lower values switch partway to text-only guidance, giving more creative freedom. 0.75 is a good starting point." style="margin:0;">Cover Strength</span>
                    <input type="range" id="audio_cover_strength" min="0" max="1" step="0.05" value="0.75" style="flex:1;" oninput="document.getElementById('cover-strength-val').textContent=this.value">
                    <span id="cover-strength-val" style="font-size:11px;color:var(--text-1);width:32px;text-align:right;font-family:'JetBrains Mono',monospace;">0.75</span>
                </div>
                <label class="section-label">Creative Intent</label>
                <div style="font-size:10px;color:var(--text-2);margin-bottom:6px;" title="Left (amber) = prompt/style influence, Right (blue) = source melody retention. Higher cover_noise_strength = more of the original tune retained.">Prompt vs Source Balance</div>
                <div class="cover-noise-presets" id="cover-noise-presets">
                    <label class="preset-card" data-value="0.0">
                        <input type="radio" name="cover_noise_preset" value="0.0" checked style="display:none;">
                        <span class="preset-label">Pure Style Transfer</span>
                        <span class="preset-stars"><span class="stars-prompt" title="Prompt influence (style/lyrics)">★★★★★</span> <span class="stars-source" title="Source melody retention">☆☆☆☆☆</span></span>
                    </label>
                    <label class="preset-card" data-value="0.15">
                        <input type="radio" name="cover_noise_preset" value="0.15" style="display:none;">
                        <span class="preset-label">Partial Style Change</span>
                        <span class="preset-stars"><span class="stars-prompt" title="Prompt influence (style/lyrics)">★★★★☆</span> <span class="stars-source" title="Source melody retention">★☆☆☆☆</span></span>
                    </label>
                    <label class="preset-card" data-value="0.35">
                        <input type="radio" name="cover_noise_preset" value="0.35" style="display:none;">
                        <span class="preset-label">Melodic Remix</span>
                        <span class="preset-stars"><span class="stars-prompt" title="Prompt influence (style/lyrics)">★★★☆☆</span> <span class="stars-source" title="Source melody retention">★★★☆☆</span></span>
                    </label>
                    <label class="preset-card" data-value="0.55">
                        <input type="radio" name="cover_noise_preset" value="0.55" style="display:none;">
                        <span class="preset-label">Balanced Cover</span>
                        <span class="preset-stars"><span class="stars-prompt" title="Prompt influence (style/lyrics)">★★☆☆☆</span> <span class="stars-source" title="Source melody retention">★★★★☆</span></span>
                    </label>
                    <label class="preset-card" data-value="0.75">
                        <input type="radio" name="cover_noise_preset" value="0.75" style="display:none;">
                        <span class="preset-label">Faithful Cover</span>
                        <span class="preset-stars"><span class="stars-prompt" title="Prompt influence (style/lyrics)">★☆☆☆☆</span> <span class="stars-source" title="Source melody retention">★★★★★</span></span>
                    </label>
                    <label class="preset-card" data-value="0.85">
                        <input type="radio" name="cover_noise_preset" value="0.85" style="display:none;">
                        <span class="preset-label">Near-Identity</span>
                        <span class="preset-stars"><span class="stars-prompt" title="Prompt influence (style/lyrics)">★☆☆☆☆</span> <span class="stars-source" title="Source melody retention">★★★★★</span></span>
                    </label>
                </div>
                <button id="cover-noise-custom-btn" class="btn-sm cover-noise-toggle-btn" style="margin-top:6px;font-size:10px;padding:2px 12px;" onclick="toggleCoverNoiseCustom()">Custom</button>
                <div class="cover-noise-custom hidden" id="cover-noise-custom">
                    <div class="field-row" style="margin-top:4px;">
                        <span style="font-size:10px;color:var(--text-2);width:70px;margin:0;">Custom Value</span>
                        <input type="range" id="cover_noise_strength" min="0" max="1" step="0.05" value="0.0" style="flex:1;" oninput="document.getElementById('custom-noise-val').textContent=this.value">
                        <span id="custom-noise-val" style="font-size:10px;color:var(--text-1);width:28px;text-align:right;font-family:'JetBrains Mono',monospace;">0.0</span>
                    </div>
                    <button class="btn-sm cover-noise-toggle-btn hidden" style="margin-top:4px;font-size:10px;padding:2px 12px;" onclick="resetCoverNoiseToPresets()">Return to Presets</button>
                </div>
            </div>

            <!-- Edit / Sound Stack layer region controls (shown for Edit/Sound Stack modes) -->
            <div class="field hidden" id="repaint-controls-field">
                <label class="section-label" id="repaint-section-label">Edit Region Controls</label>
                <!-- Waveform region selector -->
                <div id="waveform-container" class="waveform-container hidden">
                    <canvas id="waveform-canvas"></canvas>
                </div>
                <div class="field-row waveform-times-row">
                    <button class="waveform-play-btn" onclick="toggleWaveformPlay()" title="Play selected region" id="waveform-play-btn">&#9654; Play</button>
                    <span style="font-size:10px;">|</span>
                    <input type="number" id="repainting_start" value="-1" step="0.1" min="-1" title="Start time (seconds, -1 = 25% mark)">
                    <span style="font-size:10px;color:var(--text-3);">—</span>
                    <input type="number" id="repainting_end" value="-1" step="0.1" min="-1" title="End time (seconds, -1 = 75% mark)">
                    <button class="waveform-reset-btn" onclick="resetWaveformRegion()" title="Reset to full audio">Reset</button>
                </div>
                <!-- Strength preset cards -->
                <div class="edit-strength-presets" id="edit-strength-presets">
                    <label class="strength-preset-card preset-conservative" data-value="0.2">
                        <span class="preset-label">Subtle Blend</span>
                        <span class="preset-desc">Keeps most of original audio, slight changes</span>
                    </label>
                    <label class="strength-preset-card selected preset-balanced" data-value="0.5">
                        <span class="preset-label">Moderate Blend</span>
                        <span class="preset-desc">Balanced between source and prompt</span>
                    </label>
                    <label class="strength-preset-card preset-full-replace" data-value="1.0">
                        <span class="preset-label">Full Replace</span>
                        <span class="preset-desc">Max regeneration, prompt drives output</span>
                    </label>
                </div>
                <div class="field-row">
                    <span style="font-size:11px;color:var(--text-2);width:90px;" title="How much of the region gets regenerated. 0 = minimal change, 1 = full regeneration." style="margin:0;">Strength</span>
                    <input type="range" id="repaint_strength" min="0" max="1" step="0.05" value="0.5" style="flex:1;" oninput="document.getElementById('repaint-strength-val').textContent=this.value; onRepaintStrengthChange()">
                    <span id="repaint-strength-val" style="font-size:11px;color:var(--text-1);width:32px;text-align:right;font-family:'JetBrains Mono',monospace;">0.5</span>
                </div>
            </div>

            <!-- Track/Focus selector (shown for Inspiration/Sound Stack modes) -->
            <div class="field hidden" id="track-select-field">
                <label class="section-label" title="Which layer to generate. 'All / Auto' lets the model decide generically. Specific instruments tell the model which one to add on top of your source audio." style="margin:0;" id="track-selector-label">Focus</label>
                <select id="track-selector" style="width:100%;font-size:12px;" onchange="saveSettings()">
                    <option value="">All / Auto</option>
                    <option value="woodwinds">Woodwinds</option>
                    <option value="brass">Brass</option>
                    <option value="fx">Effects (FX)</option>
                    <option value="synth">Synthesizer</option>
                    <option value="strings">Strings</option>
                    <option value="percussion">Percussion</option>
                    <option value="keyboard">Keyboard</option>
                    <option value="guitar">Guitar</option>
                    <option value="bass">Bass</option>
                    <option value="drums">Drums</option>
                    <option value="backing_vocals">Backing Vocals</option>
                    <option value="vocals">Lead Vocals</option>
                </select>
            </div>

            <!-- Inspiration strength (shown for Inspiration mode) -->
            <div class="field hidden" id="inspiration-controls-field">
                <label class="section-label" title="Choose how the LLM transforms your caption before generation. Each style guides the model differently." style="margin:0;">Style</label>
                <select id="inspiration_style" onchange="updateInspirationStylePreview(); saveSettings();" style="width:100%;font-size:12px;margin-bottom:8px;">
                    <option value="detailed">Detailed Description (default)</option>
                    <option value="lyrics">Write Lyrics</option>
                    <option value="conductor">Conductor Notes</option>
                    <option value="mood">Mood & Atmosphere</option>
                </select>
                <!-- Style preview: shows what the selected preset will do -->
                <div id="inspiration-style-preview" style="font-size:10px;color:var(--text-2);margin-bottom:8px;padding:6px 8px;background:var(--bg-2);border-radius:4px;line-height:1.4;display:none;"></div>
                <label class="section-label" title="Controls how much the source audio influences the output. High (0.8–1.0) = subtle reimagining, stays close to source timbre. Medium (0.4–0.7) = balance of source and prompt. Low (0.0–0.3) = prompt dominates, source provides only a style hint." style="margin:0;">Inspiration Strength</label>
                <div class="field-row">
                    <span id="inspiration-label-left" style="font-size:10px;color:#f59e0b;width:45px;text-align:right;margin-right:2px;">Prompt</span>
                    <input type="range" id="inspiration_strength" min="0" max="1" step="0.05" value="0.5" style="flex:1;--prompt-color:#f59e0b;--source-color:#3b82f6;" oninput="updateInspirationStrength(this)">
                    <span id="inspiration-label-right" style="font-size:10px;color:#3b82f5;width:45px;text-align:left;margin-left:2px;">Source</span>
                    <span id="inspiration-strength-val" style="font-size:11px;color:var(--text-1);width:36px;text-align:right;font-family:'JetBrains Mono',monospace;">0.50</span>
                </div>
            </div>

            <!-- Custom mode extras -->
            <div class="field hidden" id="custom-fields">
                <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;">
                    <label class="section-label" title="These parameters override auto-detection. Leave blank to let the model infer automatically." style="margin:0;">Custom Parameters</label>
                    <div style="display:flex;gap:4px;">
                        <button id="randomize-btn" class="btn-sm" style="font-size:10px;padding:2px 8px;" title="Randomize BPM, Key, Time Signature, Duration, Steps, Guidance, and Seed">RANDOMIZE</button>
                        <button id="reset-btn" class="btn-sm" style="font-size:10px;padding:2px 8px;" title="Reset all parameters to their original defaults">RESET</button>
                    </div>
                </div>
                <div class="custom-grid">
                    <div class="field-row">
                        <span style="font-size:11px;color:var(--text-2);width:50px;" title="Beats per minute. Controls tempo of generated music. Leave blank for auto-detection." style="margin:0;">BPM</span>
                        <select id="bpm-select" class="compact" onchange="toggleCustomInput('bpm', this.value)">
                            <option value="" selected>Auto</option>
                            <option value="60">60</option>
                            <option value="80">80</option>
                            <option value="100">100</option>
                            <option value="120">120</option>
                            <option value="130">130</option>
                            <option value="140">140</option>
                            <option value="150">150</option>
                            <option value="160">160</option>
                            <option value="180">180</option>
                            <option value="custom">Custom...</option>
                        </select>
                        <input type="number" id="bpm-custom" class="compact" style="display:none;width:70px;" placeholder="BPM">
                    </div>
                    <div class="field-row">
                        <span style="font-size:11px;color:var(--text-2);width:50px;" title="Musical key. Determines the pitch center of the generated music. Leave blank for auto-detection." style="margin:0;">Key</span>
                        <select id="keyscale-select" class="compact" onchange="toggleCustomInput('key', this.value)">
                            <option value="" selected>Auto</option>
                            <option value="C major">C major</option>
                            <option value="C minor">C minor</option>
                            <option value="D major">D major</option>
                            <option value="D minor">D minor</option>
                            <option value="E major">E major</option>
                            <option value="E minor">E minor</option>
                            <option value="F major">F major</option>
                            <option value="F minor">F minor</option>
                            <option value="G major">G major</option>
                            <option value="G minor">G minor</option>
                            <option value="A major">A major</option>
                            <option value="A minor">A minor</option>
                            <option value="B major">B major</option>
                            <option value="B minor">B minor</option>
                            <option value="custom">Custom...</option>
                        </select>
                        <input type="text" id="key-custom" class="compact" style="display:none;width:70px;" placeholder="Key">
                    </div>
                    <div class="field-row">
                        <span style="font-size:11px;color:var(--text-2);width:50px;" title="Time signature. Number of beats per measure and which note gets the beat (e.g., 4/4 = four quarter notes). Leave blank for auto-detection." style="margin:0;">Sig</span>
                        <select id="timesignature-select" class="compact" onchange="toggleCustomInput('time', this.value)">
                            <option value="" selected>Auto</option>
                            <option value="2/4">2/4</option>
                            <option value="3/4">3/4</option>
                            <option value="4/4">4/4</option>
                            <option value="5/4">5/4</option>
                            <option value="6/8">6/8</option>
                            <option value="7/4">7/4</option>
                            <option value="custom">Custom...</option>
                        </select>
                        <input type="text" id="time-custom" class="compact" style="display:none;width:70px;" placeholder="Sig">
                    </div>
                    <div class="field-row">
                        <span style="font-size:11px;color:var(--text-2);width:50px;" title="Target duration in seconds. Leave blank for auto-detection based on prompt/lyrics length. Longer durations require more diffusion steps for quality." style="margin:0;">Dur</span>
                        <input type="number" id="duration-custom" class="compact" style="width:70px;" placeholder="auto" value="">
                        <span style="font-size:11px;color:var(--text-2);">s</span>
                    </div>
                    <div class="field-row">
                        <span style="font-size:11px;color:var(--text-2);width:50px;" title="Number of parallel generations to produce. Each uses the same prompt but different seeds (unless fixed seed is used). Batch 2 = 2x generation time." style="margin:0;">Batch</span>
                        <input type="number" id="batch-custom" class="compact" style="width:70px;" value="1" min="1" max="8">
                    </div>
                </div>
            </div>

            <!-- Advanced params (collapsed by default) -->
            <div class="section-header" onclick="toggleAccordion('adv-body', 'adv-chevron')">
                <span class="section-label">Advanced</span>
                <span class="section-chevron" id="adv-chevron">&#9654;</span>
            </div>
            <div class="accordion-body collapsed" id="adv-body">
                <div class="adv-grid">
                    <div class="field-row">
                        <span style="font-size:11px;color:var(--text-2);width:50px;" title="Number of diffusion steps. More steps = higher quality but slower generation. 8 is a good default; try 16-32 for fine details." style="margin:0;">Steps</span>
                        <input type="number" id="inference_steps" value="8" min="1" max="100" class="compact" style="width:70px;">
                    </div>
                    <div class="field-row">
                        <span style="font-size:11px;color:var(--text-2);width:50px;" title="Classifier-free guidance scale. Controls how closely the output follows your prompt. Higher = more faithful to text, but can sound harsh. 5-8 is typical range." style="margin:0;">Guidance</span>
                        <input type="number" id="guidance_scale" value="7.0" step="0.1" min="0" max="20" class="compact" style="width:70px;">
                    </div>
                    <div class="field-row">
                        <span style="font-size:11px;color:var(--text-2);width:50px;" title="Random seed for reproducibility. Use -1 (with Random checked) for a new seed each time. Same seed + same prompt = identical output." style="margin:0;">Seed</span>
                        <input type="number" id="seed" value="-1" class="compact" style="width:70px;">
                        <label style="font-size:11px;color:var(--text-1);display:flex;align-items:center;gap:4px;"><input type="checkbox" id="use_random_seed" checked> Random</label>
                    </div>
                    <div class="field-row">
                        <span style="font-size:11px;color:var(--text-2);width:50px;" title="Output audio format. FLAC = lossless (largest files). WAV = uncompressed PCM. MP3 = compressed (smallest files, slight quality tradeoff)." style="margin:0;">Format</span>
                        <select id="output_format" class="compact" style="width:70px;">
                            <option value="flac">FLAC (lossless)</option>
                            <option value="wav">WAV (uncompressed)</option>
                            <option value="mp3" selected>MP3 (compressed)</option>
                        </select>
                    </div>
                </div>
            </div>

            <!-- Runtime toggles -->
            <div class="toggle-row">
                <span class="toggle-label" title="Enable LLM reasoning to plan lyrics, structure, and metadata before generation. Uncheck for faster text2music-only mode with no planning overhead." style="margin:0;">Think (chain of thought)</span>
                <label class="toggle"><input type="checkbox" id="thinking" checked><span class="slider"></span></label>
            </div>

            <!-- Generate button -->
            <button id="generate-btn" disabled>GENERATE</button>

            <!-- Reinitialize link (appears after init) -->
            <a class="reinit-link hidden" id="reinit-link" onclick="triggerReinit()" title="Change model, device, or quantization settings">Reinitialize Models</a>
        </div>

        <!-- Draggable divider -->
        <div class="divider" id="content-divider"></div>

        <!-- Right: Results + Training -->
        <div class="results-pane" id="results-pane">
            <div class="results-scroll" id="results-scroll">
                <div class="empty-state" id="empty-state">No generations yet.<br>Prompt and click Generate.</div>
                <div class="results-header-bar">
                    <select id="results-sort" onchange="sortResults(this.value)">
                        <option value="desc">Newest first</option>
                        <option value="asc">Oldest first</option>
                    </select>
                    <button id="clear-results-btn" style="padding:4px 10px;font-size:11px;background:var(--bg-3);color:var(--text-2);border:1px solid var(--border);border-radius:6px;cursor:pointer;">CLEAR ALL RESULTS</button>
                </div>
            </div>

            <!-- Toast notification container -->
            <div class="toast-container" id="toast-container"></div>

            <!-- Training section (at bottom, collapsed by default) -->
            <div class="training-section">
                <div class="section-header" onclick="toggleAccordion('training-body', 'training-chevron')">
                    <span class="section-label">Training</span>
                    <span class="section-chevron" id="training-chevron">&#9654;</span>
                </div>
                <div class="training-body collapsed" id="training-body" style="max-height: 0;">
                    <div style="padding: 8px 0;">
                        <div class="training-tabs">
                            <button class="training-tab active" onclick="switchTrainTab('dataset')">Dataset</button>
                            <button class="training-tab" onclick="switchTrainTab('lora')">LoRA</button>
                            <button class="training-tab" onclick="switchTrainTab('lokr')">LoKr</button>
                        </div>

                        <!-- Dataset builder tab -->
                        <div class="training-panel active" id="train-dataset">
                            <div class="train-field">
                                <label class="section-label">Dataset Directory</label>
                                <input type="text" class="train-input wide" placeholder="/path/to/dataset/folder" id="dataset_dir">
                            </div>
                            <div class="train-row">
                                <button class="btn-sm" onclick="alert('Scan: specify a dataset directory first')">Scan</button>
                                <span style="font-size:11px;color:var(--text-2);" id="scan-result"></span>
                            </div>
                            <div class="train-field">
                                <label class="section-label">Label Pattern</label>
                                <input type="text" class="train-input wide" placeholder="{caption}" id="label_pattern">
                            </div>
                        </div>

                        <!-- LoRA training tab -->
                        <div class="training-panel" id="train-lora">
                            <div class="train-row">
                                <div class="train-field">
                                    <label class="section-label">Rank</label>
                                    <input type="number" class="train-input" value="16" min="1" max="512" id="lora_rank">
                                </div>
                                <div class="train-field">
                                    <label class="section-label">Alpha</label>
                                    <input type="number" class="train-input" value="8" min="1" id="lora_alpha">
                                </div>
                            </div>
                            <div class="train-row">
                                <div class="train-field">
                                    <label class="section-label">Epochs</label>
                                    <input type="number" class="train-input" value="100" min="1" id="lora_epochs">
                                </div>
                                <div class="train-field">
                                    <label class="section-label">LR</label>
                                    <input type="text" class="train-input" value="1e-4" id="lora_lr">
                                </div>
                            </div>
                            <div class="train-row">
                                <button class="btn-sm" onclick="alert('Training: configure dataset first')">Start Training</button>
                                <span style="font-size:11px;color:var(--text-2);" id="lora-status"></span>
                            </div>
                        </div>

                        <!-- LoKr training tab -->
                        <div class="training-panel" id="train-lokr">
                            <div class="train-row">
                                <div class="train-field">
                                    <label class="section-label">Rank</label>
                                    <input type="number" class="train-input" value="16" min="1" id="lokr_rank">
                                </div>
                                <div class="train-field">
                                    <label class="section-label">Factor A</label>
                                    <input type="number" class="train-input" value="8" min="1" id="lokr_factor_a">
                                </div>
                            </div>
                            <div class="train-row">
                                <div class="train-field">
                                    <label class="section-label">Epochs</label>
                                    <input type="number" class="train-input" value="100" min="1" id="lokr_epochs">
                                </div>
                                <div class="train-field">
                                    <label class="section-label">LR</label>
                                    <input type="text" class="train-input" value="1e-4" id="lokr_lr">
                                </div>
                            </div>
                            <div class="train-row">
                                <button class="btn-sm" onclick="alert('Training: configure dataset first')">Start Training</button>
                                <span style="font-size:11px;color:var(--text-2);" id="lokr-status"></span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            </div>
        </div>
    </div>
</div>
"""
