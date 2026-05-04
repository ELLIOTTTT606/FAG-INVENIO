import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { FranceMap } from '../components/FranceMap'
import { DROM_LAYOUT, METROPOLE_CENTROIDS } from '../data/departmentCentroids'

describe('FranceMap', () => {
  it('renders one marker per metropole department + DROM', () => {
    render(<FranceMap selected={null} onSelect={() => undefined} />)
    expect(screen.getAllByRole('button')).toHaveLength(
      METROPOLE_CENTROIDS.length + DROM_LAYOUT.length,
    )
    expect(screen.getByTestId('france-map-69')).toBeInTheDocument()
    expect(screen.getByTestId('france-map-2A')).toBeInTheDocument()
    expect(screen.getByTestId('france-map-974')).toBeInTheDocument()
  })

  it('flags the selected department with aria-pressed', () => {
    render(<FranceMap selected="69" onSelect={() => undefined} />)
    expect(screen.getByTestId('france-map-69')).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByTestId('france-map-13')).toHaveAttribute('aria-pressed', 'false')
  })

  it('calls onSelect when a marker is clicked', () => {
    const onSelect = vi.fn()
    render(<FranceMap selected={null} onSelect={onSelect} />)
    fireEvent.click(screen.getByTestId('france-map-13'))
    expect(onSelect).toHaveBeenCalledWith('13')
  })

  it('selects on Enter and Space keypress', () => {
    const onSelect = vi.fn()
    render(<FranceMap selected={null} onSelect={onSelect} />)
    const marker = screen.getByTestId('france-map-75')
    fireEvent.keyDown(marker, { key: 'Enter' })
    fireEvent.keyDown(marker, { key: ' ' })
    expect(onSelect).toHaveBeenCalledTimes(2)
    expect(onSelect).toHaveBeenLastCalledWith('75')
  })

  it('exposes a human-readable aria-label for each marker', () => {
    render(<FranceMap selected={null} onSelect={() => undefined} />)
    const rhone = screen.getByTestId('france-map-69')
    expect(rhone.getAttribute('aria-label')).toContain('Rhône')
  })
})
