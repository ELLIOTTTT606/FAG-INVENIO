import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import type { MachineContext } from '../api/options'
import { fetchOptions, groupByCategory, type OptionsResponse } from '../api/options'
import { OptionsAccordion } from '../components/OptionsAccordion'
import { readImport, readSelectedOptions, rememberSelectedOptions } from '../lib/sessionContext'

type Status = 'idle' | 'loading' | 'ready' | 'error'

function parseContext(params: URLSearchParams): MachineContext | null {
  const model = params.get('model') ?? ''
  const type = params.get('type') ?? ''
  const size = params.get('size') ?? ''
  if (!model || !type || !size) return null
  return { model, type, size }
}

export default function Options() {
  const [params] = useSearchParams()
  const navigate = useNavigate()

  const queryContext = parseContext(params)
  const sessionContext = useMemo(() => readImport(), [])

  const machine: MachineContext | null = queryContext ?? sessionContext?.machine ?? null
  const preselected = useMemo(
    () => new Set(sessionContext?.preselectedOptionCodes ?? []),
    [sessionContext],
  )

  const [response, setResponse] = useState<OptionsResponse | null>(null)
  const [status, setStatus] = useState<Status>('idle')
  const [selected, setSelected] = useState<Set<string>>(() => new Set(readSelectedOptions()))

  useEffect(() => {
    if (!machine) {
      setStatus('idle')
      return
    }
    const controller = new AbortController()
    setStatus('loading')
    fetchOptions(machine, controller.signal)
      .then((next) => {
        if (controller.signal.aborted) return
        setResponse(next)
        setStatus('ready')
        setSelected((prev) => {
          // Keep existing user choices; pre-check codes coming from the parsed
          // designation only the first time we load this machine.
          if (prev.size > 0) return prev
          const initial = new Set<string>()
          for (const opt of next.options) {
            if (preselected.has(opt.code)) initial.add(opt.code)
          }
          return initial
        })
      })
      .catch((err) => {
        if (controller.signal.aborted) return
        // eslint-disable-next-line no-console
        console.error(err)
        setStatus('error')
      })
    return () => controller.abort()
  }, [machine, preselected])

  const grouped = useMemo(
    () => (response ? Array.from(groupByCategory(response.options).entries()) : []),
    [response],
  )
  const totalSelected = selected.size
  const totalOptions = response?.options.length ?? 0

  useEffect(() => {
    rememberSelectedOptions(Array.from(selected))
  }, [selected])

  const toggle = (code: string) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(code)) next.delete(code)
      else next.add(code)
      return next
    })
  }

  if (!machine) {
    return (
      <section className="space-y-6">
        <p className="text-sm uppercase tracking-widest text-accent">Étape 3 · Options</p>
        <h1 className="text-3xl font-semibold md:text-4xl">Aucune machine sélectionnée</h1>
        <p className="max-w-2xl text-ink-muted">
          Importez d'abord une fiche GALLETTI pour choisir ses options. Les
          options pré-cochées seront déduites de la chaîne de désignation
          extraite.
        </p>
        <button
          type="button"
          onClick={() => navigate('/import')}
          className="inline-flex items-center gap-2 rounded-full bg-accent px-6 py-3 text-sm font-medium text-white transition hover:bg-accent-hover"
        >
          Aller à l'import
        </button>
      </section>
    )
  }

  return (
    <section className="space-y-8">
      <header>
        <p className="text-sm uppercase tracking-widest text-accent">Étape 3 · Options</p>
        <h1 className="mt-2 text-3xl font-semibold md:text-4xl">
          Sélectionnez les options pour {machine.model} · {machine.size} · {machine.type}
        </h1>
        <p className="mt-3 max-w-2xl text-ink-muted">
          Catalogue filtré par modèle, taille et type acoustique. Les options
          détectées dans la désignation sont pré-cochées.
        </p>
      </header>

      <div
        className="sticky top-0 z-10 flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-ink-muted/15 bg-surface-light/95 px-5 py-3 backdrop-blur"
        data-testid="options-counter"
      >
        <p className="text-sm">
          <strong className="text-accent">{totalSelected}</strong>
          <span className="text-ink-muted"> / {totalOptions} option(s) sélectionnée(s)</span>
        </p>
        <button
          type="button"
          onClick={() => setSelected(new Set())}
          disabled={totalSelected === 0}
          className="rounded-full border border-ink-muted/30 px-4 py-1.5 text-xs hover:border-accent disabled:opacity-50"
        >
          Tout désélectionner
        </button>
      </div>

      {status === 'loading' ? (
        <p role="status" className="text-sm text-ink-muted">
          Chargement du catalogue…
        </p>
      ) : null}
      {status === 'error' ? (
        <p role="alert" className="text-sm text-danger">
          Le catalogue d'options n'a pas pu être chargé.
        </p>
      ) : null}

      {status === 'ready' && grouped.length > 0 ? (
        <div className="flex justify-end">
          <Link
            to="/generate"
            className="inline-flex items-center gap-2 rounded-full bg-accent px-6 py-3 text-sm font-medium text-white transition hover:bg-accent-hover"
          >
            Continuer vers la génération →
          </Link>
        </div>
      ) : null}

      {status === 'ready' ? (
        grouped.length === 0 ? (
          <p className="rounded-2xl border border-dashed border-ink-muted/30 p-8 text-center text-sm italic text-ink-muted">
            Aucune option disponible pour cette configuration.
          </p>
        ) : (
          <div className="space-y-4">
            {grouped.map(([category, options]) => (
              <OptionsAccordion
                key={category}
                category={category}
                options={options}
                selected={selected}
                onToggle={toggle}
              />
            ))}
          </div>
        )
      ) : null}
    </section>
  )
}
