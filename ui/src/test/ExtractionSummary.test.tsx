import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ExtractionSummary } from '../components/ExtractionSummary'
import { pacRecord } from './fixtures'

describe('ExtractionSummary', () => {
  it('renders the family, model, size and designation header for a PAC', () => {
    render(<ExtractionSummary record={pacRecord} warnings={[]} />)

    expect(screen.getByText('PAC')).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 2 })).toHaveTextContent('PLP')
    expect(screen.getByText(pacRecord.designation_code!)).toBeInTheDocument()
  })

  it('shows extracted cooling values with the unit', () => {
    render(<ExtractionSummary record={pacRecord} warnings={[]} />)
    expect(screen.getByText('41.7 kW')).toBeInTheDocument()
    expect(screen.getByText('7155 l/h')).toBeInTheDocument()
  })

  it('shows the heating card for a PAC and SCOP value', () => {
    render(<ExtractionSummary record={pacRecord} warnings={[]} />)
    expect(screen.getByText(/Classe saisonnière/i)).toBeInTheDocument()
    expect(screen.getByText('A++')).toBeInTheDocument()
  })

  it('replaces the heating card by a "non applicable" message for a GEG', () => {
    const geg = {
      ...pacRecord,
      family: 'GEG' as const,
      type: 'CS',
      performance: { ...pacRecord.performance, heating: undefined },
    }
    render(<ExtractionSummary record={geg} warnings={[]} />)
    expect(screen.getByText(/non applicable/i)).toBeInTheDocument()
  })

  it('renders an alert when warnings are returned', () => {
    render(
      <ExtractionSummary
        record={pacRecord}
        warnings={[{ code: 'designation_decoder_missing', field: 'options', message: 'Set me up' }]}
      />,
    )
    expect(screen.getByRole('alert')).toHaveTextContent('1 avertissement')
  })

  it('shows missing fields with a placeholder text', () => {
    const incomplete = { ...pacRecord, performance: { cooling: {}, heating: {} } }
    render(<ExtractionSummary record={incomplete} warnings={[]} />)
    expect(screen.getAllByText(/Donnée non disponible/).length).toBeGreaterThan(0)
  })
})
