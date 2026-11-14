import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { GlobeLoader } from '../components/GlobeLoader'
import { LoaderStage } from '../components/LoaderStage'

describe('GlobeLoader', () => {
  it('exposes a status with an accessible name and no visible text', () => {
    render(<GlobeLoader label="Extraction en cours" />)
    const status = screen.getByRole('status', { name: 'Extraction en cours' })
    expect(status).toHaveTextContent('')
    expect(status.querySelector('canvas')).toHaveAttribute('aria-hidden', 'true')
  })

  it('defaults to a 200×200 square and honours a custom size', () => {
    const { rerender } = render(<GlobeLoader />)
    expect(screen.getByTestId('globe-loader')).toHaveStyle({ width: '200px', height: '200px' })
    rerender(<GlobeLoader size={120} />)
    expect(screen.getByTestId('globe-loader')).toHaveStyle({ width: '120px', height: '120px' })
  })
})

describe('LoaderStage', () => {
  it('wraps the loader and forwards its label and test id', () => {
    render(<LoaderStage label="Chargement du catalogue" testId="stage" />)
    expect(screen.getByTestId('stage')).toContainElement(
      screen.getByRole('status', { name: 'Chargement du catalogue' }),
    )
  })
})
