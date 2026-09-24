const MODES = [
  { id: "journal", icon: "📓", label: "Diario" },
  { id: "cds", icon: "🩺", label: "Analisi clinica" },
];

export default function TopNav({ mode, onModeChange }) {
  return (
    <header className="topnav">
      <div className="topnav-brand">
        <img className="topnav-mark" src="/icons8-psicologia-96.png" alt="" width="36" height="36" />
        <span>Consulente AI</span>
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
