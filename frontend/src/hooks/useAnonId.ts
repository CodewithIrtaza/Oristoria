/**
 * useAnonId – creates and persists a random UUID in localStorage.
 * Sent as X-Anon-Id on every API request.
 */
import { useState } from 'react'

function generateUUID(): string {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID()
  }
  // Fallback for environments without crypto.randomUUID
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0
    return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16)
  })
}

const STORAGE_KEY = 'oristoria_anon_id'

export function useAnonId(): string {
  const [anonId] = useState<string>(() => {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) return stored
    const fresh = generateUUID()
    localStorage.setItem(STORAGE_KEY, fresh)
    return fresh
  })
  return anonId
}
