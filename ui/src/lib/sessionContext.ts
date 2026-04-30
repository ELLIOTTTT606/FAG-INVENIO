import type { MachineContext } from '../api/options'
import type { CanonicalRecord } from '../api/types'

const KEY = 'invenio.lastImport'

export interface ImportContext {
  machine: MachineContext
  preselectedOptionCodes: string[]
  record?: CanonicalRecord
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
    record,
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
      record: parsed.record,
    }
  } catch {
    return null
  }
}

const SELECTION_KEY = 'invenio.selectedOptions'

export function rememberSelectedOptions(codes: readonly string[]): void {
  if (typeof sessionStorage === 'undefined') return
  try {
    sessionStorage.setItem(SELECTION_KEY, JSON.stringify(Array.from(codes)))
  } catch {
    // ignore
  }
}

export function readSelectedOptions(): string[] {
  if (typeof sessionStorage === 'undefined') return []
  try {
    const raw = sessionStorage.getItem(SELECTION_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed.filter((c): c is string => typeof c === 'string') : []
  } catch {
    return []
  }
}

const CONTACTS_KEY = 'invenio.selectedContacts'

export function rememberContacts(contacts: unknown): void {
  if (typeof sessionStorage === 'undefined') return
  if (!contacts) return
  try {
    sessionStorage.setItem(CONTACTS_KEY, JSON.stringify(contacts))
  } catch {
    // ignore
  }
}

export function readContacts<T>(): T | null {
  if (typeof sessionStorage === 'undefined') return null
  try {
    const raw = sessionStorage.getItem(CONTACTS_KEY)
    return raw ? (JSON.parse(raw) as T) : null
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
