import { Link } from 'react-router-dom'

export interface CheckItem {
  id: string
  ok: boolean
  label: string
  /** What the fiche does about it, in one short sentence. */
  hint?: string
  /** Where to fix it, when another step of the flow can. */
  to?: string
}

/** "Before sending" list: what the generated fiche will contain or omit. */
export function FicheChecklist({ items }: { items: CheckItem[] }) {
  const ready = items.filter((item) => item.ok).length
  return (
    <div className="rounded-2xl border border-ink-muted/15 p-5" data-testid="fiche-checklist">
      <div className="flex items-baseline justify-between">
        <h3 className="text-sm font-medium">Avant envoi</h3>
        <span className="text-xs text-ink-muted">
          {ready} / {items.length} complets
        </span>
      </div>
      <ul className="mt-3 space-y-2.5">
        {items.map((item) => (
          <li key={item.id} className="flex items-start gap-3 text-sm" data-testid={`check-${item.id}`}>
            <span
              aria-hidden
              className={`mt-1.5 h-2 w-2 flex-none rounded-full ${item.ok ? 'bg-success' : 'bg-warn'}`}
            />
            <span className="min-w-0 flex-1">
              <span className={item.ok ? '' : 'font-medium'}>{item.label}</span>
              {item.hint ? <span className="block text-xs text-ink-muted">{item.hint}</span> : null}
            </span>
            {!item.ok && item.to ? (
              <Link to={item.to} className="flex-none text-xs font-medium text-accent hover:text-accent-hover">
                Compléter
              </Link>
            ) : null}
          </li>
        ))}
      </ul>
    </div>
  )
}
