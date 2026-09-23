import { useState } from "react";
import TopNav from "./components/TopNav";
import JournalView from "./components/JournalView";
import CdsView from "./components/CdsView";
import "./App.css";

export default function App() {
  const [mode, setMode] = useState("journal");

  return (
    <div className={`app app--${mode}`}>
      <TopNav mode={mode} onModeChange={setMode} />
      <main className="content">
        {mode === "journal" ? <JournalView /> : <CdsView />}
      </main>
      <footer className="app-footer">
        Prototipo sperimentale basato su IA — non è un dispositivo medico né sostituisce il parere di un professionista.
      </footer>
    </div>
  );
}
