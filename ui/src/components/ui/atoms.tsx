// ─────────────────────────────────────────────────────────────────────────────
// Atomes UI — fidèles au design du JSX de référence
// ─────────────────────────────────────────────────────────────────────────────
import {
  useState, useEffect,
  type ReactNode, type CSSProperties, type InputHTMLAttributes,
} from 'react'
import { useTheme } from '../../lib/theme'

// ── Reveal (animation d'apparition au montage) ────────────────────────────────
interface RevealProps {
  delay?: number
  y?:     number
  children: ReactNode
  style?: CSSProperties
}

export function Reveal({ delay = 0, y = 20, children, style }: RevealProps) {
  const [on, setOn] = useState(false)
  useEffect(() => {
    const t = setTimeout(() => setOn(true), delay)
    return () => clearTimeout(t)
  }, [delay])

  return (
    <div
      style={{
        opacity:    on ? 1 : 0,
        transform:  on ? 'translateY(0)' : `translateY(${y}px)`,
        transition: 'opacity 0.7s cubic-bezier(0.22,1,0.36,1), transform 0.7s cubic-bezier(0.22,1,0.36,1)',
        willChange: 'opacity,transform',
        ...style,
      }}
    >
      {children}
    </div>
  )
}

// ── PageTransition ────────────────────────────────────────────────────────────
export function PageTransition({ pgKey, children }: { pgKey: string; children: ReactNode }) {
  const [show, setShow] = useState(false)

  useEffect(() => {
    setShow(false)
    const raf = requestAnimationFrame(() => setShow(true))
    return () => cancelAnimationFrame(raf)
  }, [pgKey])

  return (
    <div
      style={{
        opacity:    show ? 1 : 0,
        transform:  show ? 'translateY(0) scale(1)' : 'translateY(24px) scale(0.99)',
        filter:     show ? 'blur(0px)' : 'blur(8px)',
        transition: 'opacity 0.6s cubic-bezier(0.22,1,0.36,1), transform 0.6s, filter 0.5s ease-out',
      }}
    >
      {children}
    </div>
  )
}

// ── GhostInput ────────────────────────────────────────────────────────────────
interface GhostInputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
}

export function GhostInput({ label, style, ...rest }: GhostInputProps) {
  const { theme: t } = useTheme()
  const [focused, setFocused] = useState(false)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      {label && (
        <span
          style={{
            fontFamily:    "'JetBrains Mono', ui-monospace, monospace",
            fontSize:      10,
            letterSpacing: '0.15em',
            textTransform: 'uppercase',
            color:         focused ? t.accent : t.muted,
            transition:    'color 0.2s',
          }}
        >
          {label}
        </span>
      )}
      <input
        {...rest}
        onFocus={e => { setFocused(true); rest.onFocus?.(e) }}
        onBlur={e  => { setFocused(false); rest.onBlur?.(e) }}
        style={{
          width:           '100%',
          padding:         '14px 0',
          background:      'transparent',
          border:          'none',
          borderBottom:    `1.5px solid ${focused ? t.accent : t.border}`,
          fontSize:        18,
          fontFamily:      'inherit',
          color:           t.text,
          outline:         'none',
          transition:      'border-color 0.2s',
          ...style,
        }}
      />
    </div>
  )
}

// ── GhostSelect ───────────────────────────────────────────────────────────────
interface GhostSelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?:    string
  children:  ReactNode
}

export function GhostSelect({ label, children, style, ...rest }: GhostSelectProps) {
  const { theme: t } = useTheme()
  const [focused, setFocused] = useState(false)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      {label && (
        <span
          style={{
            fontFamily:    "'JetBrains Mono', ui-monospace, monospace",
            fontSize:      10,
            letterSpacing: '0.15em',
            textTransform: 'uppercase',
            color:         focused ? t.accent : t.muted,
            transition:    'color 0.2s',
          }}
        >
          {label}
        </span>
      )}
      <select
        {...rest}
        onFocus={e => { setFocused(true); rest.onFocus?.(e) }}
        onBlur={e  => { setFocused(false); rest.onBlur?.(e) }}
        style={{
          width:              '100%',
          padding:            '14px 24px 14px 0',
          background:         'transparent',
          border:             'none',
          borderBottom:       `1.5px solid ${focused ? t.accent : t.border}`,
          fontSize:           18,
          fontFamily:         'inherit',
          color:              rest.value ? t.text : t.muted,
          outline:            'none',
          cursor:             'pointer',
          appearance:         'none',
          WebkitAppearance:   'none',
          backgroundImage:    `url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='10' height='6'><path d='M0 0l5 6 5-6z' fill='%238b94a8'/></svg>")`,
          backgroundRepeat:   'no-repeat',
          backgroundPosition: 'right 4px center',
          transition:         'border-color 0.2s',
          ...style,
        }}
      >
        {children}
      </select>
    </div>
  )
}

