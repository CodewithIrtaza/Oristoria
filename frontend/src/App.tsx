import { useEffect, useState } from 'react'

import { Composer } from './components/Composer'
import { ChatView } from './components/ChatView'
import { Sidebar } from './components/Sidebar'
import { useAnonId } from './hooks/useAnonId'
import { useConversations } from './hooks/useConversations'
import { useChatStream } from './hooks/useChatStream'
import { useDocuments } from './hooks/useDocuments'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

function App() {
  const [status, setStatus] = useState<string>('loading…')
  const anonId = useAnonId()

  // One hook owns the conversation list; the sidebar only renders it.
  const { conversations, active, loading, error, create, select } =
    useConversations(anonId)

  const { messages, streaming, send, stop } = useChatStream(active, anonId)

  const { documents, loading: documentsLoading, upload, delete: deleteDocument } =
    useDocuments(active, anonId)

  useEffect(() => {
    fetch(`${API_BASE}/api/health`)
      .then((r) => r.json())
      .then((d) => setStatus(d.status ?? 'unknown'))
      .catch(() => setStatus('offline'))
  }, [])

  const handleCreate = () => {
    void create()
  }

  const handleSend = async (content: string) => {
    // Send to the active conversation, creating one first if needed.
    // The id is passed explicitly so a brand-new chat cannot miss it.
    const targetId = active ?? (await create())
    await send(targetId, content)
  }

  const activeTitle =
    conversations.find((c) => c.id === active)?.title ?? 'New chat'

  return (
    <main className="flex min-h-screen flex-col bg-neutral-950 text-neutral-100">
      <header className="border-b border-neutral-800 px-6 py-4">
        <h1 className="text-2xl font-bold tracking-tight">Oristoria</h1>
        <p className="text-xs text-neutral-400">
          LangGraph chat with PDF context
        </p>
      </header>

      <div className="flex flex-1 overflow-hidden">
        <Sidebar
          conversations={conversations}
          active={active}
          loading={loading}
          error={error}
          onCreate={handleCreate}
          onSelect={select}
          documents={documents}
          documentsLoading={documentsLoading}
          onUpload={upload}
          onDeleteDocument={deleteDocument}
        />

        <div className="flex flex-1 flex-col p-6">
          <div className="mb-4 flex items-center justify-between">
            <span className="text-xs uppercase tracking-widest text-neutral-500">
              Conversation
            </span>
            <span className="text-xs text-neutral-400">{activeTitle}</span>
          </div>

          <div className="mb-6 flex flex-col items-center gap-4">
            <span className="text-xs uppercase tracking-widest text-neutral-500">
              API status
            </span>
            <p className="font-mono text-lg">
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
            streaming={streaming}
            onSend={(content) => void handleSend(content)}
            onStop={stop}
          />
        </div>
      </div>
    </main>
  )
}

export default App
