import type { CanonicalRecord, Warning } from '../api/types'

interface Props {
  record: CanonicalRecord
  warnings: Warning[]
}

interface Field {
  label: string
  value: number | string | boolean | null | undefined
  unit?: string
}

function fmt(value: Field['value'], unit?: string): { text: string; ok: boolean } {
  if (value === null || value === undefined || value === '') {
    return { text: 'Donnée non disponible', ok: false }
  }
  if (typeof value === 'boolean') {
    return { text: value ? 'Oui' : 'Non', ok: true }
  }
  return { text: unit ? `${value} ${unit}` : String(value), ok: true }
}

function StatusIcon({ ok }: { ok: boolean }) {
  return (
    <span
      aria-label={ok ? 'extrait' : 'manquant'}
      className={`inline-flex h-5 w-5 items-center justify-center rounded-full text-xs ${
        ok ? 'bg-success/15 text-success' : 'bg-warn/15 text-warn'
      }`}
    >
      {ok ? '✓' : '!'}
    </span>
  )
}

function FieldRow({ label, value, unit }: Field) {
  const { text, ok } = fmt(value, unit)
  return (
    <li className="flex items-center justify-between gap-4 border-b border-ink-muted/10 py-2 last:border-b-0">
      <span className="flex items-center gap-3 text-sm text-ink-muted">
        <StatusIcon ok={ok} />
        {label}
      </span>
      <span className={`text-sm font-medium ${ok ? '' : 'text-ink-muted italic'}`}>{text}</span>
    </li>
  )
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <article className="rounded-2xl border border-ink-muted/15 p-6">
      <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-ink-muted">{title}</h3>
      <ul className="space-y-1">{children}</ul>
    </article>
  )
}

export function ExtractionSummary({ record, warnings }: Props) {
  const cooling = record.performance.cooling ?? {}
  const heating = record.performance.heating ?? {}
  const general = record.general ?? {}
  const isPac = record.family === 'PAC'

  return (
    <section className="space-y-6">
      <header className="flex flex-wrap items-baseline gap-x-6 gap-y-2">
        <span className="rounded-full bg-accent-subtle px-3 py-1 text-xs font-semibold uppercase tracking-wider text-accent">
          {record.family}
        </span>
        <h2 className="text-2xl font-semibold">
          {record.model || '?'} <span className="text-ink-muted">·</span> {record.size || '?'}
          <span className="text-ink-muted"> · </span>
          {record.type || '?'}
        </h2>
        {record.designation_code ? (
          <code className="text-xs text-ink-muted">{record.designation_code}</code>
        ) : null}
      </header>

      {warnings.length > 0 ? (
        <div
          role="alert"
          className="rounded-xl border border-warn/30 bg-warn/5 p-4 text-sm text-warn"
        >
          <p className="font-medium">{warnings.length} avertissement(s) lors de l'extraction</p>
          <ul className="mt-2 space-y-1 text-warn/90">
            {warnings.slice(0, 5).map((w, i) => (
              <li key={i} className="text-xs">
                · <strong>{w.code}</strong> {w.field ? `(${w.field})` : ''} — {w.message}
              </li>
            ))}
            {warnings.length > 5 ? (
              <li className="text-xs italic">+ {warnings.length - 5} autre(s)…</li>
            ) : null}
          </ul>
        </div>
      ) : null}

      <div className="grid gap-6 md:grid-cols-2">
        <Card title="Refroidissement">
          <FieldRow label="Puissance frigorifique" value={cooling.power_kW} unit="kW" />
          <FieldRow label="Débit eau" value={cooling.water_flow_lph} unit="l/h" />
          <FieldRow label="Perte de charge" value={cooling.pressure_drop_kPa} unit="kPa" />
          <FieldRow label="EER" value={cooling.eer} />
          <FieldRow label="SEER" value={cooling.seer} />
        </Card>

        {isPac ? (
          <Card title="Chauffage">
            <FieldRow label="Puissance calorifique" value={heating.power_kW} unit="kW" />
            <FieldRow label="Débit eau" value={heating.water_flow_lph} unit="l/h" />
            <FieldRow label="Perte de charge" value={heating.pressure_drop_kPa} unit="kPa" />
            <FieldRow label="COP" value={heating.cop} />
            <FieldRow label="SCOP" value={heating.scop} />
            <FieldRow label="Classe saisonnière" value={heating.seasonal_class} />
          </Card>
        ) : (
          <Card title="Chauffage">
            <li className="py-4 text-sm italic text-ink-muted">
              Non applicable pour un groupe d'eau glacée.
            </li>
          </Card>
        )}

        <Card title="Données générales">
          <FieldRow label="Courant max (FLA)" value={general.max_current_A} unit="A" />
          <FieldRow label="Puissance acoustique Lw" value={general.sound_power_lw_dBA} unit="dB(A)" />
          <FieldRow label="Réfrigérant" value={general.refrigerant} />
          <FieldRow label="GWP" value={general.gwp} />
          <FieldRow label="Poids" value={general.weight_kg} unit="kg" />
          <FieldRow label="Alimentation" value={general.supply} />
        </Card>

        <Card title="Options détectées (designation)">
          {record.options.length === 0 ? (
            <li className="py-4 text-sm italic text-ink-muted">
              Aucune option non-zéro détectée dans la chaîne de désignation.
            </li>
          ) : (
            record.options.slice(0, 8).map((option) => (
              <li
                key={`${option.block}-${option.position}-${option.character}`}
                className="flex items-center justify-between gap-4 border-b border-ink-muted/10 py-2 last:border-b-0"
              >
                <span className="flex items-center gap-3 text-sm text-ink-muted">
                  <StatusIcon ok={Boolean(option.decoded)} />
                  <code className="text-xs">{option.code}</code>
                  <span>{option.label}</span>
                </span>
                <span className="text-xs text-ink-muted">
                  block {option.block} · pos {option.position} · '{option.character}'
                </span>
              </li>
            ))
          )}
          {record.options.length > 8 ? (
            <li className="pt-2 text-xs italic text-ink-muted">
              + {record.options.length - 8} option(s) supplémentaire(s)…
            </li>
          ) : null}
        </Card>
      </div>
    </section>
  )
}
