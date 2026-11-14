/**
 * T06: PDF Upload, Validation & Vector Ingestion (frontend slice).
 *
 * Covers the UploadButton and document pill rendering.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { UploadButton } from '../components/UploadButton'
import { DocumentPill } from '../components/DocumentPill'

describe('T06 PDF Upload (frontend)', () => {
  const mockOnUploaded = vi.fn()
  const mockOnDeleted = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    // Mock fetch for API calls
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ id: 'doc-1', filename: 'test.pdf', page_count: 5, chunk_count: 10, status: 'ready' }),
    }))
  })

  it('renders upload button with drag-and-drop area', () => {
    render(
      <UploadButton
        conversationId="conv-1"
        anonId="anon-1"
        onUploaded={mockOnUploaded}
      />,
    )

    expect(screen.getByText('Drop PDF here or click to select')).not.toBeNull()
    expect(screen.getByText('Max 5 MB, 40 pages, 3 per conversation')).not.toBeNull()
    expect(screen.getByRole('button', { name: 'Choose PDF' })).not.toBeNull()
  })

  it('rejects non-PDF files without calling API', async () => {
    render(
      <UploadButton
        conversationId="conv-1"
        anonId="anon-1"
        onUploaded={mockOnUploaded}
      />,
    )

    const file = new File(['not a pdf'], 'test.txt', { type: 'text/plain' })
    const input = screen.getByRole('button', { name: 'Choose PDF' }).closest('div')?.querySelector('input')

    if (input) {
      fireEvent.change(input, { target: { files: [file] } })

      await waitFor(() => {
        expect(screen.getByText('File must be a PDF')).not.toBeNull()
      })
    }

    expect(mockOnUploaded).not.toHaveBeenCalled()
  })

  it('rejects files larger than 5 MB without calling API', async () => {
    render(
      <UploadButton
        conversationId="conv-1"
        anonId="anon-1"
        onUploaded={mockOnUploaded}
      />,
    )

    // Create a file larger than 5MB
    const largeContent = new Uint8Array(6 * 1024 * 1024)
    const file = new File([largeContent], 'large.pdf', { type: 'application/pdf' })
    const input = screen.getByRole('button', { name: 'Choose PDF' }).closest('div')?.querySelector('input')

    if (input) {
      fireEvent.change(input, { target: { files: [file] } })

      await waitFor(() => {
        expect(screen.getByText('File exceeds 5 MB limit')).not.toBeNull()
      })
    }

    expect(mockOnUploaded).not.toHaveBeenCalled()
  })

  it('renders document pill with filename and page count', () => {
    render(
      <DocumentPill
        doc={{
          id: 'doc-1',
          filename: 'report.pdf',
          page_count: 10,
          status: 'ready',
        }}
        conversationId="conv-1"
        anonId="anon-1"
        onDeleted={mockOnDeleted}
      />,
    )

    expect(screen.getByText('report.pdf')).not.toBeNull()
    expect(screen.getByText('10 pp')).not.toBeNull()
    expect(screen.getByRole('button', { name: 'Delete report.pdf' })).not.toBeNull()
  })

  it('shows failed status styling for failed documents', () => {
    render(
      <DocumentPill
        doc={{
          id: 'doc-2',
          filename: 'bad.pdf',
          page_count: 0,
          status: 'failed',
        }}
        conversationId="conv-1"
        anonId="anon-1"
        onDeleted={mockOnDeleted}
      />,
    )

    const pill = screen.getByText('bad.pdf').closest('div')
    expect(pill?.className).toContain('border-red-600/30')
    expect(pill?.className).toContain('text-red-400')
  })

  it('calls onDeleted when delete button is clicked', async () => {
    render(
      <DocumentPill
        doc={{
          id: 'doc-1',
          filename: 'report.pdf',
          page_count: 10,
          status: 'ready',
        }}
        conversationId="conv-1"
        anonId="anon-1"
        onDeleted={mockOnDeleted}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Delete report.pdf' }))

    await waitFor(() => {
      expect(mockOnDeleted).toHaveBeenCalledWith('doc-1')
    })
  })
})