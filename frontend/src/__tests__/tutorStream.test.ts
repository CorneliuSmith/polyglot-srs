import { describe, it, expect } from 'vitest'
import { parseSSE } from '../api/tutor'

describe('parseSSE', () => {
  it('parses complete events and keeps the partial tail', () => {
    const buffer =
      'data: {"type":"delta","text":"Hel"}\n\n' +
      'data: {"type":"delta","text":"lo"}\n\n' +
      'data: {"type":"do'
    const { events, rest } = parseSSE(buffer)
    expect(events).toEqual([
      { type: 'delta', text: 'Hel' },
      { type: 'delta', text: 'lo' },
    ])
    expect(rest).toBe('data: {"type":"do')
  })

  it('resumes cleanly once the tail completes', () => {
    const first = parseSSE('data: {"type":"delta","text":"a"}\n\ndata: {"ty')
    const second = parseSSE(first.rest + 'pe":"done","reply":"a","remembered":0,"allowance":null}\n\n')
    expect(second.events).toEqual([
      { type: 'done', reply: 'a', remembered: 0, allowance: null },
    ])
    expect(second.rest).toBe('')
  })

  it('tolerates malformed frames without dropping the stream', () => {
    const { events } = parseSSE(
      'data: not-json\n\ndata: {"type":"reset"}\n\n',
    )
    expect(events).toEqual([{ type: 'reset' }])
  })
})
