// ─────────────────────────────────────────────────────────────────────────────
// Client API GALLETTI — liste des projets et détail (Phase 1)
// ─────────────────────────────────────────────────────────────────────────────
import { ApiError } from './client'

const BASE = import.meta.env.VITE_API_URL || ''

export interface GallettiProject {
  id: number
  numero: string
  date: string
  client: string
  nom: string
  utilisateur: string
  prix_total: string
}

export interface GallettiArticle {
  position: number
  model: string
  family: string
  description: string
  price: number | null
  option_codes: string[]
}

export interface GallettiStatus {
  configured: boolean
  base_url: string
}

async function getJson<T>(path: string): Promise<T> {
  const r = await fetch(`${BASE}${path}`)
  if (!r.ok) {
    let detail = ''
    try {
      const body = await r.json()
      detail = body?.detail ?? ''
    } catch {
      detail = await r.text().catch(() => '')
    }
    throw new ApiError(detail || `Erreur GALLETTI (${r.status})`, r.status)
  }
  return r.json() as Promise<T>
}

export function getGallettiStatus(): Promise<GallettiStatus> {
  return getJson<GallettiStatus>('/galletti/status')
}

export async function listGallettiProjects(): Promise<GallettiProject[]> {
  const body = await getJson<{ projects: GallettiProject[] }>('/galletti/projects')
  return body.projects
}

export async function getGallettiProject(
  id: number,
): Promise<{ id: number; articles: GallettiArticle[] }> {
  return getJson<{ id: number; articles: GallettiArticle[] }>(`/galletti/projects/${id}`)
}
