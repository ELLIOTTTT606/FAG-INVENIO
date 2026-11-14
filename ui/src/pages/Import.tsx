import { useCallback, useState } from 'react'
import { Link } from 'react-router-dom'
import { ApiError, parseFile } from '../api/client'
import type { ParseResponse } from '../api/types'
import { Dropzone } from '../components/Dropzone'
import { LoaderStage } from '../components/LoaderStage'
import { ExtractionSummary } from '../components/ExtractionSummary'
import { withViewTransition } from '../lib/motion'
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
      // The drop card morphs into the fiche header.
      withViewTransition(() => setStatus({ kind: 'ready', filename: file.name, result }))
    } catch (err) {
      const message = err instanceof ApiError ? err.message : 'Erreur réseau lors du parsing.'
      setStatus({ kind: 'error', filename: file.name, message })
    }
  }, [])

  const reset = () => withViewTransition(() => setStatus({ kind: 'idle' }))

  return (
    <section className="stagger space-y-10">
      <div>
        <p className="text-sm uppercase tracking-widest text-accent">Étape 1 · Import</p>
        <h1 className="mt-2 text-3xl font-semibold md:text-4xl">Déposez votre fiche GALLETTI</h1>
        <p className="mt-3 max-w-2xl text-ink-muted">
          INVENIO accepte les fichiers DOCX et PDF. La désignation, les conditions
          de fonctionnement, les performances, les options et les données générales
          sont extraites automatiquement.
        </p>
      </div>

      {status.kind === 'ready' ? null : (
        <div className="fiche-card rounded-3xl bg-white/70 shadow-[0_1px_2px_rgb(0_0_0/0.03),0_8px_24px_-12px_rgb(0_0_0/0.1)] backdrop-blur">
          {status.kind === 'parsing' ? (
            <div data-testid="import-status">
              <LoaderStage
                label={`Extraction en cours pour ${status.filename}`}
                className="min-h-[220px] !bg-transparent"
              />
            </div>
          ) : (
            <Dropzone onFile={handleFile} />
          )}
        </div>
      )}

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
        <div className="stagger space-y-10">
          <ExtractionSummary
            record={status.result.data}
            warnings={status.result.warnings}
            action={
              <button
                type="button"
                onClick={reset}
                className="rounded-full border border-ink-muted/30 px-4 py-2 text-xs font-medium hover:border-accent hover:text-accent"
              >
                Importer une autre fiche
              </button>
            }
          />
          <div className="flex flex-wrap justify-end gap-3">
            <Link
              to="/options"
              className="inline-flex items-center gap-2 rounded-full border border-accent/40 px-6 py-3 text-sm font-medium text-accent transition hover:bg-accent-subtle/40"
            >
              Choisir les options →
            </Link>
            <Link
              to="/generate"
              className="inline-flex items-center gap-2 rounded-full bg-accent px-6 py-3 text-sm font-medium text-white transition hover:bg-accent-hover"
            >
              Générer la fiche →
            </Link>
          </div>
        </div>
      ) : null}
    </section>
  )
}
