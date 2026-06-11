//components/SignalCard.jsx

import {Avatar} from './Avatar';
import {Badge} from './Badge';
import { TOPIC_STYLES, URGENCY_BADGE, REACTIONS } from "../constants";

export function SignalCard({signal, currentUserId, onReact, isNew, dimmed}) {
    const topic = TOPIC_STYLES[signal.topic] || TOPIC_STYLES.general;
    const urgency = URGENCY_BADGE[signal.urgency] || URGENCY_BADGE.normal;
    const isOwn = signal.sender_id === currentUserId;

     return (
    <div
      style={{
        background: dimmed ? "#FAFAFA" : topic.bg,
        border: `1px solid ${dimmed ? "#E2E8F0" : topic.border}`,
        borderRadius: 12, padding: "12px 16px",
        opacity: dimmed ? 0.55 : 1,
        transition: "all 0.3s ease",
        animation: isNew ? "slideIn 0.25s ease" : "none",
        marginBottom: 10,
      }}
    >
      <style>{`@keyframes slideIn{from{opacity:0;transform:translateY(-8px)}to{opacity:1;transform:translateY(0)}}`}</style>
 
      {/* Header row */}
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
        <Avatar name={signal.sender_name} color={signal.sender_color} size={26} />
        <span style={{ fontSize: 13, fontWeight: 500, color: "#1E293B" }}>
          {signal.sender_name}
        </span>
        {isOwn && <Badge label="you" style={{ background: "#EEF2FF", color: "#3730A3" }} />}
 
        <div style={{ marginLeft: "auto", display: "flex", gap: 6, alignItems: "center" }}>
          <i className={`ti ${topic.icon}`} style={{ fontSize: 14, color: topic.text }} aria-hidden />
          <Badge
            label={signal.topic}
            style={{ background: "transparent", color: topic.text, border: `1px solid ${topic.border}` }}
          />
          {signal.urgency !== "normal" && (
            <Badge
              label={signal.urgency}
              style={{ background: urgency.bg, color: urgency.text }}
            />
          )}
        </div>
      </div>
 
      {/* Content */}
      <p style={{ margin: "0 0 10px", fontSize: 14, lineHeight: 1.6, color: dimmed ? "#94A3B8" : "#1E293B" }}>
        {signal.content}
      </p>
 
      {/* Footer: reactions + timestamp + routing info */}
      <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
        {REACTIONS.map((r) => {
          const count = signal.reactions?.[r] || 0;
          return (
            <button
              key={r}
              onClick={() => onReact(signal.id, r)}
              style={{
                background: count > 0 ? "rgba(124,58,237,0.08)" : "transparent",
                border: count > 0 ? "1px solid rgba(124,58,237,0.3)" : "1px solid #E2E8F0",
                borderRadius: 99, padding: "3px 9px", cursor: "pointer",
                fontSize: 13, display: "flex", alignItems: "center", gap: 4,
                color: "#475569", transition: "all 0.15s",
              }}
            >
              {r}
              {count > 0 && (
                <span style={{ fontSize: 11, fontWeight: 500, color: "#7C3AED" }}>{count}</span>
              )}
            </button>
          );
        })}
 
        <span style={{ marginLeft: "auto", fontSize: 11, color: "#94A3B8" }}>
          {new Date(signal.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
        </span>
 
        {signal.routed_to?.length > 0 && !isOwn && (
          <Badge
            label={`→ ${signal.routed_to.length} routed`}
            style={{ background: "#F1F5F9", color: "#64748B" }}
          />
        )}
      </div>
    </div>
  );
}