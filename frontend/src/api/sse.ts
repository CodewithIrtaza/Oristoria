/**
 * SSE stream parser for POST /conversations/{id}/messages.
 * Uses fetch + ReadableStream + AbortController (EventSource is GET-only).
 *
 * Handles: events split across network chunks, multi-line `data:`,
 * `: comment` keep-alive lines. Payloads are JSON per TECH_DESIGN §4.
 */

export interface SSEEvent {
  event: string
  data: unknown
}

const DECODER = new TextDecoder()

/** Read one SSE block's lines into an {event, data} pair, or null. */
function eventFromBlock(block: string): SSEEvent | null {
  let event = 'message'
  const dataLines: string[] = []
  for (const line of block.split('\n')) {
    if (line.startsWith(':')) continue // comment / keep-alive
    if (line.startsWith('event: ')) event = line.slice('event: '.length)
    else if (line.startsWith('data: ')) dataLines.push(line.slice('data: '.length))
  }
  if (dataLines.length === 0) return null
  const raw = dataLines.join('\n')
  let data: unknown = raw
  try {
    data = JSON.parse(raw)
  } catch {
    // keep raw string; server sends JSON but stay resilient
  }
  return { event, data }
}

export async function* parseSSEStream(response: Response): AsyncGenerator<SSEEvent> {
  if (!response.ok) {
    throw new Error(`stream failed with ${response.status}`)
  }
  if (!response.body) {
    throw new Error('stream response has no body')
  }

  const reader = response.body.getReader()
  let buffer = ''

  const flush = (): SSEEvent[] => {
    const events: SSEEvent[] = []
    let index: number
    while ((index = buffer.indexOf('\n\n')) !== -1) {
      const block = buffer.slice(0, index)
      buffer = buffer.slice(index + 2)
      const ev = eventFromBlock(block)
      if (ev) events.push(ev)
    }
    return events
  }

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += DECODER.decode(value, { stream: true })
      for (const ev of flush()) yield ev
    }
  } finally {
    reader.releaseLock()
  }

  // Flush a trailing block that lacked its closing blank line.
  if (buffer.trim()) {
    const ev = eventFromBlock(buffer)
    if (ev) yield ev
  }
}
