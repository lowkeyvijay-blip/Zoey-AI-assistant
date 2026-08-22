/* ===========================
   J.A.R.V.I.S. v4 — Zoey Frontend
   Powered by the local Zoey backend
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
        zoeyProcess: $('#zoeyProcess'),
        clearChatBtn: $('#clearChatBtn'),

        // Settings
        settingsBtn: $('#settingsBtn'),
        settingsOverlay: $('#settingsOverlay'),
        settingsClose: $('#settingsClose'),
        settingsSaveBtn: $('#settingsSaveBtn'),
        settingsCancelBtn: $('#settingsCancelBtn'),
        apiStatus: $('#apiStatus'),
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
    const state = {
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

        // Phase 10.9 backend state
        backendOnline: false,
        plan: null,
        planGoal: '',
        decision: null,
        planCardEl: null,
        executionCardEl: null,
        executionPolling: false,
        executionPollTimer: null,
        approvalBusy: false,
        executionBusy: false,

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
        checkBackendConnection();
        bootSequence();
    }

    // ===========================
    // Boot Sequence
    // ===========================
    async function bootSequence() {
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

        const online = await checkBackendConnection();

        setTimeout(() => {
            if (online) {
                addActivityLog('Zoey backend connected ✓', 'success');
            } else {
                addActivityLog('Zoey backend offline — using offline mode', 'warning');
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

        if (state.backendOnline) {
            return `Good ${timeOfDay}, sir. All systems are operational and my Zoey core is online. I'm ready to assist you with anything you need — just speak or type your command.`;
        }
        return `Good ${timeOfDay}. I'm J.A.R.V.I.S., your AI assistant. I'm currently running in offline mode with limited capabilities. To unlock my full potential, make sure the Zoey backend is running and serving this page.`;
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
                const resource = btn.dataset.resource;
                if (resource) {
                    handleResourceCommand(resource);
                    return;
                }
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
        state.settings.autoSpeak = DOM.autoSpeak.checked;
        state.settings.continuousListen = DOM.continuousListen.checked;
        state.settings.voiceRate = parseFloat(DOM.voiceRate.value);
        state.settings.voicePitch = parseFloat(DOM.voicePitch.value);

        const selectedVoiceOption = DOM.voiceSelect.value;
        state.settings.voiceName = selectedVoiceOption;

        // Persist
        localStorage.setItem('jarvis_autospeak', state.settings.autoSpeak);
        localStorage.setItem('jarvis_continuous', state.settings.continuousListen);
        localStorage.setItem('jarvis_voice_rate', state.settings.voiceRate);
        localStorage.setItem('jarvis_voice_pitch', state.settings.voicePitch);
        localStorage.setItem('jarvis_voice_name', state.settings.voiceName);

        closeSettings();
        addActivityLog('Settings updated', 'success');

        checkBackendConnection();
    }

    function loadSettings() {
        DOM.autoSpeak.checked = state.settings.autoSpeak;
        DOM.continuousListen.checked = state.settings.continuousListen;
        DOM.voiceRate.value = state.settings.voiceRate;
        DOM.voiceRateValue.textContent = state.settings.voiceRate + 'x';
        DOM.voicePitch.value = state.settings.voicePitch;
        DOM.voicePitchValue.textContent = state.settings.voicePitch + 'x';
    }

    async function checkBackendConnection() {
        addActivityLog('Testing Zoey backend connection...', 'warning');

        try {
            const { data } = await JarvisAPI.health();
            const online = !!(data && data.status === 'ok');
            state.backendOnline = online;
            updateConnectionUI(online);
            return online;
        } catch (e) {
            console.error('Backend check error:', e);
            state.backendOnline = false;
            updateConnectionUI(false);
            return false;
        }
    }

    function updateConnectionUI(online) {
        const dot = DOM.apiStatus.querySelector('.api-dot');
        const text = DOM.apiStatus.querySelector('.api-text');
        DOM.apiStatus.className = 'api-status ' + (online ? 'connected' : 'error');

        if (online) {
            text.textContent = 'Connected to Zoey backend ✓';
            DOM.aiEngineStatus.textContent = 'ONLINE';
            DOM.aiEngineBar.style.setProperty('--fill-width', '100%');
            DOM.zoeyProcess.classList.add('active');
            DOM.modelLabel.textContent = 'MODEL: ZOEY';
            DOM.aiBadge.textContent = 'ZOEY ONLINE';
            DOM.aiBadge.classList.add('online');
            DOM.networkStatus.textContent = 'NETWORK: CONNECTED';
        } else {
            text.textContent = 'Backend offline — using offline mode';
            DOM.aiEngineStatus.textContent = 'OFFLINE';
            DOM.aiEngineBar.style.setProperty('--fill-width', '0%');
            DOM.zoeyProcess.classList.remove('active');
            DOM.modelLabel.textContent = 'MODEL: OFFLINE';
            DOM.aiBadge.textContent = 'OFFLINE MODE';
            DOM.aiBadge.classList.remove('online');
            DOM.networkStatus.textContent = 'NETWORK: OFFLINE';
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

        // Add to local history (kept for the HUD memory stat)
        state.conversationHistory.push({ role: 'user', text: text });
        trimHistory();

        callBackend(text);
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

        state.conversationHistory.push({ role: 'model', text: text });
        trimHistory();
        state.messageCount++;
        updateStats();
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
    // Zoey Backend API (Phase 10.9)
    // ===========================

    async function callBackend(userText) {
        showThinking();
        const startTime = Date.now();

        try {
            const { data } = await JarvisAPI.chat(userText);
            removeThinking();

            handleAssistantMessage(data.message);

            const latency = Date.now() - startTime;
            DOM.latencyValue.textContent = latency;
            addActivityLog(`Response generated (${latency}ms)`, 'success');
            state.isProcessing = false;
            if (!state.executionPolling) setReactorState('standby');
            updateStats();

        } catch (err) {
            removeThinking();
            state.isProcessing = false;
            console.error('Backend error:', err);
            addActivityLog(`API Error: ${err.message}`, 'error');
            if (!state.executionPolling) setReactorState('standby');

            if (err instanceof TypeError) {
                // Network-level failure: the backend is unreachable.
                state.backendOnline = false;
                updateConnectionUI(false);
                addJarvisMessage(
                    `I couldn't reach my backend core: "${err.message}". Falling back to offline mode.\n\n` +
                    generateOfflineText(userText),
                    true
                );
            } else {
                addJarvisMessage(`I encountered an error: ${err.message}`, true);
            }
        }
    }

    // --------------------------------------------------
    // Structured assistant message dispatch
    // --------------------------------------------------

    function handleAssistantMessage(msg) {
        const type = msg.type;
        const data = msg.data || {};

        switch (type) {
            case 'plan_pending':
                state.plan = data.plan || null;
                state.planGoal = data.goal || '';
                state.decision = null;
                renderPlanCard(data, null);
                speak(msg.content || '');
                break;

            case 'goal':
                state.plan = data.plan || null;
                state.planGoal = data.goal || '';
                state.decision = 'approved';
                renderPlanCard(data, 'approved');
                speak(msg.content || '');
                break;

            case 'goal_rejected':
                state.decision = 'rejected';
                addJarvisMessage(msg.content || "OK, I won't add those tasks.", true);
                break;

            case 'plan_executed':
                state.execution = { goal: data.goal, steps: data.steps || [], status: data.status || 'completed' };
                renderExecutionCard(state.execution);
                speak(msg.content || '');
                break;

            case 'step_retried':
                state.execution = { goal: data.goal, steps: data.steps || [], status: data.status || 'failed' };
                renderExecutionCard(state.execution);
                speak(msg.content || '');
                break;

            case 'execution_cancelled':
                if (data.status === 'cancelling') {
                    addJarvisMessage(msg.content || "I'll stop the plan between steps.", true);
                } else {
                    state.execution = { goal: data.goal, steps: data.steps || [], status: data.status || 'cancelled' };
                    renderExecutionCard(state.execution);
                    speak(msg.content || '');
                }
                break;

            case 'execution_reset':
                addJarvisMessage(msg.content || 'OK, the plan is reset and approved.', true);
                break;

            case 'execution_status':
                if (data.status === 'idle' || data.status === 'pending_approval') {
                    addJarvisMessage(msg.content || '', true);
                } else {
                    state.execution = { goal: data.goal, steps: data.steps || [], status: data.status };
                    renderExecutionCard(state.execution);
                    speak(msg.content || '');
                }
                break;

            case 'error':
                addJarvisMessage(msg.content || "I couldn't process that.", true);
                break;

            default:
                addJarvisMessage(msg.content || '', true);
        }
    }

    // --------------------------------------------------
    // Message shell helper
    // --------------------------------------------------

    function createMessageShell() {
        const time = new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
        const div = document.createElement('div');
        div.className = 'message jarvis-message';

        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.innerHTML = '<div class="avatar-ring"></div><span>J</span>';

        const content = document.createElement('div');
        content.className = 'message-content';

        const header = document.createElement('div');
        header.className = 'message-header';
        const name = document.createElement('span');
        name.className = 'sender-name';
        name.textContent = 'J.A.R.V.I.S.';
        const timeEl = document.createElement('span');
        timeEl.className = 'message-time';
        timeEl.textContent = time;
        header.appendChild(name);
        header.appendChild(timeEl);

        content.appendChild(header);
        div.appendChild(avatar);
        div.appendChild(content);

        DOM.chatMessages.appendChild(div);
        scrollToBottom();

        return content;
    }

    function createElement(tag, className, text) {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text !== undefined && text !== null) node.textContent = text;
        return node;
    }

    // --------------------------------------------------
    // Plan approval card
    // --------------------------------------------------

    function renderPlanCard(data, decision) {
        const body = createMessageShell();
        const plan = data.plan || {};
        const steps = plan.steps || [];

        const card = document.createElement('div');
        card.className = 'zoey-plan-card';
        card.dataset.goal = data.goal || '';

        const header = document.createElement('div');
        header.className = 'zoey-card-header';
        header.innerHTML = '<span class="zoey-card-kicker">PROPOSED PLAN</span>';

        const goalEl = createElement('div', 'zoey-card-goal', data.goal || 'Untitled goal');

        const list = document.createElement('ol');
        list.className = 'zoey-plan-steps';

        steps.forEach((step) => {
            const li = document.createElement('li');
            li.className = 'zoey-plan-step';

            const num = createElement('span', 'zoey-plan-step-num', step.number);
            const stepBody = document.createElement('div');
            stepBody.className = 'zoey-plan-step-body';

            stepBody.appendChild(createElement('span', 'zoey-plan-step-title', step.title));

            const metaBits = [];
            if (step.tool) metaBits.push(step.tool);
            if (step.depends_on && step.depends_on.length) metaBits.push('after ' + step.depends_on.join(', '));
            if (metaBits.length) {
                stepBody.appendChild(createElement('span', 'zoey-plan-step-meta', metaBits.join(' · ')));
            }

            li.appendChild(num);
            li.appendChild(stepBody);
            list.appendChild(li);
        });

        const actions = document.createElement('div');
        actions.className = 'zoey-plan-actions';

        if (decision === null) {
            const approve = createElement('button', 'zoey-btn zoey-btn-approve', 'Approve');
            approve.addEventListener('click', () => handleApprove(card));
            const reject = createElement('button', 'zoey-btn zoey-btn-reject', 'Reject');
            reject.addEventListener('click', () => handleReject(card));
            actions.appendChild(approve);
            actions.appendChild(reject);
        } else if (decision === 'approved') {
            actions.appendChild(buildApprovedActions('Approved — ready to execute.'));
        } else {
            actions.appendChild(createElement('div', 'zoey-rejected-note', 'Discarded.'));
        }

        card.appendChild(header);
        card.appendChild(goalEl);
        card.appendChild(list);
        card.appendChild(actions);
        body.appendChild(card);

        state.planCardEl = card;
    }

    function buildApprovedActions(noteText) {
        const wrapper = document.createElement('div');
        wrapper.className = 'zoey-approved-actions';

        wrapper.appendChild(createElement('div', 'zoey-approved-note', noteText || 'Approved — ready to execute.'));

        const execute = createElement('button', 'zoey-btn zoey-btn-execute', 'Execute plan');
        execute.addEventListener('click', () => handleExecute());
        wrapper.appendChild(execute);

        return wrapper;
    }

    async function handleApprove(card) {
        if (state.approvalBusy) return;
        state.approvalBusy = true;
        card.classList.add('zoey-card-busy');

        try {
            const { data } = await JarvisAPI.approvePlan();
            state.decision = 'approved';
            const tasks = data.tasks || [];
            const note = tasks.length
                ? `Approved — ${tasks.length} task${tasks.length === 1 ? '' : 's'} saved. Execute the plan when ready.`
                : 'Plan approved. Execute the plan when ready.';
            addActivityLog(note, 'success');

            const actions = card.querySelector('.zoey-plan-actions');
            if (actions) {
                actions.innerHTML = '';
                actions.appendChild(buildApprovedActions(note));
            }
        } catch (err) {
            addActivityLog(`Approval failed: ${err.message}`, 'error');
            addJarvisMessage(`Approval failed: ${err.message}`);
        } finally {
            state.approvalBusy = false;
            card.classList.remove('zoey-card-busy');
        }
    }

    async function handleReject(card) {
        if (state.approvalBusy) return;
        state.approvalBusy = true;
        card.classList.add('zoey-card-busy');

        try {
            await JarvisAPI.rejectPlan();
            state.decision = 'rejected';
            addActivityLog('Plan discarded', 'warning');

            const actions = card.querySelector('.zoey-plan-actions');
            if (actions) {
                actions.innerHTML = '';
                actions.appendChild(createElement('div', 'zoey-rejected-note', 'Discarded.'));
            }
        } catch (err) {
            addActivityLog(`Reject failed: ${err.message}`, 'error');
            addJarvisMessage(`Reject failed: ${err.message}`);
        } finally {
            state.approvalBusy = false;
            card.classList.remove('zoey-card-busy');
        }
    }

    async function handleExecute() {
        if (state.executionBusy) return;
        state.executionBusy = true;
        if (state.planCardEl) state.planCardEl.classList.add('zoey-card-busy');

        try {
            await JarvisAPI.executePlan();
            state.execution = { goal: state.planGoal || '', steps: [], status: 'running' };
            setReactorState('processing');
            renderExecutionCard(state.execution);
            startExecutionPolling();
        } catch (err) {
            addActivityLog(`Execution error: ${err.message}`, 'error');
            addJarvisMessage(`I couldn't start execution: ${err.message}`);
        } finally {
            state.executionBusy = false;
            if (state.planCardEl) state.planCardEl.classList.remove('zoey-card-busy');
        }
    }

    // --------------------------------------------------
    // Execution card + status polling
    // --------------------------------------------------

    const TERMINAL_STATUSES = new Set([
        'completed',
        'failed',
        'cancelled',
        'blocked',
        'no_executable_steps',
    ]);

    const EXEC_STATUS_LABELS = {
        approved: 'APPROVED',
        running: 'EXECUTING',
        interrupted: 'INTERRUPTED',
        pending_approval: 'PENDING APPROVAL',
        idle: 'IDLE',
        completed: 'COMPLETED',
        failed: 'FAILED',
        cancelled: 'CANCELLED',
        blocked: 'BLOCKED',
        no_executable_steps: 'FINISHED',
        cancelling: 'CANCELLING',
    };

    const EXEC_STATUS_CLASS = {
        approved: 'zoey-exec-approved',
        running: 'zoey-exec-running',
        interrupted: 'zoey-exec-interrupted',
        pending_approval: 'zoey-exec-pending',
        idle: 'zoey-exec-idle',
        completed: 'zoey-exec-done',
        failed: 'zoey-exec-failed',
        cancelled: 'zoey-exec-cancelled',
        blocked: 'zoey-exec-blocked',
        no_executable_steps: 'zoey-exec-done',
        cancelling: 'zoey-exec-cancelling',
    };

    const STEP_LABELS = {
        pending: 'PENDING',
        running: 'RUNNING',
        completed: 'DONE',
        failed: 'FAILED',
        cancelled: 'CANCELLED',
        blocked: 'BLOCKED',
        not_auto: 'INFO',
    };

    const STEP_CLASS = {
        pending: 'zoey-step-pending',
        running: 'zoey-step-running',
        completed: 'zoey-step-done',
        failed: 'zoey-step-failed',
        cancelled: 'zoey-step-cancelled',
        blocked: 'zoey-step-blocked',
        not_auto: 'zoey-step-info',
    };

    function renderExecutionCard(execution) {
        const goal = execution.goal || state.planGoal || '';

        let card = state.executionCardEl;
        if (!card || card.dataset.goal !== goal) {
            card = null;
            state.executionCardEl = null;
        }

        if (!card) {
            const body = createMessageShell();
            card = document.createElement('div');
            card.className = 'zoey-exec-card';
            card.dataset.goal = goal;
            body.appendChild(card);
            state.executionCardEl = card;
        }

        updateExecutionCard(card, execution);
    }

    function updateExecutionCard(card, execution) {
        const status = execution.status || 'idle';
        const steps = execution.steps || [];
        const isTerminal = TERMINAL_STATUSES.has(status);

        const doneCount = steps.filter((s) => s.status === 'completed').length;
        const total = steps.length;
        const progress = total > 0 ? Math.round((doneCount / total) * 100) : 0;

        // Avoid re-rendering when nothing changed (prevents button flicker).
        const signature = status + '|' + steps.map((s) => s.number + ':' + s.status).join(',');
        if (card._sig === signature) return;
        card._sig = signature;

        card.className = 'zoey-exec-card ' + (EXEC_STATUS_CLASS[status] || '');
        card.innerHTML = '';

        const header = document.createElement('div');
        header.className = 'zoey-exec-header';
        header.appendChild(createElement('span', 'zoey-exec-title', EXEC_STATUS_LABELS[status] || (status || '').toUpperCase()));
        header.appendChild(createElement('span', 'zoey-exec-goal', execution.goal || state.planGoal || ''));

        const progressWrap = document.createElement('div');
        progressWrap.className = 'zoey-exec-progress';
        const fill = document.createElement('div');
        fill.className = 'zoey-exec-progress-fill';
        fill.style.width = progress + '%';
        progressWrap.appendChild(fill);

        const list = document.createElement('div');
        list.className = 'zoey-exec-steps';

        if (steps.length === 0) {
            list.appendChild(createElement('div', 'zoey-exec-empty', isTerminal ? 'No step details yet.' : 'Starting…'));
        } else {
            steps.forEach((step) => {
                const row = document.createElement('div');
                row.className = 'zoey-exec-step ' + (STEP_CLASS[step.status] || 'zoey-step-pending');

                row.appendChild(createElement('span', 'zoey-exec-step-num', step.number));

                const text = document.createElement('div');
                text.className = 'zoey-exec-step-text';
                text.appendChild(createElement('span', 'zoey-exec-step-name', step.title));
                if (step.status === 'failed' && step.result && step.result.error) {
                    text.appendChild(createElement('span', 'zoey-exec-step-error', step.result.error));
                }
                row.appendChild(text);

                row.appendChild(createElement('span', 'zoey-exec-step-status', STEP_LABELS[step.status] || (step.status || '').toUpperCase()));

                list.appendChild(row);
            });
        }

        const footer = document.createElement('div');
        footer.className = 'zoey-exec-footer';
        if (status === 'running') {
            const stop = createElement('button', 'zoey-btn-stop', 'Stop execution');
            stop.addEventListener('click', handleCancelExecution);
            footer.appendChild(stop);
        }

        card.appendChild(header);
        card.appendChild(progressWrap);
        card.appendChild(list);
        card.appendChild(footer);
    }

    function startExecutionPolling() {
        stopExecutionPolling();
        state.executionPolling = true;

        const tick = async () => {
            if (!state.executionPolling) return;
            try {
                const { data } = await JarvisAPI.status();
                handleExecutionStatus(data);

                const status = data.status || 'idle';
                if (TERMINAL_STATUSES.has(status)) {
                    stopExecutionPolling();
                    state.isProcessing = false;
                    setReactorState('standby');
                    const summary = summaryForStatus(status, data.steps || []);
                    addJarvisMessage(summary, true);
                    addActivityLog(`Execution ${status}`, 'success');
                }
            } catch (err) {
                console.warn('Status poll error:', err.message);
            }
        };

        state.executionPollTimer = setInterval(tick, 500);
        tick();
    }

    function stopExecutionPolling() {
        state.executionPolling = false;
        if (state.executionPollTimer) {
            clearInterval(state.executionPollTimer);
            state.executionPollTimer = null;
        }
    }

    function handleExecutionStatus(data) {
        const status = data.status || 'idle';
        if (status === 'idle' || status === 'pending_approval') return;

        const goal = data.goal || state.planGoal || '';
        const steps = data.steps || [];

        if (state.executionCardEl && state.executionCardEl.dataset.goal === goal) {
            updateExecutionCard(state.executionCardEl, { goal, steps, status });
        } else if (steps.length || status === 'running') {
            renderExecutionCard({ goal, steps, status });
        }
    }

    async function handleCancelExecution() {
        try {
            await JarvisAPI.cancelExecution();
            addActivityLog('Stop requested — finishing current step', 'warning');
        } catch (err) {
            addActivityLog(`Couldn't stop execution: ${err.message}`, 'error');
            addJarvisMessage(`I couldn't stop execution: ${err.message}`);
        }
    }

    function summaryForStatus(status, steps) {
        const done = steps.filter((s) => s.status === 'completed').length;
        const failed = steps.filter((s) => s.status === 'failed').length;

        if (status === 'cancelled') {
            return 'Plan stopped' + (done ? ` — ${done} step${done === 1 ? '' : 's'} done.` : '.');
        }
        if (status === 'failed') {
            return `Plan failed — ${failed} step${failed === 1 ? '' : 's'} failed, ${done} done.`;
        }
        if (status === 'blocked') {
            return "Plan blocked — some steps couldn't run.";
        }
        if (status === 'no_executable_steps') {
            return 'Plan saved, but none of the steps are auto-executable.';
        }
        return `Plan completed — ${done} step${done === 1 ? '' : 's'} done.`;
    }

    // --------------------------------------------------
    // Read-only resource commands (Quick Commands panel)
    // --------------------------------------------------

    async function handleResourceCommand(resource) {
        if (state.isProcessing) return;
        state.isProcessing = true;
        setReactorState('processing');

        try {
            let title = '';
            let items = [];
            let renderer = null;

            switch (resource) {
                case 'tasks': {
                    const { data } = await JarvisAPI.tasks();
                    title = 'TASKS';
                    items = data || [];
                    renderer = renderTaskItem;
                    break;
                }
                case 'events': {
                    const { data } = await JarvisAPI.events();
                    title = 'UPCOMING EVENTS';
                    items = data || [];
                    renderer = renderEventItem;
                    break;
                }
                case 'memories': {
                    const { data } = await JarvisAPI.memories();
                    title = 'MEMORIES';
                    items = data || [];
                    renderer = renderMemoryItem;
                    break;
                }
                case 'files': {
                    const { data } = await JarvisAPI.files('.');
                    title = 'FILES';
                    items = (data && data.entries) || [];
                    renderer = renderFileItem;
                    break;
                }
                case 'notifications': {
                    const { data } = await JarvisAPI.notifications();
                    title = 'NOTIFICATIONS';
                    items = data || [];
                    renderer = renderNotificationItem;
                    break;
                }
                case 'plans': {
                    const { data } = await JarvisAPI.plans();
                    title = 'SAVED PLANS';
                    items = (data && data.runs) || [];
                    renderer = renderPlanRunItem;
                    break;
                }
                default:
                    return;
            }

            renderResourceCard(title, items, renderer);
            addActivityLog(title.toLowerCase() + ' loaded', 'success');
        } catch (err) {
            addActivityLog(`Couldn't load that: ${err.message}`, 'error');
            addJarvisMessage(`I couldn't load that: ${err.message}`);
        } finally {
            state.isProcessing = false;
            setReactorState('standby');
        }
    }

    function renderResourceCard(title, items, itemRenderer) {
        const body = createMessageShell();

        const card = document.createElement('div');
        card.className = 'zoey-resource-card';

        const header = document.createElement('div');
        header.className = 'zoey-card-header';
        header.innerHTML = '<span class="zoey-card-kicker">' + title + '</span>';
        card.appendChild(header);

        if (!items.length) {
            card.appendChild(createElement('div', 'zoey-resource-empty', 'None found.'));
        } else {
            const list = document.createElement('div');
            list.className = 'zoey-resource-list';
            items.forEach((item) => {
                const row = document.createElement('div');
                row.className = 'zoey-resource-item';
                itemRenderer(row, item);
                list.appendChild(row);
            });
            card.appendChild(list);
        }

        body.appendChild(card);
    }

    function renderTaskItem(row, t) {
        const main = document.createElement('div');
        main.className = 'zoey-resource-row';
        main.appendChild(createElement('span', 'zoey-resource-title', t.title));
        main.appendChild(createElement('span', 'zoey-resource-badge ' + (t.status === 'completed' ? 'zoey-badge-done' : 'zoey-badge-pending'), t.status));
        row.appendChild(main);
        if (t.due_at) {
            row.appendChild(createElement('div', 'zoey-resource-sub', 'Due ' + t.due_at));
        }
    }

    function renderEventItem(row, e) {
        const main = document.createElement('div');
        main.className = 'zoey-resource-row';
        main.appendChild(createElement('span', 'zoey-resource-title', e.title));
        if (e.start_at) {
            main.appendChild(createElement('span', 'zoey-resource-badge zoey-badge-pending', e.start_at.replace('T', ' ').replace(/Z$/, '')));
        }
        row.appendChild(main);
        if (e.location) {
            row.appendChild(createElement('div', 'zoey-resource-sub', '📍 ' + e.location));
        }
        if (e.notes) {
            row.appendChild(createElement('div', 'zoey-resource-sub', e.notes));
        }
    }

    function renderMemoryItem(row, m) {
        const main = document.createElement('div');
        main.className = 'zoey-resource-row';
        main.appendChild(createElement('span', 'zoey-resource-title', m.content));
        main.appendChild(createElement('span', 'zoey-resource-badge zoey-badge-pending', m.memory_type || 'note'));
        row.appendChild(main);
        if (m.created_at) {
            row.appendChild(createElement('div', 'zoey-resource-sub', m.created_at));
        }
    }

    function renderFileItem(row, f) {
        const main = document.createElement('div');
        main.className = 'zoey-resource-row';
        main.appendChild(createElement('span', 'zoey-resource-title', f.name + (f.type === 'directory' ? '/' : '')));
        main.appendChild(createElement('span', 'zoey-resource-badge ' + (f.type === 'directory' ? 'zoey-badge-pending' : 'zoey-badge-done'), f.type));
        row.appendChild(main);
        const subBits = [];
        if (f.size !== undefined) subBits.push(f.size + ' B');
        if (f.modified_at) subBits.push('modified ' + f.modified_at);
        if (subBits.length) {
            row.appendChild(createElement('div', 'zoey-resource-sub', subBits.join(' · ')));
        }
    }

    function renderNotificationItem(row, n) {
        const main = document.createElement('div');
        main.className = 'zoey-resource-row';
        main.appendChild(createElement('span', 'zoey-resource-title', n.title));
        if (n.created_at) {
            main.appendChild(createElement('span', 'zoey-resource-badge zoey-badge-pending', n.created_at));
        }
        row.appendChild(main);
        if (n.message) {
            row.appendChild(createElement('div', 'zoey-resource-sub', n.message));
        }
    }

    function renderPlanRunItem(row, r) {
        const main = document.createElement('div');
        main.className = 'zoey-resource-row';
        main.appendChild(createElement('span', 'zoey-resource-title', r.goal));
        main.appendChild(createElement('span', 'zoey-resource-badge ' + (r.status === 'completed' ? 'zoey-badge-done' : r.status === 'failed' || r.status === 'cancelled' ? 'zoey-badge-error' : 'zoey-badge-pending'), r.status));
        row.appendChild(main);
        if (r.created_at) {
            row.appendChild(createElement('div', 'zoey-resource-sub', 'Run ' + r.run_id + ' · ' + r.created_at));
        }
    }

    // ===========================
    // Offline AI (Fallback)
    // ===========================
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
            return `Currently in offline mode, my capabilities include:\n\n• 🕐 Time & Date — real-time clock\n• 😄 Jokes and fun facts\n• 💡 Motivational quotes\n• 🎤 Voice input/output\n\nFor my full capabilities — planning, tasks, memory, files, calendar, app control and more — make sure the Zoey backend is running and serving this page.`;
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
            return "I can calculate that once my Zoey backend core is online. Please start the backend and ask again.";
        }

        // Diagnostics
        if (/\b(diagnostic|system|status|health)\b/.test(lower)) {
            addActivityLog('Running diagnostics...', 'warning');
            setTimeout(() => addActivityLog('Diagnostics complete ✓', 'success'), 1000);
            return `Running full system diagnostics...\n\n✅ Neural Network — Operational\n✅ Voice Module — Active\n✅ Speech Synthesis — Online\n✅ HUD Renderer — Nominal\n✅ Security — AES-256 Active\n${state.backendOnline ? '✅ Zoey Core — Connected' : '⚠️ Zoey Core — Offline'}\n\nAll core systems operating within normal parameters.`;
        }

        // Default
        return pick([
            `I'm currently in offline mode with limited capabilities. To get a complete answer to your query, make sure the Zoey backend is running and serving this page.`,
            `That's a great question, but I'd need my Zoey core online to give you a proper answer. Please check that the backend is running, then try again.`,
            `I wish I could help more with that in offline mode. Once the Zoey backend is running, I'll have the intelligence to handle any request.`,
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
