/** useDocuments – fetches and manages documents for the active conversation. */
import { useCallback, useEffect, useRef, useState } from 'react'
import { listDocuments, uploadDocument, deleteDocument } from '../api/client'

export interface DocumentUI {
  id: string
  filename: string
  page_count: number
  status: 'ready' | 'failed'
}

export function useDocuments(
  conversationId: string | null,
  anonId: string,
) {
  const [documents, setDocuments] = useState<DocumentUI[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const initialized = useRef(false)

  const fetchDocuments = useCallback(async () => {
    if (!conversationId) {
      setDocuments([])
      return
    }
    setLoading(true)
    setError(null)
    try {
      const { items } = await listDocuments(conversationId, anonId)
      setDocuments(
        items.map((d) => ({
          id: d.id,
          filename: d.filename,
          page_count: d.page_count,
          status: d.status,
        })),
      )
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load documents')
    } finally {
      setLoading(false)
    }
  }, [conversationId, anonId])

  // Load on mount and when conversationId/anonId change
  useEffect(() => {
    if (!initialized.current) {
      initialized.current = true
      fetchDocuments()
    }
  }, [fetchDocuments])

  const handleUpload = useCallback(
    async (file: File) => {
      if (!conversationId) return
      setLoading(true)
      setError(null)
      try {
        const doc = await uploadDocument(conversationId, anonId, file)
        setDocuments((prev) => [
          { id: doc.id, filename: doc.filename, page_count: doc.page_count, status: doc.status },
          ...prev,
        ])
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Upload failed')
        throw err
      } finally {
        setLoading(false)
      }
    },
    [conversationId, anonId],
  )

  const handleDelete = useCallback(
    async (docId: string) => {
      if (!conversationId) return
      setLoading(true)
      setError(null)
      try {
        await deleteDocument(conversationId, docId, anonId)
        setDocuments((prev) => prev.filter((d) => d.id !== docId))
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Delete failed')
      } finally {
        setLoading(false)
      }
    },
    [conversationId, anonId],
  )

  return { documents, loading, error, refresh: fetchDocuments, upload: handleUpload, delete: handleDelete }
}