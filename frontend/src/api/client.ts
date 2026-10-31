/**
 * Typed API client for the Oristoria backend.
 * Implemented in Task 2. Stub here for import structure.
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

export async function healthCheck(): Promise<{ status: string }> {
  const r = await fetch(`${API_BASE}/api/health`)
  return r.json()
}

// TODO Task 2: createConversation, listConversations, getConversation, deleteConversation
// TODO Task 3: sendMessage (SSE stream setup lives in sse.ts)
// TODO Task 4: uploadDocument, listDocuments, deleteDocument
