import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Client } from '../api/contacts'
import { NewClientModal } from '../components/NewClientModal'

describe('NewClientModal', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('does not render when closed', () => {
    render(<NewClientModal open={false} onClose={vi.fn()} onSaved={vi.fn()} />)
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('auto-derives the department from the postal code', () => {
    render(<NewClientModal open onClose={vi.fn()} onSaved={vi.fn()} />)
    const department = screen.getByLabelText(/département/i) as HTMLInputElement
    expect(department.value).toBe('')

    fireEvent.change(screen.getByLabelText(/code postal/i), {
      target: { value: '69001' },
    })
    expect(department.value).toBe('69')

    fireEvent.change(screen.getByLabelText(/code postal/i), {
      target: { value: '20100' },
    })
    expect(department.value).toBe('2A')
  })

  it('lets the user override the auto-derived department', () => {
    render(<NewClientModal open onClose={vi.fn()} onSaved={vi.fn()} />)
    fireEvent.change(screen.getByLabelText(/code postal/i), {
      target: { value: '69001' },
    })
    const department = screen.getByLabelText(/département/i) as HTMLInputElement
    fireEvent.change(department, { target: { value: '01' } })
    expect(department.value).toBe('01')

    // Subsequent postal-code changes do not overwrite the user's choice.
    fireEvent.change(screen.getByLabelText(/code postal/i), {
      target: { value: '75015' },
    })
    expect(department.value).toBe('01')
  })

  it('POSTs the form, calls onSaved and onClose on success', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          id: 7,
          client_code: 'C-NEW',
          client_name: 'Acme',
          postal_code: '75015',
          department: '75',
        }),
        { status: 201 },
      ),
    )
    vi.stubGlobal('fetch', fetchMock)

    const onSaved = vi.fn()
    const onClose = vi.fn()
    render(<NewClientModal open onClose={onClose} onSaved={onSaved} />)

    fireEvent.change(screen.getByLabelText(/code client/i), { target: { value: 'c-new' } })
    fireEvent.change(screen.getByLabelText(/nom du client/i), { target: { value: 'Acme' } })
    fireEvent.change(screen.getByLabelText(/code postal/i), { target: { value: '75015' } })

    fireEvent.click(screen.getByRole('button', { name: /créer le client/i }))

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1))
    const [url, init] = fetchMock.mock.calls[0]
    expect(String(url)).toContain('/clients')
    expect((init as RequestInit).method).toBe('POST')
    const body = JSON.parse((init as RequestInit).body as string)
    expect(body).toEqual({
      client_code: 'c-new',
      client_name: 'Acme',
      postal_code: '75015',
      department: '75',
    })

    await waitFor(() => expect(onSaved).toHaveBeenCalled())
    expect(onClose).toHaveBeenCalled()
    expect(onSaved.mock.calls[0][0].client_code).toBe('C-NEW')
  })

  it('pre-fills the form when initial is provided and PATCHes on save', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          id: 42,
          client_code: 'C-EDIT',
          client_name: 'Renamed',
          postal_code: '69001',
          department: '69',
        }),
        { status: 200 },
      ),
    )
    vi.stubGlobal('fetch', fetchMock)

    const initial: Client = {
      id: 42,
      client_code: 'C-EDIT',
      client_name: 'Original',
      postal_code: '69001',
      department: '69',
    }
    const onSaved = vi.fn()
    const onClose = vi.fn()
    render(
      <NewClientModal
        open
        onClose={onClose}
        onSaved={onSaved}
        initial={initial}
      />,
    )

    expect(screen.getByRole('heading', { name: /modifier original/i })).toBeInTheDocument()
    expect(screen.getByLabelText(/code client/i)).toHaveValue('C-EDIT')
    expect(screen.getByLabelText(/nom du client/i)).toHaveValue('Original')

    fireEvent.change(screen.getByLabelText(/nom du client/i), { target: { value: 'Renamed' } })
    fireEvent.click(screen.getByRole('button', { name: /enregistrer/i }))

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1))
    const [url, init] = fetchMock.mock.calls[0]
    expect(String(url)).toBe('/clients/42')
    expect((init as RequestInit).method).toBe('PATCH')
    expect(JSON.parse((init as RequestInit).body as string)).toEqual({
      client_code: 'C-EDIT',
      client_name: 'Renamed',
      postal_code: '69001',
      department: '69',
    })

    await waitFor(() => expect(onSaved).toHaveBeenCalled())
    expect(onSaved.mock.calls[0][0].client_name).toBe('Renamed')
    expect(onClose).toHaveBeenCalled()
  })

  it('surfaces 404 from PATCH without closing the dialog', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response('gone', { status: 404 }))
    vi.stubGlobal('fetch', fetchMock)

    const onClose = vi.fn()
    render(
      <NewClientModal
        open
        onClose={onClose}
        onSaved={vi.fn()}
        initial={{
          id: 1,
          client_code: 'C-X',
          client_name: 'X',
          postal_code: '75015',
          department: '75',
        }}
      />,
    )
    fireEvent.click(screen.getByRole('button', { name: /enregistrer/i }))
    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument())
    expect(onClose).not.toHaveBeenCalled()
  })

  it('shows the API error message and does not close on 409', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response('exists', { status: 409 }))
    vi.stubGlobal('fetch', fetchMock)
    const onClose = vi.fn()
    render(<NewClientModal open onClose={onClose} onSaved={vi.fn()} />)

    fireEvent.change(screen.getByLabelText(/code client/i), { target: { value: 'c-dup' } })
    fireEvent.change(screen.getByLabelText(/nom du client/i), { target: { value: 'X' } })
    fireEvent.change(screen.getByLabelText(/code postal/i), { target: { value: '75015' } })
    fireEvent.click(screen.getByRole('button', { name: /créer le client/i }))

    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument())
    expect(onClose).not.toHaveBeenCalled()
  })

  it('disables the submit button while the form is invalid', () => {
    render(<NewClientModal open onClose={vi.fn()} onSaved={vi.fn()} />)
    const submit = screen.getByRole('button', { name: /créer le client/i })
    expect(submit).toBeDisabled()

    fireEvent.change(screen.getByLabelText(/code client/i), { target: { value: 'c1' } })
    fireEvent.change(screen.getByLabelText(/nom du client/i), { target: { value: 'X' } })
    fireEvent.change(screen.getByLabelText(/code postal/i), { target: { value: '7501' } })
    expect(submit).toBeDisabled()

    fireEvent.change(screen.getByLabelText(/code postal/i), { target: { value: '75015' } })
    expect(submit).not.toBeDisabled()
  })
})
