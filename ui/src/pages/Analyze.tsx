import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError } from '../api/client'
import {
  analyzeFile,
  analyzeText,
  getAnalyzeStatus,
  type AnalysisResult,
} from '../api/analyze'

type State =
  | { kind: 'idle' }
  | { kind: 'running' }
  | { kind: 'done'; result: AnalysisResult }
  | { kind: 'error'; message: string }

export default function Analyze() {
  const [text, setText] = useState('')
  const [state, setState] = useState<State>({ kind: 'idle' })
  const [configured, setConfigured] = useState<boolean | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    getAnalyzeStatus()
      .then((s) => setConfigured(s.configured))
      .catch(() => setConfigured(null))
  }, [])

  const run = useCallback(async (fn: () => Promise<AnalysisResult>) => {
    setState({ kind: 'running' })
    try {
      setState({ kind: 'done', result: await fn() })
    } catch (err) {
      const message = err instanceof ApiError ? err.message : 'Erreur réseau.'
      setState({ kind: 'error', message })
    }
  }, [])

  return (
    <section className="space-y-8">
      <div>
        <p className="text-sm uppercase tracking-widest text-accent">Analyse de demande</p>
        <h1 className="mt-2 text-3xl font-semibold md:text-4xl">Analyser un CCTP / un mail</h1>
        <p className="mt-3 max-w-2xl text-ink-muted">
          Collez le texte d'un mail client ou déposez un CCTP (TXT, PDF, DOCX).
          INVENIO en extrait les conditions, puissances, options et propose une
          préconisation produit GALLETTI.
        </p>
      </div>

      {configured === false && (
        <div className="rounded-xl border border-amber-400/40 bg-amber-400/10 p-5 text-sm">
          <p className="font-semibold">Moteur d'analyse non configuré</p>
          <p className="mt-2 text-ink-muted">
            Définissez <code className="rounded bg-black/20 px-1">LLM_BASE_URL</code>,{' '}
            <code className="rounded bg-black/20 px-1">LLM_MODEL</code> et{' '}
            <code className="rounded bg-black/20 px-1">LLM_API_KEY</code> (ex. Groq, gratuit)
            pour activer l'analyse.
          </p>
        </div>
      )}

      <div className="space-y-3">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Collez ici le mail du commercial ou un extrait de CCTP…"
          className="h-56 w-full rounded-xl border border-ink-muted/20 bg-black/10 p-4 text-sm outline-none focus:border-accent"
        />
        <div className="flex flex-wrap items-center gap-3">
          <button
            disabled={state.kind === 'running' || text.trim().length === 0}
            onClick={() => void run(() => analyzeText(text))}
            className="rounded-lg bg-accent px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-40"
          >
            {state.kind === 'running' ? 'Analyse en cours…' : 'Analyser le texte'}
          </button>
          <span className="text-sm text-ink-muted">ou</span>
          <button
            disabled={state.kind === 'running'}
            onClick={() => fileRef.current?.click()}
            className="rounded-lg border border-ink-muted/30 px-5 py-2.5 text-sm hover:bg-white/5 disabled:opacity-40"
          >
            Déposer un fichier (TXT/PDF/DOCX)
          </button>
          <input
            ref={fileRef}
            type="file"
            accept=".txt,.md,.pdf,.docx"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0]
              if (f) void run(() => analyzeFile(f))
              e.target.value = ''
            }}
          />
        </div>
      </div>

      {state.kind === 'error' && (
        <div className="rounded-xl border border-red-400/40 bg-red-400/10 p-5 text-sm">
          <p className="font-semibold">Erreur</p>
          <p className="mt-2 text-ink-muted">{state.message}</p>
        </div>
      )}

      {state.kind === 'done' && <AnalysisView result={state.result} />}
    </section>
  )
}

function AnalysisView({ result }: { result: AnalysisResult }) {
  const r = result as Record<string, unknown>
  const obj = (v: unknown): Record<string, unknown> =>
    v && typeof v === 'object' ? (v as Record<string, unknown>) : {}
  const conclusion = obj(r.conclusion)
  const propositions = Array.isArray(conclusion.propositions)
    ? (conclusion.propositions as Record<string, unknown>[])
    : []
  const questions = Array.isArray(conclusion.questions) ? conclusion.questions : []
  return (
    <div className="space-y-6">
      {Boolean(r.resume) && (
        <div className="rounded-xl border border-accent/30 bg-accent/5 p-4">
          <p className="text-xs uppercase tracking-wider text-accent">Résumé</p>
          <p className="mt-1">{String(r.resume)}</p>
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        <Card title="Conditions">{renderKV(r.conditions)}</Card>
        <Card title="Puissances attendues">{renderKV(r.puissances)}</Card>
        <Card title="Type préconisé">{renderKV(r.type_preconise)}</Card>
        <Card title="Implantation / fluide">
          <KV label="Implantation" value={r.implantation} />
          <KV label="Fluide" value={r.fluide} />
        </Card>
      </div>

      {Array.isArray(r.options) && r.options.length > 0 && (
        <Card title="Options / accessoires">
          <ul className="list-disc space-y-1 pl-5 text-sm">
            {r.options.map((o: unknown, i: number) => (
              <li key={i}>{String(o)}</li>
            ))}
          </ul>
        </Card>
      )}

      {r.conclusion != null && (
        <Card title="Conclusion / préconisation">
          {propositions.length > 0 && (
            <div className="space-y-3">
              {propositions.map((p, i) => (
                <div key={i} className="rounded-lg bg-white/5 p-3 text-sm">
                  <p className="font-semibold">{String(p.produit ?? `Proposition ${i + 1}`)}</p>
                  {p.avantages != null && (
                    <p className="mt-1 text-ink-muted">➕ {String(p.avantages)}</p>
                  )}
                  {p.inconvenients != null && (
                    <p className="mt-1 text-ink-muted">➖ {String(p.inconvenients)}</p>
                  )}
                </div>
              ))}
            </div>
          )}
          {conclusion.recommandation != null && (
            <p className="mt-3 text-sm">
              <span className="font-semibold">Recommandation : </span>
              {String(conclusion.recommandation)}
            </p>
          )}
          {questions.length > 0 && (
            <div className="mt-3 text-sm">
              <p className="font-semibold">Questions à poser :</p>
              <ul className="list-disc space-y-1 pl-5 text-ink-muted">
                {questions.map((q, i) => (
                  <li key={i}>{String(q)}</li>
                ))}
              </ul>
            </div>
          )}
        </Card>
      )}
    </div>
  )
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-ink-muted/15 p-4">
      <p className="text-xs uppercase tracking-wider text-ink-muted">{title}</p>
      <div className="mt-2 text-sm">{children}</div>
    </div>
  )
}

function KV({ label, value }: { label: string; value: unknown }) {
  if (value === null || value === undefined || value === '') return null
  return (
    <p className="flex gap-2">
      <span className="text-ink-muted">{label} :</span>
      <span>{String(value)}</span>
    </p>
  )
}

function renderKV(obj: unknown): React.ReactNode {
  if (!obj || typeof obj !== 'object') return <span className="text-ink-muted">—</span>
  const entries = Object.entries(obj as Record<string, unknown>).filter(
    ([, v]) => v !== null && v !== undefined && v !== '',
  )
  if (entries.length === 0) return <span className="text-ink-muted">—</span>
  return (
    <div className="space-y-1">
      {entries.map(([k, v]) => (
        <KV key={k} label={k.replace(/_/g, ' ')} value={v} />
      ))}
    </div>
  )
}
