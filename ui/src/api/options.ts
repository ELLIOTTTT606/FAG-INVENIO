import { ApiError } from './client'

export interface CatalogOption {
  code: string
  category: string
  label: string
  description: string | null
  tips: string | null
  price_eur: number | null
  available: boolean
}

export interface OptionsResponse {
  model: string
  type: string
  size: string
  options: CatalogOption[]
}

export interface MachineContext {
  model: string
  type: string
  size: string
}

export async function fetchOptions(
  ctx: MachineContext,
  signal?: AbortSignal,
): Promise<OptionsResponse> {
  const params = new URLSearchParams({ model: ctx.model, type: ctx.type, size: ctx.size })
  const response = await fetch(`/options?${params.toString()}`, { signal })
  if (!response.ok) {
    throw new ApiError(`Catalogue options indisponible (${response.status})`, response.status)
  }
  return (await response.json()) as OptionsResponse
}

export function groupByCategory(options: CatalogOption[]): Map<string, CatalogOption[]> {
  const map = new Map<string, CatalogOption[]>()
  for (const option of options) {
    const list = map.get(option.category) ?? []
    list.push(option)
    map.set(option.category, list)
  }
  return map
}
