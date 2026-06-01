import { createContext, useContext, useState, type ReactNode } from 'react'

// ─────────────────────────────────────────────────────────────────────────────
// Tokens de couleur (extraits du JSX de référence)
// ─────────────────────────────────────────────────────────────────────────────
export const C = {
  galletti: '#2f4a6f',  // bleu marine France Air
  ferrari:  '#d62828',  // rouge accent
  electric: '#00a8e8',  // bleu électrique
  ink:      '#0a0e1a',  // noir encre
  teal:     '#00b4a0',  // vert teal (taille sur les covers)
} as const

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────
export type ThemeMode = 'light' | 'dark'

export interface Theme {
  mode:           ThemeMode
  bg:             string
  bg2:            string
  text:           string
  dim:            string
  muted:          string
  accent:         string
  accentHover:    string
  surface:        string
  border:         string
  borderStrong:   string
  waveOpacity:    number
  grainOpacity:   number
}

// ─────────────────────────────────────────────────────────────────────────────
// Définitions des thèmes
// ─────────────────────────────────────────────────────────────────────────────
const LIGHT: Theme = {
  mode:         'light',
  bg:           '#ffffff',
  bg2:          '#f6f8fb',
  text:         C.ink,
  dim:          '#4a5266',
  muted:        '#8b94a8',
  accent:       C.galletti,
  accentHover:  '#1f3a5f',
  surface:      'rgba(255,255,255,0.72)',
  border:       'rgba(10,14,26,0.08)',
  borderStrong: 'rgba(10,14,26,0.16)',
  waveOpacity:  0.09,
  grainOpacity: 0.035,
}

const DARK: Theme = {
  mode:         'dark',
  bg:           '#060a14',
  bg2:          '#0b1627',
  text:         '#ffffff',
  dim:          '#a8b0c0',
  muted:        '#6b7385',
  accent:       '#a8c0dd',
  accentHover:  '#ffffff',
  surface:      `rgba(47,74,111,0.22)`,
  border:       'rgba(255,255,255,0.08)',
  borderStrong: 'rgba(255,255,255,0.18)',
  waveOpacity:  0.18,
  grainOpacity: 0.06,
}

// ─────────────────────────────────────────────────────────────────────────────
// Context
// ─────────────────────────────────────────────────────────────────────────────
interface ThemeCtx {
  theme:      Theme
  toggleMode: () => void
}

const ThemeContext = createContext<ThemeCtx>({
  theme:      LIGHT,
  toggleMode: () => {},
})

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<ThemeMode>(() => {
    try {
      return (localStorage.getItem('invenio-theme') as ThemeMode) ?? 'light'
    } catch {
      return 'light'
    }
  })

  const toggleMode = () =>
    setMode(m => {
      const next = m === 'light' ? 'dark' : 'light'
      try { localStorage.setItem('invenio-theme', next) } catch {}
      return next
    })

  const theme = mode === 'dark' ? DARK : LIGHT

  return (
    <ThemeContext.Provider value={{ theme, toggleMode }}>
      {children}
    </ThemeContext.Provider>
  )
}

export const useTheme = () => useContext(ThemeContext)

// ─────────────────────────────────────────────────────────────────────────────
// Helpers de style inline réutilisables
// ─────────────────────────────────────────────────────────────────────────────
export const glassCard = (t: Theme): React.CSSProperties => ({
  background:         t.surface,
  backdropFilter:     'blur(20px)',
  WebkitBackdropFilter: 'blur(20px)',
  border:             `1px solid ${t.border}`,
  borderRadius:       16,
})

export const accentBtn = (t: Theme, enabled = true): React.CSSProperties => ({
  padding:      '14px 32px',
  borderRadius: 12,
  border:       'none',
  background:   enabled ? t.accent : t.border,
  color:        enabled ? (t.mode === 'dark' ? t.bg : '#fff') : t.muted,
  fontSize:     14,
  fontWeight:   700,
  cursor:       enabled ? 'pointer' : 'not-allowed',
  display:      'flex',
  alignItems:   'center',
  gap:          8,
  boxShadow:    enabled ? `0 8px 32px ${t.accent}25` : 'none',
  transition:   'all 0.2s cubic-bezier(0.22,1,0.36,1)',
  fontFamily:   'inherit',
})

export const monoLabel = (t: Theme, size = 10): React.CSSProperties => ({
  fontFamily:    "'JetBrains Mono', ui-monospace, monospace",
  fontSize:      size,
  letterSpacing: '0.15em',
  textTransform: 'uppercase',
  color:         t.muted,
})
