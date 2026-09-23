const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function request(path, options) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Errore ${res.status}`);
  }

  return res.json();
}

export function sendJournalMessage(messages) {
  return request("/api/journal/chat", {
    method: "POST",
    body: JSON.stringify({ messages }),
  });
}

export function analyzeCdsText(testoPaziente) {
  return request("/api/cds/analyze", {
    method: "POST",
    body: JSON.stringify({ testo_paziente: testoPaziente }),
  });
}

export function getCdsFeedbackCount() {
  return request("/api/cds/feedback/count");
}

export function saveCdsFeedback(testoOriginale, analisiIa, correzioneEsperto) {
  return request("/api/cds/feedback", {
    method: "POST",
    body: JSON.stringify({
      testo_originale: testoOriginale,
      analisi_ia: analisiIa,
      correzione_esperto: correzioneEsperto,
    }),
  });
}
