// views/LoginView.jsx
//
// Handles both new and returning users with a single form:
//
//   1. User types their username and hits Enter (or clicks Continue)
//   2. We check if that username exists via GET /api/users/?username=...
//      - Exists   → log them straight in, no extra fields needed
//      - Not found → reveal display name / skills / color fields to register
//   3. On register, POST /api/users/ creates the account then logs them in

import { useState, useEffect, useRef } from "react";
import { Avatar } from "../components/Avatar";
import { AVATAR_COLORS } from "../constants";
import { createUser, getUserByUsername } from "../api";

const INPUT_STYLE = {
  width: "100%", padding: "10px 12px",
  border: "1px solid #E2E8F0", borderRadius: 10,
  fontSize: 14, boxSizing: "border-box", outline: "none",
};

export function LoginView({ onLogin }) {
  // "username" → just the username field shown
  // "register" → full registration fields revealed
  const [step, setStep] = useState("username");


  const [username, setUsername]   = useState("");
  const [form, setForm]           = useState({
    display_name: "",
    skills: "",
    avatar_color: AVATAR_COLORS[0],
  });

  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState("");

  // Track component mount status to prevent state updates on unmounted components
  const isMountedRef = useRef(true);

  useEffect(() => {
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  // ── Step 1: check if username exists ────────────────────────────────────────

  async function handleUsernameSubmit(e) {
    e.preventDefault();
    if (!username.trim()) return;
    setLoading(true);
    setError("");
try {
  const existing = await getUserByUsername(username.trim());

  if (existing) {
    onLogin(existing);
  } else {
    setStep("register");
  }
} catch (err) {
  setError("Could not reach the server. Is the backend running?");
} finally {
  setLoading(false);
}
  }

  // ── Step 2: register new user ────────────────────────────────────────────────

  async function handleRegisterSubmit(e) {
    e.preventDefault();
    if (!form.display_name.trim()) return;
    setLoading(true);
    setError("");
    try {
      const user = await createUser({
        username: username.trim(),
        display_name: form.display_name.trim(),
        skills: form.skills.split(",").map((s) => s.trim()).filter(Boolean),
        avatar_color: form.avatar_color,
      });
      // Only update state if component is still mounted
      if (!isMountedRef.current) return;
      onLogin(user);
    } catch (err) {

      if (!isMountedRef.current) return;
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  // ── Render ───────────────────────────────────────────────────────────────────

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "linear-gradient(135deg, #F8FAFF 0%, #F0F4FF 100%)",
        display: "flex", alignItems: "center", justifyContent: "center",
        padding: 20, fontFamily: "system-ui, sans-serif",
      }}
    >
      <div
        style={{
          background: "white", borderRadius: 20, padding: 40,
          width: "100%", maxWidth: 440,
          boxShadow: "0 4px 40px rgba(124,58,237,0.12)",
        }}
      >
        {/* Brand */}
        <div style={{ textAlign: "center", marginBottom: 28 }}>
          <div
            style={{
              width: 56, height: 56,
              background: "linear-gradient(135deg,#7C3AED,#4F46E5)",
              borderRadius: 16, display: "flex", alignItems: "center",
              justifyContent: "center", margin: "0 auto 12px", fontSize: 28,
            }}
          >
            🧠
          </div>
          <h1 style={{ margin: 0, fontSize: 24, fontWeight: 700, color: "#1E293B" }}>
            MindBridge
          </h1>
          <p style={{ margin: "6px 0 0", fontSize: 14, color: "#64748B" }}>
            Real-time mind-link collaboration
          </p>
        </div>

        {/* ── Step 1: username only ── */}
        {step === "username" && (
          <form onSubmit={handleUsernameSubmit}>
            <div style={{ marginBottom: 16 }}>
              <label style={{ display: "block", fontSize: 12, fontWeight: 500, color: "#64748B", marginBottom: 5 }}>
                Username
              </label>
              <input
                autoFocus
                type="text"
                placeholder="ino_yamanaka"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                style={INPUT_STYLE}
              />
              <p style={{ margin: "6px 0 0", fontSize: 11, color: "#94A3B8" }}>
                Returning? Just enter your username. New here? We'll set you up next.
              </p>
            </div>

            {error && (
              <p style={{ color: "#DC2626", fontSize: 13, marginBottom: 12 }}>{error}</p>
            )}

            <button
              type="submit"
              disabled={loading || !username.trim()}
              style={{
                width: "100%", padding: "12px",
                background: username.trim()
                  ? "linear-gradient(135deg,#7C3AED,#4F46E5)"
                  : "#E2E8F0",
                color: username.trim() ? "white" : "#94A3B8",
                border: "none", borderRadius: 12,
                fontSize: 15, fontWeight: 600, cursor: username.trim() ? "pointer" : "default",
                transition: "all 0.15s",
              }}
            >
              {loading ? "Checking..." : "Continue →"}
            </button>
          </form>
        )}

        {/* ── Step 2: registration fields ── */}
        {step === "register" && (
          <form onSubmit={handleRegisterSubmit}>
            {/* Show username as read-only with a back link */}
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
              <div>
                <div style={{ fontSize: 11, color: "#94A3B8" }}>Username</div>
                <div style={{ fontSize: 14, fontWeight: 600, color: "#1E293B" }}>{username}</div>
              </div>
              <button
                type="button"
                onClick={() => { setStep("username"); setError(""); }}
                style={{ background: "none", border: "none", color: "#7C3AED", cursor: "pointer", fontSize: 12 }}
              >
                ← Change
              </button>
            </div>

            <div
              style={{
                background: "#F0FDF4", border: "1px solid #86EFAC",
                borderRadius: 8, padding: "8px 12px", marginBottom: 16,
                fontSize: 12, color: "#166534",
              }}
            >
              Username not found — fill in your details to register.
            </div>

            {/* Display name */}
            <div style={{ marginBottom: 14 }}>
              <label style={{ display: "block", fontSize: 12, fontWeight: 500, color: "#64748B", marginBottom: 5 }}>
                Display Name
              </label>
              <input
                autoFocus
                type="text"
                placeholder="Ino Yamanaka"
                value={form.display_name}
                onChange={(e) => setForm((p) => ({ ...p, display_name: e.target.value }))}
                style={INPUT_STYLE}
              />
            </div>

            {/* Skills */}
            <div style={{ marginBottom: 14 }}>
              <label style={{ display: "block", fontSize: 12, fontWeight: 500, color: "#64748B", marginBottom: 5 }}>
                Skills <span style={{ color: "#94A3B8", fontWeight: 400 }}>(comma-separated)</span>
              </label>
              <input
                type="text"
                placeholder="backend, devops, security"
                value={form.skills}
                onChange={(e) => setForm((p) => ({ ...p, skills: e.target.value }))}
                style={INPUT_STYLE}
              />
              <p style={{ margin: "4px 0 0", fontSize: 11, color: "#94A3B8" }}>
                Used to route signals to the right people
              </p>
            </div>

            {/* Avatar color */}
            <div style={{ marginBottom: 20 }}>
              <label style={{ display: "block", fontSize: 12, fontWeight: 500, color: "#64748B", marginBottom: 6 }}>
                Avatar Color
              </label>
              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                {AVATAR_COLORS.map((c) => (
                  <div
                    key={c}
                    onClick={() => setForm((p) => ({ ...p, avatar_color: c }))}
                    style={{
                      width: 28, height: 28, borderRadius: "50%",
                      background: c, cursor: "pointer",
                      border: form.avatar_color === c ? "3px solid #1E293B" : "2px solid transparent",
                      boxSizing: "border-box", transition: "border 0.15s",
                    }}
                  />
                ))}
                <Avatar name={form.display_name || username} color={form.avatar_color} size={28} />
              </div>
            </div>

            {error && (
              <p style={{ color: "#DC2626", fontSize: 13, marginBottom: 12 }}>{error}</p>
            )}

            <button
              type="submit"
              disabled={loading || !form.display_name.trim()}
              style={{
                width: "100%", padding: "12px",
                background: form.display_name.trim()
                  ? "linear-gradient(135deg,#7C3AED,#4F46E5)"
                  : "#E2E8F0",
                color: form.display_name.trim() ? "white" : "#94A3B8",
                border: "none", borderRadius: 12,
                fontSize: 15, fontWeight: 600,
                cursor: form.display_name.trim() ? "pointer" : "default",
                transition: "all 0.15s",
              }}
            >
              {loading ? "Creating account..." : "Enter the Mind-Link →"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}