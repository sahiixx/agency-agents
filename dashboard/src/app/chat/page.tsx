'use client';

import { useState, useRef, useEffect } from 'react';

interface Message {
  role:    'user' | 'assistant';
  content: string;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    { role: 'assistant', content: 'Agency online. Describe your mission and I\'ll orchestrate the right agents.' },
  ]);
  const [input, setInput]     = useState('');
  const [loading, setLoading] = useState(false);
  const [preset, setPreset]   = useState('full');
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  async function send() {
    const text = input.trim();
    if (!text || loading) return;
    setInput('');
    const userMsg: Message = { role: 'user', content: text };
    setMessages(prev => [...prev, userMsg]);
    setLoading(true);

    try {
      // Call the Agency A2A server via the Next.js proxy
      const res = await fetch('/api/agency', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({
          jsonrpc: '2.0',
          id:      Date.now(),
          method:  'tasks/send',
          params:  {
            id:      typeof crypto !== 'undefined' && crypto.randomUUID
              ? crypto.randomUUID()
              : `task-${Date.now()}-${Math.random().toString(36).slice(2)}`,
            message: {
              role:  'user',
              parts: [{ type: 'text', text: `${text}\n\n[preset: ${preset}]` }],
            },
          },
        }),
      });

      const data = await res.json();
      const reply =
        data?.result?.status?.message?.parts?.[0]?.text ||
        data?.result?.output ||
        JSON.stringify(data?.result ?? data, null, 2);

      setMessages(prev => [...prev, { role: 'assistant', content: reply }]);
    } catch (e) {
      setMessages(prev => [...prev, {
        role:    'assistant',
        content: `⚠️  Could not reach Agency A2A server. Is it running?\n\n` +
                 `Start it with: python3 agency.py --serve\n\nError: ${e}`,
      }]);
    } finally {
      setLoading(false);
    }
  }

  const PRESETS = ['full','saas','research','realestate','dubai','security','intel'];

  return (
    <div className="flex flex-col h-screen max-w-3xl mx-auto">
      {/* Header */}
      <div className="p-4 border-b border-gray-800 flex items-center justify-between">
        <div>
          <h1 className="font-bold text-white">Agency Chat</h1>
          <p className="text-xs text-gray-500">Connected to A2A server at localhost:8100</p>
        </div>
        <select value={preset} onChange={e => setPreset(e.target.value)}
          className="bg-gray-800 text-gray-200 rounded-lg px-3 py-1.5 text-sm border border-gray-700">
          {PRESETS.map(p => <option key={p}>{p}</option>)}
        </select>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm whitespace-pre-wrap ${
              m.role === 'user'
                ? 'bg-agency-600 text-white'
                : 'bg-gray-900 border border-gray-800 text-gray-200'
            }`}>
              {m.role === 'assistant' && (
                <span className="block text-xs text-gray-500 mb-1 font-mono">🤖 Agency Core</span>
              )}
              {m.content}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-900 border border-gray-800 rounded-2xl px-4 py-3 text-gray-400 text-sm">
              <span className="animate-pulse">⏳ Orchestrating agents…</span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t border-gray-800">
        <div className="flex gap-2">
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !e.shiftKey && send()}
            placeholder={`Mission for ${preset} preset…`}
            className="flex-1 bg-gray-900 text-white rounded-xl px-4 py-3 border border-gray-700 focus:border-agency-500 outline-none"
            disabled={loading}
          />
          <button onClick={send} disabled={loading || !input.trim()}
            className="px-5 py-3 bg-agency-600 hover:bg-agency-500 disabled:opacity-50 text-white rounded-xl font-medium transition-colors">
            Send
          </button>
        </div>
        <p className="text-xs text-gray-600 mt-2 text-center">
          Press Enter to send · Select preset to route to the right agent swarm
        </p>
      </div>
    </div>
  );
}
