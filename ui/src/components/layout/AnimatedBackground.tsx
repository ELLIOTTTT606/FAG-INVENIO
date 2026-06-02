import { useTheme, C } from '../../lib/theme'

export function AnimatedBackground() {
  const { theme: t } = useTheme()
  const dark = t.mode === 'dark'

  return (
    <>
      <style>{`
        @keyframes orbA {
          0%,100% { transform: translate(0,0) scale(1) }
          33%      { transform: translate(4vw,-3vw) scale(1.08) }
          66%      { transform: translate(-3vw,4vw) scale(0.95) }
        }
        @keyframes orbB {
          0%,100% { transform: translate(0,0) scale(1) }
          33%      { transform: translate(-5vw,2vw) scale(1.1) }
          66%      { transform: translate(3vw,-3vw) scale(0.92) }
        }
        @keyframes orbC {
          0%,100% { transform: translate(0,0) scale(1) }
          50%      { transform: translate(-4vw,3vw) scale(1.12) }
        }
        @keyframes waveShift {
          from { transform: translateX(-20%) }
          to   { transform: translateX(20%) }
        }
        @keyframes pulseDot {
          0%,100% { opacity:1; transform: scale(1) }
          50%      { opacity:.5; transform: scale(1.4) }
        }
        @keyframes pulseRing {
          0%   { transform: scale(1); opacity: .4 }
          100% { transform: scale(1.6); opacity: 0 }
        }
        @keyframes bgMove {
          from { background-position: 0% 0% }
          to   { background-position: 200% 0% }
        }
      `}</style>

      <div
        aria-hidden
        style={{
          position:      'fixed',
          inset:         0,
          overflow:      'hidden',
          pointerEvents: 'none',
          zIndex:        0,
          background:    dark
            ? `radial-gradient(ellipse 1400px 800px at 20% 10%, ${C.galletti}30 0%, transparent 60%),
               radial-gradient(ellipse 1200px 900px at 85% 85%, ${C.galletti}25 0%, transparent 55%),
               linear-gradient(180deg, ${t.bg} 0%, ${t.bg2} 100%)`
            : `linear-gradient(180deg, #fff 0%, ${t.bg2} 100%)`,
          transition: 'background 0.8s ease',
        }}
      >
        {/* Orbe rouge (haut-gauche) */}
        <div
          style={{
            position:     'absolute', width: '60vw', height: '60vw',
            top: '-15vw', left: '-10vw', borderRadius: '50%',
            background:   `radial-gradient(circle, ${C.ferrari}22 0%, transparent 65%)`,
            opacity:      dark ? 0.45 : 0.35,
            animation:    'orbA 28s ease-in-out infinite',
            filter:       'blur(40px)',
          }}
        />
        {/* Orbe bleu électrique (bas-droite) */}
        <div
          style={{
            position:       'absolute', width: '55vw', height: '55vw',
            bottom: '-10vw', right: '-10vw', borderRadius: '50%',
            background:     `radial-gradient(circle, ${C.electric}26 0%, transparent 65%)`,
            opacity:        dark ? 0.50 : 0.40,
            animation:      'orbB 32s ease-in-out infinite',
            filter:         'blur(50px)',
          }}
        />
        {/* Orbe Galletti (centre) */}
        <div
          style={{
            position:  'absolute', width: '40vw', height: '40vw',
            top: '40%', left: '60%', borderRadius: '50%',
            background: `radial-gradient(circle, ${C.galletti}18 0%, transparent 70%)`,
            opacity:   dark ? 0.60 : 0.25,
            animation: 'orbC 24s ease-in-out infinite',
            filter:    'blur(60px)',
          }}
        />

        {/* Vagues SVG style vent */}
        <svg
          width="100%" height="100%"
          viewBox="0 0 1600 900"
          preserveAspectRatio="none"
          style={{
            position:      'absolute', inset: 0,
            opacity:       t.waveOpacity,
            mixBlendMode:  dark ? 'screen' : 'multiply',
          }}
        >
          <defs>
            <linearGradient id="wgA" x1="0" x2="1">
              <stop offset="0%"   stopColor={C.ferrari}  stopOpacity="0" />
              <stop offset="50%"  stopColor={C.ferrari}  stopOpacity="1" />
              <stop offset="100%" stopColor={C.ferrari}  stopOpacity="0" />
            </linearGradient>
            <linearGradient id="wgB" x1="0" x2="1">
              <stop offset="0%"   stopColor={C.electric} stopOpacity="0" />
              <stop offset="50%"  stopColor={C.electric} stopOpacity="1" />
              <stop offset="100%" stopColor={C.electric} stopOpacity="0" />
            </linearGradient>
          </defs>
          <path d="M-400,300 Q0,200 400,300 T1200,300 T2000,300"
            stroke="url(#wgA)" strokeWidth="1.5" fill="none"
            style={{ animation: 'waveShift 22s linear infinite' }} />
          <path d="M-400,450 Q0,350 400,450 T1200,450 T2000,450"
            stroke="url(#wgB)" strokeWidth="1.2" fill="none"
            style={{ animation: 'waveShift 28s linear infinite reverse' }} />
          <path d="M-400,600 Q0,500 400,600 T1200,600 T2000,600"
            stroke="url(#wgA)" strokeWidth="1" fill="none"
            style={{ animation: 'waveShift 35s linear infinite' }} />
          <path d="M-400,750 Q0,650 400,750 T1200,750 T2000,750"
            stroke="url(#wgB)" strokeWidth="0.8" fill="none"
            style={{ animation: 'waveShift 42s linear infinite reverse' }} />
        </svg>

        {/* Grain fin */}
        <div
          style={{
            position:         'absolute', inset: 0,
            opacity:          t.grainOpacity,
            backgroundImage:  "url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='200' height='200'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='1' stitchTiles='stitch'/></filter><rect width='100%25' height='100%25' filter='url(%23n)' opacity='0.8'/></svg>\")",
          }}
        />
      </div>
    </>
  )
}
