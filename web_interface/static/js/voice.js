// 🧠 Agentic AI System - Voice Interaction Controller
// Advanced voice interaction with AI agents like Gemini AI
// Made with ❤️ by Mulky Malikul Dhaher in Indonesia 🇮🇩

class AgenticVoice {
    constructor() {
        this.isListening = false;
        this.isProcessing = false;
        this.isSpeaking = false;
        this.recognition = null;
        this.synthesis = null;
        this.currentLanguage = 'en-US';
        this.supportedLanguages = {
            'en-US': 'English (US)',
            'id-ID': 'Bahasa Indonesia',
            'en-GB': 'English (UK)',
            'ja-JP': '日本語',
            'ko-KR': '한국어',
            'zh-CN': '中文 (简体)',
            'es-ES': 'Español',
            'fr-FR': 'Français',
            'de-DE': 'Deutsch',
            'pt-BR': 'Português (Brasil)'
        };
        this.voiceCommands = [];
        this.conversationHistory = [];
        this.init();
    }

    init() {
        console.log('🎤 Initializing Agentic AI Voice System...');
        
        // Check browser support
        if (!this.checkBrowserSupport()) {
            console.error('❌ Voice features not supported in this browser');
            return;
        }

        // Initialize speech recognition
        this.initSpeechRecognition();
        
        // Initialize speech synthesis
        this.initSpeechSynthesis();
        
        // Setup voice commands
        this.setupVoiceCommands();
        
        // Setup UI elements
        this.setupVoiceUI();
        
        // Setup hotkey activation
        this.setupHotkeyActivation();
        
        console.log('✅ Agentic AI Voice System initialized successfully');
    }

    checkBrowserSupport() {
        const hasRecognition = 'webkitSpeechRecognition' in window || 'SpeechRecognition' in window;
        const hasSynthesis = 'speechSynthesis' in window;
        
        if (!hasRecognition) {
            this.showError('Speech recognition not supported in this browser');
            return false;
        }
        
        if (!hasSynthesis) {
            this.showError('Speech synthesis not supported in this browser');
            return false;
        }
        
        return true;
    }

    initSpeechRecognition() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        this.recognition = new SpeechRecognition();
        
        // Configure recognition
        this.recognition.continuous = false;
        this.recognition.interimResults = true;
        this.recognition.lang = this.currentLanguage;
        this.recognition.maxAlternatives = 3;
        
        // Event handlers
        this.recognition.onstart = () => {
            console.log('🎤 Voice recognition started');
            this.isListening = true;
            this.updateVoiceUI();
            this.showVoiceIndicator('Listening...');
        };

        this.recognition.onend = () => {
            console.log('🎤 Voice recognition ended');
            this.isListening = false;
            this.updateVoiceUI();
            this.hideVoiceIndicator();
        };

        this.recognition.onresult = (event) => {
            let finalTranscript = '';
            let interimTranscript = '';

            for (let i = event.resultIndex; i < event.results.length; i++) {
                const transcript = event.results[i][0].transcript;
                
                if (event.results[i].isFinal) {
                    finalTranscript += transcript;
                } else {
                    interimTranscript += transcript;
                }
            }

            // Update UI with interim results
            if (interimTranscript) {
                this.showVoiceIndicator(`Listening: "${interimTranscript}"`);
            }

            // Process final result
            if (finalTranscript) {
                console.log('🎤 Voice input:', finalTranscript);
                this.processVoiceInput(finalTranscript.trim());
            }
        };

