import { useEffect, useRef, useState } from 'react'

import { Composer } from './components/Composer'
import { ChatView } from './components/ChatView'
import { Sidebar } from './components/Sidebar'
import { useAnonId } from './hooks/useAnonId'
import { useConversations } from './hooks/useConversations'
import { useChatStream, type ChatMessage } from './hooks/useChatStream'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

function toChatMessages(
  msgs: Array<{ role: string; content: string }>,
): ChatMessage[] {
  return msgs.map((m, i) => ({
    id: `server-${i}`,
    role: m.role as 'user' | 'assistant',
    content: m.content,
  }))
}

function App() {
  const [status, setStatus] = useState<string>('loading…')
  const [initialMessages, setInitialMessages] = useState<ChatMessage[]>([])
  const anonId = useAnonId()

  const { conversations, active, create, select } =
    useConversations(anonId)

  const { messages, streaming, send } = useChatStream(
    active ?? '',
    anonId,
    initialMessages,
  )
  const sendRef = useRef(send)
  sendRef.current = send

  const handleSelect = async (id: string) => {
    const detail = await select(id)
    setInitialMessages(toChatMessages(detail?.messages ?? []))
  }

  const handleSend = async (content: string) => {
    if (!active) {
      const id = await create()
      await select(id)
    }
    await sendRef.current(content)
  }

  useEffect(() => {
    fetch(`${API_BASE}/api/health`)
      .then((r) => r.json())
      .then((d) => setStatus(d.status ?? 'unknown'))
      .catch(() => setStatus('offline'))
  }, [])

  return (
    <main className="min-h-screen flex flex-col bg-neutral-950 text-neutral-100">
      <header className="border-b border-neutral-800 px-6 py-4">
        <h1 className="text-2xl font-bold tracking-tight">Oristoria</h1>
        <p className="text-neutral-400 text-xs">
          LangGraph chat with PDF context
        </p>
      </header>

      <div className="flex flex-1 overflow-hidden">
        <Sidebar onSelect={handleSelect} />

        <div className="flex-1 flex flex-col p-6">
          <div className="mb-4 flex items-center justify-between">
            <span className="text-xs uppercase tracking-widest text-neutral-500">
              Conversation
            </span>
            <span className="text-xs text-neutral-400">
              {conversations.find((c) => c.id === active)?.title ?? 'New chat'}
            </span>
          </div>

          <div className="flex flex-col items-center gap-4 mb-6">
            <span className="text-xs uppercase tracking-widest text-neutral-500">
              API status
            </span>
            <p className="text-lg font-mono">
              {status === 'ok' ? (
                <span className="text-emerald-400">● ok</span>
              ) : status === 'loading…' ? (
                <span className="text-yellow-400">● {status}</span>
              ) : (
                <span className="text-red-400">● {status}</span>
              )}
            </p>
          </div>

          <div className="flex-1 overflow-y-auto">
            <ChatView messages={messages} />
          </div>

          <Composer
            disabled={streaming}
            onSend={(content) => void handleSend(content)}
          />
        </div>
      </div>
    </main>
  )
}

export default App
