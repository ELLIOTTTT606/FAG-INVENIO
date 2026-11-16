import type { CanonicalRecord } from '../api/types'
import { useCountUp } from '../lib/motion'

type Tone = 'cold' | 'warm' | 'neutral'

interface Figure {
  label: string
  value: number
  unit?: string
  tone: Tone
}

const TONE_DOT: Record<Tone, string> = {
  cold: 'bg-cold',
  warm: 'bg-warm',
  neutral: 'bg-ink-muted/40',
}

function decimalsOf(value: number): number {
  const [, fraction = ''] = String(value).split('.')
  return Math.min(fraction.length, 2)
}

function FigureTile({ label, value, unit, tone }: Figure) {
  const decimals = decimalsOf(value)
  const shown = useCountUp(value)
  return (
    <li className="lift flex min-w-0 flex-col justify-between gap-8 rounded-3xl bg-white p-6 shadow-[0_1px_2px_rgb(0_0_0/0.03),0_8px_24px_-12px_rgb(0_0_0/0.1)]">
      <span className="flex items-center gap-2 text-sm text-ink-muted">
        <span aria-hidden className={`h-2 w-2 rounded-full ${TONE_DOT[tone]}`} />
        {label}
      </span>
      <span className="font-display text-5xl font-bold tracking-tight tabular-nums">
        {shown.toLocaleString('fr-FR', {
          minimumFractionDigits: decimals,
          maximumFractionDigits: decimals,
        })}
        {unit ? <span className="ml-1.5 font-sans text-base font-medium text-ink-muted">{unit}</span> : null}
      </span>
    </li>
  )
}

/** Picks the handful of numbers a selector looks at first. */
function figuresOf(record: CanonicalRecord): Figure[] {
  const cooling = record.performance.cooling ?? {}
  const heating = record.performance.heating ?? {}
  const sound = record.general?.sound_power_lw_dBA
  const candidates: Array<Omit<Figure, 'value'> & { value: unknown }> = [
    { label: 'Puissance frigorifique', value: cooling.power_kW, unit: 'kW', tone: 'cold' },
    { label: 'Puissance calorifique', value: heating.power_kW, unit: 'kW', tone: 'warm' },
    record.family === 'PAC'
      ? { label: 'COP', value: heating.cop, tone: 'warm' }
      : { label: 'EER', value: cooling.eer, tone: 'cold' },
    { label: 'Puissance acoustique', value: sound, unit: 'dB(A)', tone: 'neutral' },
  ]
  return candidates.filter((c): c is Figure => typeof c.value === 'number' && Number.isFinite(c.value))
}

/**
 * Headline numbers of the imported machine. Blue marks cooling, orange
 * heating: colour is only ever used for that.
 */
export function KeyFigures({ record }: { record: CanonicalRecord }) {
  const figures = figuresOf(record)
  if (figures.length === 0) return null
  return (
    <ul
      className="stagger grid gap-5 sm:grid-cols-2 lg:grid-cols-4"
      aria-label="Chiffres clés"
      data-testid="key-figures"
    >
      {figures.map((figure) => (
        <FigureTile key={figure.label} {...figure} />
      ))}
    </ul>
  )
}
