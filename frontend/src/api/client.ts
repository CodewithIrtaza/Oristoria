/**
 * Typed API client for the Oristoria backend.
 *
 * Response shapes follow Docs/TECH_DESIGN.md §4.
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

export interface Conversation {
  id: string
  title: string
  created_at: string | null
  updated_at: string | null
}

export interface ConversationListItem {
  id: string
  title: string
  updated_at: string | null
}

export interface ServerMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  stopped: boolean
  tools: Array<{ name: string; chunks: number }>
}

export interface ConversationDetail {
  conversation: Conversation
  messages: ServerMessage[]
  documents: Array<{ id: string; filename: string; page_count: number }>
}

export interface Document {
  id: string
  conversation_id: string
  filename: string
  size_bytes: number
  page_count: number
  chunk_count: number
  status: 'ready' | 'failed'
  error: string | null
  created_at: string
}

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

export async function createConversation(anonId: string): Promise<Conversation> {
  const r = await fetch(`${API_BASE}/api/conversations`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Anon-Id': anonId,
    },
    body: JSON.stringify({}),
  })
  if (!r.ok) throw new Error(`createConversation failed: ${r.status}`)
  return r.json()
}

export async function listConversations(
  anonId: string,
): Promise<{ items: ConversationListItem[] }> {
  const r = await fetch(`${API_BASE}/api/conversations`, {
    headers: { 'X-Anon-Id': anonId },
  })
  if (!r.ok) throw new Error(`listConversations failed: ${r.status}`)
  return r.json()
}

export async function getConversation(
  conversationId: string,
  anonId: string,
): Promise<ConversationDetail> {
  const r = await fetch(
    `${API_BASE}/api/conversations/${conversationId}`,
    { headers: { 'X-Anon-Id': anonId } },
  )
  if (!r.ok) throw new Error(`getConversation failed: ${r.status}`)
  return r.json()
}

// Document API (Task 6)

export async function uploadDocument(
  conversationId: string,
  anonId: string,
  file: File,
): Promise<Document> {
  const formData = new FormData()
  formData.append('file', file)

  const r = await fetch(
    `${API_BASE}/api/conversations/${conversationId}/documents`,
    {
      method: 'POST',
      headers: {
        'X-Anon-Id': anonId,
      },
      body: formData,
    },
  )
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: 'Upload failed' }))
    throw new Error(err.detail || `uploadDocument failed: ${r.status}`)
  }
  return r.json()
}

export async function listDocuments(
  conversationId: string,
  anonId: string,
): Promise<{ items: Document[] }> {
  const r = await fetch(
    `${API_BASE}/api/conversations/${conversationId}/documents`,
    { headers: { 'X-Anon-Id': anonId } },
  )
  if (!r.ok) throw new Error(`listDocuments failed: ${r.status}`)
  return r.json()
}

export async function deleteDocument(
  conversationId: string,
  documentId: string,
  anonId: string,
): Promise<void> {
  const r = await fetch(
    `${API_BASE}/api/conversations/${conversationId}/documents/${documentId}`,
    {
      method: 'DELETE',
      headers: { 'X-Anon-Id': anonId },
    },
  )
  if (!r.ok) throw new Error(`deleteDocument failed: ${r.status}`)
}

// TODO Task 9: renameConversation, deleteConversation