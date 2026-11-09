/**
 * useConversations – list and manage conversations.
 * Backed by the real API (Task 3).
 */
import { useState, useCallback } from 'react'
import { createConversation, listConversations, getConversation } from '../api/client'

export interface Conversation {
  id: string
  title: string
  updated_at: string
}

export interface ConversationDetail extends Conversation {
  messages: Array<{ role: string; content: string }>
}

export function useConversations(anonId: string) {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [active, setActive] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await listConversations(anonId)
      setConversations(data)
      if (!active && data.length > 0) {
        setActive(data[0].id)
      }
    } catch {
      // Backend may not be available (e.g. in unit tests); ignore.
    } finally {
      setLoading(false)
    }
  }, [anonId, active])

  const create = useCallback(async () => {
    const data = await createConversation(anonId)
    setActive(data.id)
    return data.id
  }, [anonId, setActive])

  const select = useCallback(async (id: string) => {
    setActive(id)
    const detail = await getConversation(id, anonId)
    return detail
  }, [anonId])

  return {
    conversations,
    active,
    loading,
    load,
    create,
    select,
    setActive,
  }
}
