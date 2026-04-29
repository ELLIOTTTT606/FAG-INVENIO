import { useMemo, useState } from 'react'
import { DEPARTMENTS, filterDepartments, groupByRegion, type Department } from '../data/departments'

interface Props {
  selected: string | null
  onSelect: (code: string) => void
}

export function DepartmentPicker({ selected, onSelect }: Props) {
  const [query, setQuery] = useState('')
  const filtered = useMemo(() => filterDepartments(query), [query])
  const grouped = useMemo(() => {
    if (filtered.length === DEPARTMENTS.length) return groupByRegion()
    const map = new Map<string, Department[]>()
    for (const dep of filtered) {
      const list = map.get(dep.region) ?? []
      list.push(dep)
      map.set(dep.region, list)
    }
    return map
  }, [filtered])

  return (
    <div className="space-y-4">
      <label className="block text-sm font-medium" htmlFor="department-search">
        Rechercher un département
      </label>
      <input
        id="department-search"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder="69, Rhône, Hauts-de-Seine..."
        className="w-full rounded-xl border border-ink-muted/30 bg-transparent px-4 py-2 text-sm focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
      />

      <div className="max-h-[460px] space-y-4 overflow-y-auto pr-2">
        {Array.from(grouped.entries()).map(([region, deps]) => (
          <section key={region}>
            <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-ink-muted">
              {region}
            </h4>
            <ul className="grid grid-cols-3 gap-2 sm:grid-cols-4">
              {deps.map((dep) => {
                const isSelected = dep.code === selected
                return (
                  <li key={dep.code}>
                    <button
                      type="button"
                      onClick={() => onSelect(dep.code)}
                      title={dep.name}
                      aria-pressed={isSelected}
                      className={[
                        'w-full rounded-lg border px-3 py-2 text-left text-sm transition-all duration-300 ease-smooth',
                        isSelected
                          ? 'border-accent bg-accent text-white shadow-sm'
                          : 'border-ink-muted/15 hover:border-accent hover:bg-accent-subtle/40',
                      ].join(' ')}
                    >
                      <span className="font-mono text-xs opacity-75">{dep.code}</span>
                      <span className="ml-2 truncate">{dep.name}</span>
                    </button>
                  </li>
                )
              })}
            </ul>
          </section>
        ))}
        {grouped.size === 0 ? (
          <p className="py-8 text-center text-sm italic text-ink-muted">
            Aucun département ne correspond à « {query} ».
          </p>
        ) : null}
      </div>
    </div>
  )
}
