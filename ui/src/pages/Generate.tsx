import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { ApiError } from '../api/client'
import type { DepartmentContacts } from '../api/contacts'
import {
  fetchPdfBlob,
  fetchPreviewHtml,
  suggestedFilename,
  type GenerationRequest,
  type PlanAttachment,
} from '../api/generate'
import { PlansUploader } from '../components/PlansUploader'
import {
  readContacts,
  readImport,
  readSelectedOptions,
} from '../lib/sessionContext'

type Status = 'idle' | 'loading' | 'ready' | 'error'

export default function Generate() {
  const [previewHtml, setPreviewHtml] = useState<string | null>(null)
  const [status, setStatus] = useState<Status>('idle')
  const [error, setError] = useState<string | null>(null)
  const [downloading, setDownloading] = useState(false)
  const [plans, setPlans] = useState<PlanAttachment[]>([])

  const importContext = useMemo(() => readImport(), [])
  const contacts = useMemo(() => readContacts<DepartmentContacts>(), [])
  const selectedOptionCodes = useMemo(() => readSelectedOptions(), [])

  const request: GenerationRequest | null = useMemo(() => {
    if (!importContext?.record) return null
    return {
      record: importContext.record,
      contacts: contacts ?? null,
      selectedOptionCodes,
      plans,
    }
  }, [importContext, contacts, selectedOptionCodes, plans])

  useEffect(() => {
    if (!request) {
      setStatus('idle')
      return
    }
    const controller = new AbortController()
    setStatus('loading')
    setError(null)
    fetchPreviewHtml(request)
      .then((html) => {
        if (controller.signal.aborted) return
        setPreviewHtml(html)
        setStatus('ready')
      })
      .catch((err) => {
        if (controller.signal.aborted) return
        const message = err instanceof ApiError ? err.message : 'Erreur de prévisualisation.'
        setError(message)
        setStatus('error')
      })
    return () => controller.abort()
  }, [request])

  const handleDownload = async () => {
    if (!request) return
    setDownloading(true)
    setError(null)
    try {
      const blob = await fetchPdfBlob(request)
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = suggestedFilename(request.record)
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
    } catch (err) {
      const message = err instanceof ApiError ? err.message : 'Erreur de génération PDF.'
      setError(message)
    } finally {
      setDownloading(false)
    }
  }

  if (!request) {
    return (
      <section className="space-y-6">
        <p className="text-sm uppercase tracking-widest text-accent">Étape 4 · Génération</p>
        <h1 className="text-3xl font-semibold md:text-4xl">Aucune fiche en cours</h1>
        <p className="max-w-2xl text-ink-muted">
          Importez d'abord une fiche GALLETTI pour générer le PDF de sélection.
        </p>
        <Link
          to="/import"
          className="inline-flex items-center gap-2 rounded-full bg-accent px-6 py-3 text-sm font-medium text-white transition hover:bg-accent-hover"
        >
          Aller à l'import
        </Link>
      </section>
    )
  }

  const machine = `${request.record.model} ${request.record.size} ${request.record.type}`

  return (
    <section className="space-y-6">
      <header className="flex flex-wrap items-baseline justify-between gap-4">
        <div>
          <p className="text-sm uppercase tracking-widest text-accent">Étape 4 · Génération</p>
          <h1 className="mt-2 text-3xl font-semibold md:text-4xl">Aperçu de la fiche · {machine}</h1>
          <p className="mt-2 text-sm text-ink-muted">
            {selectedOptionCodes.length} option(s) retenues ·{' '}
            {contacts ? `département ${contacts.department}` : 'aucun contact sélectionné'}
            {plans.length > 0 ? ` · ${plans.length} plan(s)` : ''}
          </p>
        </div>
        <button
          type="button"
          onClick={handleDownload}
          disabled={downloading || status !== 'ready'}
          className="inline-flex items-center gap-2 rounded-full bg-accent px-6 py-3 text-sm font-medium text-white transition hover:bg-accent-hover disabled:opacity-50"
          data-testid="download-pdf"
        >
          {downloading ? 'Génération en cours…' : 'Télécharger le PDF'}
        </button>
      </header>

      <div className="rounded-2xl border border-ink-muted/15 p-5">
        <PlansUploader plans={plans} onChange={setPlans} />
      </div>

      {status === 'loading' ? (
        <p role="status" className="text-sm text-ink-muted">
          Construction de l'aperçu…
        </p>
      ) : null}

      {error ? (
        <div role="alert" className="rounded-2xl border border-danger/30 bg-danger/5 p-4 text-sm text-danger">
          {error}
        </div>
      ) : null}

      {previewHtml ? (
        <iframe
          title="Aperçu fiche INVENIO"
          srcDoc={previewHtml}
          className="h-[80vh] w-full rounded-2xl border border-ink-muted/15 bg-white"
          data-testid="preview-frame"
        />
      ) : null}
    </section>
  )
}
