# Consulente IA & Journaling

Applicazione con due modalità:

- **Diario Personale (Journaling)**: chat empatica per lo sfogo personale.
- **Supporto Clinico (CDS)**: analisi strutturata di testi clinici per professionisti, con feedback loop (few-shot learning) salvato su CSV e retrieval semantico (RAG) sui criteri diagnostici DSM-5-TR.

## Struttura

- [`backend/`](backend/) — API FastAPI che chiama modelli via OpenRouter (SDK OpenAI-compatibile) e gestisce i feedback su CSV.
  - [`backend/rag/`](backend/rag/) — modulo RAG: embedding multilingue (Cohere `embed-multilingual-v3.0`) + vector DB (Qdrant Cloud) sui sintomi del dataset [`backend/dsm5_tr_data/`](backend/dsm5_tr_data/).
- [`frontend/`](frontend/) — interfaccia React (Vite).

## Avvio in locale

### Backend

**Windows (PowerShell):**

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env  # inserisci OPENROUTER_API_KEY, COHERE_API_KEY, QDRANT_URL/QDRANT_API_KEY
uvicorn main:app --reload --port 8000
```

Se `Activate.ps1` dà un errore di execution policy, esegui una volta `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` e ripeti l'attivazione.

**macOS/Linux (bash):**

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # inserisci OPENROUTER_API_KEY, COHERE_API_KEY, QDRANT_URL/QDRANT_API_KEY
uvicorn main:app --reload --port 8000
```

Al primo avvio (o se cambi dataset), indicizza i sintomi su Qdrant:

```bash
python -m rag.ingest
```

> Importante: il virtualenv va **attivato** in ogni nuova sessione di terminale prima di lanciare `uvicorn`, altrimenti il comando non viene trovato (`CommandNotFoundException` su PowerShell).

### Frontend

```bash
cd frontend
npm install
cp .env.example .env  # opzionale, default punta a localhost:8000
npm run dev
```

L'app sarà disponibile su `http://localhost:5173`.
