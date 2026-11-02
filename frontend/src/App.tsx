import { useEffect, useMemo, useState } from 'react'

import { Composer } from './components/Composer'
import { ChatView } from './components/ChatView'
import { useAnonId } from './hooks/useAnonId'
import { useChatStream } from './hooks/useChatStream'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

function App() {
  const [status, setStatus] = useState<string>('loading…')
  const anonId = useAnonId()

  // T02 placeholder: a client-side id so a turn can stream without the
  // conversation table. Task 3 replaces this with real creation + sidebar.
  const conversationId = useMemo(() => crypto.randomUUID(), [])

  const { messages, streaming, send } = useChatStream(conversationId, anonId)

  useEffect(() => {
    fetch(`${API_BASE}/api/health`)
      .then((r) => r.json())
      .then((d) => setStatus(d.status ?? 'unknown'))
      .catch(() => setStatus('offline'))
  }, [])

  return (
    <main className="min-h-screen flex flex-col items-center gap-4 bg-neutral-950 text-neutral-100 py-10 px-4">
      <h1 className="text-4xl font-bold tracking-tight">Oristoria</h1>
      <p className="text-neutral-400 text-sm">LangGraph chat with PDF context</p>
      <div className="rounded-lg border border-neutral-800 px-6 py-4 text-center">
        <span className="text-xs uppercase tracking-widest text-neutral-500">API status</span>
        <p className="mt-1 text-lg font-mono">
          {status === 'ok' ? (
            <span className="text-emerald-400">● ok</span>
          ) : status === 'loading…' ? (
            <span className="text-yellow-400">● {status}</span>
          ) : (
            <span className="text-red-400">● {status}</span>
          )}
        </p>
      </div>

      <div className="flex w-full max-w-2xl flex-1 flex-col gap-4 overflow-y-auto">
        <ChatView messages={messages} />
      </div>

      <Composer disabled={streaming} onSend={(content) => void send(content)} />
    </main>
  )
}

export default App
