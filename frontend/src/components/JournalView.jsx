import { useState } from "react";
import { sendJournalMessage } from "../api";

export default function JournalView() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    const text = input.trim();
    if (!text || loading) return;

    const nextMessages = [...messages, { role: "user", content: text }];
    setMessages(nextMessages);
    setInput("");
    setError(null);
    setLoading(true);

    try {
      const { reply } = await sendJournalMessage(nextMessages);
      setMessages([...nextMessages, { role: "assistant", content: reply }]);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <div className="view-header">
        <h2>Uno spazio per pensare ad alta voce</h2>
        <p>Scrivi quello che ti passa per la testa. Nessun giudizio, nessuna fretta.</p>
      </div>

      <div className="chat-history">
        {messages.map((msg, i) => (
          <div key={i} className={`chat-message ${msg.role}`}>
            {msg.content}
          </div>
        ))}
        {loading && <div className="chat-message assistant pending">sta scrivendo…</div>}
      </div>

      {error && <div className="error">{error}</div>}

      <form onSubmit={handleSubmit} className="chat-input-form">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Di cosa vorresti parlare?"
          disabled={loading}
        />
        <button type="submit" className="primary" disabled={loading || !input.trim()}>
          Invia
        </button>
      </form>
    </div>
  );
}
