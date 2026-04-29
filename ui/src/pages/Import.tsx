import { useCallback, useState } from 'react'
import { Link } from 'react-router-dom'
import { ApiError, parseFile } from '../api/client'
import type { ParseResponse } from '../api/types'
import { Dropzone } from '../components/Dropzone'
import { ExtractionSummary } from '../components/ExtractionSummary'
import { rememberImport } from '../lib/sessionContext'

type Status =
  | { kind: 'idle' }
  | { kind: 'parsing'; filename: string }
  | { kind: 'ready'; filename: string; result: ParseResponse }
  | { kind: 'error'; filename: string; message: string }

export default function Import() {
  const [status, setStatus] = useState<Status>({ kind: 'idle' })

  const handleFile = useCallback(async (file: File) => {
    setStatus({ kind: 'parsing', filename: file.name })
    try {
      const result = await parseFile(file)
      rememberImport(result.data)
      setStatus({ kind: 'ready', filename: file.name, result })
    } catch (err) {
      const message = err instanceof ApiError ? err.message : 'Erreur réseau lors du parsing.'
      setStatus({ kind: 'error', filename: file.name, message })
    }
  }, [])

  const reset = () => setStatus({ kind: 'idle' })

  return (
    <section className="space-y-10">
      <div>
        <p className="text-sm uppercase tracking-widest text-accent">Étape 1 · Import</p>
        <h1 className="mt-2 text-3xl font-semibold md:text-4xl">Déposez votre fiche GALLETTI</h1>
        <p className="mt-3 max-w-2xl text-ink-muted">
          INVENIO accepte les fichiers DOCX et PDF. La désignation, les conditions
          de fonctionnement, les performances, les options et les données générales
          sont extraites automatiquement.
        </p>
      </div>

      <Dropzone disabled={status.kind === 'parsing'} onFile={handleFile} />

      {status.kind === 'parsing' ? (
        <p
          role="status"
          aria-live="polite"
          className="text-sm text-ink-muted"
          data-testid="import-status"
        >
          Extraction en cours pour <strong>{status.filename}</strong>…
        </p>
      ) : null}

      {status.kind === 'error' ? (
        <div
          role="alert"
          className="rounded-2xl border border-danger/30 bg-danger/5 p-4 text-sm text-danger"
          data-testid="import-error"
        >
          <p className="font-medium">Échec du parsing pour {status.filename}</p>
          <p className="mt-2 text-danger/90">{status.message}</p>
          <button
            onClick={reset}
            className="mt-3 inline-flex items-center rounded-full border border-danger/40 px-4 py-1.5 text-xs hover:bg-danger/10"
          >
            Réessayer
          </button>
        </div>
      ) : null}

      {status.kind === 'ready' ? (
        <>
          <ExtractionSummary
            record={status.result.data}
            warnings={status.result.warnings}
          />
          <div className="flex justify-end">
            <Link
              to="/options"
              className="inline-flex items-center gap-2 rounded-full bg-accent px-6 py-3 text-sm font-medium text-white transition hover:bg-accent-hover"
            >
              Continuer vers les options →
            </Link>
          </div>
        </>
      ) : null}
    </section>
  )
}
