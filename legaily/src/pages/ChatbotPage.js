// pages/ChatbotPage.js
import React, { useEffect, useState, useRef } from 'react';

const CHAT_API = 'http://localhost:8000/api/chat/';

function parseInlineBold(text) {
  const parts = String(text).split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    const m = part.match(/^\*\*([^*]+)\*\*$/);
    if (m) return <strong key={i}>{m[1]}</strong>;
    return <span key={i}>{part}</span>;
  });
}

function renderFormattedOutput(content, type = 'raw') {
  if (!content) return null;

  // Render structured legal data as clean text blocks instead of cards
  if (type === 'structured' && Array.isArray(content)) {
    return content.map((item, idx) => (
      <div key={`section-${idx}`} style={{ marginBottom: idx < content.length - 1 ? '20px' : '0' }}>
        <div style={{ fontWeight: 800, color: '#ff7a1a', fontSize: '17px', marginBottom: '6px', borderBottom: '1px solid #fff0e0', paddingBottom: '2px' }}>
          {item.section}
        </div>
        <div style={{ marginBottom: '10px', lineHeight: '1.5', color: '#333' }}>
          {parseInlineBold(item.description)}
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '14px', backgroundColor: '#fff9f2', padding: '10px', borderRadius: '8px' }}>
          {item.punishment && item.punishment !== 'N/A' && (
            <div><span style={{ fontWeight: 700, color: '#444' }}>Punishment:</span> {item.punishment}</div>
          )}
          <div style={{ display: 'flex', gap: '15px' }}>
             {item.bailable && item.bailable !== 'N/A' && (
               <div><span style={{ fontWeight: 700, color: '#444' }}>Bailable:</span> {item.bailable}</div>
             )}
             {item.cognizable && item.cognizable !== 'N/A' && (
               <div><span style={{ fontWeight: 700, color: '#444' }}>Cognizable:</span> {item.cognizable}</div>
             )}
          </div>
        </div>
        {idx < content.length - 1 && (
          <div style={{ height: '1px', background: '#eee', margin: '15px 0' }} />
        )}
      </div>
    ));
  }

  // Fallback for raw text
  const lines = String(content).split('\n');
  return lines.map((line, idx) => {
    const key = `chatfmt-${idx}`;
    const trimmed = line.trim();
    if (!trimmed) return <div key={key} style={{ height: '0.55em' }} aria-hidden="true" />;
    return (
      <div key={key} style={{ margin: '0 0 6px 0' }}>
        {parseInlineBold(line)}
      </div>
    );
  });
}

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
        body: JSON.stringify({ message: text, history, mode: 'detailed' }),
      });
      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        throw new Error(data.message || `Request failed: ${res.status}`);
      }
      const reply = data.reply ?? 'No response.';
      const resType = data.type ?? 'raw';
      setMessages((prev) => [...prev, { role: 'assistant', content: reply, type: resType }]);
    } catch (err) {
      setError(err.message || 'Something went wrong.');
      setMessages((prev) => [...prev, { role: 'assistant', content: `Error: ${err.message}`, type: 'raw' }]);
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
            padding: '12px 18px',
            textAlign: 'center',
            fontSize: '22px',
            fontWeight: 600,
            borderTopLeftRadius: '22px',
            borderTopRightRadius: '22px',
            boxShadow: '0 2px 10px rgba(255,140,0,0.13)',
            letterSpacing: '0.5px',
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center'
          }}
        >
          <div>🧑‍⚖️ Legal AI Assistant</div>
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
                maxWidth: m.type === 'structured' ? '92%' : '85%',
                padding: '12px 16px',
                borderRadius: '12px',
                backgroundColor: m.role === 'user' ? '#ff8c00' : 'white',
                color: m.role === 'user' ? 'white' : '#333',
                boxShadow: '0 1px 4px rgba(0,0,0,0.08)',
                wordBreak: 'break-word',
              }}
            >
              {m.role === 'assistant' ? renderFormattedOutput(m.content, m.type) : m.content}
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
