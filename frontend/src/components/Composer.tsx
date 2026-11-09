/** Composer – text input + send button. Disabled while streaming (T02). */
import { useState, type FormEvent } from 'react'

export interface ComposerProps {
  disabled: boolean
  onSend: (content: string) => void
}

export function Composer({ disabled, onSend }: ComposerProps) {
  const [value, setValue] = useState('')

  function submit(e: FormEvent) {
    e.preventDefault()
    const text = value.trim()
    if (!text || disabled) return
    onSend(text)
    setValue('')
  }

  return (
    <form onSubmit={submit} role="form" className="flex w-full max-w-2xl gap-2">
      <input
        aria-label="Message"
        className="flex-1 rounded-lg border border-neutral-800 bg-neutral-900 px-4 py-2 text-sm text-neutral-100 outline-none focus:border-neutral-600"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        disabled={disabled}
        placeholder={disabled ? 'Streaming…' : 'Type a message'}
      />
      <button
        type="submit"
        disabled={disabled || !value.trim()}
        className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-40"
      >
        Send
      </button>
    </form>
  )
}
