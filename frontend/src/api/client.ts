/**
 * Typed API client for the Oristoria backend.
 * Implemented in Task 2. Stub here for import structure.
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

export async function healthCheck(): Promise<{ status: string }> {
  const r = await fetch(`${API_BASE}/api/health`)
  return r.json()
}

/**
 * POST /conversations/{id}/messages and hand back the raw Response so
 * the SSE parser in sse.ts can consume it. Abort via the signal (Task 4).
 */
export async function sendMessageStream(
  conversationId: string,
  content: string,
  anonId: string,
  signal: AbortSignal,
): Promise<Response> {
  return fetch(
    `${API_BASE}/api/conversations/${conversationId}/messages`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Anon-Id': anonId,
      },
      body: JSON.stringify({ content }),
      signal,
    },
  )
}

// TODO Task 2: createConversation, listConversations, getConversation, deleteConversation
// TODO Task 3: sendMessage (SSE stream setup lives in sse.ts)
// TODO Task 4: uploadDocument, listDocuments, deleteDocument
