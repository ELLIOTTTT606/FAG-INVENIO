import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import Generate from '../pages/Generate'
import { rememberContacts, rememberImport, rememberSelectedOptions } from '../lib/sessionContext'
import { pacRecord } from './fixtures'

const PREVIEW_HTML = '<html><body><h1>Preview content</h1></body></html>'
const PDF_BYTES = new Uint8Array([0x25, 0x50, 0x44, 0x46]) // "%PDF"

function renderPage() {
  return render(
    <MemoryRouter>
      <Generate />
    </MemoryRouter>,
  )
}

describe('Generate page', () => {
  beforeEach(() => {
    sessionStorage.clear()
  })

  afterEach(() => {
    sessionStorage.clear()
    vi.unstubAllGlobals()
  })

  it('shows an empty state when no import context is in sessionStorage', () => {
    renderPage()
    expect(screen.getByText(/aucune fiche en cours/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /aller à l'import/i })).toHaveAttribute(
      'href',
      '/import',
    )
  })

  it('renders the preview iframe and download button when context is ready', async () => {
    rememberImport(pacRecord)
    rememberSelectedOptions(['P'])
    rememberContacts({ department: '69', tci: null, tcs: null, solution: null })

    const fetchMock = vi.fn().mockResolvedValue(
      new Response(PREVIEW_HTML, {
        status: 200,
        headers: { 'Content-Type': 'text/html' },
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    renderPage()

    expect(screen.getByText(/PLP 052 HS/)).toBeInTheDocument()
    expect(screen.getByText(/1 option\(s\) retenues/)).toBeInTheDocument()
    expect(screen.getByText(/département 69/i)).toBeInTheDocument()

    const frame = await waitFor(() => screen.getByTestId('preview-frame'))
    expect(frame).toHaveAttribute('srcDoc', PREVIEW_HTML)

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(String(fetchMock.mock.calls[0][0])).toContain('/generate/preview')
  })

  it('triggers a PDF download when the user clicks the button', async () => {
    rememberImport(pacRecord)
    rememberSelectedOptions(['P'])

    const fetchMock = vi
      .fn()
      // 1st call: preview
      .mockResolvedValueOnce(new Response(PREVIEW_HTML, { status: 200 }))
      // 2nd call: PDF blob
      .mockResolvedValueOnce(
        new Response(PDF_BYTES, {
          status: 200,
          headers: { 'Content-Type': 'application/pdf' },
        }),
      )
    vi.stubGlobal('fetch', fetchMock)
    const createObjectURL = vi.fn().mockReturnValue('blob:mock')
    const revokeObjectURL = vi.fn()
    vi.stubGlobal('URL', { ...URL, createObjectURL, revokeObjectURL })

    renderPage()

    await waitFor(() => screen.getByTestId('preview-frame'))
    const button = screen.getByTestId('download-pdf')
    fireEvent.click(button)

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
    expect(String(fetchMock.mock.calls[1][0])).toContain('/generate/pdf')
    expect(createObjectURL).toHaveBeenCalledTimes(1)
    expect(revokeObjectURL).toHaveBeenCalledTimes(1)
  })

  it('shows a 503 message when the PDF engine is unavailable', async () => {
    rememberImport(pacRecord)

    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(PREVIEW_HTML, { status: 200 }))
      .mockResolvedValueOnce(new Response('engine missing', { status: 503 }))
    vi.stubGlobal('fetch', fetchMock)

    renderPage()
    await waitFor(() => screen.getByTestId('preview-frame'))
    fireEvent.click(screen.getByTestId('download-pdf'))

    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent(/WeasyPrint/i),
    )
  })
})
