import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { PlanAttachment } from '../api/generate'
import { PlansUploader } from '../components/PlansUploader'

const TINY_PNG_DATA_URL =
  'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgAAIAAAUAAarVyFEAAAAASUVORK5CYII='

function makePng(name = 'plan.png'): File {
  return new File(['fake'], name, { type: 'image/png' })
}

function makeOther(name = 'doc.pdf'): File {
  return new File(['fake'], name, { type: 'application/pdf' })
}

beforeEach(() => {
  vi.spyOn(FileReader.prototype, 'readAsDataURL').mockImplementation(function (
    this: FileReader,
  ) {
    Object.defineProperty(this, 'result', { value: TINY_PNG_DATA_URL })
    const event = new ProgressEvent('load') as ProgressEvent<FileReader>
    setTimeout(() => this.onload?.(event), 0)
  })
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('PlansUploader', () => {
  it('renders the counter and "add" button when no plans yet', () => {
    render(<PlansUploader plans={[]} onChange={() => undefined} />)
    expect(screen.getByText('0 / 5')).toBeInTheDocument()
    expect(screen.getByTestId('plans-add')).toBeEnabled()
  })

  it('reads picked files as data URLs and calls onChange', async () => {
    const onChange = vi.fn()
    render(<PlansUploader plans={[]} onChange={onChange} />)

    fireEvent.change(screen.getByTestId('plans-input'), {
      target: { files: [makePng('a.png'), makePng('b.png')] },
    })

    await waitFor(() => expect(onChange).toHaveBeenCalled())
    const next = onChange.mock.calls.at(-1)![0] as PlanAttachment[]
    expect(next.map((p) => p.name)).toEqual(['a.png', 'b.png'])
    expect(next[0].dataUrl).toBe(TINY_PNG_DATA_URL)
  })

  it('rejects non-image files silently', async () => {
    const onChange = vi.fn()
    render(<PlansUploader plans={[]} onChange={onChange} />)

    fireEvent.change(screen.getByTestId('plans-input'), {
      target: { files: [makeOther()] },
    })

    await Promise.resolve()
    expect(onChange).not.toHaveBeenCalled()
  })

  it('respects the max limit and disables the button once reached', () => {
    const plans: PlanAttachment[] = Array.from({ length: 5 }, (_, i) => ({
      name: `p${i}.png`,
      dataUrl: TINY_PNG_DATA_URL,
    }))
    render(<PlansUploader plans={plans} onChange={() => undefined} max={5} />)
    expect(screen.getByText('5 / 5')).toBeInTheDocument()
    expect(screen.getByTestId('plans-add')).toBeDisabled()
  })

  it('removes a plan when its "Retirer" button is clicked', () => {
    const onChange = vi.fn()
    const plans: PlanAttachment[] = [
      { name: 'a.png', dataUrl: TINY_PNG_DATA_URL },
      { name: 'b.png', dataUrl: TINY_PNG_DATA_URL },
    ]
    render(<PlansUploader plans={plans} onChange={onChange} />)

    fireEvent.click(screen.getByTestId('plans-remove-0'))
    expect(onChange).toHaveBeenCalledWith([
      { name: 'b.png', dataUrl: TINY_PNG_DATA_URL },
    ])
  })
})
