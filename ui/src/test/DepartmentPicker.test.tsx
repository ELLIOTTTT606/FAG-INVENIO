import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { DepartmentPicker } from '../components/DepartmentPicker'

describe('DepartmentPicker', () => {
  it('groups departments by region by default', () => {
    render(<DepartmentPicker selected={null} onSelect={() => undefined} />)
    expect(screen.getByText('Auvergne-Rhône-Alpes')).toBeInTheDocument()
    expect(screen.getByText("Provence-Alpes-Côte d'Azur")).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /69/ })).toBeInTheDocument()
  })

  it('filters departments by code or name (accent-insensitive)', () => {
    render(<DepartmentPicker selected={null} onSelect={() => undefined} />)
    const input = screen.getByLabelText(/rechercher un département/i)
    fireEvent.change(input, { target: { value: 'rhone' } })
    expect(screen.getByRole('button', { name: /69/ })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Paris/ })).not.toBeInTheDocument()
  })

  it('marks the selected department with aria-pressed', () => {
    render(<DepartmentPicker selected="69" onSelect={() => undefined} />)
    const button = screen.getByRole('button', { name: /69/ })
    expect(button).toHaveAttribute('aria-pressed', 'true')
  })

  it('calls onSelect with the department code on click', () => {
    const onSelect = vi.fn()
    render(<DepartmentPicker selected={null} onSelect={onSelect} />)
    fireEvent.click(screen.getByRole('button', { name: /75/ }))
    expect(onSelect).toHaveBeenCalledWith('75')
  })

  it('shows an empty-state message when nothing matches', () => {
    render(<DepartmentPicker selected={null} onSelect={() => undefined} />)
    fireEvent.change(screen.getByLabelText(/rechercher un département/i), {
      target: { value: 'zzzz' },
    })
    expect(screen.getByText(/aucun département/i)).toBeInTheDocument()
  })
})
