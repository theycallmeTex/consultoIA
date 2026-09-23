import os
import pandas as pd

FEEDBACK_CSV = os.path.join(os.path.dirname(__file__), "feedback_esperti.csv")

COLUMNS = ["testo_originale", "analisi_ia", "correzione_esperto"]


def carica_feedback_esperti() -> pd.DataFrame:
    if os.path.exists(FEEDBACK_CSV):
        try:
            return pd.read_csv(FEEDBACK_CSV)
        except pd.errors.EmptyDataError:
            pass  # file vuoto o senza intestazione: trattalo come nessuna correzione
    return pd.DataFrame(columns=COLUMNS)


def salva_feedback_esperto(testo_orig: str, analisi_ia: str, correzione: str) -> None:
    df = carica_feedback_esperti()
    nuova_riga = pd.DataFrame([{
        "testo_originale": testo_orig,
        "analisi_ia": analisi_ia,
        "correzione_esperto": correzione,
    }])
    df = pd.concat([df, nuova_riga], ignore_index=True)
    df.to_csv(FEEDBACK_CSV, index=False)


def costruisci_prompt_cds_con_esempi(base_prompt: str) -> str:
    prompt = base_prompt
    df = carica_feedback_esperti()

    if not df.empty:
        prompt += "\n\n### ESEMPI DI CORREZIONI E PREFERENZE DI ESPERTI PASSATI (Impara da queste correzioni):\n"
        for _, row in df.tail(5).iterrows():
            prompt += f"\n- Caso: \"{row['testo_originale']}\"\n  Correzione dell'esperto: \"{row['correzione_esperto']}\"\n"

    return prompt
