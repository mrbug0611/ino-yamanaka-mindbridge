// api.js - all backend communication in one place 

const API_BASE = import.meta.env.VITE_API_BASE || '/api';

const json = (res) => {
    if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
    }

    return res.json();
};


const post = (url, body) => {
    return fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }, 
        body: JSON.stringify(body),
    });
};

export async function createUser(data) {
    const res = await post(`${API_BASE}/users`, data);

    if (res.status === 409) {
        throw new Error('User already exists');
    }

    if (!res.ok) {
        throw new Error("Login failed");
    }

    return res.json();
};


export const getUser = (userId) =>
  fetch(`${API_BASE}/users/${userId}`).then(json);
 
export const listUsers = () =>
  fetch(`${API_BASE}/users/`).then(json);

// Returns the matching user or null if username not found
export async function getUserByUsername(username) {
  const results = await fetch(
    `${API_BASE}/users/?username=${encodeURIComponent(username)}`
  ).then(json);
  return results.length > 0 ? results[0] : null;
}
 
// ── Sessions ──────────────────────────────────────────────────────────────────
 
export const listSessions = () =>
  fetch(`${API_BASE}/sessions/?status=active`).then(json);
 
export const getSession = (sessionId) =>
  fetch(`${API_BASE}/sessions/${sessionId}`).then(json);
 
export const createSession = (data) =>
  post(`${API_BASE}/sessions/`, data).then(json);
 
export const joinSession = (sessionId, userId) =>
  post(`${API_BASE}/sessions/${sessionId}/join?user_id=${userId}`).then(json);
 
export const endSession = (sessionId) =>
  post(`${API_BASE}/sessions/${sessionId}/end`).then(json);
 
// ── Signals ───────────────────────────────────────────────────────────────────
 
export const getSessionSignals = (sessionId) =>
  fetch(`${API_BASE}/signals/session/${sessionId}`).then(json);
 
export const getSignal = (signalId) =>
  fetch(`${API_BASE}/signals/${signalId}`).then(json);
 
export const createSignal = (data) =>
  post(`${API_BASE}/signals/`, data).then(json);
 
export const addReaction = (signalId, data) =>
  post(`${API_BASE}/signals/${signalId}/react`, data).then(json);