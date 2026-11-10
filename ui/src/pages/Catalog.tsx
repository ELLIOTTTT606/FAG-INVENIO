import { useCallback, useEffect, useState } from 'react'
import { ApiError } from '../api/client'
import { getFamilySizes, listFamilies, type Family, type Size } from '../api/catalog'

interface CatalogEntry extends Family {
  sizes: Size[]
}
interface CatalogSnapshot {
  updated_at: string
  families: CatalogEntry[]
}

const CACHE_KEY = 'galletti_catalog_v1'

function loadCache(): CatalogSnapshot | null {
  try {
    const raw = localStorage.getItem(CACHE_KEY)
    return raw ? (JSON.parse(raw) as CatalogSnapshot) : null
  } catch {
    return null
  }
}
function saveCache(snap: CatalogSnapshot): void {
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify(snap))
  } catch {
    /* quota / private mode : on ignore */
  }
}

type Progress = { done: number; total: number; label: string } | null

export default function Catalog() {
  const [snap, setSnap] = useState<CatalogSnapshot | null>(null)
  const [progress, setProgress] = useState<Progress>(null)
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState('')

  useEffect(() => {
    setSnap(loadCache())
  }, [])

  const refresh = useCallback(async () => {
    setError(null)
    setProgress({ done: 0, total: 1, label: 'Chargement des familles…' })
    try {
      const families = await listFamilies()
      const entries: CatalogEntry[] = []
      for (let i = 0; i < families.length; i++) {
        const f = families[i]
        setProgress({ done: i, total: families.length, label: `Tailles : ${f.name}` })
        let sizes: Size[] = []
        try {
          sizes = await getFamilySizes(f.code)
        } catch {
          sizes = [] // une famille non calculable ne bloque pas le reste
        }
        entries.push({ ...f, sizes })
      }
      const next: CatalogSnapshot = {
        updated_at: new Date().toISOString(),
        families: entries,
      }
      saveCache(next)
      setSnap(next)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur réseau catalogue.')
    } finally {
      setProgress(null)
    }
  }, [])

  const families = snap?.families ?? []
  const q = query.trim().toLowerCase()
  const filtered = q
    ? families.filter(
        (f) =>
          f.name.toLowerCase().includes(q) ||
          f.sizes.some((s) => s.model.toLowerCase().includes(q)),
      )
    : families
  const totalSizes = families.reduce((n, f) => n + f.sizes.length, 0)

  return (
    <section className="space-y-6">
      <div>
        <p className="text-sm uppercase tracking-widest text-accent">Catalogue</p>
        <h1 className="mt-2 text-3xl font-semibold md:text-4xl">Catalogue produits GALLETTI</h1>
        <p className="mt-3 max-w-2xl text-ink-muted">
          L'ensemble des gammes et de leurs tailles, récupéré depuis GALLETTI.
          Cliquez « Actualiser » pour (re)construire le catalogue avec les derniers
          prix et gammes. Il est gardé en cache dans votre navigateur.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-4">
        <button
          onClick={() => void refresh()}
          disabled={progress !== null}
          className="rounded-lg bg-accent px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-40"
        >
          {progress ? 'Actualisation…' : 'Actualiser le catalogue'}
        </button>
        {snap && (
          <span className="text-sm text-ink-muted">
            {families.length} gammes · {totalSizes} tailles · maj{' '}
            {new Date(snap.updated_at).toLocaleString('fr-FR')}
          </span>
        )}
      </div>

      {progress && (
        <div className="space-y-2">
          <div className="h-2 w-full overflow-hidden rounded-full bg-white/10">
            <div
              className="h-full bg-accent transition-all"
              style={{ width: `${Math.round((progress.done / progress.total) * 100)}%` }}
            />
          </div>
          <p className="text-sm text-ink-muted">
            {progress.label} ({progress.done}/{progress.total})
          </p>
        </div>
      )}

      {error && (
        <div className="rounded-xl border border-red-400/40 bg-red-400/10 p-5 text-sm">
          <p className="font-semibold">Erreur</p>
          <p className="mt-2 text-ink-muted">{error}</p>
        </div>
      )}

      {!snap && !progress && (
        <p className="text-ink-muted">
          Aucun catalogue en cache. Cliquez « Actualiser le catalogue » pour le construire.
        </p>
      )}

      {snap && (
        <>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Filtrer par gamme ou modèle…"
            className="w-full max-w-md rounded-lg border border-ink-muted/20 bg-black/10 px-4 py-2 text-sm outline-none focus:border-accent"
          />
          <div className="space-y-4">
            {filtered.map((f) => (
              <FamilyBlock key={f.code} entry={f} />
            ))}
          </div>
        </>
      )}
    </section>
  )
}

function FamilyBlock({ entry }: { entry: CatalogEntry }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="overflow-hidden rounded-xl border border-ink-muted/15">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between px-4 py-3 text-left hover:bg-white/5"
      >
        <span className="font-semibold">{entry.name}</span>
        <span className="text-sm text-ink-muted">
          {entry.sizes.length} taille(s) {open ? '▲' : '▼'}
        </span>
      </button>
      {open && entry.sizes.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-white/5 text-xs uppercase tracking-wider text-ink-muted">
              <tr>
                <th className="px-4 py-2">Modèle</th>
                <th className="px-4 py-2 text-right">Froid (kW)</th>
                <th className="px-4 py-2 text-right">Chaud (kW)</th>
                <th className="px-4 py-2 text-right">EER</th>
                <th className="px-4 py-2 text-right">COP</th>
              </tr>
            </thead>
            <tbody>
              {entry.sizes.map((s) => (
                <tr key={s.model} className="border-t border-ink-muted/10">
                  <td className="px-4 py-2 font-mono">{s.model}</td>
                  <td className="px-4 py-2 text-right">{s.cooling_power_kw ?? '—'}</td>
                  <td className="px-4 py-2 text-right">{s.heating_power_kw ?? '—'}</td>
                  <td className="px-4 py-2 text-right">{s.eer ?? '—'}</td>
                  <td className="px-4 py-2 text-right">{s.cop ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {open && entry.sizes.length === 0 && (
        <p className="px-4 py-3 text-sm text-ink-muted">
          Aucune taille récupérée (gamme non calculable au point standard).
        </p>
      )}
    </div>
  )
}
