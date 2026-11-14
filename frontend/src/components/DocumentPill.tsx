/** Document pill displayed in sidebar for each uploaded PDF. */
import { useCallback } from 'react'
import { deleteDocument } from '../api/client'

interface DocumentPillProps {
  doc: {
    id: string
    filename: string
    page_count: number
    status: 'ready' | 'failed'
  }
  conversationId: string
  anonId: string
  onDeleted: (docId: string) => void
}

export function DocumentPill({ doc, conversationId, anonId, onDeleted }: DocumentPillProps) {
  const handleDelete = useCallback(async () => {
    try {
      await deleteDocument(conversationId, doc.id, anonId)
      onDeleted(doc.id)
    } catch {
      // Error handled by parent if needed
    }
  }, [conversationId, doc.id, anonId, onDeleted])

  return (
    <div
      className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs ${
        doc.status === 'ready'
          ? 'bg-emerald-600/10 border border-emerald-600/30 text-emerald-400'
          : 'bg-red-600/10 border border-red-600/30 text-red-400'
      }`}
    >
      <span className="font-mono text-neutral-300">📄</span>
      <span className="truncate max-w-[120px]">{doc.filename}</span>
      <span className="text-neutral-500">{doc.page_count} pp</span>
      <button
        type="button"
        onClick={handleDelete}
        className="ml-1 p-0.5 hover:bg-neutral-700 rounded transition-colors"
        aria-label={`Delete ${doc.filename}`}
      >
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M18 6L6 18M6 6l12 12" />
        </svg>
      </button>
    </div>
  )
}