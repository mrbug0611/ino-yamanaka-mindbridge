// views/LobbyView.jsx

import { useState, useEffect, useRef } from "react";
import { Avatar } from "../components/Avatar";
import { Badge } from "../components/Badge";
import { TOPIC_STYLES, HEADER_STYLE } from "../constants";
import { listSessions, createSession, joinSession, getSession, getSessionSignals } from "../api";

// ── Toast notification ─────────────────────────────────────────────────────────

function Toast({ message, type, onDone }) {
  useEffect(() => {
    const t = setTimeout(onDone, 2500);
    return () => clearTimeout(t);
  }, [onDone]);

  const colors = {
    success: { bg: "#F0FDF4", border: "#86EFAC", text: "#166534" },
    error:   { bg: "#FEF2F2", border: "#FCA5A5", text: "#991B1B" },
    info:    { bg: "#EFF6FF", border: "#93C5FD", text: "#1E40AF" },
  };
  const c = colors[type] || colors.info;

  return (
    <div style={{
      position: "fixed", bottom: 24, left: "50%",
      transform: "translateX(-50%)",
      background: c.bg, border: `1px solid ${c.border}`,
      color: c.text, borderRadius: 10,
      padding: "10px 20px", fontSize: 13, fontWeight: 500,
      boxShadow: "0 4px 20px rgba(0,0,0,0.1)",
      zIndex: 50, whiteSpace: "nowrap",
      animation: "fadeUp 0.2s ease",
    }}>
      <style>{`@keyframes fadeUp{from{opacity:0;transform:translate(-50%,8px)}to{opacity:1;transform:translate(-50%,0)}}`}</style>
      {message}
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────

export function LobbyView({ user, onJoinSession, onLogout }) {
  const isMountedRef = useRef(true);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
    };
  }, []);


  const [sessions, setSessions]     = useState([]);
  const [newSession, setNewSession] = useState({ title: "", description: "" });
  const [loading, setLoading]       = useState(false);
  const [joiningId, setJoiningId]   = useState(null); // tracks which session is being joined
  const [error, setError]           = useState("");
  const [toast, setToast]           = useState(null); // { message, type }

  useEffect(() => {
    loadSessions();
  }, []);

  function showToast(message, type = "success") {
    setToast({ message, type });
  }

  async function loadSessions() {
    try {
      const data = await listSessions();
      if (!isMountedRef.current) return;
      setSessions(data);
    } catch {
        if (!isMountedRef.current) return;
      setError("Failed to load sessions");
    }
  }

  async function handleCreateSession(e) {
    e.preventDefault();
    if (!newSession.title.trim()) return;
    setLoading(true);
    setError("");
    try {
      const sess = await createSession({ ...newSession, host_id: user.id });
      if (!isMountedRef.current) return;
      showToast(`Session "${sess.title}" created — joining now...`, "success");
      setNewSession({ title: "", description: "" });
      await loadSessions();
      await handleJoin(sess, true); // true = already showing toast
    } catch (err) {
        if (!isMountedRef.current) return;
      setError(err.message);
      showToast("Failed to create session", "error");
    } finally {
        if (isMountedRef.current) {
          setLoading(false);
        }
    }
  }

  async function handleJoin(sess, skipToast = false) {
    setJoiningId(sess.id);
    try {
      await joinSession(sess.id, user.id);
      if (!isMountedRef.current) return;
      if (!skipToast) showToast(`Joined "${sess.title}"`, "success");
      const [signals, fullSession] = await Promise.all([
        getSessionSignals(sess.id),
        getSession(sess.id),
      ]);

      if (!isMountedRef.current) return;
      // Small delay so the toast is visible before the view changes
      await new Promise((r) => setTimeout(r, 600));
      if (!isMountedRef.current) return;
      onJoinSession(fullSession, signals);
    } catch (err) {
         if (!isMountedRef.current) return;
      setError(err.message);
      showToast("Failed to join session", "error");
    } finally {
        if (isMountedRef.current) {
          setJoiningId(null);
        }
    }
  }

  return (
    <div style={{ minHeight: "100vh", background: "#F8FAFF", fontFamily: "system-ui, sans-serif" }}>

      {/* Header */}
      <div style={HEADER_STYLE}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ fontSize: 22 }}>🧠</span>
          <span style={{ fontWeight: 700, fontSize: 16, color: "#1E293B" }}>MindBridge</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <Avatar name={user.display_name} color={user.avatar_color} size={30} />
          <span style={{ fontSize: 13, color: "#64748B" }}>{user.display_name}</span>
          <button
            onClick={onLogout}
            style={{
              marginLeft: 4, padding: "5px 12px",
              background: "none", border: "1px solid #E2E8F0",
              borderRadius: 8, fontSize: 12, color: "#94A3B8", cursor: "pointer",
            }}
          >
            Sign out
          </button>
        </div>
      </div>

      <div style={{ maxWidth: 760, margin: "0 auto", padding: "28px 20px" }}>

        {/* Welcome banner — shown on first visit */}
        <div style={{
          background: "linear-gradient(135deg, #EEF2FF, #F5F3FF)",
          border: "1px solid #C7D2FE", borderRadius: 12,
          padding: "14px 20px", marginBottom: 20,
          display: "flex", alignItems: "center", gap: 12,
        }}>
          <Avatar name={user.display_name} color={user.avatar_color} size={36} />
          <div>
            <div style={{ fontWeight: 600, fontSize: 14, color: "#1E293B" }}>
              Welcome back, {user.display_name} 👋
            </div>
            <div style={{ fontSize: 12, color: "#6366F1", marginTop: 2 }}>
              {user.skills?.length > 0
                ? `Skills: ${user.skills.join(", ")}`
                : "No skills set — signals will be broadcast to everyone"}
            </div>
          </div>
        </div>

        {/* Create session */}
        <div style={{
          background: "white", borderRadius: 16, padding: 24,
          marginBottom: 24, border: "1px solid #E2E8F0",
        }}>
          <h2 style={{ margin: "0 0 16px", fontSize: 16, fontWeight: 600, color: "#1E293B" }}>
            <i className="ti ti-plus" style={{ marginRight: 6, color: "#7C3AED" }} aria-hidden />
            Start a New Session
          </h2>
          <form onSubmit={handleCreateSession} style={{ display: "flex", gap: 10 }}>
            <input
              placeholder="Session title..."
              value={newSession.title}
              onChange={(e) => setNewSession((p) => ({ ...p, title: e.target.value }))}
              style={{ flex: 1, padding: "10px 14px", border: "1px solid #E2E8F0", borderRadius: 10, fontSize: 14, outline: "none" }}
            />
            <input
              placeholder="Description (optional)"
              value={newSession.description}
              onChange={(e) => setNewSession((p) => ({ ...p, description: e.target.value }))}
              style={{ flex: 1, padding: "10px 14px", border: "1px solid #E2E8F0", borderRadius: 10, fontSize: 14, outline: "none" }}
            />
            <button
              type="submit"
              disabled={loading || !newSession.title.trim()}
              style={{
                padding: "10px 20px",
                background: newSession.title.trim() ? "#7C3AED" : "#E2E8F0",
                color: newSession.title.trim() ? "white" : "#94A3B8",
                border: "none", borderRadius: 10, fontWeight: 600,
                cursor: newSession.title.trim() ? "pointer" : "default",
                whiteSpace: "nowrap", transition: "all 0.15s",
              }}
            >
              {loading ? "Creating..." : "Create"}
            </button>
          </form>
          {error && <p style={{ color: "#DC2626", fontSize: 13, marginTop: 8 }}>{error}</p>}
        </div>

        {/* Session list header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
          <h2 style={{ margin: 0, fontSize: 16, fontWeight: 600, color: "#1E293B" }}>
            Active Sessions
            {sessions.length > 0 && (
              <span style={{
                marginLeft: 8, fontSize: 12, fontWeight: 500,
                background: "#EEF2FF", color: "#4F46E5",
                padding: "2px 8px", borderRadius: 99,
              }}>
                {sessions.length}
              </span>
            )}
          </h2>
          <button
            onClick={loadSessions}
            style={{ background: "none", border: "none", color: "#7C3AED", cursor: "pointer", fontSize: 13 }}
          >
            <i className="ti ti-refresh" style={{ marginRight: 4 }} aria-hidden />
            Refresh
          </button>
        </div>

        {/* Session list */}
        {sessions.length === 0 ? (
          <div style={{ textAlign: "center", padding: "48px 20px", color: "#94A3B8", fontSize: 14 }}>
            No active sessions — start one above!
          </div>
        ) : (
          sessions.map((sess) => {
            const isJoining = joiningId === sess.id;
            return (
              <div
                key={sess.id}
                style={{
                  background: "white", borderRadius: 12, padding: "16px 20px",
                  border: `1px solid ${isJoining ? "#A5B4FC" : "#E2E8F0"}`,
                  marginBottom: 10,
                  display: "flex", alignItems: "center", justifyContent: "space-between",
                  transition: "border-color 0.2s",
                }}
              >
                <div>
                  <div style={{ fontWeight: 600, fontSize: 14, color: "#1E293B", marginBottom: 4 }}>
                    {sess.title}
                  </div>
                  {sess.description && (
                    <div style={{ fontSize: 12, color: "#94A3B8", marginBottom: 4 }}>
                      {sess.description}
                    </div>
                  )}
                  <div style={{ fontSize: 12, color: "#64748B", display: "flex", gap: 10, alignItems: "center" }}>
                    <span>
                      <i className="ti ti-users" style={{ marginRight: 3 }} aria-hidden />
                      {sess.member_count} {sess.member_count === 1 ? "member" : "members"}
                    </span>
                    {sess.topic && (
                      <Badge
                        label={sess.topic}
                        style={{ ...(TOPIC_STYLES[sess.topic] || TOPIC_STYLES.general), border: "none" }}
                      />
                    )}
                  </div>
                </div>
                <button
                  onClick={() => handleJoin(sess)}
                  disabled={joiningId !== null}
                  style={{
                    padding: "8px 18px",
                    background: isJoining ? "#EEF2FF" : "#EEF2FF",
                    color: "#4F46E5",
                    border: "none", borderRadius: 8, fontWeight: 600,
                    cursor: joiningId ? "default" : "pointer", fontSize: 13,
                    minWidth: 80, transition: "all 0.15s",
                  }}
                >
                  {isJoining ? "Joining..." : "Join →"}
                </button>
              </div>
            );
          })
        )}
      </div>

      {/* Toast */}
      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onDone={() => setToast(null)}
        />
      )}
    </div>
  );
}