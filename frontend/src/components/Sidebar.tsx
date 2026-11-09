/** Sidebar – conversation list with "New chat" and switching. */
import { useState } from 'react'
import { useConversations } from '../hooks/useConversations'
import { useAnonId } from '../hooks/useAnonId'

export function Sidebar({ onSelect }: { onSelect: (id: string) => void }) {
  const anonId = useAnonId()
  const { conversations, active, loading, create, select } =
    useConversations(anonId)
  const [, setNewChatName] = useState('')

  const handleCreate = async () => {
    const id = await create()
    onSelect(id)
    setNewChatName('')
  }

  return (
    <aside
      aria-label="Conversations"
      className="w-80 border-r border-neutral-800 bg-neutral-900/50 p-4"
    >
      <div className="flex items-center gap-2 mb-4">
        <button
          onClick={handleCreate}
          disabled={loading}
          className="flex-1 px-3 py-1.5 text-sm bg-neutral-800 hover:bg-neutral-700 text-neutral-100 rounded border border-neutral-700 disabled:opacity-50"
        >
          + New chat
        </button>
      </div>

      {loading ? (
        <p className="text-xs text-neutral-400">Loading…</p>
      ) : conversations.length === 0 ? (
        <p className="text-xs text-neutral-500">No conversations yet.</p>
      ) : (
        <ul className="space-y-1">
          {conversations.map((conv) => (
            <li key={conv.id}>
              <button
                onClick={() => {
                  select(conv.id).then(() => onSelect(conv.id))
                }}
                className={`w-full text-left px-3 py-2 rounded text-sm ${
                  active === conv.id
                    ? 'bg-phosphor-accent/10 text-phosphor-accent border border-phosphor-accent/30'
                    : 'text-neutral-300 hover:bg-neutral-800'
                }`}
              >
                {conv.title}
              </button>
            </li>
          ))}
        </ul>
      )}
    </aside>
  )
}
