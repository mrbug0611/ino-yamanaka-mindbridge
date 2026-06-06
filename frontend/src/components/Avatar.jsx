//components/Avatar.jsx

export function Avatar({name, color, size = 32 }) {
    const initials =     name
      ?.split(" ")
      .filter((w) => w.length > 0) // filter out empty words
      .map((w) => w[0]) // get first letter of each word
      .slice(0, 2) // only get first 2 elements of array 
      .join("") 
      .toUpperCase() || "?";


  return (
    <div
      aria-label={name ? `${name}'s avatar` : "User avatar"}
      style={{
        width: size, height: size, borderRadius: "50%",
        background: color || "#7C3AED",
        display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: size * 0.35, fontWeight: 500, color: "#fff",
        flexShrink: 0, fontFamily: "monospace",
      }}
    >
      {initials}
    </div>
  );
}