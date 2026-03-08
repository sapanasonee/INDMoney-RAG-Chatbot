import React, { useState, useEffect, useRef } from 'react';

const DEFAULT_API_URL = import.meta.env.VITE_API_URL || "http://localhost:8002";
const FALLBACK_PORT = 8001;

const DEMO_QUESTIONS = [
  "What is the expense ratio of HDFC Small Cap Fund?",
  "What is the AUM of HDFC Flexi Cap Fund?",
  "What is the benchmark of HDFC Small Cap Fund?",
  "Who is the fund manager of SBI Contra Fund?",
  "What is the exit load for SBI Contra Fund?",
  "What is the riskometer of Parag Parikh Flexi Cap?",
];

function TypingIndicator() {
  return (
    <div className="flex items-start gap-3 max-w-[85%]">
      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-emerald-400 to-teal-500 flex items-center justify-center flex-shrink-0 shadow-sm">
        <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 3.104v5.714a2.25 2.25 0 0 1-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 0 1 4.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0 1 12 15a9.065 9.065 0 0 0-6.23.693L5 14.5m14.8.8 1.402 1.402c1.232 1.232.65 3.318-1.067 3.611A48.309 48.309 0 0 1 12 21c-2.773 0-5.491-.235-8.135-.687-1.718-.293-2.3-2.379-1.067-3.61L5 14.5" /></svg>
      </div>
      <div className="bg-white border border-gray-100 rounded-2xl rounded-tl-md px-5 py-3 shadow-sm">
        <div className="flex gap-1.5 items-center h-5">
          <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:0ms]" />
          <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:150ms]" />
          <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:300ms]" />
        </div>
      </div>
    </div>
  );
}

