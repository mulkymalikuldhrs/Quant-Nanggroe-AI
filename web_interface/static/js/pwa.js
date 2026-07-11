// 🧠 Agentic AI System - PWA Controller
// Progressive Web App functionality and installation
// Made with ❤️ by Mulky Malikul Dhaher in Indonesia 🇮🇩

class AgenticPWA {
    constructor() {
        this.deferredPrompt = null;
        this.isInstalled = false;
        this.init();
    }

    init() {
        console.log('🚀 Initializing Agentic AI PWA...');
        
        // Register service worker
        this.registerServiceWorker();
        
        // Setup installation handlers
        this.setupInstallHandlers();
        
        // Check if already installed
        this.checkInstallationStatus();
        
        // Setup offline detection
        this.setupOfflineDetection();
        
        // Initialize IndexedDB for offline storage
        this.initOfflineStorage();
        
        console.log('✅ Agentic AI PWA initialized successfully');
    }

    async registerServiceWorker() {
        if ('serviceWorker' in navigator) {
            try {
                const registration = await navigator.serviceWorker.register('/static/sw.js');
                console.log('✅ Service Worker registered:', registration.scope);
                
                // Handle service worker updates
                registration.addEventListener('updatefound', () => {
                    const newWorker = registration.installing;
                    newWorker.addEventListener('statechange', () => {
                        if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                            this.showUpdateNotification();
                        }
                    });
                });
                
            } catch (error) {
                console.error('❌ Service Worker registration failed:', error);
            }
        }
    }

    setupInstallHandlers() {
        // Listen for install prompt
        window.addEventListener('beforeinstallprompt', (e) => {
            console.log('📱 Install prompt available');
            e.preventDefault();
            this.deferredPrompt = e;
            this.showInstallButton();
        });

        // Listen for app installed
        window.addEventListener('appinstalled', () => {
            console.log('✅ Agentic AI installed as PWA');
            this.isInstalled = true;
            this.hideInstallButton();
            this.showWelcomeMessage();
        });

        // Setup install button click handler
        const installBtn = document.getElementById('install-btn');
        if (installBtn) {
            installBtn.addEventListener('click', () => this.installApp());
        }
    }

    async installApp() {
        if (!this.deferredPrompt) {
            console.log('❌ Install prompt not available');
            return;
        }

        try {
            this.deferredPrompt.prompt();
            const { outcome } = await this.deferredPrompt.userChoice;
            
            if (outcome === 'accepted') {
                console.log('✅ User accepted install');
            } else {
                console.log('❌ User dismissed install');
            }
            
            this.deferredPrompt = null;
        } catch (error) {
            console.error('❌ Install error:', error);
        }
    }

    showInstallButton() {
        const installBtn = document.getElementById('install-btn');
        const installBanner = document.getElementById('install-banner');
        
        if (installBtn) {
            installBtn.style.display = 'block';
            installBtn.innerHTML = `
                <i class="fas fa-download"></i>
                Install Agentic AI
            `;
        }
        
        if (installBanner) {
            installBanner.style.display = 'block';
            installBanner.innerHTML = `
                <div class="install-banner">
                    <div class="install-content">
                        <h3>🧠 Install Agentic AI</h3>
                        <p>Get the full app experience with offline access and voice commands!</p>
                        <button onclick="agenticPWA.installApp()" class="btn btn-primary">
                            <i class="fas fa-mobile-alt"></i> Add to Home Screen
                        </button>
                        <button onclick="this.parentElement.parentElement.style.display='none'" class="btn btn-secondary">
                            Later
                        </button>
                    </div>
                </div>
            `;
        }
    }

    hideInstallButton() {
        const installBtn = document.getElementById('install-btn');
        const installBanner = document.getElementById('install-banner');
        
        if (installBtn) installBtn.style.display = 'none';
        if (installBanner) installBanner.style.display = 'none';
    }

    checkInstallationStatus() {
        // Check if running as PWA
        const isStandalone = window.matchMedia('(display-mode: standalone)').matches;
        const isFullscreen = window.matchMedia('(display-mode: fullscreen)').matches;
        const isMinimalUI = window.matchMedia('(display-mode: minimal-ui)').matches;
        
        this.isInstalled = isStandalone || isFullscreen || isMinimalUI || 
                          (window.navigator.standalone === true);
        
        if (this.isInstalled) {
            console.log('✅ Running as installed PWA');
            this.hideInstallButton();
            document.body.classList.add('pwa-installed');
        }
    }

    setupOfflineDetection() {
        const updateOnlineStatus = () => {
            const statusElement = document.getElementById('connection-status');
            
            if (navigator.onLine) {
                console.log('🌐 Online');
                document.body.classList.remove('offline');
                document.body.classList.add('online');
                if (statusElement) {
                    statusElement.innerHTML = '<i class="fas fa-wifi"></i> Online';
                    statusElement.className = 'status online';
                }
            } else {
                console.log('📴 Offline');
                document.body.classList.remove('online');
                document.body.classList.add('offline');
                if (statusElement) {
                    statusElement.innerHTML = '<i class="fas fa-wifi-slash"></i> Offline';
                    statusElement.className = 'status offline';
                }
                this.showOfflineMessage();
            }
        };

        window.addEventListener('online', updateOnlineStatus);
        window.addEventListener('offline', updateOnlineStatus);
        updateOnlineStatus();
    }

    async initOfflineStorage() {
        try {
            const db = await this.openDB();
            console.log('✅ Offline storage initialized');
            return db;
        } catch (error) {
            console.error('❌ Offline storage initialization failed:', error);
        }
    }

    openDB() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open('AgenticAI', 1);
            
            request.onupgradeneeded = (event) => {
                const db = event.target.result;
                
                // Create object stores
                if (!db.objectStoreNames.contains('tasks')) {
                    const taskStore = db.createObjectStore('tasks', { keyPath: 'id', autoIncrement: true });
                    taskStore.createIndex('timestamp', 'timestamp', { unique: false });
                }
                
                if (!db.objectStoreNames.contains('voiceCommands')) {
                    const voiceStore = db.createObjectStore('voiceCommands', { keyPath: 'id', autoIncrement: true });
                    voiceStore.createIndex('timestamp', 'timestamp', { unique: false });
                }
                
                if (!db.objectStoreNames.contains('agents')) {
                    const agentStore = db.createObjectStore('agents', { keyPath: 'id' });
                    agentStore.createIndex('name', 'name', { unique: false });
                }
            };
            
            request.onsuccess = (event) => resolve(event.target.result);
            request.onerror = (event) => reject(event.target.error);
        });
    }

    async storeOfflineTask(task) {
        try {
            const db = await this.openDB();
            const transaction = db.transaction(['tasks'], 'readwrite');
            const store = transaction.objectStore('tasks');
            
            task.timestamp = Date.now();
            task.offline = true;
            
            await store.add(task);
            console.log('💾 Task stored for offline sync');
            
            // Request background sync
            if ('serviceWorker' in navigator && 'sync' in window.ServiceWorkerRegistration.prototype) {
                const registration = await navigator.serviceWorker.ready;
                await registration.sync.register('agent-task');
            }
        } catch (error) {
            console.error('❌ Error storing offline task:', error);
        }
    }

    async storeOfflineVoiceCommand(command) {
        try {
            const db = await this.openDB();
            const transaction = db.transaction(['voiceCommands'], 'readwrite');
            const store = transaction.objectStore('voiceCommands');
            
            command.timestamp = Date.now();
            command.offline = true;
            
            await store.add(command);
            console.log('🎤 Voice command stored for offline sync');
            
            // Request background sync
            if ('serviceWorker' in navigator && 'sync' in window.ServiceWorkerRegistration.prototype) {
                const registration = await navigator.serviceWorker.ready;
                await registration.sync.register('voice-commands');
            }
        } catch (error) {
            console.error('❌ Error storing offline voice command:', error);
        }
    }

    showUpdateNotification() {
        const notification = document.createElement('div');
        notification.className = 'update-notification';
        notification.innerHTML = `
            <div class="update-content">
                <h4>🆕 Update Available</h4>
                <p>A new version of Agentic AI is ready!</p>
                <button onclick="agenticPWA.applyUpdate()" class="btn btn-primary">Update Now</button>
                <button onclick="this.parentElement.parentElement.remove()" class="btn btn-secondary">Later</button>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.classList.add('show');
        }, 100);
    }

    async applyUpdate() {
        if ('serviceWorker' in navigator) {
            const registration = await navigator.serviceWorker.getRegistration();
            if (registration && registration.waiting) {
                registration.waiting.postMessage({ type: 'SKIP_WAITING' });
                window.location.reload();
            }
        }
    }

    showWelcomeMessage() {
        const welcome = document.createElement('div');
        welcome.className = 'welcome-notification';
        welcome.innerHTML = `
            <div class="welcome-content">
                <h3>🎉 Welcome to Agentic AI!</h3>
                <p>App installed successfully. Enjoy offline access and voice commands!</p>
                <p><small>Made with ❤️ by Mulky Malikul Dhaher 🇮🇩</small></p>
                <button onclick="this.parentElement.parentElement.remove()" class="btn btn-primary">Get Started</button>
            </div>
        `;
        
        document.body.appendChild(welcome);
        
        setTimeout(() => {
            welcome.classList.add('show');
        }, 100);
        
        setTimeout(() => {
            welcome.remove();
        }, 5000);
    }

    showOfflineMessage() {
        const offline = document.createElement('div');
        offline.className = 'offline-notification';
        offline.innerHTML = `
            <div class="offline-content">
                <h4>📴 You're Offline</h4>
                <p>Don't worry! You can still use voice commands and basic features.</p>
                <p>Your actions will sync when you're back online.</p>
            </div>
        `;
        
        document.body.appendChild(offline);
        
        setTimeout(() => {
            offline.classList.add('show');
        }, 100);
        
        setTimeout(() => {
            offline.remove();
        }, 4000);
    }

    // Device integration helpers
    async requestDeviceAccess(type) {
        try {
            switch (type) {
                case 'camera':
                    const stream = await navigator.mediaDevices.getUserMedia({ video: true });
                    console.log('📹 Camera access granted');
                    return stream;
                
                case 'microphone':
                    const audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    console.log('🎤 Microphone access granted');
                    return audioStream;
                
                case 'location':
                    const position = await new Promise((resolve, reject) => {
                        navigator.geolocation.getCurrentPosition(resolve, reject);
                    });
                    console.log('📍 Location access granted');
                    return position;
                
                case 'notifications':
                    const permission = await Notification.requestPermission();
                    console.log('🔔 Notification permission:', permission);
                    return permission === 'granted';
                
                default:
                    throw new Error('Unknown device access type');
            }
        } catch (error) {
            console.error(`❌ Error requesting ${type} access:`, error);
            throw error;
        }
    }

    // Share API integration
    async shareContent(data) {
        if (navigator.share) {
            try {
                await navigator.share(data);
                console.log('✅ Content shared successfully');
            } catch (error) {
                console.error('❌ Error sharing content:', error);
                this.fallbackShare(data);
            }
        } else {
            this.fallbackShare(data);
        }
    }

    fallbackShare(data) {
        // Fallback share implementation
        const shareUrl = `mailto:?subject=${encodeURIComponent(data.title)}&body=${encodeURIComponent(data.text + ' ' + data.url)}`;
        window.open(shareUrl);
    }
}

// Initialize PWA when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.agenticPWA = new AgenticPWA();
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AgenticPWA;
}

console.log('🧠 Agentic AI PWA Controller loaded - Made with ❤️ by Mulky Malikul Dhaher 🇮🇩');
