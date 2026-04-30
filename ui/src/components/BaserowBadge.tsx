import { useEffect, useState } from 'react'
import type { BaserowStatus } from '../api/admin'
import { fetchBaserowStatus } from '../api/admin'

export function BaserowBadge() {
  const [status, setStatus] = useState<BaserowStatus | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    fetchBaserowStatus(controller.signal).then(setStatus)
    return () => controller.abort()
  }, [])

  const mode = status?.mode ?? 'mock'
  const live = mode === 'live'
  const label = live ? 'Baserow live' : 'Baserow mock'
  const tooltip = live
    ? `Connecté à ${status?.url}`
    : 'Aucun token Baserow configuré, données factices.'

  return (
    <span
      title={tooltip}
      className={[
        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-medium uppercase tracking-wider',
        live
          ? 'bg-success/15 text-success'
          : 'bg-warn/15 text-warn',
      ].join(' ')}
      data-testid="baserow-badge"
      data-mode={mode}
    >
      <span
        aria-hidden
        className={['h-1.5 w-1.5 rounded-full', live ? 'bg-success' : 'bg-warn'].join(' ')}
      />
      {label}
    </span>
  )
}
