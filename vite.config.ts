import path from 'path';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// SECURITY NOTE: API keys (GEMINI_API_KEY, GOOGLE_DRIVE_FOLDER_ID) must NOT be
// injected into the client bundle via `define`. They are managed at runtime
// through the application's Settings panel and stored in IndexedDB/localStorage.
// Exposing them in the bundle would make them accessible to anyone inspecting
// the browser's developer tools.

export default defineConfig({
    server: {
      port: 3000,
      host: '0.0.0.0',
    },
    plugins: [react()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, '.'),
      }
    }
});
