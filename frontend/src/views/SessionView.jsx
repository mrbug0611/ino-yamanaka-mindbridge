//views/SessionView.jsx

import { useState, useEffect, useRef, useCallback } from "react"; //useCallback for memoizing websocket callbacks
import { Avatar } from "../components/Avatar";
import { Badge } from "../components/Badge";
import { SignalCard } from "../components/SignalCard";
import { OnlineUsers } from "../components/Onlineusers";
import { SummaryPanel } from "../components/SummaryPanel";
import { TOPIC_STYLES, REACTIONS, HEADER_STYLE } from "../constants";
import { createSignal, addReaction, endSession } from "../api";
import { useWebSocket } from "../hooks/Usewebsocket";

export function SessionView({user, session, initialSignals, onLeave }) {
    const [signals, setSignals]         = useState(initialSignals || []);
    const [onlineIds, setOnlineIds]     = useState([]);
    const [typingUsers, setTypingUsers] = useState([]);
    const [input, setInput]             = useState("");
    const [sending, setSending]         = useState(false);
    const [summary, setSummary]         = useState(null);
    const [newSignalIds, setNewSignalIds] = useState(new Set());
    const [dimmedIds, setDimmedIds]       = useState(new Set());
    
    const messagesEndRef = useRef(null);
    const typingTimeoutRef = useRef(null);


  // ── WebSocket callbacks ────────────────────────────────────────────────────
  const onSignal = useCallback((sig, isDimmed) => {
    setSignals((prev) => {
        if (prev.find(s => s.id === sig.id)) return prev; // deduplication
        return [...prev, sig]; 
    });

    if (isDimmed) {
        setDimmedIds((prev) => new Set([...prev, sig.id])); // track dimmed signals
    }
    else {
        setNewSignalIds((prev) => new Set([...prev, sig.id])); // track new signals
        setTimeout(() => {
            setNewSignalIds((prev) => {
                const n = new Set(prev);
                n.delete(sig.id); // remove highlight after 5 seconds
                return n;
            });
        }, 800); // highlight new signals for 0.8 seconds
    }
  }, []);

  const onReactionUpdate = useCallback((signalId, reactions) => {
    setSignals((prev) => prev.map(s => s.id === signalId ? {...s, reactions} : s)); // update reactions for the signal
  }, []);

  const onPresenceChange = useCallback((ids) => {
    setOnlineIds(ids);
  }, []);

  const onTypingChange = useCallback((userId, isTyping) => {
    setTypingUsers((prev) =>
      isTyping
        ? [...new Set([...prev, userId])]
        : prev.filter((id) => id !== userId)
    );
  }, []);

  const onSessionEnded = useCallback(() => {
    setSummary({ message: "Session has ended" }); 
  }, []);

  const { connect, disconnect, notifyTyping } = useWebSocket({
    onSignal,
    onReactionUpdate,
    onPresenceChange,
    onTypingChange,
    onSessionEnded,
  });

    // ── Lifecycle ──────────────────────────────────────────────────────────────
    useEffect(() => {
        connect(session.id, user.id);
        return () => disconnect();
    }, [session.id, user.id, connect, disconnect]);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [signals]);

    // ── Actions ────────────────────────────────────────────────────────────────
    async function handleSendSignal(e) {
        e.preventDefault();
        if (!input.trim() || sending) return;
        // Immediately clear typing timeout and notify server we stopped typing
        if (typingTimeoutRef.current) {
            clearTimeout(typingTimeoutRef.current);
            typingTimeoutRef.current = null;
        }
        notifyTyping(false); // Tell server we are done typing
        setSending(true);
        try {
            const sig = await createSignal({
                session_id: session.id,
                sender_id: user.id,
                content: input.trim(),
            });
            setSignals((prev) => [...prev.filter(s => s.id !== sig.id), sig]);
            setInput("");
        } finally {
            setSending(false);
        }
    }

    function handleInputChange(val) {
        setInput(val);

        // If the input was empty and they started typing, send "true" immediately
        if (!typingTimeoutRef.current && val.trim().length > 0) {
            notifyTyping(true);
        }

        // Clear the previous timeout clock
        if (typingTimeoutRef.current) {
            clearTimeout(typingTimeoutRef.current);
        }
        
        // Start a fresh 2-second countdown before marking them as stopped
        typingTimeoutRef.current = setTimeout(() => {
            notifyTyping(false);
            typingTimeoutRef.current = null;
        }, 2000);
    }

    async function handleReact(signalId, reaction) {
        try {
            await addReaction(signalId, { user_id: user.id, reaction });
        } catch (error) {
            console.error("Failed to add reaction:", error);
        }
    }

    async function handleEndSession() {
        try {
            const data = await endSession(session.id);
            setSummary(data.summary);
        } catch (error) {
            console.error("Failed to end session:", error);
        }
    }

    function handleLeave() {
        disconnect();
        onLeave();
    }

  // ── Derived ────────────────────────────────────────────────────────────────
    const members = session.members || [];
    const typingNames = typingUsers
        .filter((id) => id !== user.id) // Don't show your own name to yourself
        .map((id) => members.find((m) => m.id === id)?.display_name)
        .filter(Boolean);

    const topicCounts = signals.reduce((acc, s) => {
        acc[s.topic] = (acc[s.topic] || 0) + 1;
        return acc;
    }, {}); 


// ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column", background: "#F8FAFF", fontFamily: "system-ui, sans-serif" }}>
 
      {/* Header */}
      <div style={HEADER_STYLE}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{ fontSize: 20 }}>🧠</span>
          <div>
            <div style={{ fontWeight: 700, fontSize: 14, color: "#1E293B" }}>{session.title}</div>
            <div style={{ fontSize: 11, color: "#7C3AED" }}>
              <i className="ti ti-circle-filled" style={{ fontSize: 8, marginRight: 4 }} aria-hidden />
              {onlineIds.length} online
            </div>
          </div>
        </div>
 
        <OnlineUsers members={members} onlineIds={onlineIds} />
 
        <div style={{ display: "flex", gap: 8 }}>
          <button
            onClick={handleEndSession}
            style={{
              padding: "7px 14px", background: "#FEF2F2", color: "#DC2626",
              border: "1px solid #FCA5A5", borderRadius: 8,
              cursor: "pointer", fontSize: 12, fontWeight: 500,
            }}
          >
            End & Summarize
          </button>
          <button
            onClick={handleLeave}
            style={{
              padding: "7px 14px", background: "#F1F5F9", color: "#475569",
              border: "1px solid #E2E8F0", borderRadius: 8,
              cursor: "pointer", fontSize: 12,
            }}
          >
            Leave
          </button>
        </div>
      </div>
 
      {/* Topic cluster bar */}
      {signals.length > 0 && (
        <div style={{ padding: "8px 20px", background: "white", borderBottom: "1px solid #F1F5F9", display: "flex", gap: 6, flexWrap: "wrap" }}>
          {Object.entries(topicCounts).map(([topic, count]) => {
            const s = TOPIC_STYLES[topic] || TOPIC_STYLES.general;
            return (
              <Badge
                key={topic}
                label={`${topic} · ${count}`}
                style={{ background: s.bg, color: s.text, border: `1px solid ${s.border}`, fontSize: 11 }}
              />
            );
          })}
        </div>
      )}
 
      {/* Signal feed */}
      <div style={{ flex: 1, overflowY: "auto", padding: "16px 20px" }}>
        {signals.length === 0 && (
          <div style={{ textAlign: "center", padding: "60px 20px", color: "#94A3B8" }}>
            <div style={{ fontSize: 40, marginBottom: 12 }}>🧠</div>
            <div style={{ fontSize: 15, fontWeight: 500 }}>The mind-link is open</div>
            <div style={{ fontSize: 13, marginTop: 6 }}>
              Send your first thought — it will be routed automatically
            </div>
          </div>
        )}
 
        {signals.map((sig) => (
          <SignalCard
            key={sig.id}
            signal={sig}
            currentUserId={user.id}
            onReact={handleReact}
            isNew={newSignalIds.has(sig.id)}
            dimmed={dimmedIds.has(sig.id)}
          />
        ))}
 
        {typingNames.length > 0 && (
          <div style={{ fontSize: 12, color: "#94A3B8", padding: "4px 8px" }}>
            {typingNames.join(", ")} {typingNames.length === 1 ? "is" : "are"} thinking...
          </div>
        )}
 
        <div ref={messagesEndRef} />
      </div>
 
      {/* Input bar */}
      <div style={{ background: "white", borderTop: "1px solid #E2E8F0", padding: "12px 20px" }}>
        <form onSubmit={handleSendSignal} style={{ display: "flex", gap: 10 }}>
          <Avatar name={user.display_name} color={user.avatar_color} size={34} />
          <input
            placeholder="Send a thought... (NLP will classify and route it automatically)"
            value={input}
            onChange={(e) => handleInputChange(e.target.value)}
            style={{
              flex: 1, padding: "10px 16px",
              border: "1px solid #E2E8F0", borderRadius: 99,
              fontSize: 14, outline: "none", background: "#F8FAFF",
            }}
          />
          <button
            type="submit"
            disabled={sending || !input.trim()}
            style={{
              padding: "10px 20px",
              background: input.trim() ? "#7C3AED" : "#E2E8F0",
              color: input.trim() ? "white" : "#94A3B8",
              border: "none", borderRadius: 99, fontWeight: 600,
              cursor: input.trim() ? "pointer" : "default",
              transition: "all 0.15s", fontSize: 14,
            }}
          >
            {sending ? "..." : "Send ⚡"}
          </button>
        </form>
        <div style={{ fontSize: 11, color: "#94A3B8", marginTop: 6, paddingLeft: 44 }}>
          Topics auto-detected · Smart routing to relevant teammates · Reactions: {REACTIONS.join(" ")}
        </div>
      </div>
 
      {summary && <SummaryPanel summary={summary} onClose={() => setSummary(null)} />}
    </div>
  );
}


