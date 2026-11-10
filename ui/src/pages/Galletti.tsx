import { useCallback, useEffect, useState } from 'react'
import { ApiError } from '../api/client'
import {
  getGallettiProject,
  listGallettiProjects,
  type GallettiArticle,
  type GallettiProject,
} from '../api/galletti'

type Status =
  | { kind: 'loading' }
  | { kind: 'ready'; projects: GallettiProject[] }
  | { kind: 'not-configured'; message: string }
  | { kind: 'error'; message: string }

export default function Galletti() {
  const [status, setStatus] = useState<Status>({ kind: 'loading' })
  const [openId, setOpenId] = useState<number | null>(null)
  const [articles, setArticles] = useState<Record<number, GallettiArticle[]>>({})
  const [articlesError, setArticlesError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setStatus({ kind: 'loading' })
    try {
      const projects = await listGallettiProjects()
      setStatus({ kind: 'ready', projects })
    } catch (err) {
      if (err instanceof ApiError && err.status === 503) {
        setStatus({ kind: 'not-configured', message: err.message })
      } else {
        const message = err instanceof ApiError ? err.message : 'Erreur réseau GALLETTI.'
        setStatus({ kind: 'error', message })
      }
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const toggle = useCallback(
    async (id: number) => {
      if (openId === id) {
        setOpenId(null)
        return
      }
      setOpenId(id)
      setArticlesError(null)
      if (!articles[id]) {
        try {
          const detail = await getGallettiProject(id)
          setArticles((prev) => ({ ...prev, [id]: detail.articles }))
        } catch (err) {
          setArticlesError(err instanceof ApiError ? err.message : 'Erreur chargement projet.')
        }
      }
    },
    [openId, articles],
  )

  return (
    <section className="space-y-8">
      <div>
        <p className="text-sm uppercase tracking-widest text-accent">Projets GALLETTI</p>
        <h1 className="mt-2 text-3xl font-semibold md:text-4xl">Vos sélections GALLETTI</h1>
        <p className="mt-3 max-w-2xl text-ink-muted">
          Retrouvez ici les projets de votre compte GALLETTI Quality Selector.
          Cliquez un projet pour voir ses articles, puis générez la fiche INVENIO.
        </p>
      </div>

      {status.kind === 'loading' && <p className="text-ink-muted">Chargement des projets…</p>}

      {status.kind === 'not-configured' && (
        <div className="rounded-xl border border-amber-400/40 bg-amber-400/10 p-5">
          <p className="font-semibold">Connexion GALLETTI non configurée</p>
          <p className="mt-2 text-sm text-ink-muted">{status.message}</p>
          <p className="mt-3 text-sm text-ink-muted">
            Ajoutez votre cookie de session dans la variable d'environnement{' '}
            <code className="rounded bg-black/20 px-1">GALLETTI_COOKIE</code> pour activer
            la liste des projets.
          </p>
        </div>
      )}

      {status.kind === 'error' && (
        <div className="rounded-xl border border-red-400/40 bg-red-400/10 p-5">
          <p className="font-semibold">Erreur</p>
          <p className="mt-2 text-sm text-ink-muted">{status.message}</p>
          <button
            onClick={() => void load()}
            className="mt-3 rounded-lg border border-ink-muted/30 px-4 py-2 text-sm hover:bg-white/5"
          >
            Réessayer
          </button>
        </div>
      )}

      {status.kind === 'ready' && status.projects.length === 0 && (
        <p className="text-ink-muted">Aucun projet trouvé sur votre compte GALLETTI.</p>
      )}

      {status.kind === 'ready' && status.projects.length > 0 && (
        <div className="overflow-hidden rounded-xl border border-ink-muted/15">
          <table className="w-full text-left text-sm">
            <thead className="bg-white/5 text-xs uppercase tracking-wider text-ink-muted">
              <tr>
                <th className="px-4 py-3">N° projet</th>
                <th className="px-4 py-3">Date</th>
                <th className="px-4 py-3">Nom du projet</th>
                <th className="px-4 py-3">Utilisateur</th>
                <th className="px-4 py-3 text-right">Total</th>
              </tr>
            </thead>
            <tbody>
              {status.projects.map((p) => (
                <ProjectRow
                  key={p.id}
                  project={p}
                  open={openId === p.id}
                  articles={articles[p.id]}
                  articlesError={openId === p.id ? articlesError : null}
                  onToggle={() => void toggle(p.id)}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

function fmtPrice(v: number | null): string {
  if (v === null) return '—'
  return v.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })
}

interface RowProps {
  project: GallettiProject
  open: boolean
  articles: GallettiArticle[] | undefined
  articlesError: string | null
  onToggle: () => void
}

function ProjectRow({ project, open, articles, articlesError, onToggle }: RowProps) {
  return (
    <>
      <tr
        onClick={onToggle}
        className="cursor-pointer border-t border-ink-muted/10 hover:bg-white/5"
      >
        <td className="px-4 py-3 font-mono">{project.numero}</td>
        <td className="px-4 py-3">{project.date}</td>
        <td className="px-4 py-3">{project.nom}</td>
        <td className="px-4 py-3 text-ink-muted">{project.utilisateur}</td>
        <td className="px-4 py-3 text-right">{project.prix_total}</td>
      </tr>
      {open && (
        <tr className="border-t border-ink-muted/10 bg-black/10">
          <td colSpan={5} className="px-4 py-4">
            {articlesError && <p className="text-sm text-red-400">{articlesError}</p>}
            {!articlesError && !articles && (
              <p className="text-sm text-ink-muted">Chargement des articles…</p>
            )}
            {articles && articles.length === 0 && (
              <p className="text-sm text-ink-muted">Aucun article dans ce projet.</p>
            )}
            {articles && articles.length > 0 && (
              <ul className="space-y-2">
                {articles
                  .filter((a) => a.model)
                  .map((a, i) => (
                    <li
                      key={`${a.model}-${i}`}
                      className="flex items-center justify-between rounded-lg bg-white/5 px-3 py-2 text-sm"
                    >
                      <span>
                        <span className="font-mono font-semibold">{a.model}</span>
                        <span className="ml-2 text-ink-muted">{a.family}</span>
                        {a.option_codes.length > 0 && (
                          <span className="ml-2 text-xs text-ink-muted">
                            · {a.option_codes.length} option(s)
                          </span>
                        )}
                      </span>
                      <span className="text-ink-muted">{fmtPrice(a.price)}</span>
                    </li>
                  ))}
              </ul>
            )}
          </td>
        </tr>
      )}
    </>
  )
}