        this.recognition.onerror = (event) => {
            console.error('❌ Voice recognition error:', event.error);
            this.isListening = false;
            this.updateVoiceUI();
            
            let errorMessage = 'Voice recognition error';
            switch (event.error) {
                case 'network':
                    errorMessage = 'Network error. Please check your connection.';
                    break;
                case 'not-allowed':
                    errorMessage = 'Microphone access denied. Please allow microphone access.';
                    break;
                case 'no-speech':
                    errorMessage = 'No speech detected. Please try again.';
                    break;
                case 'audio-capture':
                    errorMessage = 'Audio capture failed. Please check your microphone.';
                    break;
            }
            
            this.showError(errorMessage);
        };
    }

    initSpeechSynthesis() {
        this.synthesis = window.speechSynthesis;
        
        // Load available voices
        this.loadVoices();
        
        // Update voices when they change
        this.synthesis.onvoiceschanged = () => {
            this.loadVoices();
        };
    }

    loadVoices() {
        const voices = this.synthesis.getVoices();
        this.availableVoices = voices;
        
        // Find best voice for current language
        this.selectBestVoice();
        
        console.log(`🔊 Loaded ${voices.length} voices`);
    }

    selectBestVoice() {
        const voices = this.availableVoices;
        if (!voices || voices.length === 0) return;

        // Try to find a voice that matches current language
        let selectedVoice = voices.find(voice => 
            voice.lang === this.currentLanguage
        );

        // Fallback to default voice
        if (!selectedVoice) {
            selectedVoice = voices.find(voice => voice.default) || voices[0];
        }

        this.currentVoice = selectedVoice;
        console.log('🔊 Selected voice:', selectedVoice?.name);
    }

    setupVoiceCommands() {
        this.voiceCommands = [
            {
                patterns: ['create agent', 'make agent', 'new agent', 'buat agent'],
                action: 'createAgent',
                description: 'Create a new AI agent'
            },
            {
                patterns: ['create app', 'make app', 'build app', 'buat aplikasi'],
                action: 'createApp',
                description: 'Create a new application'
            },
            {
                patterns: ['show agents', 'list agents', 'tampilkan agent'],
                action: 'showAgents',
                description: 'Show all available agents'
            },
            {
                patterns: ['open agent manager', 'agent manager', 'manager agent'],
                action: 'openAgentManager',
                description: 'Open agent manager'
            },
            {
                patterns: ['generate code', 'write code', 'tulis kode'],
                action: 'generateCode',
                description: 'Generate code'
            },
            {
                patterns: ['deploy app', 'deploy application', 'deploy ke production'],
                action: 'deployApp',
                description: 'Deploy application'
            },
            {
                patterns: ['system status', 'check status', 'status sistem'],
                action: 'systemStatus',
                description: 'Check system status'
            },
            {
                patterns: ['help', 'bantuan', 'what can you do'],
                action: 'showHelp',
                description: 'Show available commands'
            },
            {
                patterns: ['stop listening', 'berhenti mendengar'],
                action: 'stopListening',
                description: 'Stop voice recognition'
            },
            {
                patterns: ['change language', 'ganti bahasa'],
                action: 'changeLanguage',
                description: 'Change language'
            }
        ];
    }

    setupVoiceUI() {
        // Create voice button if it doesn't exist
        if (!document.getElementById('voice-btn')) {
            this.createVoiceButton();
        }

        // Create voice indicator
        if (!document.getElementById('voice-indicator')) {
            this.createVoiceIndicator();
        }

        // Create voice controls panel
        if (!document.getElementById('voice-controls')) {
            this.createVoiceControls();
        }
    }

    createVoiceButton() {
        const voiceBtn = document.createElement('button');
        voiceBtn.id = 'voice-btn';
        voiceBtn.className = 'voice-btn';
        voiceBtn.innerHTML = `
            <i class="fas fa-microphone"></i>
            <span class="voice-text">Voice</span>
        `;
        voiceBtn.title = 'Click to start voice interaction (or press Ctrl+Space)';
        voiceBtn.onclick = () => this.toggleVoiceRecognition();
        
        // Add to navigation or create floating button
        const nav = document.querySelector('nav') || document.querySelector('.navbar');
        if (nav) {
            nav.appendChild(voiceBtn);
        } else {
            voiceBtn.classList.add('floating-voice-btn');
            document.body.appendChild(voiceBtn);
        }
    }

    createVoiceIndicator() {
        const indicator = document.createElement('div');
        indicator.id = 'voice-indicator';
        indicator.className = 'voice-indicator hidden';
        indicator.innerHTML = `
            <div class="voice-indicator-content">
                <div class="voice-animation">
                    <div class="voice-wave"></div>
                    <div class="voice-wave"></div>
                    <div class="voice-wave"></div>
                </div>
                <div class="voice-status">Ready to listen...</div>
            </div>
        `;
        
        document.body.appendChild(indicator);
    }

    createVoiceControls() {
        const controls = document.createElement('div');
        controls.id = 'voice-controls';
        controls.className = 'voice-controls hidden';
        controls.innerHTML = `
            <div class="voice-controls-panel">
                <h3>🎤 Voice Controls</h3>
                <div class="voice-settings">
                    <label for="voice-lang">Language:</label>
                    <select id="voice-lang" onchange="agenticVoice.changeLanguage(this.value)">
                        ${Object.entries(this.supportedLanguages).map(([code, name]) => 
                            `<option value="${code}" ${code === this.currentLanguage ? 'selected' : ''}>${name}</option>`
                        ).join('')}
                    </select>
                </div>
                <div class="voice-commands-list">
                    <h4>Available Commands:</h4>
                    <ul>
                        ${this.voiceCommands.map(cmd => 
                            `<li><strong>"${cmd.patterns[0]}"</strong> - ${cmd.description}</li>`
                        ).join('')}
                    </ul>
                </div>
                <div class="voice-controls-buttons">
                    <button onclick="agenticVoice.toggleVoiceRecognition()" class="btn btn-primary">
                        <i class="fas fa-microphone"></i> Start Listening
                    </button>
                    <button onclick="agenticVoice.toggleVoiceControls()" class="btn btn-secondary">
                        Close
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(controls);
    }

    setupHotkeyActivation() {
        document.addEventListener('keydown', (event) => {
            // Ctrl+Space to toggle voice recognition
            if (event.ctrlKey && event.code === 'Space') {
                event.preventDefault();
                this.toggleVoiceRecognition();
            }
            
            // Ctrl+Shift+V to open voice controls
            if (event.ctrlKey && event.shiftKey && event.key === 'V') {
                event.preventDefault();
                this.toggleVoiceControls();
            }
            
            // Escape to stop voice recognition
            if (event.key === 'Escape' && this.isListening) {
                event.preventDefault();
                this.stopVoiceRecognition();
            }
        });
    }

    toggleVoiceRecognition() {
        if (this.isListening) {
            this.stopVoiceRecognition();
        } else {
            this.startVoiceRecognition();
        }
    }

    async startVoiceRecognition() {
        if (this.isListening || this.isProcessing) return;

        try {
            // Request microphone permission
            await agenticPWA.requestDeviceAccess('microphone');
            
            this.recognition.start();
            console.log('🎤 Starting voice recognition...');
        } catch (error) {
            console.error('❌ Failed to start voice recognition:', error);
            this.showError('Failed to access microphone. Please check permissions.');
        }
    }

    stopVoiceRecognition() {
        if (!this.isListening) return;
        
        this.recognition.stop();
        console.log('🎤 Stopping voice recognition...');
    }

    async processVoiceInput(input) {
        if (this.isProcessing) return;
        
        this.isProcessing = true;
        this.showVoiceIndicator('Processing...');
        
        console.log('🧠 Processing voice input:', input);
        
        try {
            // Add to conversation history
            this.conversationHistory.push({
                type: 'user',
                content: input,
                timestamp: Date.now()
            });

            // Check for voice commands first
            const command = this.matchVoiceCommand(input);
            if (command) {
                await this.executeVoiceCommand(command, input);
            } else {
                // Send to AI agent for processing
                await this.sendToAgent(input);
            }
            
        } catch (error) {
            console.error('❌ Error processing voice input:', error);
            this.speak('Sorry, I encountered an error processing your request.');
        } finally {
            this.isProcessing = false;
            this.hideVoiceIndicator();
        }
    }

    matchVoiceCommand(input) {
        const lowercaseInput = input.toLowerCase();
        
        for (const command of this.voiceCommands) {
            for (const pattern of command.patterns) {
                if (lowercaseInput.includes(pattern.toLowerCase())) {
                    return command;
                }
            }
        }
        
        return null;
    }

    async executeVoiceCommand(command, input) {
        console.log('🎯 Executing voice command:', command.action);
        
        switch (command.action) {
            case 'createAgent':
                await this.createAgent(input);
                break;
            case 'createApp':
                await this.createApp(input);
                break;
            case 'showAgents':
                await this.showAgents();
                break;
            case 'openAgentManager':
                this.openAgentManager();
                break;
            case 'generateCode':
                await this.generateCode(input);
                break;
            case 'deployApp':
                await this.deployApp(input);
                break;
            case 'systemStatus':
                await this.getSystemStatus();
                break;
            case 'showHelp':
                this.showVoiceHelp();
                break;
            case 'stopListening':
                this.stopVoiceRecognition();
                break;
            case 'changeLanguage':
                this.showLanguageSelector();
                break;
            default:
                await this.sendToAgent(input);
        }
    }

    async sendToAgent(input) {
        try {
            const response = await fetch('/api/prompt/process', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    prompt: input,
                    input_type: 'voice',
                    metadata: {
                        language: this.currentLanguage,
                        timestamp: Date.now()
                    }
                })
            });

            const result = await response.json();
            
            if (result.success) {
                let responseText = '';
                
                if (result.data && result.data.response) {
                    responseText = result.data.response;
                } else if (result.data && result.data.message) {
                    responseText = result.data.message;
                } else {
                    responseText = 'Task completed successfully!';
                }
                
                // Add to conversation history
                this.conversationHistory.push({
                    type: 'agent',
                    content: responseText,
                    timestamp: Date.now()
                });
                
                // Speak the response
                await this.speak(responseText);
                
            } else {
                throw new Error(result.error || 'Unknown error');
            }
            
        } catch (error) {
            console.error('❌ Error sending to agent:', error);
            
            // Store for offline sync if offline
            if (!navigator.onLine) {
                await agenticPWA.storeOfflineVoiceCommand({
                    input: input,
                    timestamp: Date.now(),
                    language: this.currentLanguage
                });
                await this.speak('You are offline. I will process this when you are back online.');
            } else {
                await this.speak('Sorry, I could not process your request. Please try again.');
            }
        }
    }

    async speak(text, options = {}) {
        if (this.isSpeaking) {
            this.synthesis.cancel();
        }

        return new Promise((resolve, reject) => {
            const utterance = new SpeechSynthesisUtterance(text);
            
            // Configure utterance
            utterance.voice = this.currentVoice;
            utterance.lang = this.currentLanguage;
            utterance.rate = options.rate || 1;
            utterance.pitch = options.pitch || 1;
            utterance.volume = options.volume || 1;

            // Event handlers
            utterance.onstart = () => {
                this.isSpeaking = true;
                console.log('🔊 Speaking:', text);
            };

            utterance.onend = () => {
                this.isSpeaking = false;
                console.log('🔊 Speaking completed');
                resolve();
            };

            utterance.onerror = (error) => {
                this.isSpeaking = false;
                console.error('❌ Speech synthesis error:', error);
                reject(error);
            };

            // Speak
            this.synthesis.speak(utterance);
        });
    }

    // Voice command implementations
    async createAgent(input) {
        const agentType = this.extractAgentType(input);
        await this.speak(`Creating a new ${agentType} agent. Please wait...`);
        
        // Navigate to agent creation or trigger agent maker
        window.location.href = '/agents?action=create&type=' + agentType;
    }

    async createApp(input) {
        const appType = this.extractAppType(input);
        await this.speak(`I will help you create a ${appType}. Let me start the development process.`);
        
        // Send to fullstack dev agent
        await this.sendToAgent(`Create a ${appType}: ${input}`);
    }

    async showAgents() {
        try {
            const response = await fetch('/api/agents/list');
            const result = await response.json();
            
            if (result.success) {
                const agentCount = result.data.length;
                const activeCount = result.data.filter(a => a.status === 'ready').length;
                
                await this.speak(`You have ${agentCount} agents total, with ${activeCount} currently active.`);
                
                // Navigate to agents page
                window.location.href = '/agents';
            }
        } catch (error) {
            await this.speak('Unable to retrieve agent information.');
        }
    }

    openAgentManager() {
        window.location.href = '/agents';
        this.speak('Opening agent manager.');
    }

    async generateCode(input) {
        await this.speak('I will generate code for you. Please wait...');
        await this.sendToAgent(`Generate code: ${input}`);
    }

    async deployApp(input) {
        await this.speak('Starting deployment process. This may take a few minutes.');
        await this.sendToAgent(`Deploy application: ${input}`);
    }

    async getSystemStatus() {
        try {
            const response = await fetch('/api/system/status');
            const result = await response.json();
            
            if (result.success) {
                const status = result.data;
                await this.speak(`System is ${status.system_status}. ${status.agents_active} agents are active out of ${status.total_agents} total.`);
            }
        } catch (error) {
            await this.speak('Unable to retrieve system status.');
        }
    }

    showVoiceHelp() {
        this.toggleVoiceControls();
        this.speak('Voice controls panel opened. You can see all available commands there.');
    }

    showLanguageSelector() {
        this.toggleVoiceControls();
        this.speak('Opening language settings. You can change the voice language there.');
    }

    // Utility methods
    extractAgentType(input) {
        const types = ['data scientist', 'web developer', 'content writer', 'devops engineer', 'designer'];
        for (const type of types) {
            if (input.toLowerCase().includes(type)) {
                return type;
            }
        }
        return 'general purpose';
    }

    extractAppType(input) {
        const types = ['web app', 'mobile app', 'api', 'website', 'dashboard'];
        for (const type of types) {
            if (input.toLowerCase().includes(type)) {
                return type;
            }
        }
        return 'application';
    }

    changeLanguage(languageCode) {
        this.currentLanguage = languageCode;
        if (this.recognition) {
            this.recognition.lang = languageCode;
        }
        this.selectBestVoice();
        console.log('🌐 Language changed to:', languageCode);
    }

    // UI helper methods
    updateVoiceUI() {
        const voiceBtn = document.getElementById('voice-btn');
        if (voiceBtn) {
            if (this.isListening) {
                voiceBtn.classList.add('listening');
                voiceBtn.innerHTML = `<i class="fas fa-microphone-slash"></i><span class="voice-text">Stop</span>`;
            } else {
                voiceBtn.classList.remove('listening');
                voiceBtn.innerHTML = `<i class="fas fa-microphone"></i><span class="voice-text">Voice</span>`;
            }
        }
    }

    showVoiceIndicator(message) {
        const indicator = document.getElementById('voice-indicator');
        if (indicator) {
            indicator.querySelector('.voice-status').textContent = message;
            indicator.classList.remove('hidden');
        }
    }

    hideVoiceIndicator() {
        const indicator = document.getElementById('voice-indicator');
        if (indicator) {
            indicator.classList.add('hidden');
        }
    }

    toggleVoiceControls() {
        const controls = document.getElementById('voice-controls');
        if (controls) {
            controls.classList.toggle('hidden');
        }
    }

    showError(message) {
        console.error('❌ Voice Error:', message);
        
        // Show error notification
        const notification = document.createElement('div');
        notification.className = 'voice-error-notification';
        notification.innerHTML = `
            <div class="error-content">
                <i class="fas fa-exclamation-triangle"></i>
                <span>${message}</span>
                <button onclick="this.parentElement.parentElement.remove()">×</button>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 5000);
    }
}

// Initialize voice system when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.agenticVoice = new AgenticVoice();
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AgenticVoice;
}

console.log('🎤 Agentic AI Voice Controller loaded - Made with ❤️ by Mulky Malikul Dhaher 🇮🇩');
