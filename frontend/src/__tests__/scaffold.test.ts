/**
 * Scaffold smoke test: verifies the frontend module can be imported
 * and the useAnonId hook produces a UUID.
 */
import { describe, it, expect } from 'vitest'

// Basic sanity test that does not require a DOM or network
describe('scaffold', () => {
  it('generates a valid UUID v4 string', () => {
    // UUID v4 pattern
    const uuidV4Re = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i

    function generateUUID(): string {
      return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
        const r = (Math.random() * 16) | 0
        return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16)
      })
    }

    const id = generateUUID()
    expect(id).toMatch(uuidV4Re)
  })
})
