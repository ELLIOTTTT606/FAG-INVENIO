import { useMemo } from 'react'
import { DROM_LAYOUT, METROPOLE_CENTROIDS } from '../data/departmentCentroids'
import { findDepartment } from '../data/departments'

interface Props {
  selected: string | null
  onSelect: (code: string) => void
}

const VIEW = {
  width: 720,
  height: 600,
  lonMin: -5.5,
  lonMax: 9.5,
  latMin: 41,
  latMax: 51.5,
} as const

const RADIUS = 12
const DROM_RADIUS = 18

interface Projected {
  code: string
  cx: number
  cy: number
}

function projectMetropole(): Projected[] {
  const lonRange = VIEW.lonMax - VIEW.lonMin
  const latRange = VIEW.latMax - VIEW.latMin
  return METROPOLE_CENTROIDS.map((entry) => {
    const x = ((entry.lon - VIEW.lonMin) / lonRange) * VIEW.width + (entry.dx ?? 0)
    const y = ((VIEW.latMax - entry.lat) / latRange) * VIEW.height + (entry.dy ?? 0)
    return { code: entry.code, cx: x, cy: y }
  })
}

export function FranceMap({ selected, onSelect }: Props) {
  const metropole = useMemo(projectMetropole, [])

  return (
    <figure
      className="rounded-2xl border border-ink-muted/15 bg-surface-light p-4"
      data-testid="france-map"
    >
      <figcaption className="mb-3 text-xs uppercase tracking-wider text-ink-muted">
        Carte interactive
      </figcaption>
      <svg
        role="img"
        aria-label="Carte des départements français"
        viewBox={`-10 -10 ${VIEW.width + 20} ${VIEW.height + 240}`}
        className="h-auto w-full select-none"
      >
        {/* Background outline (rough metropole frame) */}
        <rect
          x={-4}
          y={-4}
          width={VIEW.width + 8}
          height={VIEW.height + 8}
          rx={20}
          ry={20}
          className="fill-accent-subtle/30 stroke-ink-muted/15"
        />
        <text
          x={VIEW.width / 2}
          y={28}
          textAnchor="middle"
          className="fill-ink-muted text-[14px] uppercase tracking-[0.18em]"
        >
          Métropole
        </text>

        {metropole.map((entry) => (
          <Marker
            key={entry.code}
            code={entry.code}
            cx={entry.cx}
            cy={entry.cy}
            radius={RADIUS}
            selected={entry.code === selected}
            onSelect={onSelect}
          />
        ))}

        {/* DROM inset */}
        <g transform={`translate(0, ${VIEW.height + 30})`}>
          <rect
            x={-4}
            y={-4}
            width={220}
            height={120}
            rx={16}
            ry={16}
            className="fill-accent-subtle/20 stroke-ink-muted/15"
          />
          <text
            x={108}
            y={20}
            textAnchor="middle"
            className="fill-ink-muted text-[12px] uppercase tracking-[0.18em]"
          >
            Outre-mer
          </text>
          {DROM_LAYOUT.map((entry) => (
            <Marker
              key={entry.code}
              code={entry.code}
              cx={entry.cx}
              cy={entry.cy + 20}
              radius={DROM_RADIUS}
              selected={entry.code === selected}
              onSelect={onSelect}
            />
          ))}
        </g>
      </svg>
    </figure>
  )
}

interface MarkerProps {
  code: string
  cx: number
  cy: number
  radius: number
  selected: boolean
  onSelect: (code: string) => void
}

function Marker({ code, cx, cy, radius, selected, onSelect }: MarkerProps) {
  const dep = findDepartment(code)
  const ariaLabel = dep ? `${code} · ${dep.name}` : code
  return (
    <g
      role="button"
      tabIndex={0}
      aria-label={ariaLabel}
      aria-pressed={selected}
      data-code={code}
      data-testid={`france-map-${code}`}
      className="cursor-pointer focus:outline-none"
      onClick={() => onSelect(code)}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault()
          onSelect(code)
        }
      }}
    >
      <title>{ariaLabel}</title>
      <circle
        cx={cx}
        cy={cy}
        r={radius}
        className={[
          'transition-all duration-300 ease-smooth',
          selected
            ? 'fill-accent stroke-accent-hover'
            : 'fill-surface-light stroke-ink-muted/40 hover:fill-accent-subtle/70 hover:stroke-accent',
        ].join(' ')}
        strokeWidth={selected ? 2 : 1}
      />
      <text
        x={cx}
        y={cy + 3.5}
        textAnchor="middle"
        className={[
          'pointer-events-none text-[10px] font-semibold',
          selected ? 'fill-white' : 'fill-ink-light',
        ].join(' ')}
      >
        {code}
      </text>
    </g>
  )
}
