import { useEffect, useState, useMemo }    from 'react'
import { useNavigate }                     from 'react-router-dom'
import { useTheme, C }                     from '../lib/theme'
import { loadMachine, loadProject, loadClient, loadOptions, saveOptions } from '../lib/sessionContext'
import { Reveal, PageTransition, MonoLabel, Spinner } from '../components/ui/atoms'
import { BottomBar }                       from '../components/layout/Navigation'

// ── Types API options ─────────────────────────────────────────────────────────
interface Option {
  code:        string
  label:       string
  category:    string
  description?: string
  tips?:        string
  price?:       number | null
}

interface OptionsResponse {
  model:   string
  type:    string
  size:    string
  options: Option[]
}

async function fetchOptions(model: string, type: string, size: string): Promise<OptionsResponse> {
  const params = new URLSearchParams({ model, type, size })
  const r = await fetch(`${import.meta.env.VITE_API_URL || ''}/options?${params}`)
  if (!r.ok) throw new Error(`Options API error ${r.status}`)
  return r.json()
}

// ─────────────────────────────────────────────────────────────────────────────
export default function Options() {
  const { theme: t }  = useTheme()
  const navigate      = useNavigate()
  const machine       = loadMachine()
  const project       = loadProject()
  const client        = loadClient()

  const [options,  setOptions]  = useState<Option[]>([])
  const [selected, setSelected] = useState<Set<string>>(new Set(loadOptions()))
  const [loading,  setLoading]  = useState(true)
  const [error,    setError]    = useState<string | null>(null)
  const [expanded, setExpanded] = useState<Set<string>>(new Set())

  // Charger le catalogue depuis Baserow
  useEffect(() => {
    if (!machine?.model) { setLoading(false); return }
    const type = `${machine.family === 'PAC' ? 'H' : 'C'}${machine.acoustic ?? 'S'}`
    const size = machine.size.padStart(3, '0')
    fetchOptions(machine.model, type, size)
      .then(data => setOptions(data.options ?? []))
      .catch(() => setError('Impossible de charger les options depuis Baserow.'))
      .finally(() => setLoading(false))
  }, [machine])

  // Grouper par catégorie
  const grouped = useMemo(() => {
    const map = new Map<string, Option[]>()
    for (const opt of options) {
      if (!map.has(opt.category)) map.set(opt.category, [])
      map.get(opt.category)!.push(opt)
    }
    return map
  }, [options])

  const toggleOption = (code: string) => {
    setSelected(prev => {
      const next = new Set(prev)
      if (next.has(code)) { next.delete(code) } else { next.add(code) }
      return next
    })
  }

  const toggleCategory = (cat: string) => {
    setExpanded(prev => {
      const next = new Set(prev)
      if (next.has(cat)) { next.delete(cat) } else { next.add(cat) }
      return next
    })
  }

  const handleNext = () => {
    saveOptions([...selected])
    navigate('/generate')
  }

  // ─────────────────────────────────────────────────────────────────────────
  return (
    <PageTransition pgKey="options">
      <main style={{ minHeight: '100vh', padding: '120px 48px 140px' }}>
        <div style={{ maxWidth: 1000, margin: '0 auto' }}>

          {/* ── En-tête ── */}
          <Reveal delay={50}>
            <MonoLabel style={{ marginBottom: 24 }}>
              <span style={{ width: 24, height: 1, background: t.muted }} />
              Étape 04 · Options &amp; accessoires
            </MonoLabel>
          </Reveal>

          <Reveal delay={120}>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 20, flexWrap: 'wrap', marginBottom: 8 }}>
              <h1
                style={{
                  fontSize:      'clamp(36px, 5vw, 64px)',
                  fontWeight:    700,
                  letterSpacing: '-0.03em',
                  lineHeight:    1,
                  color:         t.text,
                  margin:        0,
                }}
              >
                {project?.name || 'Options'}
              </h1>
              {project?.number && (
                <span
                  style={{
                    fontFamily:    "'JetBrains Mono', ui-monospace, monospace",
                    fontSize:      14, color: t.accent, fontWeight: 600,
                  }}
                >
                  {project.number}
                </span>
              )}
            </div>
          </Reveal>

          <Reveal delay={200}>
            <p style={{ fontSize: 15, color: t.dim, marginBottom: 48 }}>
              {machine
                ? `${machine.model} ${machine.size} — ${machine.family ?? ''} · ${client?.name ?? ''}`
                : ''}
            </p>
          </Reveal>

          {/* ── Compteur options sélectionnées ── */}
          {selected.size > 0 && (
            <Reveal delay={0}>
              <div
                style={{
                  display:      'flex',
                  alignItems:   'center',
                  gap:          12,
                  padding:      '12px 20px',
                  borderRadius: 12,
                  background:   `${t.accent}10`,
                  border:       `1px solid ${t.accent}25`,
                  marginBottom: 32,
                  fontSize:     14,
                  color:        t.accent,
                  fontWeight:   600,
                }}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
                {selected.size} option{selected.size > 1 ? 's' : ''} sélectionnée{selected.size > 1 ? 's' : ''}
                <button
                  onClick={() => setSelected(new Set())}
                  style={{
                    marginLeft: 'auto', background: 'none', border: 'none',
                    color: t.muted, fontSize: 12, cursor: 'pointer', fontFamily: 'inherit',
                  }}
                >
                  Tout désélectionner
                </button>
              </div>
            </Reveal>
          )}

          {/* ── Catalogue ── */}
          {loading ? (
            <div style={{ padding: '60px 0' }}>
              <Spinner label="Chargement du catalogue…" />
            </div>
          ) : error ? (
            <Reveal delay={0}>
              <div
                style={{
                  padding: '20px 24px', borderRadius: 12,
                  background: `${C.ferrari}08`, border: `1px solid ${C.ferrari}25`,
                  color: C.ferrari, fontSize: 14,
                }}
              >
                {error}
              </div>
            </Reveal>
          ) : options.length === 0 ? (
            <Reveal delay={0}>
              <div style={{ padding: '40px 0', color: t.muted, textAlign: 'center' }}>
                Aucune option disponible pour ce modèle dans Baserow.
              </div>
            </Reveal>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {[...grouped.entries()].map(([category, opts], i) => (
                <Reveal key={category} delay={200 + i * 60}>
                  <CategoryAccordion
                    category={category}
                    options={opts}
                    selected={selected}
                    expanded={expanded.has(category)}
                    onToggleExpand={() => toggleCategory(category)}
                    onToggleOption={toggleOption}
                  />
                </Reveal>
              ))}
            </div>
          )}
        </div>
      </main>

      <BottomBar
        onBack={() => navigate('/contacts')}
        onNext={handleNext}
        canNext
        nextLabel="Générer la fiche"
      />
    </PageTransition>
  )
}

