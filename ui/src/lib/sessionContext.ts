// ─────────────────────────────────────────────────────────────────────────────
// Session INVENIO — état partagé entre les 5 étapes
// Stocké en sessionStorage pour survivre aux navigations React Router
// ─────────────────────────────────────────────────────────────────────────────
import type { AcousticType, MachineFamily, MediumType } from './machines'
import type { CanonicalRecord }           from '../api/types'
import type { DepartmentContacts }         from '../api/contacts'

// ── Types ─────────────────────────────────────────────────────────────────────
export interface MachineState {
  model:    string
  size:     string
  family:   MachineFamily | null
  acoustic: AcousticType | null
  medium:   MediumType
}

export interface ProjectState {
  number: string   // ex: "2026-0142"
  name:   string   // ex: "Bureaux Lyon"
}

export interface ClientState {
  id:         number | null
  code:       string   // code tiers Baserow
  name:       string
  postalCode: string
  department: string
}

export interface SolutionContact {
  name:  string
  email: string
  phone: string
}

export interface PlanAttachment {
  name:    string
  dataUrl: string
}

// ── Clés de stockage ──────────────────────────────────────────────────────────
const KEYS = {
  machine:  'inv_machine',
  project:  'inv_project',
  client:   'inv_client',
  contacts: 'inv_contacts',
  solution: 'inv_solution',
  options:  'inv_options',
  record:   'inv_record',
  plans:    'inv_plans',
} as const

// ── Helpers génériques ────────────────────────────────────────────────────────
function save<T>(key: string, value: T): void {
  try { sessionStorage.setItem(key, JSON.stringify(value)) } catch { /* storage unavailable */ }
}

function load<T>(key: string): T | null {
  try {
    const raw = sessionStorage.getItem(key)
    return raw ? (JSON.parse(raw) as T) : null
  } catch {
    return null
  }
}

function clear(key: string): void {
  try { sessionStorage.removeItem(key) } catch { /* storage unavailable */ }
}

// ── API publique ──────────────────────────────────────────────────────────────

// Étape 1 — Machine
export const saveMachine    = (m: MachineState)              => save(KEYS.machine, m)
export const loadMachine    = ()                              => load<MachineState>(KEYS.machine)
export const clearMachine   = ()                              => clear(KEYS.machine)

// Record parsé depuis le fichier GALLETTI
export const saveRecord     = (r: CanonicalRecord)           => save(KEYS.record, r)
export const loadRecord     = ()                              => load<CanonicalRecord>(KEYS.record)
export const clearRecord    = ()                              => clear(KEYS.record)

// Étape 2 — Projet & Client
export const saveProject    = (p: ProjectState)              => save(KEYS.project, p)
export const loadProject    = ()                              => load<ProjectState>(KEYS.project)

export const saveClient     = (c: ClientState)               => save(KEYS.client, c)
export const loadClient     = ()                              => load<ClientState>(KEYS.client)

export const saveSolution   = (s: SolutionContact)           => save(KEYS.solution, s)
export const loadSolution   = ()                              => load<SolutionContact>(KEYS.solution)

// Étape 3 — Contacts
export const saveContacts   = (c: DepartmentContacts)        => save(KEYS.contacts, c)
export const loadContacts   = ()                              => load<DepartmentContacts>(KEYS.contacts)

// Étape 4 — Options
export const saveOptions    = (codes: string[])              => save(KEYS.options, codes)
export const loadOptions    = ()                              => load<string[]>(KEYS.options) ?? []

// Plans (PDF generation)
export const savePlans      = (plans: PlanAttachment[])      => save(KEYS.plans, plans)
export const loadPlans      = ()                              => load<PlanAttachment[]>(KEYS.plans) ?? []

// Réinitialisation complète
export function clearSession(): void {
  Object.values(KEYS).forEach(k => clear(k))
}

// ── Rétrocompatibilité avec l'ancien sessionContext ────────────────────────────
// (pour que les anciens tests et imports continuent de fonctionner)
export const rememberImport         = (r: CanonicalRecord)  => saveRecord(r)
export const clearImport            = ()                    => clearRecord()
export const readImport             = () => {
  const r = loadRecord()
  if (!r?.model) return null
  return {
    record: r,
    data:   r,
    machine: { model: r.model, type: r.type, size: r.size },
    preselectedOptionCodes: r.options.filter(o => o.selected).map(o => o.code),
  }
}
export const rememberSelectedOptions = (codes: string[])   => saveOptions(codes)
export const readSelectedOptions    = ()                    => loadOptions()
export const rememberContacts       = (c: DepartmentContacts) => saveContacts(c)
export const readContacts           = <T,>()                => loadContacts() as T | null
