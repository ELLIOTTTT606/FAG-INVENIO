import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import type { CanonicalRecord } from '../api/types'
import { clearImport, readImport, rememberImport } from '../lib/sessionContext'
import { pacRecord } from './fixtures'

describe('sessionContext', () => {
  beforeEach(() => sessionStorage.clear())
  afterEach(() => sessionStorage.clear())

  it('round-trips machine context and selected option codes', () => {
    rememberImport(pacRecord)
    const ctx = readImport()
    expect(ctx?.machine).toEqual({ model: 'PLP', type: 'HS', size: '052' })
    expect(ctx?.preselectedOptionCodes).toEqual(['B1P00'])
  })

  it('skips records without a complete machine identity', () => {
    const partial: CanonicalRecord = { ...pacRecord, model: '' }
    rememberImport(partial)
    expect(readImport()).toBeNull()
  })

  it('clearImport empties the store', () => {
    rememberImport(pacRecord)
    clearImport()
    expect(readImport()).toBeNull()
  })

  it('returns null when sessionStorage holds malformed JSON', () => {
    sessionStorage.setItem('invenio.lastImport', '{not json')
    expect(readImport()).toBeNull()
  })
})
