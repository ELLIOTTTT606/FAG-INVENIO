import type { MachineContext } from '../api/options'
import type { CanonicalRecord } from '../api/types'

const KEY = 'invenio.lastImport'

export interface ImportContext {
  machine: MachineContext
  preselectedOptionCodes: string[]
}

export function rememberImport(record: CanonicalRecord): void {
  if (typeof sessionStorage === 'undefined') return
  if (!record.model || !record.type || !record.size) return
  const payload: ImportContext = {
    machine: { model: record.model, type: record.type, size: record.size },
    preselectedOptionCodes: record.options
      .filter((opt) => opt.selected)
      .map((opt) => opt.code)
      .filter((code) => Boolean(code)),
  }
  try {
    sessionStorage.setItem(KEY, JSON.stringify(payload))
  } catch {
    // Quota / privacy mode: silently ignore.
  }
}

export function readImport(): ImportContext | null {
  if (typeof sessionStorage === 'undefined') return null
  try {
    const raw = sessionStorage.getItem(KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as ImportContext
    if (!parsed?.machine?.model || !parsed.machine.type || !parsed.machine.size) return null
    return {
      machine: parsed.machine,
      preselectedOptionCodes: parsed.preselectedOptionCodes ?? [],
    }
  } catch {
    return null
  }
}

export function clearImport(): void {
  if (typeof sessionStorage === 'undefined') return
  try {
    sessionStorage.removeItem(KEY)
  } catch {
    // ignore
  }
}
