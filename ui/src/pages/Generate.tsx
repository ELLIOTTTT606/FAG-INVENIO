import { useState, useCallback }           from 'react'
import { useNavigate }                     from 'react-router-dom'
import { useTheme, C }                     from '../lib/theme'
import {
  loadMachine, loadProject, loadClient,
  loadSolution, loadContacts, loadOptions,
  clearSession,
} from '../lib/sessionContext'
import { getFamilyLabel }                  from '../lib/machines'
import { Reveal, PageTransition, MonoLabel, LiveField } from '../components/ui/atoms'
import { BottomBar }                       from '../components/layout/Navigation'

// ── Types ─────────────────────────────────────────────────────────────────────
type GenState = 'idle' | 'generating' | 'done' | 'error'

// ── Helpers ───────────────────────────────────────────────────────────────────
function coverUrl(model: string, size: string): string {
  // Les PNG sont servis depuis ui/public/covers/ (ou /api/covers/ selon config)
  return `/covers/${model}_${size}.png`
}

// ─────────────────────────────────────────────────────────────────────────────
export default function Generate() {
  const { theme: t }  = useTheme()
  const navigate      = useNavigate()
  const machine       = loadMachine()
  const project       = loadProject()
  const client        = loadClient()
  const solution      = loadSolution()
  const contacts      = loadContacts()
  const optionCodes   = loadOptions()

  const [genState,  setGenState]  = useState<GenState>('idle')
  const [progress,  setProgress]  = useState(0)
  const [pdfUrl,    setPdfUrl]    = useState<string | null>(null)
  const [error,     setError]     = useState<string | null>(null)

  const familyLabel = machine
    ? getFamilyLabel(machine.family ?? 'PAC', machine.medium)
    : ''

  // ── Génération PDF ─────────────────────────────────────────────────────────
  const generate = useCallback(async () => {
    setGenState('generating')
    setProgress(0)
    setError(null)

    const tick = setInterval(() => setProgress(p => Math.min(p + 2, 90)), 100)

    try {
      const body: Record<string, unknown> = {
        machine: {
          model:    machine?.model,
          size:     machine?.size,
          family:   machine?.family,
          acoustic: machine?.acoustic,
          medium:   machine?.medium,
        },
        project: {
          number: project?.number,
          name:   project?.name,
        },
        client: {
          name:       client?.name,
          code:       client?.code,
          department: client?.department,
        },
        solution: solution
          ? { name: solution.name, email: solution.email, phone: solution.phone }
          : null,
        contacts: contacts
          ? { tci: contacts.tci, tcs: contacts.tcs }
          : null,
        selected_options: optionCodes,
      }

      const r = await fetch(`${import.meta.env.VITE_API_URL || ''}/generate/pdf`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(body),
      })

      clearInterval(tick)

      if (!r.ok) {
        const detail = await r.text().catch(() => '')
        throw new Error(detail || `Erreur ${r.status}`)
      }

      // Réponse : blob PDF
      const blob = await r.blob()
      setPdfUrl(URL.createObjectURL(blob))
      setProgress(100)
      setGenState('done')
    } catch (err: unknown) {
      clearInterval(tick)
      setGenState('error')
      setError(err instanceof Error ? err.message : 'Erreur inconnue')
    }
  }, [machine, project, client, solution, contacts, optionCodes])

  const handleDownload = () => {
    if (!pdfUrl) return
    const a = document.createElement('a')
    a.href  = pdfUrl
    a.download = `INVENIO_${machine?.model}_${machine?.size}_${project?.name ?? 'fiche'}.pdf`
      .replace(/[^a-zA-Z0-9_\-.]/g, '_')
    a.click()
  }

  const handleReset = () => {
    clearSession()
    navigate('/')
  }

  // ─────────────────────────────────────────────────────────────────────────
  return (
    <PageTransition pgKey="generate">
      <main style={{ minHeight: '100vh', padding: '120px 48px 140px' }}>
        <div style={{ maxWidth: 1200, margin: '0 auto' }}>

          <Reveal delay={50}>
            <MonoLabel style={{ marginBottom: 24 }}>
              <span style={{ width: 24, height: 1, background: t.muted }} />
              Étape 05 · Génération
            </MonoLabel>
          </Reveal>

          <Reveal delay={120}>
            <h1
              style={{
                fontSize:      'clamp(40px, 5vw, 72px)',
                fontWeight:    700, letterSpacing: '-0.035em', lineHeight: 1,
                color:         t.text, margin: '0 0 52px',
              }}
            >
              {genState === 'done'
                ? 'Fiche prête. 🎉'
                : genState === 'generating'
                  ? 'Génération en cours…'
                  : 'Vérifiez et générez.'}
            </h1>
          </Reveal>

          <div
            style={{
              display:             'grid',
              gridTemplateColumns: '1fr 1.2fr',
              gap:                 60,
              alignItems:         'start',
            }}
          >
            {/* ── Aperçu cover page ── */}
            <Reveal delay={200}>
              <div>
                <MonoLabel style={{ marginBottom: 16 }}>Aperçu page de garde</MonoLabel>
                <CoverPreview
                  model={machine?.model ?? ''}
                  size={machine?.size ?? ''}
                  projectName={project?.name ?? ''}
                  familyLabel={familyLabel}
                />
              </div>
            </Reveal>

            {/* ── Récapitulatif + actions ── */}
            <Reveal delay={300}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>

                {/* Récapitulatif */}
                <div
                  style={{
                    padding:      28,
                    borderRadius: 16,
                    background:   t.surface,
                    backdropFilter: 'blur(20px)',
                    WebkitBackdropFilter: 'blur(20px)',
                    border:       `1px solid ${t.border}`,
                  }}
                >
                  <MonoLabel style={{ marginBottom: 20 }}>Récapitulatif</MonoLabel>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                    <LiveField label="Machine" mono>
                      {machine?.model} {machine?.size}
                    </LiveField>
                    <LiveField label="Type" mono>
                      {machine?.family} {machine?.acoustic === 'L' ? '· Silencieux' : ''}
                    </LiveField>
                    <LiveField label="Fluide" mono>{machine?.medium?.replace('_', '/')}</LiveField>
                    <div style={{ height: 1, background: t.border }} />
                    <LiveField label="Projet">{project?.name || '—'}</LiveField>
                    <LiveField label="N°" mono>{project?.number || '—'}</LiveField>
                    <LiveField label="Client">{client?.name || '—'}</LiveField>
                    <LiveField label="Dépt." mono>{client?.department || '—'}</LiveField>
                    {solution && (
                      <>
                        <div style={{ height: 1, background: t.border }} />
                        <LiveField label="Solution">{solution.name}</LiveField>
                      </>
                    )}
                    {contacts?.tci?.name && (
                      <LiveField label="TCI">{contacts.tci.name}</LiveField>
                    )}
                    {contacts?.tcs?.name && (
                      <LiveField label="TCS">{contacts.tcs.name}</LiveField>
                    )}
                    {optionCodes.length > 0 && (
                      <>
                        <div style={{ height: 1, background: t.border }} />
                        <LiveField label="Options" mono>{optionCodes.length} sélectionnées</LiveField>
                      </>
                    )}
                  </div>
                </div>

                {/* Barre de progression */}
                {genState === 'generating' && (
                  <ProgressBar progress={progress} accent={t.accent} border={t.border} />
                )}

                {/* Erreur */}
                {genState === 'error' && error && (
                  <div
                    style={{
                      padding: '16px 20px', borderRadius: 12,
                      background: `${C.ferrari}08`, border: `1px solid ${C.ferrari}25`,
                      color: C.ferrari, fontSize: 14,
                    }}
                  >
                    {error}
                  </div>
                )}

                {/* Bouton principal */}
                {genState !== 'done' && (
                  <GenerateButton
                    state={genState}
                    accent={t.accent}
                    textColor={t.mode === 'dark' ? t.bg : '#fff'}
                    onClick={generate}
                  />
                )}

                {/* Succès : télécharger */}
                {genState === 'done' && pdfUrl && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                    <a
                      href={pdfUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{
                        padding:        '10px 20px',
                        borderRadius:   10,
                        background:     `${t.accent}10`,
                        border:         `1px solid ${t.accent}25`,
                        color:          t.accent,
                        fontSize:       13,
                        textAlign:      'center',
                        textDecoration: 'none',
                        fontWeight:     500,
                      }}
                    >
                      Ouvrir la prévisualisation
                    </a>
                  </div>
                )}
              </div>
            </Reveal>
          </div>
        </div>
      </main>

      <BottomBar
        onBack={genState !== 'done' ? () => navigate('/options') : undefined}
        isLast={genState === 'done'}
        onReset={handleReset}
        onDownload={handleDownload}
        wide
      />
    </PageTransition>
  )
}

