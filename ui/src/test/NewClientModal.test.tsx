import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { NewClientModal } from '../components/NewClientModal'

describe('NewClientModal', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('does not render when closed', () => {
    render(<NewClientModal open={false} onClose={vi.fn()} onCreated={vi.fn()} />)
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('auto-derives the department from the postal code', () => {
    render(<NewClientModal open onClose={vi.fn()} onCreated={vi.fn()} />)
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
    render(<NewClientModal open onClose={vi.fn()} onCreated={vi.fn()} />)
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

  it('POSTs the form, calls onCreated and onClose on success', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          client_code: 'C-NEW',
          client_name: 'Acme',
          postal_code: '75015',
          department: '75',
        }),
        { status: 201 },
      ),
    )
    vi.stubGlobal('fetch', fetchMock)

    const onCreated = vi.fn()
    const onClose = vi.fn()
    render(<NewClientModal open onClose={onClose} onCreated={onCreated} />)

    fireEvent.change(screen.getByLabelText(/code client/i), { target: { value: 'c-new' } })
    fireEvent.change(screen.getByLabelText(/nom du client/i), { target: { value: 'Acme' } })
    fireEvent.change(screen.getByLabelText(/code postal/i), { target: { value: '75015' } })

    fireEvent.click(screen.getByRole('button', { name: /créer le client/i }))

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1))
    expect(String(fetchMock.mock.calls[0][0])).toContain('/clients')
    const body = JSON.parse((fetchMock.mock.calls[0][1] as RequestInit).body as string)
    expect(body).toEqual({
      client_code: 'c-new',
      client_name: 'Acme',
      postal_code: '75015',
      department: '75',
    })

    await waitFor(() => expect(onCreated).toHaveBeenCalled())
    expect(onClose).toHaveBeenCalled()
    expect(onCreated.mock.calls[0][0].client_code).toBe('C-NEW')
  })

  it('shows the API error message and does not close on 409', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response('exists', { status: 409 }))
    vi.stubGlobal('fetch', fetchMock)
    const onClose = vi.fn()
    render(<NewClientModal open onClose={onClose} onCreated={vi.fn()} />)

    fireEvent.change(screen.getByLabelText(/code client/i), { target: { value: 'c-dup' } })
    fireEvent.change(screen.getByLabelText(/nom du client/i), { target: { value: 'X' } })
    fireEvent.change(screen.getByLabelText(/code postal/i), { target: { value: '75015' } })
    fireEvent.click(screen.getByRole('button', { name: /créer le client/i }))

    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument())
    expect(onClose).not.toHaveBeenCalled()
  })

  it('disables the submit button while the form is invalid', () => {
    render(<NewClientModal open onClose={vi.fn()} onCreated={vi.fn()} />)
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
