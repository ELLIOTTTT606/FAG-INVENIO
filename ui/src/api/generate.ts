import { ApiError } from './client'
import type { DepartmentContacts } from './contacts'
import type { CanonicalRecord } from './types'

export interface PlanAttachment {
  name: string
  dataUrl: string
}

export interface GenerationRequest {
  record: CanonicalRecord
  projectName?: string
  contacts?: DepartmentContacts | null
  selectedOptionCodes: string[]
  documentReference?: string
  plans?: PlanAttachment[]
}

function toBody(request: GenerationRequest): Record<string, unknown> {
  return {
    record: request.record,
    project_name: request.projectName?.trim() || null,
    contacts: request.contacts ?? null,
    selected_option_codes: request.selectedOptionCodes,
    document_reference: request.documentReference ?? null,
    plans: (request.plans ?? []).map((plan) => ({
      name: plan.name,
      data_url: plan.dataUrl,
    })),
  }
}

export async function fetchPreviewHtml(request: GenerationRequest): Promise<string> {
  const response = await fetch(`${import.meta.env.VITE_API_URL || ''}/generate/preview`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(toBody(request)),
  })
  if (!response.ok) {
    const detail = await response.text().catch(() => '')
    throw new ApiError(detail || `Preview failed (${response.status})`, response.status)
  }
  return await response.text()
}

export async function fetchPdfBlob(request: GenerationRequest): Promise<Blob> {
  const response = await fetch(`${import.meta.env.VITE_API_URL || ''}/generate/pdf`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(toBody(request)),
  })
  if (!response.ok) {
    if (response.status === 503) {
      throw new ApiError(
        "Le moteur PDF (WeasyPrint) n'est pas installé sur ce serveur.",
        503,
      )
    }
    const detail = await response.text().catch(() => '')
    throw new ApiError(detail || `Generation PDF echouee (${response.status})`, response.status)
  }
  return await response.blob()
}

/** Same rule as the API's `suggested_filename`: project, model, size, type. */
export function suggestedFilename(
  record: CanonicalRecord,
  extension = 'pdf',
  projectName?: string,
): string {
  const base = [projectName, record.model, record.size, record.type]
    .map((part) => (part ?? '').trim())
    .filter(Boolean)
    .join('-')
  const slug = base
    .normalize('NFKD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[^A-Za-z0-9-]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .toLowerCase()
  return `INVENIO-${slug || 'fiche'}.${extension}`
}