// ── Aperçu page de garde ───────────────────────────────────────────────────────
function CoverPreview({
  model, size, projectName, familyLabel,
}: {
  model:       string
  size:        string
  projectName: string
  familyLabel: string
}) {
  const { theme: t } = useTheme()
  const [imgError, setImgError] = useState(false)

  if (!model || !size) {
    return (
      <div
        style={{
          aspectRatio: '1/1.41', borderRadius: 12,
          background:  t.surface, border: `1px dashed ${t.border}`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: t.muted, fontSize: 14,
        }}
      >
        Aucun modèle sélectionné
      </div>
    )
  }

  return (
    <div
      style={{
        position:     'relative',
        aspectRatio:  '1/1.41',
        borderRadius: 12,
        overflow:     'hidden',
        boxShadow:    '0 20px 60px rgba(0,0,0,0.15)',
      }}
    >
      {/* PNG de fond */}
      {!imgError ? (
        <img
          src={coverUrl(model, size)}
          alt={`Cover ${model} ${size}`}
          onError={() => setImgError(true)}
          style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
        />
      ) : (
        /* Fallback si PNG absent */
        <FallbackCover model={model} size={size} />
      )}

      {/* Overlay : nom projet + sous-titre machine */}
      <div
        style={{
          position:       'absolute',
          top:            '22%', left: '50%',
          transform:      'translateX(-50%)',
          width:          '75%', textAlign: 'center',
          /* Rectangle masquant le texte "Projet COURNEUVE" éventuel */
          background:     'rgba(238, 239, 241, 0.96)',
          padding:        '10px 8px',
          borderRadius:   4,
        }}
      >
        <div
          style={{
            fontSize:      'clamp(16px, 3.5vw, 28px)',
            fontWeight:    700,
            color:         '#2f4a6f',
            letterSpacing: '-0.02em',
            lineHeight:    1.1,
          }}
        >
          {projectName ? `Projet ${projectName.toUpperCase()}` : 'Nom du projet'}
        </div>
        {familyLabel && (
          <div
            style={{
              fontSize:   'clamp(8px, 1.5vw, 12px)',
              fontWeight: 700,
              color:      '#2f4a6f',
              marginTop:  4,
            }}
          >
            {familyLabel.charAt(0).toUpperCase() + familyLabel.slice(1)}
          </div>
        )}
      </div>
    </div>
  )
}

