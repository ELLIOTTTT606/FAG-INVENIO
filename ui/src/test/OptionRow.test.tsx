import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { CatalogOption } from '../api/options'
import { OptionRow } from '../components/OptionRow'

const baseOption: CatalogOption = {
  code: 'P',
  category: 'Kit antigel',
  label: 'Protection echangeur + pompe',
  description: 'Resistance electrique + traceur thermique.',
  tips: 'Recommande en climat froid.',
  price_eur: 199.0,
  available: true,
}

describe('OptionRow', () => {
  it('renders the label, code, and toggles selection on checkbox change', () => {
    const onToggle = vi.fn()
    render(<OptionRow option={baseOption} selected={false} onToggle={onToggle} />)

    expect(screen.getByText(baseOption.label)).toBeInTheDocument()
    expect(screen.getByText('P')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('checkbox'))
    expect(onToggle).toHaveBeenCalledWith('P')
  })

  it('hides description and tips behind a "voir les détails" toggle', () => {
    render(<OptionRow option={baseOption} selected onToggle={() => undefined} />)
    expect(screen.queryByText(baseOption.description!)).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /voir les détails/i }))
    expect(screen.getByText(baseOption.description!)).toBeInTheDocument()
    expect(screen.getByText(/Recommande en climat froid/)).toBeInTheDocument()
    expect(screen.getByText(/199\.00/)).toBeInTheDocument()
  })

  it('disables the checkbox and shows "indisponible" when option.available is false', () => {
    render(
      <OptionRow
        option={{ ...baseOption, available: false }}
        selected={false}
        onToggle={() => undefined}
      />,
    )
    expect(screen.getByRole('checkbox')).toBeDisabled()
    expect(screen.getByText(/indisponible/i)).toBeInTheDocument()
  })
})
