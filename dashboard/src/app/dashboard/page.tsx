'use client';

import { useState } from 'react';
import useSWR from 'swr';

const fetcher = (url: string) => fetch(url).then(r => r.json());

interface MissionLog {
  id:      string;
  mission: string;
  preset:  string;
  verdict: string;
  ts:      string;
}

export default function DashboardPage() {
  const { data: status, error } = useSWR('/api/agency/.well-known/agent.json', fetcher, {
    refreshInterval: 5000,
  });

  const agencyOnline = !error && status;

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Dashboard</h1>
          <p className="text-gray-400">Agency mission control</p>
        </div>
        <div className="flex items-center gap-2">
          <span className={`inline-block w-2 h-2 rounded-full ${agencyOnline ? 'bg-green-400' : 'bg-red-400'}`} />
          <span className="text-sm text-gray-400">{agencyOnline ? 'A2A Online' : 'A2A Offline'}</span>
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { label: 'Agents',   value: '152', color: 'text-blue-400'   },
          { label: 'Tools',    value: '19+', color: 'text-green-400'  },
          { label: 'Presets',  value: '12',  color: 'text-yellow-400' },
          { label: 'Providers',value: '7',   color: 'text-purple-400' },
        ].map(s => (
          <div key={s.label} className="bg-gray-900 rounded-xl p-4 border border-gray-800">
            <div className={`text-2xl font-bold ${s.color}`}>{s.value}</div>
            <div className="text-gray-400 text-sm">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Providers */}
      <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
        <h2 className="text-lg font-semibold mb-4 text-white">Provider Layer</h2>
        <div className="flex flex-wrap gap-2">
          {['anthropic','ollama','openai','adk','autogen','rasa','n8n'].map(p => (
            <span key={p} className="px-3 py-1 bg-gray-800 text-gray-300 rounded-full text-sm font-mono">
              {p}
            </span>
          ))}
        </div>
      </div>

      {/* Quick mission launch */}
      <MissionLauncher />

      {/* Agent status */}
      <AgentGraph />
    </div>
  );
}

function MissionLauncher() {
  const [mission, setMission]   = useState('');
  const [preset, setPreset]     = useState('full');
  const [provider, setProvider] = useState('anthropic');
  const [result, setResult]     = useState('');
  const [running, setRunning]   = useState(false);

  const PRESETS   = ['full','saas','research','realestate','dubai','security','intel','docs','moltbot','trust'];
  const PROVIDERS = ['anthropic','ollama','openai','adk','autogen','rasa','n8n'];

  async function launch() {
    if (!mission.trim()) return;
    setRunning(true);
    setResult('');
    try {
      const res = await fetch('/api/agency', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ jsonrpc: '2.0', id: 1, method: 'tasks/send', params: {
          id:      typeof crypto !== 'undefined' && crypto.randomUUID
            ? crypto.randomUUID()
            : `task-${Date.now()}-${Math.random().toString(36).slice(2)}`,
          message: { role: 'user', parts: [{ type: 'text', text: `${mission}|preset:${preset}|provider:${provider}` }] },
        }}),
      });
      const data = await res.json();
      setResult(JSON.stringify(data?.result ?? data, null, 2));
    } catch (e) {
      setResult(`Error: ${e}`);
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="bg-gray-900 rounded-xl p-6 border border-gray-800 space-y-4">
      <h2 className="text-lg font-semibold text-white">Launch Mission</h2>
      <div className="flex gap-2 flex-wrap">
        <select value={preset} onChange={e => setPreset(e.target.value)}
          className="bg-gray-800 text-gray-200 rounded-lg px-3 py-2 text-sm border border-gray-700">
          {PRESETS.map(p => <option key={p}>{p}</option>)}
        </select>
        <select value={provider} onChange={e => setProvider(e.target.value)}
          className="bg-gray-800 text-gray-200 rounded-lg px-3 py-2 text-sm border border-gray-700">
          {PROVIDERS.map(p => <option key={p}>{p}</option>)}
        </select>
      </div>
      <div className="flex gap-2">
        <input
          value={mission}
          onChange={e => setMission(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && launch()}
          placeholder="Describe your mission…"
          className="flex-1 bg-gray-800 text-white rounded-lg px-4 py-2 border border-gray-700 focus:border-agency-500 outline-none"
        />
        <button onClick={launch} disabled={running || !mission.trim()}
          className="px-4 py-2 bg-agency-600 hover:bg-agency-500 disabled:opacity-50 text-white rounded-lg font-medium transition-colors">
          {running ? '⏳' : '▶ Run'}
        </button>
      </div>
      {result && (
        <pre className="bg-gray-950 text-green-400 text-xs rounded-lg p-4 overflow-auto max-h-64 font-mono">
          {result}
        </pre>
      )}
    </div>
  );
}

function AgentGraph() {
  const agents = [
    { name: 'pm',        category: 'Planning',   color: '#4f46e5' },
    { name: 'frontend',  category: 'Engineering',color: '#0891b2' },
    { name: 'backend',   category: 'Engineering',color: '#0891b2' },
    { name: 'security',  category: 'Security',   color: '#dc2626' },
    { name: 'qa',        category: 'Testing',    color: '#d97706' },
    { name: 'ai',        category: 'Engineering',color: '#0891b2' },
    { name: 'devops',    category: 'Engineering',color: '#0891b2' },
    { name: 'growth',    category: 'Marketing',  color: '#16a34a' },
    { name: 'sales',     category: 'Sales',      color: '#15803d' },
    { name: 'core',      category: 'Core',       color: '#9333ea' },
  ];

  return (
    <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
      <h2 className="text-lg font-semibold mb-4 text-white">Agent Registry (152 total)</h2>
      <div className="flex flex-wrap gap-2">
        {agents.map(a => (
          <div key={a.name}
            className="px-3 py-1 rounded-full text-xs font-mono text-white"
            style={{ backgroundColor: a.color + '33', border: `1px solid ${a.color}66` }}>
            {a.name}
          </div>
        ))}
        <div className="px-3 py-1 rounded-full text-xs font-mono text-gray-400 border border-gray-700">
          +142 more…
        </div>
      </div>
    </div>
  );
}