// ── Fallback si PNG manquant ──────────────────────────────────────────────────
function FallbackCover({ model, size }: { model: string; size: string }) {
  return (
    <div
      style={{
        width:      '100%', height: '100%',
        background: 'linear-gradient(160deg, #eef0f4 0%, #dde0e8 100%)',
        display:    'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'flex-end',
        padding:    '0 0 10%',
      }}
    >
      <div
        style={{
          fontSize:  'clamp(40px, 12vw, 80px)',
          fontWeight: 900,
          color:      '#2f4a6f',
          letterSpacing: '-0.04em',
          lineHeight: 1,
        }}
      >
        {model}
      </div>
      <div style={{ fontSize: 'clamp(24px, 7vw, 48px)', fontWeight: 700, color: '#00b4a0' }}>
        {size}
      </div>
    </div>
  )
}

// ── Barre de progression ──────────────────────────────────────────────────────
function ProgressBar({ progress, accent, border }: { progress: number; accent: string; border: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
      <div style={{ flex: 1, height: 2, background: border, borderRadius: 2, overflow: 'hidden' }}>
        <div
          style={{
            height:          '100%',
            background:      `linear-gradient(90deg, ${accent}, ${accent}bb)`,
            width:           `${progress}%`,
            transition:      'width 0.15s linear',
          }}
        />
      </div>
      <div
        style={{
          fontFamily: "'JetBrains Mono', ui-monospace, monospace",
          fontSize:   13, color: accent, fontWeight: 600, minWidth: 40, textAlign: 'right',
        }}
      >
        {Math.round(progress)}%
      </div>
    </div>
  )
}

// ── Bouton générer ────────────────────────────────────────────────────────────
function GenerateButton({
  state, accent, textColor, onClick,
}: {
  state:     GenState
  accent:    string
  textColor: string
  onClick:   () => void
}) {
  const [hov, setHov] = useState(false)
  const isLoading = state === 'generating'

  return (
    <button
      onClick={onClick}
      disabled={isLoading}
      onMouseEnter={() => { if (!isLoading) setHov(true) }}
      onMouseLeave={() => setHov(false)}
      style={{
        padding:      '16px 32px', borderRadius: 14, border: 'none',
        background:   accent, color: textColor,
        fontSize:     15, fontWeight: 700, cursor: isLoading ? 'wait' : 'pointer',
        fontFamily:   'inherit',
        display:      'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
        boxShadow:    `0 8px 32px ${accent}30`,
        transform:    hov ? 'translateY(-2px)' : 'none',
        transition:   'all 0.2s cubic-bezier(0.22,1,0.36,1)',
        opacity:      isLoading ? 0.85 : 1,
      }}
    >
      {isLoading ? (
        <>
          <div
            style={{
              width: 16, height: 16, borderRadius: '50%',
              border: `2px solid rgba(255,255,255,0.4)`, borderTopColor: '#fff',
              animation: 'spin 0.7s linear infinite',
            }}
          />
          Génération en cours…
        </>
      ) : (
        <>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8zM14 2v6h6" />
            <line x1="12" y1="18" x2="12" y2="12" /><line x1="9" y1="15" x2="15" y2="15" />
          </svg>
          {state === 'error' ? 'Réessayer' : 'Générer la fiche PDF'}
        </>
      )}
      <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
    </button>
  )
}
