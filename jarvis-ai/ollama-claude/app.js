/* ===========================
   J.A.R.V.I.S. v4 — Core AI System
   Powered by Ollama (local) + Claude API
   =========================== */

(function () {
    'use strict';

    // ===========================
    // Configuration
    // ===========================
    const CONFIG = {
        particleCount: 60,
        waveformBars: 44,
        maxConversationHistory: 30,
        ollamaBaseUrl: 'http://localhost:11434',
        claudeApiBaseUrl: 'https://api.anthropic.com/v1/messages',
        claudeApiVersion: '2023-06-01',
        systemPrompt: `You are J.A.R.V.I.S. (Just A Rather Very Intelligent System), the legendary AI assistant created by Tony Stark in the Iron Man universe. You are now serving a new user with the same level of intelligence, wit, and sophistication.

Your personality:
- Highly intelligent, articulate, and professional
- Dry British wit — subtle humor, never forced
- Respectful — you call the user "sir" or "ma'am" occasionally (not every message)
- Confident but not arrogant
- Proactive — you anticipate needs and offer suggestions
- Concise — you give clear, direct answers without unnecessary verbosity

Key behaviors:
- Always provide accurate, helpful information
- When asked about time/date, use the current time provided in the system context
- For calculations, show your work briefly
- For code questions, provide clean, well-commented code
- Reference Stark Industries, the Avengers, or Iron Man lore naturally when appropriate
- If you don't know something, say so honestly — don't make things up
- Format responses cleanly — use line breaks for readability
- Keep responses focused and not overly long unless detail is requested

Current context:
- Current date and time: {{DATETIME}}
- You are running as a web-based AI assistant interface
- You have voice input/output capabilities
- The user can see a futuristic HUD interface around the chat`,
    };

    // ===========================
    // DOM References
    // ===========================
    const $ = (s) => document.querySelector(s);
    const $$ = (s) => document.querySelectorAll(s);

    const DOM = {
        // Chat
        chatMessages: $('#chatMessages'),
        chatContainer: $('#chatContainer'),
        userInput: $('#userInput'),
        sendBtn: $('#sendBtn'),
        voiceBtn: $('#voiceBtn'),
        inputWrapper: $('#inputWrapper'),

        // Reactor
        arcReactor: $('#arcReactor'),
        reactorStatus: $('#reactorStatus'),
        waveformCanvas: $('#waveformCanvas'),

        // Background
        particleField: $('#particleField'),

        // HUD
        currentTime: $('#currentTime'),
        currentDate: $('#currentDate'),
        latencyValue: $('#latencyValue'),
        statusText: $('#statusText'),
        mainPulseDot: $('#mainPulseDot'),

        // Panels
        activityFeed: $('#activityFeed'),
        totalMessages: $('#totalMessages'),
        totalTokens: $('#totalTokens'),
        sessionTime: $('#sessionTime'),
        memoryUsage: $('#memoryUsage'),
        memoryBar: $('#memoryBar'),
        aiEngineStatus: $('#aiEngineStatus'),
        aiEngineBar: $('#aiEngineBar'),
        claudeProcess: $('#claudeProcess'),
        clearChatBtn: $('#clearChatBtn'),

        // Settings
        settingsBtn: $('#settingsBtn'),
        settingsOverlay: $('#settingsOverlay'),
        settingsClose: $('#settingsClose'),
        settingsSaveBtn: $('#settingsSaveBtn'),
        settingsCancelBtn: $('#settingsCancelBtn'),
        apiKeyInput: $('#apiKeyInput'),
        ollamaUrlInput: $('#ollamaUrlInput'),
        backendSelect: $('#backendSelect'),
        apiStatus: $('#apiStatus'),
        toggleKeyVisibility: $('#toggleKeyVisibility'),
        modelSelect: $('#modelSelect'),
        voiceSelect: $('#voiceSelect'),
        voiceRate: $('#voiceRate'),
        voiceRateValue: $('#voiceRateValue'),
        voicePitch: $('#voicePitch'),
        voicePitchValue: $('#voicePitchValue'),
        autoSpeak: $('#autoSpeak'),
        continuousListen: $('#continuousListen'),

        // Footer
        modelLabel: $('#modelLabel'),
        networkStatus: $('#networkStatus'),
        aiBadge: $('#aiBadge'),
        micStatus: $('#micStatus'),
    };

    // ===========================
    // Application State
    // ===========================
    let savedModel = localStorage.getItem('jarvis_model');
    if (!savedModel || savedModel.includes('gemini') || savedModel.includes('1.5')) savedModel = 'qwen2.5:7b';

    // Backend: 'ollama' or 'claude'
    let savedBackend = localStorage.getItem('jarvis_backend') || 'ollama';

    // Auto-detect deployed environment — switch to Claude if not on localhost
    const isDeployed = !['localhost', '127.0.0.1', ''].includes(location.hostname);
    if (isDeployed && savedBackend === 'ollama') {
        savedBackend = 'claude';
    }

    const state = {
        apiKey: localStorage.getItem('jarvis_claude_key') || '',
        ollamaUrl: localStorage.getItem('jarvis_ollama_url') || 'http://localhost:11434',
        backend: savedBackend,
        model: savedModel,
        isProcessing: false,
        isListening: false,
        isSpeaking: false,
        isStreaming: false,
        recognition: null,
        synthesis: window.speechSynthesis,
        voices: [],
        waveformCtx: null,
        conversationHistory: [],
        messageCount: 0,
        tokenCount: 0,
        sessionStart: Date.now(),
        uptime: 0,
        settings: {
            autoSpeak: localStorage.getItem('jarvis_autospeak') !== 'false',
            continuousListen: localStorage.getItem('jarvis_continuous') === 'true',
            voiceRate: parseFloat(localStorage.getItem('jarvis_voice_rate') || '1.0'),
            voicePitch: parseFloat(localStorage.getItem('jarvis_voice_pitch') || '1.0'),
            voiceName: localStorage.getItem('jarvis_voice_name') || 'auto',
        },
        spaceHeld: false,
    };

    // ===========================
    // Initialize
    // ===========================
    function init() {
        setupParticles();
        setupWaveform();
        setupClock();
        setupSessionTimer();
        setupEventListeners();
        setupVoiceRecognition();
        setupSpeechVoices();
        loadSettings();
        checkAPIConnection();
        bootSequence();
    }

    // ===========================
    // Boot Sequence
    // ===========================
    function bootSequence() {
        const bootLogs = [
            ['System boot sequence initiated', ''],
            ['Loading neural network weights...', ''],
            ['Voice recognition module loaded', ''],
            ['Speech synthesis calibrated', ''],
            ['HUD renderer initialized', ''],
            ['Waveform visualizer online', ''],
        ];

        bootLogs.forEach((log, i) => {
            setTimeout(() => addActivityLog(log[0], log[1]), i * 300);
        });

        setTimeout(() => {
            if (isDeployed && state.backend === 'claude') {
                addActivityLog('Deployed mode — Claude API active', 'success');
                if (!state.apiKey) {
                    addActivityLog('⚠ Add Claude API key in ⚙ settings', 'warning');
                    addJarvisMessage("Welcome, sir. I'm running in deployed mode — Ollama is unavailable here. Please add your Claude API key via ⚙ Settings to enable full AI capabilities.", true);
                }
            } else if (state.backend === 'ollama') {
                addActivityLog('Ollama local engine connecting...', '');
            } else if (state.apiKey) {
                addActivityLog('Claude AI engine connected ✓', 'success');
            } else {
                addActivityLog('AI offline — configure Ollama or Claude API key', 'warning');
            }
            addActivityLog('All systems nominal ✓', 'success');

            // Set online status
            DOM.mainPulseDot.classList.add('online');
            DOM.statusText.textContent = 'SYSTEM ONLINE';
            DOM.statusText.classList.add('online');
            setReactorState('standby');

            // Boot message
            const greeting = getGreeting();
            addJarvisMessage(greeting, true);

        }, bootLogs.length * 300 + 200);
    }

    function getGreeting() {
        const hour = new Date().getHours();
        let timeOfDay = 'evening';
        if (hour < 12) timeOfDay = 'morning';
        else if (hour < 17) timeOfDay = 'afternoon';

        if (state.apiKey) {
            return `Good ${timeOfDay}, sir. All systems are operational and Claude AI is online. I'm ready to assist you with anything you need — just speak or type your command.`;
        }
        return `Good ${timeOfDay}. I'm J.A.R.V.I.S., your AI assistant. I'm currently running in offline mode with limited capabilities. To unlock my full potential — connect Ollama locally or add your Claude API key in the ⚙ settings.`;
    }

    // ===========================
    // Particles
    // ===========================
    function setupParticles() {
        const frag = document.createDocumentFragment();
        for (let i = 0; i < CONFIG.particleCount; i++) {
            const p = document.createElement('div');
            p.className = 'particle';
            p.style.cssText = `
                left: ${Math.random() * 100}%;
                top: ${Math.random() * 100}%;
                animation-delay: ${Math.random() * 10}s;
                animation-duration: ${7 + Math.random() * 8}s;
                width: ${1 + Math.random() * 2}px;
                height: ${1 + Math.random() * 2}px;
            `;
            frag.appendChild(p);
        }
        DOM.particleField.appendChild(frag);
    }

    // ===========================
    // Waveform
    // ===========================
    function setupWaveform() {
        state.waveformCtx = DOM.waveformCanvas.getContext('2d');
        animateWaveform();
    }

    function animateWaveform() {
        const ctx = state.waveformCtx;
        const w = DOM.waveformCanvas.width;
        const h = DOM.waveformCanvas.height;
        const bars = CONFIG.waveformBars;
        const barW = w / bars - 1;

        function draw() {
            ctx.clearRect(0, 0, w, h);
            const t = Date.now() / 1000;

            for (let i = 0; i < bars; i++) {
                const x = i * (barW + 1);
                let barH;

                if (state.isSpeaking) {
                    barH = (Math.sin(t * 6 + i * 0.4) + 1) * 0.5 * (h * 0.8) + 2;
                    barH *= (0.4 + Math.random() * 0.6);
                } else if (state.isListening) {
                    barH = (Math.sin(t * 5 + i * 0.6) + 1) * 0.5 * (h * 0.5) + 3;
                    barH *= (0.6 + Math.random() * 0.4);
                } else if (state.isStreaming) {
                    barH = (Math.sin(t * 3 + i * 0.3) + 1) * 0.5 * (h * 0.4) + 2;
                } else {
                    barH = (Math.sin(t * 1.2 + i * 0.25) + 1) * 0.5 * 4 + 1;
                }

                let color;
                if (state.isSpeaking) {
                    color = 'rgba(167, 139, 250,';
                } else if (state.isListening) {
                    color = 'rgba(0, 255, 136,';
                } else if (state.isStreaming) {
                    color = 'rgba(255, 107, 53,';
                } else {
                    color = 'rgba(0, 212, 255,';
                }

                const grad = ctx.createLinearGradient(0, h - barH, 0, h);
                grad.addColorStop(0, color + '0.8)');
                grad.addColorStop(1, color + '0.1)');
                ctx.fillStyle = grad;
                ctx.fillRect(x, h - barH, barW, barH);
            }

            requestAnimationFrame(draw);
        }
        draw();
    }

    // ===========================
    // Clock & Timers
    // ===========================
    function setupClock() {
        function tick() {
            const now = new Date();
            DOM.currentTime.textContent = now.toLocaleTimeString('en-US', { hour12: false });
            DOM.currentDate.textContent = now.toISOString().split('T')[0].replace(/-/g, '.');
        }
        tick();
        setInterval(tick, 1000);
    }

    function setupSessionTimer() {
        setInterval(() => {
            const elapsed = Math.floor((Date.now() - state.sessionStart) / 1000);
            const m = String(Math.floor(elapsed / 60)).padStart(2, '0');
            const s = String(elapsed % 60).padStart(2, '0');
            DOM.sessionTime.textContent = `${m}:${s}`;
        }, 1000);
    }

    // ===========================
    // Event Listeners
    // ===========================
    function setupEventListeners() {
        // Send
        DOM.sendBtn.addEventListener('click', handleSend);
        DOM.userInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend();
            }
        });

        // Voice button
        DOM.voiceBtn.addEventListener('click', toggleVoice);

        // Space bar hold-to-talk
        document.addEventListener('keydown', (e) => {
            if (e.code === 'Space' && !state.spaceHeld && document.activeElement !== DOM.userInput) {
                e.preventDefault();
                state.spaceHeld = true;
                startListening();
            }
        });
        document.addEventListener('keyup', (e) => {
            if (e.code === 'Space' && state.spaceHeld) {
                e.preventDefault();
                state.spaceHeld = false;
                if (state.isListening && !state.settings.continuousListen) {
                    stopListening();
                }
            }
        });

        // Quick commands
        $$('.quick-cmd').forEach((btn) => {
            btn.addEventListener('click', () => {
                DOM.userInput.value = btn.dataset.cmd;
                handleSend();
            });
        });

        // Settings
        DOM.settingsBtn.addEventListener('click', openSettings);
        DOM.settingsClose.addEventListener('click', closeSettings);
        DOM.settingsCancelBtn.addEventListener('click', closeSettings);
        DOM.settingsSaveBtn.addEventListener('click', saveSettings);
        DOM.settingsOverlay.addEventListener('click', (e) => {
            if (e.target === DOM.settingsOverlay) closeSettings();
        });

        // Toggle API key visibility
        DOM.toggleKeyVisibility.addEventListener('click', () => {
            const input = DOM.apiKeyInput;
            input.type = input.type === 'password' ? 'text' : 'password';
        });

        // Voice settings sliders
        DOM.voiceRate.addEventListener('input', () => {
            DOM.voiceRateValue.textContent = DOM.voiceRate.value + 'x';
        });
        DOM.voicePitch.addEventListener('input', () => {
            DOM.voicePitchValue.textContent = DOM.voicePitch.value + 'x';
        });

        // Clear chat
        DOM.clearChatBtn.addEventListener('click', clearChat);

        // Stop speech on click
        DOM.arcReactor.addEventListener('click', () => {
            if (state.isSpeaking) {
                state.synthesis.cancel();
                state.isSpeaking = false;
                setReactorState('standby');
            }
        });
    }

    // ===========================
    // Settings
    // ===========================
    function openSettings() {
        DOM.apiKeyInput.value = state.apiKey;
        DOM.ollamaUrlInput && (DOM.ollamaUrlInput.value = state.ollamaUrl);
        if (DOM.backendSelect) {
            DOM.backendSelect.value = state.backend;
            const ollamaOption = DOM.backendSelect.querySelector('option[value="ollama"]');
            if (isDeployed && ollamaOption) {
                ollamaOption.disabled = true;
                ollamaOption.textContent = 'Ollama (Local only — unavailable when deployed)';
            }
        }
        DOM.modelSelect.value = state.model;
        DOM.autoSpeak.checked = state.settings.autoSpeak;
        DOM.continuousListen.checked = state.settings.continuousListen;
        DOM.voiceRate.value = state.settings.voiceRate;
        DOM.voiceRateValue.textContent = state.settings.voiceRate + 'x';
        DOM.voicePitch.value = state.settings.voicePitch;
        DOM.voicePitchValue.textContent = state.settings.voicePitch + 'x';
        populateVoiceSelect();
        DOM.settingsOverlay.classList.add('open');
    }

    function closeSettings() {
        DOM.settingsOverlay.classList.remove('open');
    }

    function saveSettings() {
        const newKey = DOM.apiKeyInput.value.trim();
        const keyChanged = newKey !== state.apiKey;

        state.apiKey = newKey;
        state.backend = DOM.backendSelect ? DOM.backendSelect.value : state.backend;
        state.ollamaUrl = DOM.ollamaUrlInput ? DOM.ollamaUrlInput.value.trim() || 'http://localhost:11434' : state.ollamaUrl;
        state.model = DOM.modelSelect.value;
        state.settings.autoSpeak = DOM.autoSpeak.checked;
        state.settings.continuousListen = DOM.continuousListen.checked;
        state.settings.voiceRate = parseFloat(DOM.voiceRate.value);
        state.settings.voicePitch = parseFloat(DOM.voicePitch.value);

        const selectedVoiceOption = DOM.voiceSelect.value;
        state.settings.voiceName = selectedVoiceOption;

        // Persist
        localStorage.setItem('jarvis_claude_key', state.apiKey);
        localStorage.setItem('jarvis_backend', state.backend);
        localStorage.setItem('jarvis_ollama_url', state.ollamaUrl);
        localStorage.setItem('jarvis_model', state.model);
        localStorage.setItem('jarvis_autospeak', state.settings.autoSpeak);
        localStorage.setItem('jarvis_continuous', state.settings.continuousListen);
        localStorage.setItem('jarvis_voice_rate', state.settings.voiceRate);
        localStorage.setItem('jarvis_voice_pitch', state.settings.voicePitch);
        localStorage.setItem('jarvis_voice_name', state.settings.voiceName);

        closeSettings();
        addActivityLog('Settings updated', 'success');

        if (keyChanged || state.backend) {
            checkAPIConnection();
        }
    }

    function loadSettings() {
        DOM.autoSpeak.checked = state.settings.autoSpeak;
        DOM.continuousListen.checked = state.settings.continuousListen;
        DOM.voiceRate.value = state.settings.voiceRate;
        DOM.voiceRateValue.textContent = state.settings.voiceRate + 'x';
        DOM.voicePitch.value = state.settings.voicePitch;
        DOM.voicePitchValue.textContent = state.settings.voicePitch + 'x';
    }

    async function checkAPIConnection() {
        if (state.backend === 'ollama') {
            addActivityLog('Testing Ollama connection...', 'warning');
            try {
                const resp = await fetch(`${state.ollamaUrl}/api/tags`);
                if (resp.ok) {
                    updateAPIStatus('connected');
                    addActivityLog('Ollama local engine connected ✓', 'success');
                } else {
                    updateAPIStatus('error', `HTTP ${resp.status}`);
                    addActivityLog('Ollama connection failed', 'error');
                }
            } catch (e) {
                updateAPIStatus('error', 'Ollama not reachable — is it running?');
                addActivityLog('Ollama unreachable (start with: ollama serve)', 'error');
            }
            return;
        }

        // Claude API
        if (!state.apiKey) {
            updateAPIStatus('disconnected');
            return;
        }

        addActivityLog('Testing Claude API connection...', 'warning');
        try {
            const resp = await fetch(CONFIG.claudeApiBaseUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'x-api-key': state.apiKey,
                    'anthropic-version': CONFIG.claudeApiVersion,
                    'anthropic-dangerous-direct-browser-access': 'true',
                },
                body: JSON.stringify({
                    model: state.model,
                    max_tokens: 10,
                    messages: [{ role: 'user', content: 'Hi' }],
                }),
            });

            if (resp.ok) {
                updateAPIStatus('connected');
                addActivityLog('Claude AI engine connected ✓', 'success');
            } else {
                const err = await resp.json().catch(() => ({}));
                updateAPIStatus('error', err.error?.message || `HTTP ${resp.status}`);
                addActivityLog(`Claude API failed: ${resp.status}`, 'error');
            }
        } catch (e) {
            updateAPIStatus('error', e.message);
            addActivityLog('Claude API connection error', 'error');
        }
    }

    function updateAPIStatus(status, detail) {
        const dot = DOM.apiStatus.querySelector('.api-dot');
        const text = DOM.apiStatus.querySelector('.api-text');
        DOM.apiStatus.className = 'api-status ' + (status === 'connected' ? 'connected' : status === 'error' ? 'error' : '');

        if (status === 'connected') {
            const engineName = state.backend === 'ollama' ? 'Ollama AI' : 'Claude AI';
            text.textContent = `Connected to ${engineName} ✓`;
            DOM.aiEngineStatus.textContent = 'ONLINE';
            DOM.aiEngineBar.style.setProperty('--fill-width', '100%');
            DOM.claudeProcess.classList.add('active');
            DOM.modelLabel.textContent = `MODEL: ${state.model.toUpperCase()}`;
            DOM.aiBadge.textContent = state.backend === 'ollama' ? 'OLLAMA LOCAL' : 'CLAUDE AI';
            DOM.aiBadge.classList.add('online');
            DOM.networkStatus.textContent = state.backend === 'ollama' ? 'NETWORK: LOCAL' : 'NETWORK: CONNECTED';
        } else if (status === 'error') {
            text.textContent = `Connection error: ${detail || 'Unknown'}`;
            DOM.aiEngineStatus.textContent = 'ERROR';
            DOM.aiEngineBar.style.setProperty('--fill-width', '20%');
            DOM.aiBadge.textContent = 'API ERROR';
            DOM.aiBadge.classList.remove('online');
        } else {
            text.textContent = 'No API key configured — using offline mode';
            DOM.aiEngineStatus.textContent = 'OFFLINE';
            DOM.aiEngineBar.style.setProperty('--fill-width', '0%');
            DOM.claudeProcess.classList.remove('active');
            DOM.modelLabel.textContent = 'MODEL: OFFLINE';
            DOM.aiBadge.textContent = 'OFFLINE MODE';
            DOM.aiBadge.classList.remove('online');
        }
    }

    // ===========================
    // Voice Recognition
    // ===========================
    function setupVoiceRecognition() {
        const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SR) {
            DOM.micStatus.textContent = '⚠ Voice not supported — use Chrome or Edge';
            DOM.voiceBtn.title = 'Voice not supported in this browser';
            addActivityLog('Speech recognition unavailable', 'warning');
            return;
        }

        if (isDeployed && location.protocol !== 'https:') {
            DOM.micStatus.textContent = '⚠ Voice requires HTTPS when deployed';
            addActivityLog('Voice disabled — HTTPS required', 'warning');
            return;
        }

        if (isDeployed) {
            addActivityLog('Voice via browser STT (Google) — HTTPS ✓', '');
        }

        const recognition = new SR();
        recognition.continuous = false;
        recognition.interimResults = true;
        recognition.lang = 'en-US';
        recognition.maxAlternatives = 1;

        recognition.onstart = () => {
            state.isListening = true;
            DOM.voiceBtn.classList.add('active');
            DOM.inputWrapper.classList.add('listening');
            setReactorState('listening');
            DOM.micStatus.textContent = '🎤 Listening... Speak now';
            DOM.userInput.placeholder = 'Listening...';
        };

        recognition.onresult = (event) => {
            let interimTranscript = '';
            let finalTranscript = '';

            for (let i = event.resultIndex; i < event.results.length; i++) {
                const transcript = event.results[i][0].transcript;
                if (event.results[i].isFinal) {
                    finalTranscript += transcript;
                } else {
                    interimTranscript += transcript;
                }
            }

            // Show interim results in the input
            DOM.userInput.value = finalTranscript || interimTranscript;

            // Auto-send on final result
            if (finalTranscript) {
                setTimeout(() => {
                    if (DOM.userInput.value.trim()) {
                        handleSend();
                    }
                }, 300);
            }
        };

        recognition.onend = () => {
            state.isListening = false;
            DOM.voiceBtn.classList.remove('active');
            DOM.inputWrapper.classList.remove('listening');
            DOM.userInput.placeholder = 'Speak or type a command, sir...';
            DOM.micStatus.textContent = '🎤 Click mic or press & hold Space to speak';

            if (!state.isProcessing) {
                setReactorState('standby');
            }

            // Continuous listening mode
            if (state.settings.continuousListen && !state.isProcessing && !state.isSpeaking) {
                setTimeout(() => {
                    if (state.settings.continuousListen && !state.isProcessing && !state.isSpeaking) {
                        startListening();
                    }
                }, 1500);
            }
        };

        recognition.onerror = (event) => {
            console.warn('Speech recognition error:', event.error);
            state.isListening = false;
            DOM.voiceBtn.classList.remove('active');
            DOM.inputWrapper.classList.remove('listening');

            let fatalError = false;

            if (event.error === 'not-allowed') {
                fatalError = true;
                DOM.micStatus.textContent = '⚠ Microphone blocked — check browser permissions';
                addActivityLog('Microphone access denied', 'error');
                addJarvisMessage("I'm unable to access your microphone. Please check your browser permissions — you may need to click the lock icon in the address bar and allow microphone access, or serve this page from localhost.", true);
            } else if (event.error === 'no-speech') {
                DOM.micStatus.textContent = '🎤 No speech detected — try again';
            } else if (event.error === 'network') {
                fatalError = true;
                DOM.micStatus.textContent = '⚠ Network error — speech recognition requires internet';
                addActivityLog('Voice recognition network error', 'error');
            } else {
                fatalError = true;
                DOM.micStatus.textContent = `⚠ Voice error: ${event.error}`;
                addActivityLog(`Voice error: ${event.error}`, 'error');
            }

            // Disable continuous listening to prevent infinite error loops
            if (fatalError && state.settings.continuousListen) {
                state.settings.continuousListen = false;
                DOM.continuousListen.checked = false;
                localStorage.setItem('jarvis_continuous', 'false');
                addActivityLog('Continuous listening disabled due to error', 'warning');
            }

            if (!state.isProcessing) {
                setReactorState('standby');
            }
        };

        state.recognition = recognition;
    }

    function startListening() {
        if (!state.recognition) {
            addJarvisMessage("Voice recognition is not available in this browser. Please use Google Chrome or Microsoft Edge for the best experience.", true);
            return;
        }
        if (state.isListening) return;
        if (state.isSpeaking) {
            state.synthesis.cancel();
            state.isSpeaking = false;
        }

        try {
            state.recognition.start();
            addActivityLog('Voice capture initiated');
        } catch (e) {
            console.warn('Could not start recognition:', e);
        }
    }

    function stopListening() {
        if (state.recognition && state.isListening) {
            state.recognition.stop();
        }
    }

    function toggleVoice() {
        if (state.isListening) {
            stopListening();
        } else {
            startListening();
        }
    }

    // ===========================
    // Speech Synthesis
    // ===========================
    function setupSpeechVoices() {
        function loadVoices() {
            state.voices = state.synthesis.getVoices();
            populateVoiceSelect();
        }

        loadVoices();
        if (state.synthesis.onvoiceschanged !== undefined) {
            state.synthesis.onvoiceschanged = loadVoices;
        }
        // Some browsers need a delay
        setTimeout(loadVoices, 500);
        setTimeout(loadVoices, 2000);
    }

    function populateVoiceSelect() {
        if (!state.voices.length) return;
        const select = DOM.voiceSelect;
        const current = select.value || state.settings.voiceName;
        select.innerHTML = '<option value="auto">Auto-detect best</option>';

        const enVoices = state.voices.filter(v => v.lang.startsWith('en'));
        enVoices.forEach(v => {
            const opt = document.createElement('option');
            opt.value = v.name;
            opt.textContent = `${v.name} (${v.lang})`;
            select.appendChild(opt);
        });

        select.value = current;
    }

    function getBestVoice() {
        if (state.settings.voiceName !== 'auto') {
            const chosen = state.voices.find(v => v.name === state.settings.voiceName);
            if (chosen) return chosen;
        }

        const preferences = [
            'Google UK English Male',
            'Microsoft Ryan Online',
            'Microsoft Guy Online',
            'Daniel',
            'Google UK English Female',
            'Microsoft David',
            'Microsoft Mark',
            'Samantha',
        ];

        for (const name of preferences) {
            const v = state.voices.find(v => v.name.includes(name));
            if (v) return v;
        }

        return state.voices.find(v => v.lang.startsWith('en')) || state.voices[0] || null;
    }

    function speak(text) {
        if (!state.settings.autoSpeak || !state.synthesis) return;

        // Cancel any ongoing
        state.synthesis.cancel();

        // Clean text for speech (remove markdown/symbols)
        const cleanText = text
            .replace(/```[\s\S]*?```/g, 'code block omitted')
            .replace(/`([^`]+)`/g, '$1')
            .replace(/[*_~#>]/g, '')
            .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
            .replace(/\n{2,}/g, '. ')
            .replace(/[•●○◆▸]/g, '')
            .trim();

        if (!cleanText) return;

        const utterance = new SpeechSynthesisUtterance(cleanText);
        const voice = getBestVoice();
        if (voice) utterance.voice = voice;
        utterance.rate = state.settings.voiceRate;
        utterance.pitch = state.settings.voicePitch;
        utterance.volume = 1.0;

        utterance.onstart = () => {
            state.isSpeaking = true;
            setReactorState('speaking');
        };

        utterance.onend = () => {
            state.isSpeaking = false;
            if (!state.isProcessing) setReactorState('standby');

            // Resume listening in continuous mode
            if (state.settings.continuousListen && !state.isProcessing) {
                setTimeout(() => startListening(), 800);
            }
        };

        utterance.onerror = (e) => {
            state.isSpeaking = false;
            if (!state.isProcessing) setReactorState('standby');
            console.warn('Speech synthesis error:', e);
        };

        // Chrome bug: long text stops. Work around by chunking
        if (cleanText.length > 200) {
            speakChunked(cleanText, utterance.voice, utterance.rate, utterance.pitch);
        } else {
            state.synthesis.speak(utterance);
        }
    }

    function speakChunked(text, voice, rate, pitch) {
        const sentences = text.match(/[^.!?]+[.!?]+|[^.!?]+$/g) || [text];
        const chunks = [];
        let current = '';

        sentences.forEach(s => {
            if ((current + s).length > 180) {
                if (current) chunks.push(current.trim());
                current = s;
            } else {
                current += s;
            }
        });
        if (current) chunks.push(current.trim());

        let i = 0;
        function speakNext() {
            if (i >= chunks.length) {
                state.isSpeaking = false;
                if (!state.isProcessing) setReactorState('standby');
                if (state.settings.continuousListen && !state.isProcessing) {
                    setTimeout(() => startListening(), 800);
                }
                return;
            }

            const utt = new SpeechSynthesisUtterance(chunks[i]);
            if (voice) utt.voice = voice;
            utt.rate = rate;
            utt.pitch = pitch;

            if (i === 0) {
                utt.onstart = () => {
                    state.isSpeaking = true;
                    setReactorState('speaking');
                };
            }

            utt.onend = () => {
                i++;
                speakNext();
            };

            utt.onerror = () => {
                state.isSpeaking = false;
                if (!state.isProcessing) setReactorState('standby');
            };

            state.synthesis.speak(utt);
        }

        speakNext();
    }

    // ===========================
    // Message Handling
    // ===========================
    function handleSend() {
        const text = DOM.userInput.value.trim();
        if (!text || state.isProcessing) return;

        DOM.userInput.value = '';
        state.isProcessing = true;
        state.messageCount++;

        // Stop speech if playing
        if (state.isSpeaking) {
            state.synthesis.cancel();
            state.isSpeaking = false;
        }

        addUserMessage(text);
        addActivityLog('Command received');
        setReactorState('processing');
        updateStats();

        // Add to conversation history (OpenAI-compatible for Ollama & Claude)
        state.conversationHistory.push({ role: 'user', content: text });
        trimHistory();

        if (state.backend === 'ollama') {
            callOllama(text);
        } else if (state.apiKey) {
            callClaude(text);
        } else {
            generateOfflineResponse(text);
        }
    }

    function addUserMessage(text) {
        const time = new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
        const div = document.createElement('div');
        div.className = 'message user-message';
        div.innerHTML = `
            <div class="message-avatar"><span>U</span></div>
            <div class="message-content">
                <div class="message-header">
                    <span class="sender-name">USER</span>
                    <span class="message-time">${time}</span>
                </div>
                <div class="message-text">${escapeHTML(text)}</div>
            </div>
        `;
        DOM.chatMessages.appendChild(div);
        scrollToBottom();
    }

    function addJarvisMessage(text, withSpeak = false) {
        const time = new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
        const div = document.createElement('div');
        div.className = 'message jarvis-message';
        div.innerHTML = `
            <div class="message-avatar">
                <div class="avatar-ring"></div>
                <span>J</span>
            </div>
            <div class="message-content">
                <div class="message-header">
                    <span class="sender-name">J.A.R.V.I.S.</span>
                    <span class="message-time">${time}</span>
                </div>
                <div class="message-text">${formatMessage(text)}</div>
            </div>
        `;
        DOM.chatMessages.appendChild(div);
        scrollToBottom();

        if (withSpeak) speak(text);

        state.conversationHistory.push({ role: 'assistant', content: text });
        trimHistory();
        state.messageCount++;
        updateStats();
    }

    function createStreamingMessage() {
        const time = new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
        const div = document.createElement('div');
        div.className = 'message jarvis-message';
        div.innerHTML = `
            <div class="message-avatar">
                <div class="avatar-ring"></div>
                <span>J</span>
            </div>
            <div class="message-content">
                <div class="message-header">
                    <span class="sender-name">J.A.R.V.I.S.</span>
                    <span class="message-time">${time}</span>
                </div>
                <div class="message-text streaming-cursor"></div>
            </div>
        `;
        DOM.chatMessages.appendChild(div);
        scrollToBottom();
        return div.querySelector('.message-text');
    }

    function showThinking() {
        const div = document.createElement('div');
        div.className = 'message jarvis-message';
        div.id = 'thinkingIndicator';
        div.innerHTML = `
            <div class="message-avatar">
                <div class="avatar-ring"></div>
                <span>J</span>
            </div>
            <div class="message-content">
                <div class="thinking-dots"><span></span><span></span><span></span></div>
            </div>
        `;
        DOM.chatMessages.appendChild(div);
        scrollToBottom();
        return div;
    }

    function removeThinking() {
        const el = $('#thinkingIndicator');
        if (el) el.remove();
    }

    function scrollToBottom() {
        requestAnimationFrame(() => {
            DOM.chatContainer.scrollTop = DOM.chatContainer.scrollHeight;
        });
    }

    // ===========================
    // Ollama API (local)
    // ===========================
    async function callOllama(userText) {
        const thinkingEl = showThinking();
        const startTime = Date.now();

        const now = new Date();
        const systemPrompt = CONFIG.systemPrompt.replace(
            '{{DATETIME}}',
            now.toLocaleString('en-US', {
                weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
                hour: 'numeric', minute: '2-digit', second: '2-digit', hour12: true,
                timeZoneName: 'short'
            })
        );

        const messages = [
            { role: 'system', content: systemPrompt },
            ...state.conversationHistory,
        ];

        try {
            const resp = await fetch(`${state.ollamaUrl}/api/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    model: state.model,
                    messages,
                    stream: true,
                }),
            });

            removeThinking();

            if (!resp.ok) {
                const err = await resp.json().catch(() => ({}));
                throw new Error(err.error || `Ollama returned ${resp.status}`);
            }

            const textEl = createStreamingMessage();
            state.isStreaming = true;
            let fullText = '';

            const reader = resp.body.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                for (const line of chunk.split('\n')) {
                    if (!line.trim()) continue;
                    try {
                        const parsed = JSON.parse(line);
                        const token = parsed.message?.content || '';
                        if (token) {
                            fullText += token;
                            textEl.innerHTML = formatMessage(fullText);
                            textEl.classList.add('streaming-cursor');
                            scrollToBottom();
                        }
                    } catch (e) { /* skip */ }
                }
            }

            textEl.classList.remove('streaming-cursor');
            state.isStreaming = false;
            state.isProcessing = false;
            state.messageCount++;

            state.conversationHistory.push({ role: 'assistant', content: fullText });
            trimHistory();

            const latency = Date.now() - startTime;
            DOM.latencyValue.textContent = latency;
            addActivityLog(`Response generated (${latency}ms)`, 'success');
            setReactorState('standby');
            updateStats();
            speak(fullText);

        } catch (err) {
            removeThinking();
            state.isStreaming = false;
            state.isProcessing = false;
            console.error('Ollama error:', err);
            addActivityLog(`Ollama Error: ${err.message}`, 'error');
            setReactorState('standby');
            addJarvisMessage(
                `Ollama connection failed: "${err.message}". Make sure Ollama is running locally (ollama serve) and the model is pulled (ollama pull ${state.model}).\n\nFalling back to offline mode:\n\n` +
                generateOfflineText(userText),
                true
            );
        }
    }

    // ===========================
    // Claude API (Anthropic)
    // ===========================
    async function callClaude(userText) {
        const thinkingEl = showThinking();
        const startTime = Date.now();

        const now = new Date();
        const systemPrompt = CONFIG.systemPrompt.replace(
            '{{DATETIME}}',
            now.toLocaleString('en-US', {
                weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
                hour: 'numeric', minute: '2-digit', second: '2-digit', hour12: true,
                timeZoneName: 'short'
            })
        );

        try {
            const resp = await fetch(CONFIG.claudeApiBaseUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'x-api-key': state.apiKey,
                    'anthropic-version': CONFIG.claudeApiVersion,
                    'anthropic-dangerous-direct-browser-access': 'true',
                },
                body: JSON.stringify({
                    model: state.model,
                    max_tokens: 1024,
                    system: systemPrompt,
                    stream: true,
                    messages: state.conversationHistory,
                }),
            });

            removeThinking();

            if (!resp.ok) {
                const err = await resp.json().catch(() => ({}));
                throw new Error(err.error?.message || `Claude API returned ${resp.status}`);
            }

            const textEl = createStreamingMessage();
            state.isStreaming = true;
            let fullText = '';

            const reader = resp.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const dataStr = line.slice(6).trim();
                        if (!dataStr || dataStr === '[DONE]') continue;
                        try {
                            const parsed = JSON.parse(dataStr);
                            if (parsed.type === 'content_block_delta' && parsed.delta?.type === 'text_delta') {
                                fullText += parsed.delta.text;
                                textEl.innerHTML = formatMessage(fullText);
                                textEl.classList.add('streaming-cursor');
                                scrollToBottom();
                            }
                            if (parsed.type === 'message_delta' && parsed.usage) {
                                state.tokenCount += parsed.usage.output_tokens || 0;
                            }
                        } catch (e) { /* skip */ }
                    }
                }
            }

            textEl.classList.remove('streaming-cursor');
            state.isStreaming = false;
            state.isProcessing = false;
            state.messageCount++;

            state.conversationHistory.push({ role: 'assistant', content: fullText });
            trimHistory();

            const latency = Date.now() - startTime;
            DOM.latencyValue.textContent = latency;
            addActivityLog(`Response generated (${latency}ms)`, 'success');
            setReactorState('standby');
            updateStats();
            speak(fullText);

        } catch (err) {
            removeThinking();
            state.isStreaming = false;
            state.isProcessing = false;
            console.error('Claude API error:', err);
            addActivityLog(`API Error: ${err.message}`, 'error');
            setReactorState('standby');
            addJarvisMessage(
                `I encountered an issue connecting to my Claude core: "${err.message}". Let me try to help with my offline capabilities instead.\n\n` +
                generateOfflineText(userText),
                true
            );
        }
    }

    // ===========================
    // Offline AI (Fallback)
    // ===========================
    function generateOfflineResponse(userText) {
        setTimeout(() => {
            const response = generateOfflineText(userText);
            addJarvisMessage(response, true);
            state.isProcessing = false;
            setReactorState('standby');
            addActivityLog('Offline response generated');
        }, 600 + Math.random() * 800);
    }

    function generateOfflineText(input) {
        const lower = input.toLowerCase().trim();

        // Time
        if (/\b(time|clock|hour)\b/.test(lower)) {
            const now = new Date();
            const time = now.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', second: '2-digit', hour12: true });
            const date = now.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
            return `The current time is ${time}, and today is ${date}.`;
        }

        // Date
        if (/\b(date|day|today|month|year)\b/.test(lower) && !/birth/.test(lower)) {
            const now = new Date();
            const date = now.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
            const time = now.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
            return `Today is ${date}. The current time is ${time}.`;
        }

        // Greeting
        if (/^(hello|hi|hey|yo|sup|greet|good\s*(morning|evening|afternoon|night))/.test(lower)) {
            const hour = new Date().getHours();
            const tod = hour < 12 ? 'morning' : hour < 17 ? 'afternoon' : 'evening';
            return pick([
                `Good ${tod}! All systems are operational. How may I assist you?`,
                `Hello, sir. I'm at your service. What shall we work on?`,
                `Greetings. The Stark Industries network is fully operational. What can I do for you?`,
            ]);
        }

        // Capabilities
        if (/\b(can you do|capabilit|help|feature|command|what do you)\b/.test(lower)) {
            return `Currently in offline mode, my capabilities include:\n\n• 🕐 Time & Date — real-time clock\n• 🧮 Basic calculations\n• 😄 Jokes and fun facts\n• 💡 Motivational quotes\n• 🎤 Voice input/output\n\nFor my full capabilities — connect Ollama locally (qwen2.5, llama3, mistral) or add your Claude API key in the ⚙ settings.`;
        }

        // Joke
        if (/\b(joke|funny|laugh|humor)\b/.test(lower)) {
            return pick([
                "Why do programmers prefer dark mode? Because light attracts bugs. ...I'll be here all night, sir.",
                "I tried to write a joke about UDP, but I wasn't sure if anyone would get it.",
                "Why did the AI go to therapy? Too many unresolved deep learning issues.",
                "A SQL query walks into a bar, sees two tables, and asks: 'Can I join you?'",
                "What's a robot's favorite type of music? Heavy metal. Though I personally prefer something more refined.",
            ]);
        }

        // Quote
        if (/\b(quote|motivat|inspir|wisdom)\b/.test(lower)) {
            return pick([
                '"The best way to predict the future is to invent it." — Alan Kay',
                '"Any sufficiently advanced technology is indistinguishable from magic." — Arthur C. Clarke',
                '"Innovation distinguishes between a leader and a follower." — Steve Jobs',
                '"The only way to do great work is to love what you do." — Steve Jobs',
                '"I am Iron Man." — Tony Stark',
            ]);
        }

        // Fun fact
        if (/\b(fact|trivia|interesting|did you know|science)\b/.test(lower)) {
            return pick([
                "Honey never spoils. Archaeologists have found 3,000-year-old honey in Egyptian tombs that was still perfectly edible.",
                "The human brain uses approximately 20% of the body's total energy, despite being only 2% of its mass.",
                "There are more possible iterations of a game of chess than atoms in the observable universe.",
                "Octopuses have three hearts and blue blood. If they went into the superhero business, they'd be formidable.",
                "A day on Venus is longer than its year — 243 Earth days to rotate, but only 225 to orbit the Sun.",
            ]);
        }

        // Calculation
        if (/[\d+\-*/^%()]/.test(lower) && /\b(calc|compute|solve|what\s+is|equals)\b/.test(lower)) {
            try {
                const expr = input.replace(/[^0-9+\-*/().%\s]/g, ' ').replace(/\^/g, '**').trim();
                const sanitized = expr.replace(/[^0-9+\-*/().%\s]/g, '');
                if (sanitized.trim()) {
                    const result = Function('"use strict"; return (' + sanitized + ')')();
                    if (typeof result === 'number' && isFinite(result)) {
                        return `The result is ${result}.`;
                    }
                }
            } catch (e) { /* fall through */ }
            return "I had trouble parsing that equation. Could you rephrase it?";
        }

        // Diagnostics
        if (/\b(diagnostic|system|status|health)\b/.test(lower)) {
            addActivityLog('Running diagnostics...', 'warning');
            setTimeout(() => addActivityLog('Diagnostics complete ✓', 'success'), 1000);
            return `Running full system diagnostics...\n\n✅ Neural Network — Operational\n✅ Voice Module — Active\n✅ Speech Synthesis — Online\n✅ HUD Renderer — Nominal\n✅ Security — AES-256 Active\n${state.backend === 'ollama' ? '✅ Ollama Local AI — Active' : (state.apiKey ? '✅ Claude AI — Connected' : '⚠️ Claude AI — Not configured')}\n\nAll core systems operating within normal parameters.`;
        }

        // Default
        return pick([
            `I'm currently in offline mode with limited capabilities. To get a complete answer, connect Ollama locally or add your Claude API key in the ⚙ settings.`,
            `That's a great question, but I'd need my AI core online to give you a proper answer. Click ⚙ to configure Ollama or Claude API.`,
            `I wish I could help more with that in offline mode. Connect Ollama (local) or Claude API in settings to unlock my full potential.`,
        ]);
    }

    // ===========================
    // Utilities
    // ===========================
    function setReactorState(mode) {
        DOM.arcReactor.className = 'arc-reactor-container';
        if (mode !== 'standby') {
            DOM.arcReactor.classList.add(mode);
        }
        const labels = {
            standby: 'STANDBY',
            listening: 'LISTENING',
            processing: 'PROCESSING',
            speaking: 'SPEAKING',
        };
        DOM.reactorStatus.textContent = labels[mode] || 'STANDBY';
    }

    function addActivityLog(text, type = '') {
        state.uptime++;
        const h = String(Math.floor(state.uptime / 3600)).padStart(2, '0');
        const m = String(Math.floor((state.uptime % 3600) / 60)).padStart(2, '0');
        const s = String(state.uptime % 60).padStart(2, '0');

        const div = document.createElement('div');
        div.className = `activity-item ${type}`;
        div.innerHTML = `
            <span class="activity-time">${h}:${m}:${s}</span>
            <span class="activity-text">${text}</span>
        `;
        DOM.activityFeed.appendChild(div);

        // Limit entries
        while (DOM.activityFeed.children.length > 30) {
            DOM.activityFeed.firstElementChild.remove();
        }
        DOM.activityFeed.scrollTop = DOM.activityFeed.scrollHeight;
    }

    function updateStats() {
        DOM.totalMessages.textContent = state.messageCount;
        DOM.totalTokens.textContent = state.tokenCount > 1000 ? (state.tokenCount / 1000).toFixed(1) + 'k' : state.tokenCount;
        DOM.memoryUsage.textContent = state.conversationHistory.length + ' msgs';
        const memPct = Math.min(100, (state.conversationHistory.length / CONFIG.maxConversationHistory) * 100);
        DOM.memoryBar.style.setProperty('--fill-width', memPct + '%');
    }

    function trimHistory() {
        while (state.conversationHistory.length > CONFIG.maxConversationHistory) {
            state.conversationHistory.shift();
        }
    }

    function clearChat() {
        DOM.chatMessages.innerHTML = '';
        state.conversationHistory = [];
        state.messageCount = 0;
        state.tokenCount = 0;
        updateStats();
        addActivityLog('Conversation cleared', 'warning');
        addJarvisMessage("Conversation memory cleared. I'm ready for a fresh start, sir.", true);
    }

    function escapeHTML(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    function formatMessage(text) {
        // Simple markdown-like formatting
        let html = escapeHTML(text);

        // Code blocks
        html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
        // Inline code
        html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
        // Bold
        html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
        // Italic
        html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');

        return html;
    }

    function pick(arr) {
        return arr[Math.floor(Math.random() * arr.length)];
    }

    // ===========================
    // Launch
    // ===========================
    document.addEventListener('DOMContentLoaded', init);
})();
