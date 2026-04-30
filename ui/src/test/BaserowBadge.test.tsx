import { render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { BaserowBadge } from '../components/BaserowBadge'

describe('BaserowBadge', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows mock by default before the request resolves', () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => new Promise(() => undefined)),
    )
    render(<BaserowBadge />)
    expect(screen.getByTestId('baserow-badge')).toHaveAttribute('data-mode', 'mock')
  })

  it('switches to live when the API reports a configured Baserow', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          mode: 'live',
          url: 'https://baserow.example',
          tables: { clients: 1 },
        }),
        { status: 200 },
      ),
    )
    vi.stubGlobal('fetch', fetchMock)
    render(<BaserowBadge />)
    await waitFor(() =>
      expect(screen.getByTestId('baserow-badge')).toHaveAttribute('data-mode', 'live'),
    )
    expect(screen.getByText(/baserow live/i)).toBeInTheDocument()
  })

  it('falls back to mock when the API returns an error', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response('boom', { status: 500 }))
    vi.stubGlobal('fetch', fetchMock)
    render(<BaserowBadge />)
    await waitFor(() => expect(fetchMock).toHaveBeenCalled())
    expect(screen.getByTestId('baserow-badge')).toHaveAttribute('data-mode', 'mock')
  })
})
