/** PDF upload button with drag-and-drop and progress indicator. */
import { useCallback, useRef, useState } from 'react'
import { uploadDocument } from '../api/client'

type Status = 'idle' | 'uploading' | 'success' | 'error'

export interface UploadButtonProps {
  conversationId: string
  anonId: string
  onUploaded: (doc: { id: string; filename: string; page_count: number }) => void
}

export function UploadButton({ conversationId, anonId, onUploaded }: UploadButtonProps) {
  const [status, setStatus] = useState<Status>('idle')
  const [error, setError] = useState<string | null>(null)
  const [progress, setProgress] = useState(0)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileSelect = useCallback(
    async (file: File) => {
      if (file.type !== 'application/pdf') {
        setError('File must be a PDF')
        setStatus('error')
        return
      }
      if (file.size > 5 * 1024 * 1024) {
        setError('File exceeds 5 MB limit')
        setStatus('error')
        return
      }

      setStatus('uploading')
      setError(null)
      setProgress(0)

      try {
        // Simulate progress since fetch doesn't support upload progress natively
        const progressInterval = setInterval(() => {
          setProgress((p) => Math.min(p + 10, 90))
        }, 100)

        const doc = await uploadDocument(conversationId, anonId, file)

        clearInterval(progressInterval)
        setProgress(100)
        setStatus('success')
        onUploaded({ id: doc.id, filename: doc.filename, page_count: doc.page_count })

        // Reset after short delay
        setTimeout(() => {
          setStatus('idle')
          setProgress(0)
        }, 1500)
      } catch (err) {
        setStatus('error')
        setError(err instanceof Error ? err.message : 'Upload failed')
        setProgress(0)
      }
    },
    [conversationId, anonId, onUploaded],
  )

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      const file = e.dataTransfer.files[0]
      if (file) handleFileSelect(file)
    },
    [handleFileSelect],
  )

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
  }, [])

  const triggerFileSelect = () => fileInputRef.current?.click()

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) handleFileSelect(file)
  }

  return (
    <div
      className="border-2 border-dashed border-neutral-700 rounded-lg p-4 text-center transition-colors hover:border-emerald-600"
      onDrop={handleDrop}
      onDragOver={handleDragOver}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf"
        className="hidden"
        onChange={handleInputChange}
      />

      {status === 'uploading' ? (
        <div className="space-y-2">
          <div className="w-full h-2 bg-neutral-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-emerald-600 transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="text-xs text-neutral-400">Uploading… {progress}%</p>
        </div>
      ) : status === 'success' ? (
        <p className="text-sm text-emerald-400">✓ Uploaded</p>
      ) : status === 'error' ? (
        <p className="text-sm text-red-400" role="alert">
          {error}
        </p>
      ) : (
        <>
          <p className="text-sm text-neutral-300">Drop PDF here or click to select</p>
          <p className="text-xs text-neutral-500 mt-1">
            Max 5 MB, 40 pages, 3 per conversation
          </p>
        </>
      )}

      <button
        type="button"
        onClick={triggerFileSelect}
        disabled={status === 'uploading'}
        className="mt-3 w-full rounded border border-neutral-700 bg-neutral-800 px-3 py-1.5 text-sm text-neutral-100 hover:bg-neutral-700 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {status === 'uploading' ? 'Uploading…' : 'Choose PDF'}
      </button>
    </div>
  )
}