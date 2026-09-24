import { useEffect, useState } from "react";
import { analyzeCdsText, getCdsFeedbackCount, saveCdsFeedback } from "../api";

export default function CdsView() {
  const [feedbackCount, setFeedbackCount] = useState(null);
  const [testoPaziente, setTestoPaziente] = useState("");
  const [analisi, setAnalisi] = useState(null);
  const [rag, setRag] = useState(null);
  const [correzione, setCorrezione] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [saveNotice, setSaveNotice] = useState(null);

  useEffect(() => {
    getCdsFeedbackCount()
      .then(({ count }) => setFeedbackCount(count))
      .catch(() => setFeedbackCount(null));
  }, []);

  async function handleAnalyze() {
    if (!testoPaziente.trim()) {
      setError("Per favore inserisci un testo da analizzare.");
      return;
    }
    setError(null);
    setAnalyzing(true);
    try {
      const { analisi: risultato, rag: ragRisultato } = await analyzeCdsText(testoPaziente);
      try {
        JSON.parse(risultato);
      } catch {
        setAnalisi(null);
        setError("La risposta dell'IA è incompleta o non valida (possibili token insufficienti). Riprova.");
        return;
      }
      setAnalisi(risultato);
      setRag(ragRisultato || null);
    } catch (err) {
      setError(err.message);
    } finally {
      setAnalyzing(false);
    }
  }

  async function handleSaveFeedback() {
    if (!correzione.trim()) {
      setSaveNotice({ type: "warning", text: "Inserisci una nota prima di salvare." });
      return;
    }
    setSaving(true);
    setSaveNotice(null);
    try {
      await saveCdsFeedback(testoPaziente, analisi, correzione);
      setSaveNotice({
        type: "success",
        text: "Correzione salvata. Verrà usata come esempio nelle prossime analisi.",
      });
      setCorrezione("");
      const { count } = await getCdsFeedbackCount();
      setFeedbackCount(count);
    } catch (err) {
      setSaveNotice({ type: "error", text: err.message });
    } finally {
      setSaving(false);
    }
  }

  let analisiParsata = null;
  try {
    analisiParsata = JSON.parse(analisi);
  } catch {
    // gestito sotto: se il parsing fallisce mostriamo il testo grezzo
  }

  const puntiChiave = analisiParsata?.punti_chiave || [];
  const raccomandazioni = analisiParsata?.raccomandazioni_cliniche || [];
  const diagnosiDifferenziali = analisiParsata?.diagnosi_differenziali || [];
  const ambiguita = rag?.ambiguita;
  const candidate = rag?.candidate?.lista || [];

  return (
    <div>
      <div className="view-header">
        <h2>Analisi clinica</h2>
        <p>Analisi assistita del testo del paziente, con riferimento ai criteri DSM-5-TR.</p>
      </div>

      {feedbackCount !== null && (
        <p className="cds-metric">
          <strong>{feedbackCount}</strong> correzioni di esperti raccolte finora
        </p>
      )}

      <label htmlFor="testo-paziente">Testo o trascrizione del diario del paziente</label>
      <textarea
        id="testo-paziente"
        rows={8}
        value={testoPaziente}
        onChange={(e) => setTestoPaziente(e.target.value)}
        placeholder="Es: Il paziente riferisce sensazione di oppressione al petto la mattina e difficoltà a dormire..."
        style={{ marginTop: "0.5rem", marginBottom: "0.9rem" }}
      />

      <button onClick={handleAnalyze} disabled={analyzing} className="primary">
        {analyzing ? "Analisi in corso…" : "Analizza caso"}
      </button>

      {error && <div className="error">{error}</div>}

      {analisi && (
        <>
          {analisiParsata ? (
            <div className="cds-result">
              <div className="cds-result-label">Ipotesi diagnostica</div>
              <p className="hypothesis">{analisiParsata.ipotesi_diagnostica}</p>

              {rag && (
                <div className="stat-cards">
                  <div className={`stat-card ambiguity ${ambiguita?.livello || ""}`}>
                    <div className="stat-card-label">System ambiguity score</div>
                    <div className="stat-card-value">
                      {ambiguita?.ambiguita != null ? `${ambiguita.ambiguita}%` : "—"}
                    </div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-card-label">Potential diagnoses</div>
                    <div className="stat-card-value positive">{rag.candidate?.conteggio ?? candidate.length}</div>
                  </div>
                </div>
              )}

              <div className="cds-columns">
                <div>
                  <div className="cds-column-title">
                    Punti chiave <span className="count">({puntiChiave.length})</span>
                  </div>
                  <ul className="point-list">
                    {puntiChiave.map((punto, i) => (
                      <li key={i}>{punto}</li>
                    ))}
                  </ul>
                </div>

                <div>
                  <div className="cds-column-title">
                    Raccomandazioni <span className="count">({raccomandazioni.length})</span>
                  </div>
                  <ul className="reco-list">
                    {raccomandazioni.map((reco, i) => (
                      <li key={i}>{reco}</li>
                    ))}
                  </ul>
                </div>
              </div>

              {(candidate.length > 0 || diagnosiDifferenziali.length > 0) && (
                <div className="cds-columns" style={{ marginTop: "1.75rem" }}>
                  {candidate.length > 0 && (
                    <div>
                      <div className="cds-column-title">
                        Diagnosi candidate <span className="count">({candidate.length})</span>
                      </div>
                      <ul className="point-list">
                        {candidate.map((c, i) => (
                          <li key={i}>
                            {c.diagnosis_name}{" "}
                            {c.diagnostic_code && <span className="diagnostic-code">({c.diagnostic_code})</span>}
                            {" "}— rilevanza {c.punteggio_norm}/100, {c.n_sintomi_match} sintomi
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {diagnosiDifferenziali.length > 0 && (
                    <div>
                      <div className="cds-column-title">
                        Diagnosi differenziali<span className="count">({diagnosiDifferenziali.length})</span>
                      </div>
                      <ul className="reco-list">
                        {diagnosiDifferenziali.map((d, i) => (
                          <li key={i}>{d}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
          ) : (
            <pre className="raw-json">{analisi}</pre>
          )}

          <div className="feedback-section">
            <h3>Feedback del professionista</h3>
            <p>
              Se l'analisi è imprecisa o incompleta, correggila qui: verrà usata come
              esempio nelle prossime analisi.
            </p>

            <textarea
              rows={4}
              value={correzione}
              onChange={(e) => setCorrezione(e.target.value)}
              placeholder="La tua valutazione o correzione clinica…"
              style={{ marginBottom: "0.9rem" }}
            />

            <button onClick={handleSaveFeedback} disabled={saving}>
              {saving ? "Salvataggio…" : "Salva correzione"}
            </button>

            {saveNotice && (
              <div className={saveNotice.type === "error" ? "error" : saveNotice.type}>
                {saveNotice.text}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
