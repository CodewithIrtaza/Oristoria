/** ChatView – scrollable message list + streaming messages (T02). */
import type { ChatMessage } from '../hooks/useChatStream'
import { Message } from './Message'

export function ChatView({ messages }: { messages: ChatMessage[] }) {
  return (
    <div className="flex w-full max-w-2xl flex-col gap-3" aria-label="Chat">
      {messages.map((m) => (
        <Message key={`${m.role}-${m.id}`} message={m} />
      ))}
    </div>
  )
}
