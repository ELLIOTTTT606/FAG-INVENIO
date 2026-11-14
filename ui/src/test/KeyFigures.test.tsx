import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { KeyFigures } from '../components/KeyFigures'
import { pacRecord } from './fixtures'

describe('KeyFigures', () => {
  it('shows the headline numbers of a PAC in French notation', () => {
    render(<KeyFigures record={pacRecord} />)
    const list = screen.getByTestId('key-figures')
    expect(within(list).getAllByRole('listitem')).toHaveLength(4)
    expect(within(list).getByText('Puissance frigorifique').parentElement).toHaveTextContent(
      /41,7\s*kW/,
    )
    expect(within(list).getByText('COP')).toBeInTheDocument()
  })

  it('shows EER instead of COP and drops heating power for a GEG', () => {
    const geg = {
      ...pacRecord,
      family: 'GEG' as const,
      performance: { cooling: pacRecord.performance.cooling },
    }
    render(<KeyFigures record={geg} />)
    const list = screen.getByTestId('key-figures')
    expect(within(list).getByText('EER')).toBeInTheDocument()
    expect(within(list).queryByText('COP')).toBeNull()
    expect(within(list).queryByText('Puissance calorifique')).toBeNull()
  })

  it('renders nothing when no figure was extracted', () => {
    const empty = { ...pacRecord, performance: {}, general: {} }
    const { container } = render(<KeyFigures record={empty} />)
    expect(container).toBeEmptyDOMElement()
  })
})
