import { ApiError } from './client'

export interface Client {
  client_code: string
  client_name: string
  postal_code: string
  department: string
  id?: number | null
}

export interface ContactInfo {
  name: string | null
  email: string | null
  phone: string | null
}

export interface DepartmentContacts {
  department: string
  tci: ContactInfo | null
  tcs: ContactInfo | null
  solution: ContactInfo | null
}

export async function searchClients(query: string, signal?: AbortSignal): Promise<Client[]> {
  const trimmed = query.trim()
  if (trimmed.length < 2) return []
  const params = new URLSearchParams({ q: trimmed })
  const response = await fetch(`/clients/search?${params.toString()}`, { signal })
  if (!response.ok) {
    throw new ApiError(`Recherche clients echouee (${response.status})`, response.status)
  }
  return (await response.json()) as Client[]
}

function clientPayload(input: Client): Record<string, string> {
  return {
    client_code: input.client_code,
    client_name: input.client_name,
    postal_code: input.postal_code,
    department: input.department,
  }
}

export async function createClient(input: Client, signal?: AbortSignal): Promise<Client> {
  const response = await fetch('/clients', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(clientPayload(input)),
    signal,
  })
  if (!response.ok) {
    const detail = await response.text().catch(() => '')
    if (response.status === 409) {
      throw new ApiError(detail || 'Ce code client existe déjà.', 409)
    }
    if (response.status === 422 || response.status === 400) {
      throw new ApiError(detail || 'Données invalides.', response.status)
    }
    throw new ApiError(detail || `Création impossible (${response.status}).`, response.status)
  }
  return (await response.json()) as Client
}

export async function updateClient(
  clientId: number,
  input: Client,
  signal?: AbortSignal,
): Promise<Client> {
  const response = await fetch(`/clients/${clientId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(clientPayload(input)),
    signal,
  })
  if (!response.ok) {
    const detail = await response.text().catch(() => '')
    if (response.status === 404) {
      throw new ApiError(detail || 'Client introuvable.', 404)
    }
    if (response.status === 409) {
      throw new ApiError(detail || 'Ce code client est déjà utilisé.', 409)
    }
    if (response.status === 422 || response.status === 400) {
      throw new ApiError(detail || 'Données invalides.', response.status)
    }
    throw new ApiError(detail || `Modification impossible (${response.status}).`, response.status)
  }
  return (await response.json()) as Client
}

export async function fetchDepartmentContacts(
  department: string,
  signal?: AbortSignal,
): Promise<DepartmentContacts> {
  const response = await fetch(`/contacts/department/${encodeURIComponent(department)}`, { signal })
  if (!response.ok) {
    throw new ApiError(
      `Contacts indisponibles pour le département ${department}`,
      response.status,
    )
  }
  return (await response.json()) as DepartmentContacts
}