function MessageBubble({ msg }) {
  const isUser = msg.sender === 'user';
  return (
    <div className={`flex items-start gap-3 ${isUser ? 'flex-row-reverse' : ''} max-w-[85%] ${isUser ? 'ml-auto' : ''} animate-[fadeSlideIn_0.3s_ease-out]`}>
      {isUser ? (
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center flex-shrink-0 shadow-sm">
          <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.501 20.118a7.5 7.5 0 0 1 14.998 0A17.933 17.933 0 0 1 12 21.75c-2.676 0-5.216-.584-7.499-1.632Z" /></svg>
        </div>
      ) : (
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-emerald-400 to-teal-500 flex items-center justify-center flex-shrink-0 shadow-sm">
          <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 3.104v5.714a2.25 2.25 0 0 1-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 0 1 4.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0 1 12 15a9.065 9.065 0 0 0-6.23.693L5 14.5m14.8.8 1.402 1.402c1.232 1.232.65 3.318-1.067 3.611A48.309 48.309 0 0 1 12 21c-2.773 0-5.491-.235-8.135-.687-1.718-.293-2.3-2.379-1.067-3.61L5 14.5" /></svg>
        </div>
      )}
      <div>
        <div className={`rounded-2xl px-4 py-3 shadow-sm leading-relaxed text-[15px] ${
          isUser
            ? 'bg-gradient-to-br from-blue-500 to-indigo-600 text-white rounded-tr-md'
            : 'bg-white border border-gray-100 text-gray-800 rounded-tl-md'
        }`}>
          {msg.text}
        </div>
        {msg.sources?.length > 0 && (
          <div className="mt-2 bg-gray-50 border border-gray-200 rounded-xl px-3 py-2.5">
            <p className="text-[11px] font-semibold text-gray-500 uppercase tracking-wide mb-1.5">Sources</p>
            <div className="flex flex-col gap-1.5">
              {msg.sources.map((url, j) => (
                <a
                  key={j}
                  href={url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-teal-600 hover:text-teal-800 hover:underline flex items-center gap-1.5 transition-colors"
                >
                  <svg className="w-3.5 h-3.5 flex-shrink-0 text-teal-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.19 8.688a4.5 4.5 0 0 1 1.242 7.244l-4.5 4.5a4.5 4.5 0 0 1-6.364-6.364l1.757-1.757m9.86-2.54a4.5 4.5 0 0 0-1.242-7.244l-4.5-4.5a4.5 4.5 0 0 0-6.364 6.364L5 8.688" /></svg>
                  <span className="truncate">{decodeURIComponent(url).replace(/https?:\/\/(www\.)?/, '')}</span>
                </a>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function App() {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [apiUrl, setApiUrl] = useState(DEFAULT_API_URL);
  const [backendStatus, setBackendStatus] = useState('checking');
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => { scrollToBottom(); }, [messages, loading]);

  const checkBackend = React.useCallback(async () => {
    setBackendStatus('checking');
    const tryUrl = async (url) => {
      try {
        const r = await fetch(`${url}/health`, { method: 'GET' });
        if (r.ok) return url;
      } catch (_) {}
      return null;
    };
    const u1 = await tryUrl(DEFAULT_API_URL);
    if (u1) { setApiUrl(u1); setBackendStatus('connected'); return; }
    const fallback = `http://localhost:${FALLBACK_PORT}`;
    const u2 = await tryUrl(fallback);
    if (u2) { setApiUrl(u2); setBackendStatus('connected'); return; }
    setBackendStatus('disconnected');
  }, []);

  useEffect(() => { checkBackend(); }, [checkBackend]);

  const handleSend = async (overrideMessage) => {
    const messageToSend = (overrideMessage || input).trim();
    if (!messageToSend) return;

    setMessages(prev => [...prev, { text: messageToSend, sender: 'user' }]);
    setInput('');
    setLoading(true);

    const doFetch = (signal) =>
      fetch(`${apiUrl}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: messageToSend }),
        signal,
      });

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 90000);
      let response = await doFetch(controller.signal);
      clearTimeout(timeoutId);

      if (!response.ok) {
        let errText = '';
        try {
          const data = await response.json();
          errText = data?.detail || data?.message || response.statusText;
        } catch (_) {
          errText = await response.text() || response.statusText;
        }
        setMessages(prev => [...prev, { text: errText || 'Request failed.', sender: 'bot' }]);
        return;
      }

      let data;
      try { data = await response.json(); } catch (_) {
        setMessages(prev => [...prev, { text: 'Invalid response from backend.', sender: 'bot' }]);
        return;
      }
      setMessages(prev => [...prev, { text: data.answer || 'No answer.', sender: 'bot', sources: data.sources }]);
    } catch (error) {
      if (error.name === 'AbortError') {
        setMessages(prev => [...prev, { text: 'Request timed out. The backend may be loading. Try again in a moment.', sender: 'bot' }]);
        return;
      }
      try {
        const controller2 = new AbortController();
        const timeoutId2 = setTimeout(() => controller2.abort(), 90000);
        const response2 = await doFetch(controller2.signal);
        clearTimeout(timeoutId2);
        if (response2.ok) {
          const data2 = await response2.json().catch(() => ({}));
          setMessages(prev => [...prev, { text: data2.answer || 'No answer.', sender: 'bot', sources: data2.sources }]);
          return;
        }
        const errData = await response2.json().catch(() => ({}));
        setMessages(prev => [...prev, { text: errData?.detail || 'Request failed.', sender: 'bot' }]);
      } catch {
        setMessages(prev => [...prev, { text: 'Cannot reach backend. Make sure it is running on port 8002.', sender: 'bot' }]);
      }
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const showSuggestions = messages.length === 0 && !loading;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-teal-50 flex flex-col items-center justify-center p-4">
      <div className="w-full max-w-2xl flex flex-col h-[calc(100vh-2rem)] max-h-[700px]">

        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 via-indigo-600 to-teal-500 rounded-t-2xl px-6 py-4 shadow-lg">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-white/20 backdrop-blur rounded-xl flex items-center justify-center">
              <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 6v12m-3-2.818.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" /></svg>
            </div>
            <div>
              <h1 className="text-white font-semibold text-lg leading-tight">Mutual Fund Assistant</h1>
              <p className="text-white/70 text-xs">Facts-only answers from official sources</p>
            </div>
          </div>
          {/* Status pill */}
          <div className="mt-3 flex items-center gap-2">
            {backendStatus === 'checking' && (
              <span className="inline-flex items-center gap-1.5 text-xs bg-white/15 text-white/80 px-3 py-1 rounded-full">
                <span className="w-1.5 h-1.5 bg-yellow-300 rounded-full animate-pulse" /> Connecting...
              </span>
            )}
            {backendStatus === 'connected' && (
              <span className="inline-flex items-center gap-1.5 text-xs bg-white/15 text-white/90 px-3 py-1 rounded-full">
                <span className="w-1.5 h-1.5 bg-emerald-300 rounded-full" /> Connected
              </span>
            )}
            {backendStatus === 'disconnected' && (
              <span className="inline-flex items-center gap-1.5 text-xs bg-red-500/30 text-white px-3 py-1 rounded-full cursor-pointer hover:bg-red-500/40 transition-colors" onClick={checkBackend}>
                <span className="w-1.5 h-1.5 bg-red-300 rounded-full" /> Disconnected — click to retry
              </span>
            )}
          </div>
        </div>

        {/* Chat body */}
        <div className="flex-1 bg-gray-50/80 backdrop-blur overflow-y-auto px-5 py-4 space-y-4 chat-scrollbar">
          {showSuggestions && (
            <div className="flex flex-col items-center justify-center h-full text-center animate-[fadeSlideIn_0.4s_ease-out]">
              <div className="w-16 h-16 bg-gradient-to-br from-blue-100 to-teal-100 rounded-2xl flex items-center justify-center mb-4">
                <svg className="w-8 h-8 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 0 1 .865-.501 48.172 48.172 0 0 0 3.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0 0 12 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018Z" /></svg>
              </div>
              <h2 className="text-gray-700 font-semibold text-base mb-1">Ask me about mutual funds</h2>
              <p className="text-gray-400 text-sm mb-6 max-w-xs">
                I provide factual information about 5 schemes — HDFC Small Cap, HDFC Flexi Cap, SBI Contra, HDFC ELSS, and Parag Parikh Flexi Cap.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-lg">
                {DEMO_QUESTIONS.map((q, i) => (
                  <button
                    key={i}
                    onClick={() => handleSend(q)}
                    disabled={loading || backendStatus !== 'connected'}
                    className="text-left text-sm text-gray-600 bg-white border border-gray-200 rounded-xl px-4 py-3 hover:border-indigo-300 hover:bg-indigo-50/50 hover:text-indigo-700 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed group"
                  >
                    <span className="text-indigo-400 group-hover:text-indigo-500 mr-1.5">&#8250;</span>
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            <MessageBubble key={i} msg={msg} />
          ))}
          {loading && <TypingIndicator />}
          <div ref={messagesEndRef} />
        </div>

        {/* Input bar */}
        <div className="bg-white border-t border-gray-200 rounded-b-2xl px-4 py-3 shadow-lg">
          <form onSubmit={(e) => { e.preventDefault(); handleSend(); }} className="flex gap-2 items-center">
            <input
              ref={inputRef}
              className="flex-1 bg-gray-100 border-0 rounded-xl px-4 py-2.5 text-sm text-gray-800 placeholder-gray-400 outline-none focus:ring-2 focus:ring-indigo-400/50 focus:bg-white transition-all"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about expense ratio, exit load, riskometer..."
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="bg-gradient-to-r from-blue-500 to-indigo-600 text-white p-2.5 rounded-xl hover:from-blue-600 hover:to-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-200 shadow-sm hover:shadow-md"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 12 3.269 3.125A59.769 59.769 0 0 1 21.485 12 59.768 59.768 0 0 1 3.27 20.875L5.999 12Zm0 0h7.5" /></svg>
            </button>
          </form>
          <p className="text-[10px] text-gray-400 text-center mt-2">Powered by Gemini. Facts only — no investment advice.</p>
        </div>
      </div>
    </div>
  );
}

export default App;
