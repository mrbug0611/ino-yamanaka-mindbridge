// constants.js - shared look up table used across components 

export const AVATAR_COLORS = [
  "#E85D75", // Sakura Haruno (Cherry blossom pink)
  "#5D54A4", // Hinata Hyuga (Indigo hair / Lavender eyes)
  "#E0B034", // Temari (Sand blonde / Fan gold)
  "#901A1E", // Tenten (Deep auburn / Chinese dress red)
  "#8E7CC3", // Ino Yamanaka (Purple outfit / Lavender accents)
  "#D97706", // Tsunade (Hokage haori orange-gold)
  "#14B8A6"  // Kushina Uzumaki (Habenero red hair contrast teal)
];

export const REACTIONS = ["⚡", "💡", "❓", "✅", "🔥", "👁️"];
 
export const TOPIC_STYLES = {
  bug:      { bg: "#FEF2F2", border: "#FCA5A5", text: "#991B1B", icon: "ti-bug" },
  planning: { bg: "#EFF6FF", border: "#93C5FD", text: "#1E40AF", icon: "ti-calendar" },
  idea:     { bg: "#F0FDF4", border: "#86EFAC", text: "#166534", icon: "ti-bulb" },
  decision: { bg: "#FDF4FF", border: "#D8B4FE", text: "#6B21A8", icon: "ti-scale" },
  review:   { bg: "#FFF7ED", border: "#FDB97D", text: "#9A3412", icon: "ti-eye" },
  question: { bg: "#F0F9FF", border: "#7DD3FC", text: "#0C4A6E", icon: "ti-help" },
  urgent:   { bg: "#FFF1F2", border: "#FB7185", text: "#881337", icon: "ti-alert-triangle" },
  general:  { bg: "#F8FAFC", border: "#CBD5E1", text: "#334155", icon: "ti-message" },
};
 
export const URGENCY_BADGE = {
  critical: { bg: "#FEE2E2", text: "#7F1D1D" },
  high:     { bg: "#FFEDD5", text: "#7C2D12" },
  normal:   { bg: "#F1F5F9", text: "#475569" },
  low:      { bg: "#F0FDF4", text: "#14532D" },
};
 
export const HEADER_STYLE = {
  display: "flex", alignItems: "center", justifyContent: "space-between",
  padding: "14px 24px", background: "white",
  borderBottom: "1px solid #E2E8F0",
  position: "sticky", top: 0, zIndex: 10,
};
 