import { ApiError } from './client'
import type { DepartmentContacts } from './contacts'
import type { CanonicalRecord } from './types'

export interface GenerationRequest {
  record: CanonicalRecord
  contacts?: DepartmentContacts | null
  selectedOptionCodes: string[]
  documentReference?: string
}

function toBody(request: GenerationRequest): Record<string, unknown> {
  return {
    record: request.record,
    contacts: request.contacts ?? null,
    selected_option_codes: request.selectedOptionCodes,
    document_reference: request.documentReference ?? null,
  }
}

export async function fetchPreviewHtml(request: GenerationRequest): Promise<string> {
  const response = await fetch('/generate/preview', {
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
  const response = await fetch('/generate/pdf', {
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

export function suggestedFilename(record: CanonicalRecord, extension = 'pdf'): string {
  const slug = `${record.model}-${record.size}-${record.type}`.toLowerCase().replace(/[^a-z0-9-]+/g, '-')
  return `INVENIO-${slug || 'fiche'}.${extension}`
}
