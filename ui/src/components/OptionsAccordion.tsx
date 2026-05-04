import { useState } from 'react'
import type { CatalogOption } from '../api/options'
import { OptionRow } from './OptionRow'

interface Props {
  category: string
  options: CatalogOption[]
  selected: ReadonlySet<string>
  onToggle: (code: string) => void
  defaultOpen?: boolean
}

export function OptionsAccordion({
  category,
  options,
  selected,
  onToggle,
  defaultOpen = true,
}: Props) {
  const [open, setOpen] = useState(defaultOpen)
  const selectedCount = options.reduce((acc, opt) => (selected.has(opt.code) ? acc + 1 : acc), 0)

  return (
    <section className="rounded-2xl border border-ink-muted/15">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left"
      >
        <h3 className="text-sm font-semibold uppercase tracking-wider">{category}</h3>
        <span className="flex items-center gap-3 text-xs text-ink-muted">
          {selectedCount > 0 ? (
            <span className="rounded-full bg-accent px-2 py-0.5 text-white">
              {selectedCount} sélectionnée{selectedCount > 1 ? 's' : ''}
            </span>
          ) : (
            <span>{options.length} option{options.length > 1 ? 's' : ''}</span>
          )}
          <span aria-hidden className="transition-transform duration-300">
            {open ? '▾' : '▸'}
          </span>
        </span>
      </button>
      {open ? (
        <ul className="space-y-2 border-t border-ink-muted/10 p-4">
          {options.map((option) => (
            <OptionRow
              key={option.code}
              option={option}
              selected={selected.has(option.code)}
              onToggle={onToggle}
            />
          ))}
        </ul>
      ) : null}
    </section>
  )
}
