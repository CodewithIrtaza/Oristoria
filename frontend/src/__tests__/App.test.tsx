/**
 * T01: Connected Health & Liveness Baseline.
 * App shows a green "● ok" badge when the backend is reachable,
 * and "● offline" when the backend is stopped/unreachable.
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import App from '../App'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('App health badge (T01)', () => {
  it('shows a green ok badge when the backend answers /api/health', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ json: async () => ({ status: 'ok' }) }),
    )

    render(<App />)

    // getByText throws if the badge never appears — that is the failure signal.
    await waitFor(() => {
      const badge = screen.getByText('● ok')
      expect(badge.className).toContain('text-emerald-400')
    })
  })

  it('shows offline when the backend is unreachable', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockRejectedValue(new Error('connection refused')),
    )

    render(<App />)

    await waitFor(() => {
      const badge = screen.getByText('● offline')
      expect(badge.className).toContain('text-red-400')
    })
  })
})
