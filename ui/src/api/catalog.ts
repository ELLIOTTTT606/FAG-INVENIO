// ─────────────────────────────────────────────────────────────────────────────
// Client API — Catalogue produits GALLETTI (familles → tailles)
// ─────────────────────────────────────────────────────────────────────────────
import { ApiError } from './client'

const BASE = import.meta.env.VITE_API_URL || ''

export interface Family {
  code: string
  name: string
}

export interface Size {
  model: string
  cooling_power_kw: number | null
  heating_power_kw: number | null
  eer: number | null
  cop: number | null
}

async function getJson<T>(path: string): Promise<T> {
  const r = await fetch(`${BASE}${path}`)
  if (!r.ok) {
    let detail = ''
    try {
      detail = (await r.json())?.detail ?? ''
    } catch {
      detail = await r.text().catch(() => '')
    }
    throw new ApiError(detail || `Erreur catalogue (${r.status})`, r.status)
  }
  return r.json() as Promise<T>
}

export async function listFamilies(): Promise<Family[]> {
  const body = await getJson<{ families: Family[] }>('/galletti/families')
  return body.families
}

export async function getFamilySizes(familyCode: string): Promise<Size[]> {
  const body = await getJson<{ family: string; sizes: Size[] }>(
    `/galletti/families/${encodeURIComponent(familyCode)}/sizes`,
  )
  return body.sizes
}
