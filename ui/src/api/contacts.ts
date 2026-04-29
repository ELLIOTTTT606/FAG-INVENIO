import { ApiError } from './client'

export interface Client {
  client_code: string
  client_name: string
  postal_code: string
  department: string
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
