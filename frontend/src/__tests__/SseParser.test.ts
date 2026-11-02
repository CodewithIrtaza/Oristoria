/**
 * T02: SSE parser for POST /conversations/{id}/messages.
 * Must handle events split across TCP chunks, comments (keep-alive)
 * and JSON payloads, per Docs/TECH_DESIGN.md §SSE stream.
 */
import { describe, expect, it } from 'vitest'
import { parseSSEStream } from '../api/sse'
import type { SSEEvent } from '../api/sse'

function streamFromChunks(chunks: string[]): Response {
  const encoder = new TextEncoder()
  const body = new ReadableStream({
    start(controller) {
      for (const c of chunks) controller.enqueue(encoder.encode(c))
      controller.close()
    },
  })
  return new Response(body, { status: 200, headers: { 'content-type': 'text/event-stream' } })
}

async function collect(response: Response): Promise<SSEEvent[]> {
  const out: SSEEvent[] = []
  for await (const ev of parseSSEStream(response)) out.push(ev)
  return out
}

describe('parseSSEStream (T02)', () => {
  it('parses event/data pairs from a complete chunk', async () => {
    const res = streamFromChunks([
      'event: message_start\ndata: {"message_id":"m1","conversation_id":"c1"}\n\n',
      'event: token\ndata: {"delta":"Hello"}\n\n',
      'event: message_end\ndata: {"message_id":"m1","finish_reason":"stop","usage":{"input_tokens":1,"output_tokens":2}}\n\n',
    ])
    const events = await collect(res)
    expect(events.map((e) => e.event)).toEqual(['message_start', 'token', 'message_end'])
    expect(events[0].data).toEqual({ message_id: 'm1', conversation_id: 'c1' })
    expect(events[2].data).toEqual({
      message_id: 'm1',
      finish_reason: 'stop',
      usage: { input_tokens: 1, output_tokens: 2 },
    })
  })

  it('reassembles events split across network chunks', async () => {
    const res = streamFromChunks([
      'event: to',
      'ken\nda',
      'ta: {"del',
      'ta":"Hi"}',
      '\n\n',
    ])
    const events = await collect(res)
    expect(events).toEqual([{ event: 'token', data: { delta: 'Hi' } }])
  })

  it('ignores keep-alive comment lines', async () => {
    const res = streamFromChunks([
      ': ping\n\nevent: token\ndata: {"delta":"a"}\n\n',
    ])
    const events = await collect(res)
    expect(events).toEqual([{ event: 'token', data: { delta: 'a' } }])
  })

  it('merges multiple data lines of one event', async () => {
    const res = streamFromChunks([
      'event: token\ndata: {"delta":"a"}\ndata: {"delta":"b"}\n\n',
    ])
    const events = await collect(res)
    expect(events).toEqual([{ event: 'token', data: '{"delta":"a"}\n{"delta":"b"}' }])
  })
})
