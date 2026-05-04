import { render, screen, fireEvent } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { Dropzone } from '../components/Dropzone'

describe('Dropzone', () => {
  it('forwards the dropped file to onFile', () => {
    const onFile = vi.fn()
    render(<Dropzone onFile={onFile} />)

    const dropzone = screen.getByRole('button', { name: /déposer une fiche/i })
    const file = new File(['content'], 'fiche.docx', { type: 'application/octet-stream' })
    const dataTransfer = { files: [file] } as unknown as DataTransfer

    fireEvent.drop(dropzone, { dataTransfer })
    expect(onFile).toHaveBeenCalledWith(file)
  })

  it('forwards the picked file from the hidden input', () => {
    const onFile = vi.fn()
    render(<Dropzone onFile={onFile} />)
    const input = screen.getByTestId('dropzone-input') as HTMLInputElement
    const file = new File(['x'], 'fiche.pdf', { type: 'application/pdf' })

    fireEvent.change(input, { target: { files: [file] } })
    expect(onFile).toHaveBeenCalledWith(file)
  })

  it('does not forward when disabled', () => {
    const onFile = vi.fn()
    render(<Dropzone disabled onFile={onFile} />)

    const dropzone = screen.getByRole('button', { name: /déposer une fiche/i })
    const file = new File(['x'], 'fiche.docx')
    fireEvent.drop(dropzone, { dataTransfer: { files: [file] } as unknown as DataTransfer })

    expect(onFile).not.toHaveBeenCalled()
  })
})
