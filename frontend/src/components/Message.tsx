/** Message bubble. T05 adds markdown rendering for assistant messages. */
import type { ChatMessage } from '../hooks/useChatStream'
import { MarkdownRenderer } from './MarkdownRenderer'

export function Message({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user'
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        data-testid="message"
        data-role={message.role}
        className={`max-w-[75%] rounded-xl px-4 py-2 text-sm ${
          isUser
            ? 'bg-emerald-600 text-white whitespace-pre-wrap'
            : 'bg-neutral-900 border border-neutral-800 text-neutral-100'
        }`}
      >
        {isUser ? (
          message.content || (message.error ? '' : <span className="animate-pulse">…</span>)
        ) : (
          <MarkdownRenderer content={message.content} />
        )}
        {message.error && (
          <p className="mt-1 text-xs text-red-400" role="alert">
            {message.error}
          </p>
        )}
      </div>
    </div>
  )
}
