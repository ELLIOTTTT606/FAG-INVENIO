import { useState } from 'react'
import type { CatalogOption } from '../api/options'

interface Props {
  option: CatalogOption
  selected: boolean
  onToggle: (code: string) => void
}

export function OptionRow({ option, selected, onToggle }: Props) {
  const [expanded, setExpanded] = useState(false)
  const hasDetails = Boolean(option.description || option.tips)
  const disabled = !option.available

  return (
    <li
      className={[
        'rounded-xl border transition-colors duration-300 ease-smooth',
        selected ? 'border-accent bg-accent-subtle/40' : 'border-ink-muted/15',
        disabled ? 'opacity-60' : '',
      ].join(' ')}
    >
      <div className="flex items-start gap-3 p-4">
        <input
          id={`option-${option.code}`}
          type="checkbox"
          checked={selected}
          disabled={disabled}
          onChange={() => onToggle(option.code)}
          className="mt-1 h-4 w-4 cursor-pointer accent-accent"
        />
        <div className="flex-1">
          <label
            htmlFor={`option-${option.code}`}
            className="flex cursor-pointer items-baseline gap-3 text-sm font-medium"
          >
            <span>{option.label}</span>
            <code className="text-xs font-normal text-ink-muted">{option.code}</code>
            {disabled ? (
              <span className="text-xs italic text-warn">indisponible</span>
            ) : null}
          </label>
          {hasDetails ? (
            <button
              type="button"
              onClick={() => setExpanded((value) => !value)}
              aria-expanded={expanded}
              className="mt-1 text-xs text-accent hover:text-accent-hover"
            >
              {expanded ? 'Masquer les détails' : 'Voir les détails'}
            </button>
          ) : null}
          {expanded ? (
            <div className="mt-2 space-y-1 text-sm text-ink-muted">
              {option.description ? <p>{option.description}</p> : null}
              {option.tips ? (
                <p className="rounded-md bg-accent-subtle/40 px-3 py-2 text-xs">
                  💡 {option.tips}
                </p>
              ) : null}
              {option.price_eur != null ? (
                <p className="text-xs">Prix indicatif : {option.price_eur.toFixed(2)} €</p>
              ) : null}
            </div>
          ) : null}
        </div>
      </div>
    </li>
  )
}