// ── PillBtn ───────────────────────────────────────────────────────────────────
interface PillBtnProps {
  active:   boolean
  onClick:  () => void
  mono?:    boolean
  children: ReactNode
}

export function PillBtn({ active, onClick, mono = false, children }: PillBtnProps) {
  const { theme: t } = useTheme()
  const [hov, setHov] = useState(false)

  return (
    <button
      onClick={onClick}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        padding:      '10px 16px',
        minWidth:     54,
        borderRadius: 10,
        border:       `1px solid ${active ? t.accent : hov ? t.borderStrong : t.border}`,
        background:   active ? t.accent : 'transparent',
        color:        active ? '#fff' : hov ? t.text : t.dim,
        fontSize:     13,
        fontWeight:   600,
        cursor:       'pointer',
        fontFamily:   mono ? "'JetBrains Mono', ui-monospace, monospace" : 'inherit',
        letterSpacing: mono ? '0.05em' : 0,
        transition:   'all 0.2s cubic-bezier(0.22,1,0.36,1)',
      }}
    >
      {children}
    </button>
  )
}

// ── Avatar (initiales) ────────────────────────────────────────────────────────
export function Avatar({ name, size = 36 }: { name: string; size?: number }) {
  const { theme: t } = useTheme()
  const initials = name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()

  return (
    <div
      style={{
        width:          size,
        height:         size,
        borderRadius:   '50%',
        background:     `linear-gradient(135deg, ${t.accent}20, ${t.accent}35)`,
        border:         `1px solid ${t.border}`,
        display:        'flex',
        alignItems:     'center',
        justifyContent: 'center',
        fontSize:       size * 0.32,
        fontWeight:     700,
        color:          t.accent,
        flexShrink:     0,
        fontFamily:     'inherit',
      }}
    >
      {initials}
    </div>
  )
}

// ── LiveField (preview temps réel) ────────────────────────────────────────────
export function LiveField({
  label,
  mono = false,
  children,
}: {
  label:    string
  mono?:    boolean
  children: ReactNode
}) {
  const { theme: t } = useTheme()

  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 16 }}>
      <span
        style={{
          fontFamily:    "'JetBrains Mono', ui-monospace, monospace",
          fontSize:      10,
          letterSpacing: '0.15em',
          color:         t.muted,
          textTransform: 'uppercase',
          flexShrink:    0,
        }}
      >
        {label}
      </span>
      <span
        style={{
          fontSize:      15,
          fontWeight:    600,
          color:         t.text,
          textAlign:     'right',
          fontFamily:    mono ? "'JetBrains Mono', ui-monospace, monospace" : 'inherit',
          letterSpacing: mono ? '0.05em' : 0,
          transition:    'color 0.3s',
          wordBreak:     'break-word',
        }}
      >
        {children}
      </span>
    </div>
  )
}

// ── MonoLabel ─────────────────────────────────────────────────────────────────
export function MonoLabel({
  children,
  size = 10,
  style,
}: {
  children: ReactNode
  size?:    number
  style?:   CSSProperties
}) {
  const { theme: t } = useTheme()

  return (
    <div
      style={{
        fontFamily:    "'JetBrains Mono', ui-monospace, monospace",
        fontSize:      size,
        letterSpacing: '0.15em',
        textTransform: 'uppercase',
        color:         t.muted,
        display:       'flex',
        alignItems:    'center',
        gap:           10,
        ...style,
      }}
    >
      {children}
    </div>
  )
}

// ── Spinner ───────────────────────────────────────────────────────────────────
export function Spinner({ label = 'Chargement…' }: { label?: string }) {
  const { theme: t } = useTheme()

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 20 }}>
      <div
        style={{
          width:        40,
          height:       40,
          borderRadius: '50%',
          border:       `2.5px solid ${t.border}`,
          borderTopColor: t.accent,
          animation:    'spin 0.8s linear infinite',
        }}
      />
      <MonoLabel>{label}</MonoLabel>
      <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
    </div>
  )
}

// ── TypeRef ───────────────────────────────────────────────────────────────────
// Correction TypeScript pour les styles WebKit
declare module 'react' {
  interface CSSProperties {
    WebkitBackdropFilter?: string
    WebkitAppearance?: string
  }
}
