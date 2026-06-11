// components/OnlineUsers.jsx
 
import { Avatar } from "./Avatar";
 
export function OnlineUsers({ members, onlineIds }) {
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
      {members.map((m) => (
        <div key={m.id} style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <div style={{ position: "relative" }}>
            <Avatar name={m.display_name} color={m.avatar_color} size={28} />
            {/* Online/offline indicator dot */}
            <div
              style={{
                position: "absolute", bottom: 0, right: 0,
                width: 8, height: 8, borderRadius: "50%",
                background: onlineIds.includes(m.id) ? "#10B981" : "#D1D5DB",
                border: "1.5px solid white",
              }}
            />
          </div>
          <span style={{ fontSize: 12, color: "#475569" }}>{m.display_name}</span>
        </div>
      ))}
    </div>
  );
}
 