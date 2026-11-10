// ─────────────────────────────────────────────────────────────────────────────
// Client API — Pré-analyse de demande (CCTP / mail) — Phase 2
// ─────────────────────────────────────────────────────────────────────────────
import { ApiError } from './client'

const BASE = import.meta.env.VITE_API_URL || ''

export interface AnalyzeStatus {
  configured: boolean
  base_url: string
  model: string
  has_api_key: boolean
}

// Résultat volontairement souple : le schéma peut évoluer côté LLM.
export type AnalysisResult = Record<string, unknown>

async function handle(r: Response): Promise<AnalysisResult> {
  if (!r.ok) {
    let detail = ''
    try {
      detail = (await r.json())?.detail ?? ''
    } catch {
      detail = await r.text().catch(() => '')
    }
    throw new ApiError(detail || `Erreur analyse (${r.status})`, r.status)
  }
  return r.json()
}

export async function getAnalyzeStatus(): Promise<AnalyzeStatus> {
  const r = await fetch(`${BASE}/analyze/status`)
  if (!r.ok) throw new ApiError(`Erreur status (${r.status})`, r.status)
  return r.json()
}

export async function analyzeText(text: string): Promise<AnalysisResult> {
  const r = await fetch(`${BASE}/analyze/text`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  })
  return handle(r)
}

export async function analyzeFile(file: File): Promise<AnalysisResult> {
  const form = new FormData()
  form.append('file', file)
  const r = await fetch(`${BASE}/analyze/file`, { method: 'POST', body: form })
  return handle(r)
}
