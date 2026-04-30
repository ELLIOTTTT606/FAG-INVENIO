import { describe, expect, it } from 'vitest'
import { departmentFromPostalCode } from '../lib/postalCode'

describe('departmentFromPostalCode', () => {
  it('returns the first two digits for metropole codes', () => {
    expect(departmentFromPostalCode('75015')).toBe('75')
    expect(departmentFromPostalCode('69001')).toBe('69')
    expect(departmentFromPostalCode('59650')).toBe('59')
  })

  it('maps Corsica codes to 2A / 2B', () => {
    expect(departmentFromPostalCode('20100')).toBe('2A')
    expect(departmentFromPostalCode('20200')).toBe('2B')
    expect(departmentFromPostalCode('20620')).toBe('2B')
  })

  it('maps overseas (DROM/COM) codes to 3 digits', () => {
    expect(departmentFromPostalCode('97100')).toBe('971')
    expect(departmentFromPostalCode('97400')).toBe('974')
    expect(departmentFromPostalCode('98800')).toBe('988')
  })

  it('returns null for invalid postal codes', () => {
    expect(departmentFromPostalCode('abcde')).toBeNull()
    expect(departmentFromPostalCode('123')).toBeNull()
    expect(departmentFromPostalCode('')).toBeNull()
    expect(departmentFromPostalCode('123456')).toBeNull()
  })

  it('trims surrounding whitespace before validating', () => {
    expect(departmentFromPostalCode('  75015  ')).toBe('75')
  })
})
