/**
 * T05: Streaming Markdown & Syntax-Highlighted Code.
 *
 * Covers rendering of GitHub-Flavored Markdown with Shiki syntax highlighting.
 */
import { describe, it, expect } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { Message } from '../components/Message'

describe('T05 Markdown rendering', () => {
  it('renders code block with syntax highlighting and language label', async () => {
    const markdown = '```python\nprint("hello")\n```'
    render(
      <Message
        message={{
          id: 'm-1',
          role: 'assistant',
          content: markdown,
        }}
      />,
    )

    // Wait for Streamdown's Suspense to resolve and verify all code block elements
    await waitFor(() => {
      const codeBlock = document.body.querySelector('[data-streamdown="code-block"]')
      expect(codeBlock).toBeDefined()
      expect(codeBlock?.getAttribute('data-streamdown')).toBe('code-block')
      expect(codeBlock?.getAttribute('data-language')).toBe('python')

      const langLabel = document.body.querySelector('[data-streamdown="code-block-header"] .ml-1')
      expect(langLabel).toBeDefined()

      const codeBody = document.body.querySelector('[data-streamdown="code-block-body"]')
      expect(codeBody).toBeDefined()
      expect(codeBody?.textContent).toContain('print')

      const copyBtn = document.body.querySelector('[data-streamdown="code-block-copy-button"]')
      expect(copyBtn).toBeDefined()
    })
  })

  it('renders headings, bold, italics, links, blockquotes, and lists', async () => {
    const markdown = `
# Heading 1
## Heading 2

**bold** and *italic* and ~~strikethrough~~

[link](https://example.com)

> blockquote

- item 1
- item 2

1. ordered 1
2. ordered 2
`
    render(
      <Message
        message={{
          id: 'm-2',
          role: 'assistant',
          content: markdown,
        }}
      />,
    )

    await waitFor(() => {
      expect(screen.getByText('Heading 1')).toBeDefined()
    })

    expect(screen.getByText('Heading 1')).toBeDefined()
    expect(screen.getByText('Heading 2')).toBeDefined()
    expect(screen.getByText('bold')).toBeDefined()
    expect(screen.getByText('italic')).toBeDefined()
    expect(screen.getByText('strikethrough')).toBeDefined()
    const link = screen.getByRole('link', { name: 'link' })
    expect(link).toBeDefined()
    expect(link.getAttribute('href')).toBe('https://example.com/')
    expect(screen.getByText('blockquote')).toBeDefined()
    expect(screen.getByText('item 1')).toBeDefined()
    expect(screen.getByText('item 2')).toBeDefined()
    expect(screen.getByText('ordered 1')).toBeDefined()
    expect(screen.getByText('ordered 2')).toBeDefined()
  })

  it('does not throw on mid-stream partial markdown (unclosed fence)', () => {
    const partial = '```python\nprint("hello"'
    expect(() => {
      render(
        <Message
          message={{
            id: 'm-3',
            role: 'assistant',
            content: partial,
          }}
        />,
      )
    }).not.toThrow()
  })

  it('does not throw on mid-stream partial markdown (unclosed bold)', () => {
    const partial = 'This is **bold without close'
    expect(() => {
      render(
        <Message
          message={{
            id: 'm-4',
            role: 'assistant',
            content: partial,
          }}
        />,
      )
    }).not.toThrow()
  })

  it('user messages render as plain text (no markdown processing)', () => {
    const markdown = '```python\nprint("hello")\n```'
    render(
      <Message
        message={{
          id: 'm-5',
          role: 'user',
          content: markdown,
        }}
      />,
    )

    // User message should NOT have code block rendering
    expect(screen.queryByTestId('code-block')).toBeNull()
    // Should render as raw text (with newlines)
    const userMessage = screen.getByTestId('message')
    expect(userMessage.textContent).toContain('print("hello")')
  })
})