/**
 * T02: Composer calls onSend when form is submitted.
 */
import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { Composer } from '../components/Composer'

describe('Composer', () => {
  it('calls onSend with input value on submit', async () => {
    const onSend = vi.fn()
    render(<Composer disabled={false} onSend={onSend} />)

    const input = screen.getByLabelText('Message')
    fireEvent.change(input, { target: { value: 'hi there' } })
    fireEvent.click(screen.getByRole('button', { name: 'Send' }))

    expect(onSend).toHaveBeenCalledWith('hi there')
  })

  it('does not call onSend with empty input', async () => {
    const onSend = vi.fn()
    render(<Composer disabled={false} onSend={onSend} />)

    fireEvent.click(screen.getByRole('button', { name: 'Send' }))

    expect(onSend).not.toHaveBeenCalled()
  })

  it('is disabled when streaming prop is true', async () => {
    render(<Composer disabled={true} onSend={vi.fn()} />)

    const input = screen.getByLabelText('Message')
    const button = screen.getByRole('button', { name: 'Send' })

    expect(input.getAttribute('disabled')).toBeDefined()
    expect(button.getAttribute('disabled')).toBeDefined()
  })
})
