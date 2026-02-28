// pages/ChatbotPage.js
import React, { useEffect, useState, useRef } from 'react';

const CHAT_API = 'http://localhost:8000/api/chat/';

export default function ChatbotPage() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const bottomRef = useRef(null);

  useEffect(() => {
    document.body.style.margin = '0';
    document.body.style.overflow = 'hidden';
    document.documentElement.style.margin = '0';
    document.body.style.backgroundColor = '#fff8f0';
    document.documentElement.style.backgroundColor = '#fff8f0';

    const style = document.createElement('style');
    style.innerHTML = `
      html, body { overflow: hidden !important; }
      ::-webkit-scrollbar { display: none; }
      body { -ms-overflow-style: none; scrollbar-width: none; }
    `;
    document.head.appendChild(style);
    return () => {
      document.body.style.overflow = '';
      document.head.removeChild(style);
    };
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async () => {
    const text = input.trim();
    if (!text || loading) return;

    setInput('');
    setError(null);
    const userMsg = { role: 'user', content: text };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      const history = messages.map((m) => ({ role: m.role, content: m.content }));
      const res = await fetch(CHAT_API, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, history }),
      });
      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        throw new Error(data.message || `Request failed: ${res.status}`);
      }
      const reply = data.reply ?? 'No response.';
      setMessages((prev) => [...prev, { role: 'assistant', content: reply }]);
    } catch (err) {
      setError(err.message || 'Something went wrong.');
      setMessages((prev) => [...prev, { role: 'assistant', content: `Error: ${err.message}` }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: '70vh',
        width: '70vw',
        backgroundColor: '#ffffff',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        boxSizing: 'border-box',
        overflow: 'hidden',
      }}
    >
      <div
        style={{
          width: '100%',
          maxWidth: '900px',
          height: '80vh',
          backgroundColor: 'white',
          borderRadius: '25px',
          boxShadow: '0 8px 40px rgba(255,140,0,0.18)',
          border: '2.5px solid #ff8c00',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          position: 'relative',
        }}
      >
        <div
          style={{
            background: '#ff7a1a',
            color: 'white',
            padding: '18px',
            textAlign: 'center',
            fontSize: '22px',
            fontWeight: 600,
            borderTopLeftRadius: '22px',
            borderTopRightRadius: '22px',
            boxShadow: '0 2px 10px rgba(255,140,0,0.13)',
            letterSpacing: '0.5px',
          }}
        >
          🧑‍⚖️ Legal AI Assistant
        </div>

        <div
          style={{
            flex: 1,
            overflow: 'auto',
            padding: '16px',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
            backgroundColor: '#fafafa',
          }}
        >
          {messages.length === 0 && (
            <div style={{ textAlign: 'center', color: '#666', marginTop: '24px' }}>
              How can I help you today? Ask about Indian law, IPC, or general legal concepts.
            </div>
          )}
          {messages.map((m, i) => (
            <div
              key={i}
              style={{
                alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start',
                maxWidth: '85%',
                padding: '12px 16px',
                borderRadius: '12px',
                backgroundColor: m.role === 'user' ? '#ff8c00' : 'white',
                color: m.role === 'user' ? 'white' : '#333',
                boxShadow: '0 1px 4px rgba(0,0,0,0.08)',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
              }}
            >
              {m.content}
            </div>
          ))}
          {loading && (
            <div
              style={{
                alignSelf: 'flex-start',
                padding: '12px 16px',
                borderRadius: '12px',
                backgroundColor: 'white',
                boxShadow: '0 1px 4px rgba(0,0,0,0.08)',
                color: '#666',
              }}
            >
              Thinking…
            </div>
          )}
          {error && (
            <div style={{ color: '#c00', fontSize: '14px', padding: '8px' }}>{error}</div>
          )}
          <div ref={bottomRef} />
        </div>

        <div style={{ padding: '12px 16px', borderTop: '1px solid #eee', backgroundColor: 'white' }}>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              sendMessage();
            }}
            style={{ display: 'flex', gap: '8px' }}
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about law, IPC, contracts..."
              disabled={loading}
              style={{
                flex: 1,
                padding: '12px 16px',
                borderRadius: '20px',
                border: '2px solid #e0e0e0',
                fontSize: '16px',
                outline: 'none',
              }}
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              style={{
                padding: '12px 24px',
                borderRadius: '20px',
                border: 'none',
                background: '#ff8c00',
                color: 'white',
                fontWeight: 600,
                cursor: loading ? 'not-allowed' : 'pointer',
                opacity: loading || !input.trim() ? 0.7 : 1,
              }}
            >
              Send
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
