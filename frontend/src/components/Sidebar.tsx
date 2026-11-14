/** Sidebar – conversation list with "New chat", switching, and document pills. */
import { UploadButton } from './UploadButton'
import { DocumentPill } from './DocumentPill'
import type { ConversationListItem, Document } from '../api/client'

export interface SidebarProps {
  conversations: ConversationListItem[]
  active: string | null
  loading: boolean
  error: string | null
  onCreate: () => void
  onSelect: (id: string) => void
  documents: Document[]
  documentsLoading: boolean
  onUpload: (file: File) => void
  onDeleteDocument: (docId: string) => void
}

export function Sidebar({
  conversations,
  active,
  loading,
  error,
  onCreate,
  onSelect,
  documents,
  documentsLoading,
  onUpload,
  onDeleteDocument,
}: SidebarProps) {
  return (
    <aside
      aria-label="Conversations"
      className="w-80 shrink-0 border-r border-neutral-800 bg-neutral-900/50 p-4 flex flex-col"
    >
      <div className="mb-4 flex items-center gap-2">
        <button
          onClick={onCreate}
          disabled={loading}
          className="flex-1 rounded border border-neutral-700 bg-neutral-800 px-3 py-1.5 text-sm text-neutral-100 hover:bg-neutral-700 disabled:opacity-50"
        >
          + New chat
        </button>
      </div>

      {error ? (
        <p className="text-xs text-red-400" role="alert">
          {error}
        </p>
      ) : loading ? (
        <p className="text-xs text-neutral-400">Loading…</p>
      ) : conversations.length === 0 ? (
        <p className="text-xs text-neutral-500">No conversations yet.</p>
      ) : (
        <ul className="space-y-1 flex-1 overflow-y-auto">
          {conversations.map((conv) => (
            <li key={conv.id}>
              <button
                onClick={() => onSelect(conv.id)}
                aria-current={active === conv.id}
                className={`w-full rounded px-3 py-2 text-left text-sm ${
                  active === conv.id
                    ? 'border border-emerald-600/30 bg-emerald-600/10 text-emerald-400'
                    : 'text-neutral-300 hover:bg-neutral-800'
                }`}
              >
                {conv.title}
              </button>
            </li>
          ))}
        </ul>
      )}

      {active && (
        <div className="mt-4 border-t border-neutral-800 pt-4 space-y-2">
          <div className="flex items-center gap-2">
            <span className="text-xs uppercase tracking-widest text-neutral-500">
              Documents
            </span>
            <span className="text-xs text-neutral-400">{documents.length}/3</span>
          </div>

          <UploadButton
            conversationId={active}
            anonId=""
            onUploaded={onUpload}
          />

          {documentsLoading ? (
            <p className="text-xs text-neutral-400">Loading documents…</p>
          ) : documents.length === 0 ? (
            <p className="text-xs text-neutral-500">No documents attached</p>
          ) : (
            <div className="space-y-1.5">
              {documents.map((doc) => (
                <DocumentPill
                  key={doc.id}
                  doc={doc}
                  conversationId={active}
                  anonId=""
                  onDeleted={onDeleteDocument}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </aside>
  )
}