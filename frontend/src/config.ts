// The backend serves this build from the same origin, so API calls are relative.
// In dev, vite's proxy (see vite.config.ts) forwards them to the Flask server.
// Set VITE_API_URL at build time only to point at a separately hosted backend.
export const API_URL = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '');
