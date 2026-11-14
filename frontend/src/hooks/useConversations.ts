/**
 * useConversations – the single source of truth for the conversation
 * list. The sidebar and the chat view both read from this hook, so the
 * list and the active conversation can never disagree.
 */
import { useCallback, useEffect, useState } from 'react'
import {
  createConversation,
  listConversations,
  type ConversationListItem,
} from '../api/client'

export interface Conversations {
  conversations: ConversationListItem[]
  active: string | null
  loading: boolean
  error: string | null
  create: () => Promise<string>
  select: (id: string) => void
}

export function useConversations(anonId: string): Conversations {
  const [conversations, setConversations] = useState<ConversationListItem[]>([])
  const [active, setActive] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Load the list once per anon id and select the most recent chat.
  useEffect(() => {
    let cancelled = false
    void (async () => {
      try {
        const { items } = await listConversations(anonId)
        if (cancelled) return
        setConversations(items)
        setError(null)
        setActive((current) => current ?? items[0]?.id ?? null)
      } catch (err) {
        if (cancelled) return
        setError(err instanceof Error ? err.message : 'Could not load chats')
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [anonId])

  const create = useCallback(async (): Promise<string> => {
    const created = await createConversation(anonId)
    setConversations((prev) => [created, ...prev.filter((c) => c.id !== created.id)])
    setActive(created.id)
    return created.id
  }, [anonId])

  const select = useCallback((id: string) => {
    setActive(id)
  }, [])

  return { conversations, active, loading, error, create, select }
}
