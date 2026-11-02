/**
 * T02: sending a message streams tokens into the chat view.
 * fetch is stubbed: /api/health returns JSON; the messages endpoint
 * returns a text/event-stream ReadableStream body.
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from '../App'

function sseResponse(chunks: string[]): Response {
  const encoder = new TextEncoder()
  const body = new ReadableStream({
    start(controller) {
      for (const c of chunks) controller.enqueue(encoder.encode(c))
      controller.close()
    },
  })
  return new Response(body, {
    status: 200,
    headers: { 'content-type': 'text/event-stream' },
  })
}

function stubFetch() {
  const messages = sseResponse([
    'event: message_start\ndata: {"message_id":"m1","conversation_id":"c1"}\n\n',
    'event: token\ndata: {"delta":"Hello"}\n\n',
    'event: token\ndata: {"delta":"!"}\n\n',
    'event: message_end\ndata: {"message_id":"m1","finish_reason":"stop","usage":{"input_tokens":0,"output_tokens":0}}\n\n',
  ])
  const fetchMock = vi.fn((url: string | URL | Request, _options?: unknown) => {
    const href = typeof url === 'string' ? url : url instanceof Request ? url.url : url.href
    if (href.includes('/api/health')) {
      return Promise.resolve(new Response(JSON.stringify({ status: 'ok' }), {
        headers: { 'content-type': 'application/json' },
      }))
    }
    if (href.includes('/messages')) return Promise.resolve(messages)
    throw new Error(`unexpected fetch: ${href}`)
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

afterEach(() => {
  vi.unstubAllGlobals()
  localStorage.clear()
})

describe('chat streaming (T02)', () => {
  it('streams the fake reply token-by-token into the chat view', async () => {
    const fetchMock = stubFetch()
    const user = userEvent.setup()
    render(<App />)

    await screen.findByText('● ok')

    const input = screen.getByLabelText('Message')
    await user.type(input, 'hi there')
    await user.click(screen.getByRole('button', { name: 'Send' }))

    // The user turn is echoed, and the streamed tokens assemble into
    // the assistant reply.
    await screen.findByText('hi there')
    await waitFor(() => {
      const bubbles = screen
        .getAllByTestId('message')
        .filter((m) => m.getAttribute('data-role') === 'assistant')
      const reply = bubbles[bubbles.length - 1]
      expect(reply.textContent).toBe('Hello!')
    })

    // Both requests used the anon id header.
    const messagesCall = fetchMock.mock.calls.find(([href]) =>
      String(href).includes('/messages'),
    )
    const init = messagesCall?.[1] as
      | { headers: Record<string, string>; body: string }
      | undefined
    expect(init?.headers['X-Anon-Id']).toBeTruthy()
    expect(JSON.parse(init?.body ?? '{}')).toEqual({ content: 'hi there' })
  })

  it('sends nothing on empty input', async () => {
    const fetchMock = stubFetch()
    const user = userEvent.setup()
    render(<App />)

    await screen.findByText('● ok')
    await user.click(screen.getByRole('button', { name: 'Send' }))

    expect(fetchMock.mock.calls.filter(([h]) => String(h).includes('/messages'))).toHaveLength(0)
  })
})
