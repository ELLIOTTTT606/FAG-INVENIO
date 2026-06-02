import { useState } from 'react'
import { useTheme } from '../../lib/theme'
import { BaserowBadge } from '../BaserowBadge'

// ─────────────────────────────────────────────────────────────────────────────
// Étapes du workflow
// ─────────────────────────────────────────────────────────────────────────────
export const STEPS = [
  { path: '/machine',  label: 'Machine'  },
  { path: '/projet',   label: 'Projet'   },
  { path: '/contacts', label: 'Contacts' },
  { path: '/options',  label: 'Options'  },
  { path: '/generate', label: 'Générer'  },
] as const

export type StepPath = typeof STEPS[number]['path']

function currentStep(pathname: string): number {
  return STEPS.findIndex(s => pathname.startsWith(s.path))
}

// ─────────────────────────────────────────────────────────────────────────────
// Stepper
// ─────────────────────────────────────────────────────────────────────────────
export function Stepper({ pathname }: { pathname: string }) {
  const { theme: t } = useTheme()
  const cur = currentStep(pathname)

  return (
    <div
      style={{
        display:             'flex',
        alignItems:          'center',
        gap:                 4,
        padding:             '8px 16px',
        borderRadius:        999,
        background:          t.surface,
        backdropFilter:      'blur(20px)',
        WebkitBackdropFilter:'blur(20px)',
        border:              `1px solid ${t.border}`,
        fontFamily:          "'JetBrains Mono', ui-monospace, monospace",
        fontSize:            11,
        letterSpacing:       '0.1em',
      }}
    >
      {STEPS.map((step, i) => {
        const active = i === cur
        const done   = i < cur
        return (
          <div key={step.path} style={{ display: 'flex', alignItems: 'center' }}>
            <div
              style={{
                display:    'flex',
                alignItems: 'center',
                gap:        6,
                padding:    '4px 10px',
                color:      active ? t.text : done ? t.dim : t.muted,
                fontWeight: active ? 700 : 500,
                transition: 'color 0.3s',
              }}
            >
              <span style={{ fontSize: 10, opacity: 0.6 }}>0{i + 1}</span>
              <span style={{ textTransform: 'uppercase' }}>{step.label}</span>
            </div>
            {i < STEPS.length - 1 && (
              <span style={{ color: t.muted, opacity: 0.4, fontSize: 12 }}>·</span>
            )}
          </div>
        )
      })}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// TopBar
// ─────────────────────────────────────────────────────────────────────────────
interface TopBarProps {
  pathname: string
  onHome:   () => void
}

export function TopBar({ pathname, onHome }: TopBarProps) {
  const { theme: t, toggleMode } = useTheme()
  const showStepper = pathname !== '/'
  const dark = t.mode === 'dark'

  const iconBtn: React.CSSProperties = {
    width:               40,
    height:              40,
    borderRadius:        10,
    background:          t.surface,
    backdropFilter:      'blur(16px)',
    WebkitBackdropFilter:'blur(16px)',
    border:              `1px solid ${t.border}`,
    cursor:              'pointer',
    display:             'flex',
    alignItems:          'center',
    justifyContent:      'center',
    color:               t.text,
    transition:          'all 0.2s',
  }

  return (
    <header
      style={{
        position:      'fixed',
        top: 0, left: 0, right: 0,
        zIndex:        20,
        padding:       '20px 32px',
        display:       'flex',
        alignItems:    'center',
        justifyContent:'space-between',
        pointerEvents: 'none',
      }}
    >
      {/* Logo + home */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 14, pointerEvents: 'auto' }}>
        <button
          onClick={onHome}
          aria-label="Accueil"
          style={iconBtn}
          onMouseEnter={e => { e.currentTarget.style.borderColor = t.borderStrong; e.currentTarget.style.transform = 'scale(1.05)' }}
          onMouseLeave={e => { e.currentTarget.style.borderColor = t.border; e.currentTarget.style.transform = 'scale(1)' }}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
            <path d="M3 12l9-9 9 9M5 10v10h5v-6h4v6h5V10" />
          </svg>
        </button>
        <div
          style={{
            fontFamily:    "'JetBrains Mono', ui-monospace, monospace",
            fontSize:      11,
            fontWeight:    500,
            letterSpacing: '0.2em',
            color:         t.muted,
            textTransform: 'uppercase',
          }}
        >
          Invenio · v2.0
        </div>
      </div>

      {/* Stepper centré */}
      {showStepper && (
        <div style={{ pointerEvents: 'auto' }}>
          <Stepper pathname={pathname} />
        </div>
      )}

      {/* Baserow status + Toggle thème */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, pointerEvents: 'auto' }}>
        <BaserowBadge />
      <button
        onClick={toggleMode}
        aria-label={dark ? 'Passer en mode clair' : 'Passer en mode sombre'}
        style={{ ...iconBtn, pointerEvents: 'auto' }}
        onMouseEnter={e => { e.currentTarget.style.borderColor = t.borderStrong }}
        onMouseLeave={e => { e.currentTarget.style.borderColor = t.border }}
      >
        {dark
          ? <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/></svg>
          : <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"/></svg>
        }
      </button>
      </div>
    </header>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// BottomBar
// ─────────────────────────────────────────────────────────────────────────────
interface BottomBarProps {
  onBack?:    () => void
  onNext?:    () => void
  canNext?:   boolean
  isLast?:    boolean
  onReset?:   () => void
  onDownload?: () => void
  nextLabel?:  string
  wide?:       boolean
}

export function BottomBar({
  onBack,
  onNext,
  canNext = true,
  isLast  = false,
  onReset,
  onDownload,
  nextLabel,
  wide    = false,
}: BottomBarProps) {
  const { theme: t } = useTheme()
  const dark = t.mode === 'dark'

  const [hovBack, setHovBack]   = useState(false)
  const [hovNext, setHovNext]   = useState(false)
  const [hovReset, setHovReset] = useState(false)

  return (
    <div
      style={{
        position:       'fixed',
        bottom: 0, left: 0, right: 0,
        zIndex:         20,
        padding:        '20px 32px',
        background:     dark
          ? 'linear-gradient(180deg, transparent 0%, rgba(6,10,20,0.9) 60%)'
          : 'linear-gradient(180deg, transparent 0%, rgba(255,255,255,0.95) 60%)',
        backdropFilter: 'blur(12px)',
        WebkitBackdropFilter: 'blur(12px)',
      }}
    >
      <div
        style={{
          display:    'flex',
          gap:        12,
          maxWidth:   wide ? 1400 : 900,
          margin:     '0 auto',
          alignItems: 'center',
        }}
      >
        {/* Retour */}
        {onBack && !isLast && (
          <button
            onClick={onBack}
            onMouseEnter={() => setHovBack(true)}
            onMouseLeave={() => setHovBack(false)}
            style={{
              padding:      '14px 24px',
              borderRadius: 12,
              border:       `1px solid ${hovBack ? t.borderStrong : t.border}`,
              background:   t.surface,
              color:        t.text,
              fontSize:     14,
              fontWeight:   600,
              cursor:       'pointer',
              fontFamily:   'inherit',
              display:      'flex',
              alignItems:   'center',
              gap:          8,
              transition:   'all 0.2s',
              transform:    hovBack ? 'translateX(-2px)' : 'none',
            }}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M19 12H5M12 19l-7-7 7-7" />
            </svg>
            Retour
          </button>
        )}

        <div style={{ flex: 1 }} />

        {isLast ? (
          /* Dernière page : Reset + Télécharger */
          <>
            <button
              onClick={onReset}
              onMouseEnter={() => setHovReset(true)}
              onMouseLeave={() => setHovReset(false)}
              style={{
                padding:      '14px 24px',
                borderRadius: 12,
                border:       `1px solid ${hovReset ? t.borderStrong : t.border}`,
                background:   t.surface,
                color:        t.text,
                fontSize:     14,
                fontWeight:   600,
                cursor:       'pointer',
                fontFamily:   'inherit',
              }}
            >
              ↺ Nouvelle fiche
            </button>
            <button
              onClick={onDownload}
              onMouseEnter={() => setHovNext(true)}
              onMouseLeave={() => setHovNext(false)}
              style={{
                padding:      '14px 28px',
                borderRadius: 12,
                border:       'none',
                background:   t.accent,
                color:        dark ? t.bg : '#fff',
                fontSize:     14,
                fontWeight:   700,
                cursor:       'pointer',
                fontFamily:   'inherit',
                display:      'flex',
                alignItems:   'center',
                gap:          8,
                boxShadow:    `0 8px 32px ${t.accent}35`,
                transform:    hovNext ? 'translateY(-1px)' : 'none',
                transition:   'all 0.2s',
              }}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3" />
              </svg>
              Télécharger le PDF
            </button>
          </>
        ) : (
          /* Bouton Continuer / Générer */
          <button
            onClick={canNext ? onNext : undefined}
            disabled={!canNext}
            onMouseEnter={() => { if (canNext) setHovNext(true) }}
            onMouseLeave={() => setHovNext(false)}
            style={{
              padding:      '14px 32px',
              borderRadius: 12,
              border:       'none',
              background:   canNext ? t.accent : t.border,
              color:        canNext ? (dark ? t.bg : '#fff') : t.muted,
              fontSize:     14,
              fontWeight:   700,
              cursor:       canNext ? 'pointer' : 'not-allowed',
              fontFamily:   'inherit',
              display:      'flex',
              alignItems:   'center',
              gap:          8,
              boxShadow:    canNext ? `0 8px 32px ${t.accent}25` : 'none',
              transition:   'all 0.2s cubic-bezier(0.22,1,0.36,1)',
              transform:    hovNext && canNext ? 'translateX(2px)' : 'none',
            }}
          >
            {nextLabel ?? 'Continuer'}
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M5 12h14M12 5l7 7-7 7" />
            </svg>
          </button>
        )}
      </div>
    </div>
  )
}
