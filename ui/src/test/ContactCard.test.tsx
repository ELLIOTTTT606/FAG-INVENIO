import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ContactCard } from '../components/ContactCard'

describe('ContactCard', () => {
  it('renders the role, name, email and phone when provided', () => {
    render(
      <ContactCard
        role="TCI"
        contact={{ name: 'Léa Martin', email: 'l@x.com', phone: '04 91 10 20 30' }}
      />,
    )
    expect(screen.getByRole('heading', { name: /TCI/ })).toBeInTheDocument()
    expect(screen.getByText('Léa Martin')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'l@x.com' })).toHaveAttribute(
      'href',
      'mailto:l@x.com',
    )
    expect(screen.getByRole('link', { name: '04 91 10 20 30' })).toHaveAttribute(
      'href',
      'tel:0491102030',
    )
    expect(screen.getByText('disponible')).toBeInTheDocument()
  })

  it('shows the empty state when contact is null', () => {
    render(<ContactCard role="TCS" contact={null} />)
    expect(screen.getByText(/aucun contact dédié/i)).toBeInTheDocument()
    expect(screen.getByText('non assigné')).toBeInTheDocument()
  })
})
