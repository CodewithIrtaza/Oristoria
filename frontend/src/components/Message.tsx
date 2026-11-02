/** Message bubble. T02 renders plain text; markdown arrives with Task 5. */
import type { ChatMessage } from '../hooks/useChatStream'

export function Message({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user'
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        data-testid="message"
        data-role={message.role}
        className={`max-w-[75%] rounded-xl px-4 py-2 text-sm whitespace-pre-wrap ${
          isUser
            ? 'bg-emerald-600 text-white'
            : 'bg-neutral-900 border border-neutral-800 text-neutral-100'
        }`}
      >
        {message.content || (message.error ? '' : <span className="animate-pulse">…</span>)}
        {message.error && (
          <p className="mt-1 text-xs text-red-400" role="alert">
            {message.error}
          </p>
        )}
      </div>
    </div>
  )
}
