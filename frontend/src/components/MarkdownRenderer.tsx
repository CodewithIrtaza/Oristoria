/**
 * MarkdownRenderer – wraps Streamdown with Shiki syntax highlighting.
 *
 * Handles partial/streaming markdown gracefully (no crashes on unclosed
 * fences, asterisks, etc.). Only processes assistant messages; user
 * messages remain plain text in Message.tsx.
 */
import { Streamdown } from 'streamdown'

interface MarkdownRendererProps {
  /** Raw markdown string (may be partial mid-stream). */
  content: string
}

export function MarkdownRenderer({ content }: MarkdownRendererProps) {
  return (
    <Streamdown
      mode="static"
      parseIncompleteMarkdown={true}
      shikiTheme={['github-dark', 'github-dark']}
      className="space-y-4"
    >
      {content}
    </Streamdown>
  )
}