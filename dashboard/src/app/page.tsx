import Link from 'next/link';

export default function Home() {
  return (
    <main className="flex flex-col items-center justify-center min-h-screen px-4">
      <div className="max-w-2xl w-full text-center space-y-8">
        <div>
          <h1 className="text-5xl font-bold text-white mb-2">The Agency</h1>
          <p className="text-agency-500 text-xl font-mono">152 agents. All into one.</p>
        </div>

        <p className="text-gray-400 text-lg">
          Claude-powered multi-agent orchestrator — unified entry point for every
          capability across your 109 repos.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-8">
          <Link href="/dashboard"
            className="block p-6 bg-gray-900 border border-gray-800 rounded-xl hover:border-agency-500 transition-colors group">
            <div className="text-2xl mb-2">📊</div>
            <h2 className="text-lg font-semibold text-white group-hover:text-agency-500">Dashboard</h2>
            <p className="text-gray-400 text-sm mt-1">Active missions, agent graph, swarm logs, Titans memory</p>
          </Link>

          <Link href="/chat"
            className="block p-6 bg-gray-900 border border-gray-800 rounded-xl hover:border-agency-500 transition-colors group">
            <div className="text-2xl mb-2">💬</div>
            <h2 className="text-lg font-semibold text-white group-hover:text-agency-500">Chat</h2>
            <p className="text-gray-400 text-sm mt-1">Launch missions via conversational interface</p>
          </Link>

          <Link href="/agents"
            className="block p-6 bg-gray-900 border border-gray-800 rounded-xl hover:border-agency-500 transition-colors group">
            <div className="text-2xl mb-2">🤖</div>
            <h2 className="text-lg font-semibold text-white group-hover:text-agency-500">Agents</h2>
            <p className="text-gray-400 text-sm mt-1">Browse all 152 agents, presets, and capabilities</p>
          </Link>

          <Link href="/memory"
            className="block p-6 bg-gray-900 border border-gray-800 rounded-xl hover:border-agency-500 transition-colors group">
            <div className="text-2xl mb-2">🧠</div>
            <h2 className="text-lg font-semibold text-white group-hover:text-agency-500">Memory</h2>
            <p className="text-gray-400 text-sm mt-1">Titans memory ledger — past missions and surprise weights</p>
          </Link>
        </div>

        <div className="mt-8 text-xs text-gray-600 font-mono">
          API: http://localhost:8100 (A2A)  ·  Agency: python3 agency.py --mission "..."
        </div>
      </div>
    </main>
  );
}
