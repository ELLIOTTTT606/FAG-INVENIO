import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from '../App'

function renderApp(initialPath = '/') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <App />
    </MemoryRouter>,
  )
}

function stubMotionPreference(reduced: boolean) {
  vi.stubGlobal(
    'matchMedia',
    vi.fn((query: string) => ({
      matches: reduced,
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    })),
  )
}

describe('App shell', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => new Promise(() => undefined)),
    )
    vi.stubGlobal('scrollTo', vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('marks the link of the current route as active', async () => {
    renderApp('/import')
    expect(await screen.findByRole('heading', { level: 1, name: /déposez votre fiche/i })).toBeVisible()
    expect(screen.getByRole('link', { name: 'Importer une fiche' })).toHaveAttribute(
      'aria-current',
      'page',
    )
    expect(screen.getByRole('link', { name: 'Accueil' })).not.toHaveAttribute('aria-current')
  })

  it('swaps pages immediately when reduced motion is requested', async () => {
    stubMotionPreference(true)
    renderApp('/')
    await screen.findByRole('heading', { level: 1, name: /générez vos fiches/i })

    await userEvent.click(screen.getByRole('link', { name: 'Importer une fiche' }))

    expect(await screen.findByRole('heading', { level: 1, name: /déposez votre fiche/i })).toBeVisible()
    expect(document.querySelector('.page-exit')).toBeNull()
  })

  it('fades the outgoing page out before showing the next one', async () => {
    stubMotionPreference(false)
    renderApp('/')
    const home = await screen.findByRole('heading', { level: 1, name: /générez vos fiches/i })

    await userEvent.click(screen.getByRole('link', { name: 'Importer une fiche' }))

    // The old page is still mounted, now playing its exit animation.
    expect(home).toBeInTheDocument()
    expect(home.closest('.page-exit')).not.toBeNull()

    const next = await screen.findByRole('heading', { level: 1, name: /déposez votre fiche/i })
    expect(next.closest('.page-enter')).not.toBeNull()
    await waitFor(() => expect(home).not.toBeInTheDocument())
    expect(window.scrollTo).toHaveBeenCalledWith({ top: 0 })
  })

  it('shows the bare loading indicator on /loader', async () => {
    renderApp('/loader')
    expect(await screen.findByRole('status', { name: 'Chargement' })).toBeInTheDocument()
  })
})
