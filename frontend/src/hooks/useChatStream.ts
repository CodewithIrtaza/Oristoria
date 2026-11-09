/**
 * useChatStream – owns the message list and streaming state machine
 * for the (single) T02 conversation. Stop-button abort arrives in
 * Task 4; the hook already builds on AbortController for that.
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import { sendMessageStream } from '../api/client'
import { parseSSEStream } from '../api/sse'

export interface ChatMessage {
  /** Server message id when known (stable React key), temp id otherwise. */
  id: string
  role: 'user' | 'assistant'
  content: string
  error?: string
}

export interface ChatStream {
  messages: ChatMessage[]
  streaming: boolean
  send: (content: string) => Promise<void>
  stop: () => void
}

let tempId = 0

export function useChatStream(
  conversationId: string,
  anonId: string,
  initialMessages: ChatMessage[] = [],
): ChatStream {
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages)
  const [streaming, setStreaming] = useState(false)
  const controller = useRef<AbortController | null>(null)

  // Reset message list when switching conversations.
  useEffect(() => {
    setMessages(initialMessages)
  }, [conversationId, initialMessages])

  const stop = useCallback(() => {
    controller.current?.abort()
    controller.current = null
    setStreaming(false)
  }, [])

  const send = useCallback(
    async (content: string) => {
      const text = content.trim()
      if (!text || controller.current) return

      tempId += 1
      setMessages((prev) => [
        ...prev,
        { id: `user-${tempId}`, role: 'user', content: text },
        { id: `assistant-${tempId}`, role: 'assistant', content: '' },
      ])
      setStreaming(true)
      controller.current = new AbortController()

      try {
        const response = await sendMessageStream(
          conversationId,
          text,
          anonId,
          controller.current.signal,
        )
        for await (const ev of parseSSEStream(response)) {
          if (ev.event === 'message_start' || ev.event === 'message_end') {
            // The server id is the stable React key; set it once the
            // stream names the message. Both events carry message_id.
            const messageId = String((ev.data as { message_id: string }).message_id)
            setMessages((prev) => patchLastAssistant(prev, (m) => ({ ...m, id: messageId })))
          } else if (ev.event === 'token') {
            const delta = String((ev.data as { delta: string }).delta)
            setMessages((prev) => patchLastAssistant(prev, (m) => ({ ...m, content: m.content + delta })))
          } else if (ev.event === 'error') {
            const data = ev.data as { message: string }
            setMessages((prev) => patchLastAssistant(prev, (m) => ({ ...m, error: data.message })))
          }
        }
      } catch (err) {
        // Ignore AbortError - it's expected when user clicks Stop
        if (err instanceof Error && err.name === 'AbortError') {
          return
        }
        setMessages((prev) =>
          patchLastAssistant(prev, (m) => ({
            ...m,
            error: err instanceof Error ? err.message : 'Stream failed',
          })),
        )
      } finally {
        controller.current = null
        setStreaming(false)
      }
    },
    [conversationId, anonId],
  )

  return { messages, streaming, send, stop }
}

/** Patch the trailing assistant bubble – the one currently streaming. */
function patchLastAssistant(
  messages: ChatMessage[],
  patch: (m: ChatMessage) => ChatMessage,
): ChatMessage[] {
  let last = -1
  for (let i = messages.length - 1; i >= 0; i -= 1) {
    if (messages[i].role === 'assistant') {
      last = i
      break
    }
  }
  if (last === -1) return messages
  return messages.map((m, i) => (i === last ? patch(m) : m))
}
