import type { ParseResponse } from './types'

export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message)
    this.name = 'ApiError'
  }
}

export async function parseFile(file: File): Promise<ParseResponse> {
  const ext = file.name.toLowerCase().split('.').pop()
  if (ext !== 'docx' && ext !== 'pdf') {
    throw new ApiError(`Unsupported file type .${ext}. Use .docx or .pdf.`, 415)
  }
  const path = ext === 'docx' ? '/parse/docx' : '/parse/pdf'
  const url = `${import.meta.env.VITE_API_URL || ''}${path}`

  const body = new FormData()
  body.append('file', file)

  const response = await fetch(url, { method: 'POST', body })
  if (!response.ok) {
    const detail = await response.text().catch(() => '')
    throw new ApiError(detail || `Parse failed with status ${response.status}`, response.status)
  }
  return (await response.json()) as ParseResponse
}
