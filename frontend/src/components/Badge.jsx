//components/Badge.jsx

export function Badge({label = '', style = {}}) {      return (
    <span
      style={{
        fontSize: 11, fontWeight: 500,
        padding: "2px 8px", borderRadius: 99,
        whiteSpace: "nowrap", ...style,
      }}
    >
      {label}
    </span>
  );
}