import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ClientSearch } from '../components/ClientSearch'

describe('ClientSearch', () => {
  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  it('does not call fetch under 2 characters', () => {
    vi.useFakeTimers()
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)

    render(<ClientSearch onSelect={() => undefined} />)
    fireEvent.change(screen.getByLabelText(/rechercher un client/i), {
      target: { value: 'l' },
    })
    vi.advanceTimersByTime(1000)
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('debounces and fires one request after typing >=2 chars', () => {
    vi.useFakeTimers()
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify([]), { status: 200 }),
    )
    vi.stubGlobal('fetch', fetchMock)

    render(<ClientSearch onSelect={() => undefined} />)
    const input = screen.getByLabelText(/rechercher un client/i)
    fireEvent.change(input, { target: { value: 'ly' } })
    vi.advanceTimersByTime(100)
    expect(fetchMock).not.toHaveBeenCalled()
    vi.advanceTimersByTime(300)
    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(String(fetchMock.mock.calls[0][0])).toContain('q=ly')
  })

  it('renders results and forwards the selected client', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify([
          {
            client_code: 'C1',
            client_name: 'Acme Lyon',
            postal_code: '69001',
            department: '69',
          },
        ]),
        { status: 200 },
      ),
    )
    vi.stubGlobal('fetch', fetchMock)

    const onSelect = vi.fn()
    render(<ClientSearch onSelect={onSelect} />)
    fireEvent.change(screen.getByLabelText(/rechercher un client/i), {
      target: { value: 'lyon' },
    })
    await waitFor(() => expect(screen.getByText('Acme Lyon')).toBeInTheDocument())
    fireEvent.click(screen.getByText('Acme Lyon'))
    expect(onSelect).toHaveBeenCalledWith({
      client_code: 'C1',
      client_name: 'Acme Lyon',
      postal_code: '69001',
      department: '69',
    })
  })

  it('shows an error message when the request fails', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response('boom', { status: 500 }))
    vi.stubGlobal('fetch', fetchMock)

    render(<ClientSearch onSelect={() => undefined} />)
    fireEvent.change(screen.getByLabelText(/rechercher un client/i), {
      target: { value: 'lyon' },
    })
    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument())
  })
})
