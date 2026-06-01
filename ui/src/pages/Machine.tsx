import { useRef, useState }              from 'react'
import { useNavigate }                   from 'react-router-dom'
import { useTheme }                      from '../lib/theme'
import { MACHINES, FLUIDS, findMachine, type MachineFamily, type AcousticType } from '../lib/machines'
import { loadMachine, saveMachine }      from '../lib/sessionContext'
import { Reveal, PageTransition, PillBtn, MonoLabel } from '../components/ui/atoms'
import { BottomBar }                     from '../components/layout/Navigation'

export default function Machine() {
  const { theme: t }  = useTheme()
  const navigate      = useNavigate()
  const fileRef       = useRef<HTMLInputElement>(null)

  // Pré-remplir depuis la session si on revient en arrière
  const saved = loadMachine()
  const [model,    setModel]    = useState<string>(saved?.model    ?? '')
  const [size,     setSize]     = useState<string>(saved?.size     ?? '')
  const [family,   setFamily]   = useState<MachineFamily | null>(saved?.family ?? null)
  const [acoustic, setAcoustic] = useState<AcousticType | null>(saved?.acoustic ?? null)
  const [showAll,  setShowAll]  = useState(!saved?.model)

  const machine = findMachine(model)
  const canNext = Boolean(model && size && family)

  const handleNext = () => {
    if (!canNext || !machine) return
    saveMachine({
      model,
      size,
      family,
      acoustic: acoustic ?? 'S',
      medium:   machine.medium,
    })
    navigate('/projet')
  }

  const handleBack = () => {
    setShowAll(true)
    setModel('')
    setSize('')
    setFamily(null)
    setAcoustic(null)
  }

  // ─────────────────────────────────────────────────────────────────────────
  return (
    <PageTransition pgKey={`machine-${showAll}`}>
      <main style={{ minHeight: '100vh', padding: '120px 48px 140px' }}>
        {!showAll && model ? (
          /* ── Vue modèle sélectionné ── */
          <div style={{ maxWidth: 1200, margin: '0 auto' }}>
            <Reveal delay={50}>
              <MonoLabel style={{ marginBottom: 24 }}>
                <span style={{ width: 24, height: 1, background: t.muted }} />
                Étape 01 · Machine
              </MonoLabel>
            </Reveal>

            <div
              style={{
                display:       'grid',
                gridTemplateColumns: '1.3fr 1fr',
                gap:           80,
                alignItems:    'start',
                marginTop:     24,
              }}
            >
              {/* Gauche : nom du modèle + infos */}
              <div>
                <Reveal delay={150}>
                  <h1
                    style={{
                      fontSize:      'clamp(64px, 10vw, 160px)',
                      fontWeight:    700,
                      letterSpacing: '-0.045em',
                      lineHeight:    0.92,
                      color:         t.text,
                    }}
                  >
                    {model}
                  </h1>
                </Reveal>

                <Reveal delay={280}>
                  <div
                    style={{
                      display:       'flex',
                      alignItems:    'center',
                      gap:           16,
                      marginTop:     24,
                      fontFamily:    "'JetBrains Mono', ui-monospace, monospace",
                      fontSize:      12,
                      letterSpacing: '0.15em',
                      color:         t.muted,
                      textTransform: 'uppercase',
                    }}
                  >
                    <span>
                      Fluide · {FLUIDS.find(f => f.models.includes(model))?.code}
                    </span>
                    <span style={{ width: 1, height: 16, background: t.border }} />
                    <span>{machine?.sizes.length} tailles</span>
                    <span style={{ width: 1, height: 16, background: t.border }} />
                    <span>{machine?.medium.replace('_', '/').replace('eau', 'eau')}</span>
                  </div>
                </Reveal>

                <Reveal delay={400}>
                  <button
                    onClick={() => { setShowAll(true); setModel(''); setSize(''); setFamily(null) }}
                    style={{
                      marginTop:  36, background: 'none', border: 'none',
                      color:      t.dim, fontSize: 14, cursor: 'pointer',
                      fontFamily: 'inherit', display: 'flex', alignItems: 'center', gap: 8,
                      padding:    0, transition: 'color 0.2s',
                    }}
                    onMouseEnter={e => { (e.currentTarget as HTMLElement).style.color = t.text }}
                    onMouseLeave={e => { (e.currentTarget as HTMLElement).style.color = t.dim }}
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M3 12h18M12 3v18" />
                    </svg>
                    Changer de modèle
                  </button>
                </Reveal>
              </div>

              {/* Droite : taille + type + acoustique */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 40 }}>

                {/* Taille */}
                <Reveal delay={350}>
                  <div>
                    <MonoLabel style={{ marginBottom: 16 }}>Taille</MonoLabel>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                      {machine?.sizes.map(s => (
                        <PillBtn key={s} active={size === s} onClick={() => setSize(s)} mono>
                          {s}
                        </PillBtn>
                      ))}
                    </div>
                  </div>
                </Reveal>

                {/* Type : PAC ou GEG */}
                <Reveal delay={500}>
                  <div>
                    <MonoLabel style={{ marginBottom: 16 }}>Type</MonoLabel>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                      {([
                        ['PAC', "Pompe à chaleur", "PAC"],
                        ['GEG', "Groupe d'eau glacée", "GEG"],
                      ] as const).map(([key, label, abbr]) => (
                        <button
                          key={key}
                          onClick={() => setFamily(key)}
                          style={{
                            padding:      '22px 20px',
                            borderRadius: 14,
                            border:       `1.5px solid ${family === key ? t.accent : t.border}`,
                            background:   family === key ? `${t.accent}10` : 'transparent',
                            cursor:       'pointer',
                            fontFamily:   'inherit',
                            textAlign:    'left',
                            transition:   'all 0.2s',
                          }}
                          onMouseEnter={e => { if (family !== key) (e.currentTarget as HTMLElement).style.borderColor = t.borderStrong }}
                          onMouseLeave={e => { if (family !== key) (e.currentTarget as HTMLElement).style.borderColor = t.border }}
                        >
                          <div
                            style={{
                              fontFamily:    "'JetBrains Mono', ui-monospace, monospace",
                              fontSize:      10, letterSpacing: '0.15em',
                              color:         family === key ? t.accent : t.muted,
                              marginBottom:  6,
                            }}
                          >
                            {abbr}
                          </div>
                          <div style={{ fontSize: 15, fontWeight: 600, color: family === key ? t.text : t.dim }}>
                            {label}
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>
                </Reveal>

                {/* Acoustique */}
                <Reveal delay={620}>
                  <div>
                    <MonoLabel style={{ marginBottom: 16 }}>Version acoustique</MonoLabel>
                    <div style={{ display: 'flex', gap: 8 }}>
                      {([
                        ['S', 'Standard'],
                        ['L', 'Silencieuse'],
                      ] as const).map(([key, label]) => (
                        <PillBtn key={key} active={acoustic === key} onClick={() => setAcoustic(key)}>
                          {label}
                        </PillBtn>
                      ))}
                    </div>
                  </div>
                </Reveal>

              </div>
            </div>
          </div>
        ) : (
          /* ── Vue catalogue complet ── */
          <CatalogueView
            onSelect={(code) => { setModel(code); setSize(''); setFamily(null); setShowAll(false) }}
            fileRef={fileRef}
          />
        )}
      </main>

      <BottomBar
        onBack={!showAll ? handleBack : undefined}
        onNext={handleNext}
        canNext={canNext}
        nextLabel="Continuer"
      />
    </PageTransition>
  )
}

// ── Vue catalogue : tous les modèles groupés par fluide ───────────────────────
function CatalogueView({
  onSelect,
  fileRef,
}: {
  onSelect:  (code: string) => void
  fileRef:   React.RefObject<HTMLInputElement>
}) {
  const { theme: t } = useTheme()
  const total = MACHINES.reduce((acc, m) => acc + m.sizes.length, 0)

  return (
    <div style={{ maxWidth: 1400, margin: '0 auto' }}>
      <Reveal delay={50}>
        <MonoLabel style={{ marginBottom: 24 }}>
          <span style={{ width: 24, height: 1, background: t.muted }} />
          Étape 01 · Sélection du modèle
        </MonoLabel>
      </Reveal>

      <Reveal delay={150}>
        <h1
          style={{
            fontSize:      'clamp(40px, 5vw, 72px)',
            fontWeight:    700,
            letterSpacing: '-0.03em',
            lineHeight:    1,
            color:         t.text,
            margin:        '0 0 16px',
          }}
        >
          Choisissez un modèle.
        </h1>
      </Reveal>

      <Reveal delay={250}>
        <p style={{ fontSize: 17, color: t.dim, maxWidth: 560, marginBottom: 56 }}>
          {MACHINES.length} modèles · {total} tailles disponibles dans la gamme GALLETTI.
        </p>
      </Reveal>

      {/* Groupes par fluide */}
      {FLUIDS.map((fl, fi) => {
        const flMachines = fl.models
          .map(code => MACHINES.find(m => m.code === code))
          .filter(Boolean) as typeof MACHINES

        return (
          <Reveal key={fl.code} delay={350 + fi * 80}>
            <div style={{ marginBottom: 48 }}>
              <div
                style={{
                  display:       'flex',
                  alignItems:    'baseline',
                  gap:           16,
                  marginBottom:  20,
                  paddingBottom: 16,
                  borderBottom:  `1px solid ${t.border}`,
                }}
              >
                <span
                  style={{
                    fontFamily:    "'JetBrains Mono', ui-monospace, monospace",
                    fontSize:      12, fontWeight: 600, letterSpacing: '0.15em', color: t.text,
                  }}
                >
                  {fl.code}
                </span>
                <span style={{ fontSize: 13, color: t.muted }}>
                  {flMachines.length} modèle{flMachines.length > 1 ? 's' : ''}
                </span>
              </div>

              <div
                style={{
                  display:             'grid',
                  gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
                  gap:                 12,
                }}
              >
                {flMachines.map(m => (
                  <ModelCard key={m.code} machine={m} onClick={() => onSelect(m.code)} />
                ))}
              </div>
            </div>
          </Reveal>
        )
      })}
    </div>
  )
}

// ── Carte d'un modèle ─────────────────────────────────────────────────────────
function ModelCard({
  machine,
  onClick,
}: {
  machine: typeof MACHINES[number]
  onClick: () => void
}) {
  const { theme: t } = useTheme()
  const [hov, setHov] = useState(false)

  return (
    <button
      onClick={onClick}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        padding:      '32px 24px',
        borderRadius: 16,
        border:       `1px solid ${hov ? t.accent : t.border}`,
        background:   t.surface,
        backdropFilter: 'blur(12px)',
        WebkitBackdropFilter: 'blur(12px)',
        cursor:       'pointer',
        textAlign:    'left',
        fontFamily:   'inherit',
        transition:   'all 0.3s cubic-bezier(0.22,1,0.36,1)',
        transform:    hov ? 'translateY(-4px)' : 'none',
        boxShadow:    hov ? `0 16px 40px ${t.accent}15` : 'none',
      }}
    >
      <div style={{ fontSize: 28, fontWeight: 700, letterSpacing: '-0.02em', color: t.text, marginBottom: 8 }}>
        {machine.code}
      </div>
      <div
        style={{
          fontFamily:    "'JetBrains Mono', ui-monospace, monospace",
          fontSize:      10, letterSpacing: '0.12em',
          color:         t.muted, textTransform: 'uppercase',
        }}
      >
        {machine.sizes.length} tailles · {machine.medium.replace('_', '/')}
      </div>
    </button>
  )
}
