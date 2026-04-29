import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { CatalogOption } from '../api/options'
import { OptionsAccordion } from '../components/OptionsAccordion'

const options: CatalogOption[] = [
  {
    code: '0',
    category: 'Pompe',
    label: 'Absente',
    description: null,
    tips: null,
    price_eur: null,
    available: true,
  },
  {
    code: '1',
    category: 'Pompe',
    label: 'Pompe simple',
    description: 'desc',
    tips: null,
    price_eur: null,
    available: true,
  },
]

describe('OptionsAccordion', () => {
  it('shows option count when no option is selected', () => {
    render(
      <OptionsAccordion
        category="Pompe"
        options={options}
        selected={new Set()}
        onToggle={() => undefined}
      />,
    )
    expect(screen.getByText(/2 options/i)).toBeInTheDocument()
  })

  it('shows the selected counter when at least one option is checked', () => {
    render(
      <OptionsAccordion
        category="Pompe"
        options={options}
        selected={new Set(['1'])}
        onToggle={() => undefined}
      />,
    )
    expect(screen.getByText(/1 sélectionnée/i)).toBeInTheDocument()
  })

  it('toggles the body open/closed via the header button', () => {
    render(
      <OptionsAccordion
        category="Pompe"
        options={options}
        selected={new Set()}
        onToggle={() => undefined}
      />,
    )
    const header = screen.getByRole('button', { name: /Pompe/ })
    expect(header).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByText('Pompe simple')).toBeInTheDocument()

    fireEvent.click(header)
    expect(header).toHaveAttribute('aria-expanded', 'false')
    expect(screen.queryByText('Pompe simple')).not.toBeInTheDocument()
  })

  it('forwards onToggle from a child OptionRow', () => {
    const onToggle = vi.fn()
    render(
      <OptionsAccordion
        category="Pompe"
        options={options}
        selected={new Set()}
        onToggle={onToggle}
      />,
    )
    fireEvent.click(screen.getAllByRole('checkbox')[1])
    expect(onToggle).toHaveBeenCalledWith('1')
  })
})
