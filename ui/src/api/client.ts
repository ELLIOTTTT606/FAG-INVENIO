// ─────────────────────────────────────────────────────────────────────────────
// Client API INVENIO — fonctions partagées
// ─────────────────────────────────────────────────────────────────────────────

export class ApiError extends Error {
  constructor(message: string, public status: number) {
    super(message)
    this.name = 'ApiError'
  }
}

const BASE = import.meta.env.VITE_API_URL || ''

// ── Parser de fichier GALLETTI (DOCX ou PDF) ──────────────────────────────────
import type { ParseResponse } from './types'
export type { CanonicalRecord, Warning, ParseResponse } from './types'

export async function parseFile(file: File): Promise<ParseResponse> {
  const form = new FormData()
  form.append('file', file)

  const ext = file.name.split('.').pop()?.toLowerCase()
  const endpoint = ext === 'pdf' ? '/parse/pdf' : '/parse/docx'

  try {
    const r = await fetch(`${BASE}${endpoint}`, {
      method: 'POST',
      body:   form,
    })

    if (!r.ok) {
      const detail = await r.text().catch(() => '')
      throw new ApiError(
        detail || `Erreur de parsing (${r.status})`,
        r.status,
      )
    }

    return r.json()
  } catch (err) {
    console.error('parseFile error:', err)
    throw err
  }
}

// ── Health check ──────────────────────────────────────────────────────────────
export async function healthCheck(): Promise<boolean> {
  try {
    const r = await fetch(`${BASE}/health`, { signal: AbortSignal.timeout(3000) })
    return r.ok
  } catch {
    return false
  }
}
