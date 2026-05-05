export type BaserowMode = 'live' | 'mock'

export interface BaserowStatus {
  mode: BaserowMode
  url: string
  tables: Record<string, number>
}

export async function fetchBaserowStatus(signal?: AbortSignal): Promise<BaserowStatus | null> {
  try {
    const response = await fetch(
      `${import.meta.env.VITE_API_URL || ''}/admin/baserow-status`,
      { signal },
    )
    if (!response.ok) return null
    return (await response.json()) as BaserowStatus
  } catch {
    return null
  }
}