// ── Accordéon par catégorie ───────────────────────────────────────────────────
function CategoryAccordion({
  category, options, selected, expanded, onToggleExpand, onToggleOption,
}: {
  category:        string
  options:         Option[]
  selected:        Set<string>
  expanded:        boolean
  onToggleExpand:  () => void
  onToggleOption:  (code: string) => void
}) {
  const { theme: t } = useTheme()
  const checkedCount = options.filter(o => selected.has(o.code)).length
  const [hoveredOption, setHoveredOption] = useState<string | null>(null)

  return (
    <div
      style={{
        borderRadius: 14,
        border:       `1px solid ${expanded ? t.borderStrong : t.border}`,
        overflow:     'hidden',
        background:   t.surface,
        backdropFilter: 'blur(12px)',
        WebkitBackdropFilter: 'blur(12px)',
        transition:   'border-color 0.2s',
      }}
    >
      {/* Header catégorie */}
      <button
        onClick={onToggleExpand}
        style={{
          width:          '100%',
          padding:        '20px 24px',
          background:     'none',
          border:         'none',
          cursor:         'pointer',
          display:        'flex',
          alignItems:     'center',
          gap:            16,
          fontFamily:     'inherit',
          textAlign:      'left',
        }}
      >
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 16, fontWeight: 600, color: t.text }}>{category}</div>
          <div
            style={{
              fontFamily:    "'JetBrains Mono', ui-monospace, monospace",
              fontSize:      10, color: t.muted,
              letterSpacing: '0.12em', textTransform: 'uppercase', marginTop: 4,
            }}
          >
            {options.length} option{options.length > 1 ? 's' : ''}
          </div>
        </div>
        {checkedCount > 0 && (
          <span
            style={{
              padding:      '4px 10px', borderRadius: 20,
              background:   `${t.accent}15`, color: t.accent,
              fontSize:     12, fontWeight: 700,
              fontFamily:   "'JetBrains Mono', ui-monospace, monospace",
            }}
          >
            {checkedCount} ✓
          </span>
        )}
        <svg
          width="16" height="16" viewBox="0 0 24 24"
          fill="none" stroke={t.muted} strokeWidth="1.8"
          style={{ transition: 'transform 0.3s', transform: expanded ? 'rotate(180deg)' : 'none' }}
        >
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>

      {/* Options */}
      {expanded && (
        <div style={{ borderTop: `1px solid ${t.border}` }}>
          {options.map((opt, i) => {
            const isChecked  = selected.has(opt.code)
            const isHovered  = hoveredOption === opt.code
            return (
              <div
                key={opt.code}
                onClick={() => onToggleOption(opt.code)}
                onMouseEnter={() => setHoveredOption(opt.code)}
                onMouseLeave={() => setHoveredOption(null)}
                style={{
                  padding:        '16px 24px',
                  borderBottom:   i < options.length - 1 ? `1px solid ${t.border}` : 'none',
                  cursor:         'pointer',
                  display:        'flex',
                  alignItems:     'flex-start',
                  gap:            16,
                  background:     isChecked
                    ? `${t.accent}07`
                    : isHovered
                      ? `${t.borderStrong}30`
                      : 'transparent',
                  transition:     'background 0.15s',
                }}
              >
                {/* Checkbox */}
                <div
                  style={{
                    width:          20, height: 20,
                    borderRadius:   6,
                    border:         `2px solid ${isChecked ? t.accent : t.borderStrong}`,
                    background:     isChecked ? t.accent : 'transparent',
                    display:        'flex', alignItems: 'center', justifyContent: 'center',
                    flexShrink:     0, marginTop: 2,
                    transition:     'all 0.2s',
                  }}
                >
                  {isChecked && (
                    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="3">
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                  )}
                </div>

                {/* Contenu */}
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <span style={{ fontWeight: 600, fontSize: 14, color: t.text }}>{opt.label}</span>
                    <span
                      style={{
                        fontFamily:    "'JetBrains Mono', ui-monospace, monospace",
                        fontSize:      10, color: t.muted, letterSpacing: '0.1em',
                      }}
                    >
                      {opt.code}
                    </span>
                    {opt.price != null && (
                      <span style={{ marginLeft: 'auto', fontSize: 13, color: t.dim }}>
                        {opt.price.toLocaleString('fr-FR')} €
                      </span>
                    )}
                  </div>
                  {opt.description && (
                    <div style={{ fontSize: 13, color: t.dim, marginTop: 6, lineHeight: 1.5 }}>
                      {opt.description}
                    </div>
                  )}
                  {opt.tips && isHovered && (
                    <div
                      style={{
                        marginTop:    8, padding: '8px 12px',
                        borderRadius: 8, background: `${t.accent}10`,
                        border:       `1px solid ${t.accent}20`,
                        fontSize:     12, color: t.accent, lineHeight: 1.5,
                      }}
                    >
                      💡 {opt.tips}
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
