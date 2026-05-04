import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import Home from '../pages/Home'

describe('Home', () => {
  it('renders the headline and CTA pointing to /import', () => {
    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>,
    )

    expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument()
    const cta = screen.getByRole('link', { name: /générer ma fiche/i })
    expect(cta).toHaveAttribute('href', '/import')
  })
})
