import { useEffect, useRef, useState } from 'react'
import type { Client } from '../api/contacts'
import { searchClients } from '../api/contacts'

interface Props {
  onSelect: (client: Client) => void
  onEdit?: (client: Client) => void
}

const DEBOUNCE_MS = 250

export function ClientSearch({ onSelect, onEdit }: Props) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<Client[]>([])
  const [status, setStatus] = useState<'idle' | 'loading' | 'error'>('idle')
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => {
    const trimmed = query.trim()
    if (trimmed.length < 2) {
      setResults([])
      setStatus('idle')
      abortRef.current?.abort()
      return
    }
    const timeout = window.setTimeout(async () => {
      abortRef.current?.abort()
      const controller = new AbortController()
      abortRef.current = controller
      setStatus('loading')
      try {
        const next = await searchClients(trimmed, controller.signal)
        setResults(next)
        setStatus('idle')
      } catch (err) {
        if (controller.signal.aborted) return
        // eslint-disable-next-line no-console
        console.error(err)
        setStatus('error')
      }
    }, DEBOUNCE_MS)
    return () => window.clearTimeout(timeout)
  }, [query])

  return (
    <div className="space-y-3">
      <label className="block text-sm font-medium" htmlFor="client-search">
        Rechercher un client
      </label>
      <input
        id="client-search"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder="Nom, code ou code postal (>= 2 caractères)"
        className="w-full rounded-xl border border-ink-muted/30 bg-transparent px-4 py-2 text-sm focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
      />

      {status === 'loading' ? (
        <p role="status" className="text-xs text-ink-muted">
          Recherche…
        </p>
      ) : null}
      {status === 'error' ? (
        <p role="alert" className="text-xs text-danger">
          Erreur réseau lors de la recherche client.
        </p>
      ) : null}

      {results.length > 0 ? (
        <ul className="overflow-hidden rounded-xl border border-ink-muted/15 divide-y divide-ink-muted/10">
          {results.map((client) => (
            <li key={client.id ?? client.client_code} className="flex items-stretch">
              <button
                type="button"
                onClick={() => onSelect(client)}
                className="flex flex-1 items-baseline justify-between gap-4 px-4 py-3 text-left text-sm transition hover:bg-accent-subtle/40"
              >
                <span className="font-medium">{client.client_name}</span>
                <span className="text-xs text-ink-muted">
                  <code>{client.client_code}</code> · {client.postal_code} · dpt{' '}
                  {client.department}
                </span>
              </button>
              {onEdit && client.id != null ? (
                <button
                  type="button"
                  onClick={() => onEdit(client)}
                  className="border-l border-ink-muted/10 px-3 text-xs text-ink-muted transition hover:bg-accent-subtle/40 hover:text-accent"
                  data-testid={`edit-client-${client.id}`}
                  aria-label={`Modifier ${client.client_name}`}
                  title={`Modifier ${client.client_name}`}
                >
                  ✎
                </button>
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}
