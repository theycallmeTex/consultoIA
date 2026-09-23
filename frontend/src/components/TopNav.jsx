const MODES = [
  { id: "journal", icon: "📓", label: "Diario" },
  { id: "cds", icon: "🩺", label: "Analisi clinica" },
];

export default function TopNav({ mode, onModeChange }) {
  return (
    <header className="topnav">
      <div className="topnav-brand">
        <span className="topnav-mark" aria-hidden="true" />
        <span>Consulente IA</span>
      </div>

      <nav className="tabs" role="tablist" aria-label="Modalità">
        {MODES.map((m) => (
          <button
            key={m.id}
            type="button"
            role="tab"
            aria-selected={mode === m.id}
            className={`tab ${mode === m.id ? "active" : ""}`}
            onClick={() => onModeChange(m.id)}
          >
            <span aria-hidden="true">{m.icon}</span> {m.label}
          </button>
        ))}
      </nav>
    </header>
  );
}
