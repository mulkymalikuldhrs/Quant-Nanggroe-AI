// 🧠 Agentic AI System - Service Worker
// PWA Service Worker for offline functionality and app-like experience
// Made with ❤️ by Mulky Malikul Dhaher in Indonesia 🇮🇩

const CACHE_NAME = 'agentic-ai-v2.0.0';
const urlsToCache = [
  '/',
  '/static/css/main.css',
  '/static/js/main.js',
  '/static/js/voice.js',
  '/static/js/pwa.js',
  '/static/manifest.json',
  '/static/icons/icon-192x192.png',
  '/static/icons/icon-512x512.png',
  '/agents',
  '/workflows',
  '/monitoring',
  '/offline.html'
];

// Install event - cache resources
self.addEventListener('install', (event) => {
  console.log('🚀 Agentic AI Service Worker installing...');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('📦 Caching app resources');
        return cache.addAll(urlsToCache);
      })
      .then(() => {
        console.log('✅ Service Worker installed successfully');
        return self.skipWaiting();
      })
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  console.log('🔄 Agentic AI Service Worker activating...');
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            console.log('🗑️ Removing old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => {
      console.log('✅ Service Worker activated');
      return self.clients.claim();
    })
  );
});

// Fetch event - serve from cache, fallback to network
self.addEventListener('fetch', (event) => {
  // Skip non-GET requests
  if (event.request.method !== 'GET') {
    return;
  }

  // Skip external requests (APIs, CDNs)
  if (!event.request.url.startsWith(self.location.origin)) {
    return;
  }

  event.respondWith(
    caches.match(event.request)
      .then((response) => {
        // Return cached version if available
        if (response) {
          return response;
        }

        // Clone the request because it's a stream
        const fetchRequest = event.request.clone();

        return fetch(fetchRequest).then((response) => {
          // Check if valid response
          if (!response || response.status !== 200 || response.type !== 'basic') {
            return response;
          }

          // Clone the response because it's a stream
          const responseToCache = response.clone();

          caches.open(CACHE_NAME)
            .then((cache) => {
              cache.put(event.request, responseToCache);
            });

          return response;
        }).catch(() => {
          // Return offline page for navigation requests
          if (event.request.mode === 'navigate') {
            return caches.match('/offline.html');
          }
        });
      })
  );
});

// Background sync for offline actions
self.addEventListener('sync', (event) => {
  console.log('🔄 Background sync:', event.tag);
  
  if (event.tag === 'agent-task') {
    event.waitUntil(syncAgentTasks());
  }
  
  if (event.tag === 'voice-commands') {
    event.waitUntil(syncVoiceCommands());
  }
});

// Push notifications
self.addEventListener('push', (event) => {
  console.log('📢 Push notification received');
  
  const options = {
    body: event.data ? event.data.text() : 'Agentic AI System notification',
    icon: '/static/icons/icon-192x192.png',
    badge: '/static/icons/badge-72x72.png',
    vibrate: [100, 50, 100],
    data: {
      dateOfArrival: Date.now(),
      primaryKey: 1
    },
    actions: [
      {
        action: 'explore',
        title: 'Open App',
        icon: '/static/icons/explore.png'
      },
      {
        action: 'close',
        title: 'Close',
        icon: '/static/icons/close.png'
      }
    ]
  };

  event.waitUntil(
    self.registration.showNotification('🧠 Agentic AI System', options)
  );
});

// Notification click handling
self.addEventListener('notificationclick', (event) => {
  console.log('📱 Notification clicked:', event.action);
  
  event.notification.close();

  if (event.action === 'explore') {
    event.waitUntil(
      clients.openWindow('/')
    );
  }
});

// Message handling for communication with main app
self.addEventListener('message', (event) => {
  console.log('💬 Message received:', event.data);
  
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
  
  if (event.data && event.data.type === 'CACHE_AGENT') {
    cacheNewAgent(event.data.agentData);
  }
});

// Helper functions
async function syncAgentTasks() {
  try {
    const tasks = await getStoredTasks();
    for (const task of tasks) {
      await submitTask(task);
      await removeStoredTask(task.id);
    }
    console.log('✅ Agent tasks synced successfully');
  } catch (error) {
    console.error('❌ Error syncing agent tasks:', error);
  }
}

async function syncVoiceCommands() {
  try {
    const commands = await getStoredVoiceCommands();
    for (const command of commands) {
      await processVoiceCommand(command);
      await removeStoredVoiceCommand(command.id);
    }
    console.log('✅ Voice commands synced successfully');
  } catch (error) {
    console.error('❌ Error syncing voice commands:', error);
  }
}

async function cacheNewAgent(agentData) {
  try {
    const cache = await caches.open(CACHE_NAME);
    const agentUrl = `/agents/${agentData.id}`;
    await cache.add(agentUrl);
    console.log('✅ New agent cached:', agentData.name);
  } catch (error) {
    console.error('❌ Error caching new agent:', error);
  }
}

// IndexedDB helpers for offline storage
async function getStoredTasks() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('AgenticAI', 1);
    request.onsuccess = (event) => {
      const db = event.target.result;
      const transaction = db.transaction(['tasks'], 'readonly');
      const store = transaction.objectStore('tasks');
      const getAll = store.getAll();
      getAll.onsuccess = () => resolve(getAll.result);
      getAll.onerror = () => reject(getAll.error);
    };
    request.onerror = () => reject(request.error);
  });
}

async function getStoredVoiceCommands() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('AgenticAI', 1);
    request.onsuccess = (event) => {
      const db = event.target.result;
      const transaction = db.transaction(['voiceCommands'], 'readonly');
      const store = transaction.objectStore('voiceCommands');
      const getAll = store.getAll();
      getAll.onsuccess = () => resolve(getAll.result);
      getAll.onerror = () => reject(getAll.error);
    };
    request.onerror = () => reject(request.error);
  });
}

console.log('🧠 Agentic AI Service Worker loaded - Made with ❤️ by Mulky Malikul Dhaher 🇮🇩');
