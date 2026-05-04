import { useCallback, useRef, useState, type DragEvent, type ChangeEvent } from 'react'

interface DropzoneProps {
  accept?: string
  disabled?: boolean
  onFile: (file: File) => void
}

export function Dropzone({ accept = '.docx,.pdf', disabled = false, onFile }: DropzoneProps) {
  const [isDragging, setDragging] = useState(false)
  const inputRef = useRef<HTMLInputElement | null>(null)

  const pickFile = useCallback(
    (file: File | null | undefined) => {
      if (file) onFile(file)
    },
    [onFile],
  )

  const onDrop = useCallback(
    (event: DragEvent<HTMLDivElement>) => {
      event.preventDefault()
      setDragging(false)
      if (disabled) return
      pickFile(event.dataTransfer?.files?.[0])
    },
    [disabled, pickFile],
  )

  const onChange = useCallback(
    (event: ChangeEvent<HTMLInputElement>) => {
      pickFile(event.target.files?.[0])
      event.target.value = ''
    },
    [pickFile],
  )

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label="Déposer une fiche GALLETTI"
      aria-disabled={disabled}
      onDragOver={(event) => {
        event.preventDefault()
        if (!disabled) setDragging(true)
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
      onClick={() => !disabled && inputRef.current?.click()}
      onKeyDown={(event) => {
        if ((event.key === 'Enter' || event.key === ' ') && !disabled) {
          event.preventDefault()
          inputRef.current?.click()
        }
      }}
      className={[
        'flex min-h-[220px] cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed p-10 text-center transition-all duration-300 ease-smooth',
        isDragging
          ? 'border-accent bg-accent-subtle/40'
          : 'border-ink-muted/30 hover:border-accent hover:bg-accent-subtle/20',
        disabled ? 'pointer-events-none opacity-50' : '',
      ].join(' ')}
    >
      <p className="text-lg font-medium">Glissez-déposez votre fiche GALLETTI</p>
      <p className="mt-2 text-sm text-ink-muted">
        ou cliquez pour parcourir · formats acceptés : .docx, .pdf
      </p>
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        onChange={onChange}
        data-testid="dropzone-input"
      />
    </div>
  )
}
