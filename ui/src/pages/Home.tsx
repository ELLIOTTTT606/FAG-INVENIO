import { useCallback, useRef, useState } from 'react'
import { Link, useNavigate }             from 'react-router-dom'
import { useTheme, C }                   from '../lib/theme'
import { parseFilename }                 from '../lib/machines'
import { saveMachine, saveRecord }       from '../lib/sessionContext'
import { parseFile as apiParseFile }     from '../api/client'
import { Reveal, PageTransition }        from '../components/ui/atoms'

type UploadState = 'idle' | 'analyzing' | 'error'

export default function Home() {
  const { theme: t }         = useTheme()
  const navigate             = useNavigate()
  const fileRef              = useRef<HTMLInputElement>(null)
  const dragCounter          = useRef(0)

  const [drag,    setDrag]   = useState(false)
  const [state,   setState]  = useState<UploadState>('idle')
  const [progress,setProgress] = useState(0)
  const [filename, setFilename] = useState<string | null>(null)
  const [error,   setError]  = useState<string | null>(null)

  // ── Traitement du fichier ──────────────────────────────────────────────────
  const processFile = useCallback(async (file: File) => {
    if (!['.docx', '.doc', '.pdf'].some(ext => file.name.toLowerCase().endsWith(ext))) {
      setError('Format non supporté. Déposez un fichier .docx ou .pdf.')
      return
    }

    setFilename(file.name)
    setState('analyzing')
    setError(null)
    setProgress(0)

    // Progression simulée pendant l'appel API
    const interval = setInterval(() => {
      setProgress(p => Math.min(p + 3, 90))
    }, 80)

    try {
      const result = await apiParseFile(file)
      clearInterval(interval)
      setProgress(100)

      // Sauvegarder le record parsé
      saveRecord(result.data)

      // Détecter le modèle depuis le nom de fichier
      const detected = parseFilename(file.name)

      saveMachine({
        model:    detected.model    ?? '',
        size:     detected.size     ?? '',
        family:   detected.family,
        acoustic: detected.acoustic,
        medium:   'air_eau',         // valeur par défaut, sera précisée à l'étape Machine
      })

      // Légère pause pour l'animation de complétion
      setTimeout(() => navigate('/machine'), 400)
    } catch {
      clearInterval(interval)
      setState('error')
      setError("Impossible d'analyser ce fichier. Vérifiez qu'il s'agit bien d'une fiche GALLETTI.")
    }
  }, [navigate])

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) processFile(e.target.files[0])
  }

  // ── Drag & Drop ────────────────────────────────────────────────────────────
  const onDragEnter  = (e: React.DragEvent) => { e.preventDefault(); dragCounter.current++; setDrag(true) }
  const onDragLeave  = (e: React.DragEvent) => { e.preventDefault(); dragCounter.current--; if (!dragCounter.current) setDrag(false) }
  const onDragOver   = (e: React.DragEvent) => e.preventDefault()
  const onDrop       = (e: React.DragEvent) => {
    e.preventDefault()
    dragCounter.current = 0
    setDrag(false)
    if (e.dataTransfer.files?.[0]) processFile(e.dataTransfer.files[0])
  }

  // ─────────────────────────────────────────────────────────────────────────
  return (
    <PageTransition pgKey="home">
      <main
        style={{
          minHeight:      '100vh',
          display:        'flex',
          flexDirection:  'column',
          alignItems:     'center',
          justifyContent: 'center',
          padding:        '100px 24px 80px',
        }}
      >
        {state === 'analyzing' ? (
          /* ── Écran d'analyse ── */
          <AnalyzingScreen filename={filename!} progress={progress} />
        ) : (
          /* ── Landing ── */
          <div style={{ maxWidth: 640, width: '100%', textAlign: 'center' }}>
            <Reveal delay={0}>
              <div
                style={{
                  display:        'inline-flex',
                  alignItems:     'center',
                  gap:            8,
                  padding:        '8px 18px',
                  borderRadius:   999,
                  background:     `${t.accent}12`,
                  border:         `1px solid ${t.accent}30`,
                  marginBottom:   32,
                  fontFamily:     "'JetBrains Mono', ui-monospace, monospace",
                  fontSize:       11,
                  letterSpacing:  '0.15em',
                  textTransform:  'uppercase',
                  color:          t.accent,
                }}
              >
                <span
                  style={{
                    width: 6, height: 6, borderRadius: '50%',
                    background: '#22c55e',
                    animation: 'pulseDot 2s ease-in-out infinite',
                  }}
                />
                Détection automatique active
              </div>
            </Reveal>

            <Reveal delay={80}>
              <h1
                style={{
                  fontSize:      'clamp(48px, 8vw, 88px)',
                  fontWeight:    800,
                  letterSpacing: '-0.045em',
                  lineHeight:    0.9,
                  color:         t.text,
                  margin:        '0 0 24px',
                }}
              >
                Votre fiche<br />
                <span style={{ color: t.accent }}>INVENIO.</span>
              </h1>
            </Reveal>

            <Reveal delay={180}>
              <p style={{ fontSize: 17, color: t.dim, lineHeight: 1.6, marginBottom: 52 }}>
                Importez une fiche GALLETTI en .docx ou .pdf.<br />
                INVENIO extrait, restructure et génère votre fiche au design France Air.
              </p>
            </Reveal>

            {/* CTA principal */}
            <Reveal delay={240}>
              <Link
                to="/import"
                style={{
                  display:        'inline-block',
                  padding:        '16px 40px',
                  borderRadius:   14,
                  background:     t.accent,
                  color:          t.mode === 'dark' ? t.bg : '#fff',
                  textDecoration: 'none',
                  fontSize:       16,
                  fontWeight:     700,
                  marginBottom:   32,
                  boxShadow:      `0 8px 32px ${t.accent}30`,
                }}
              >
                Générer ma fiche
              </Link>
            </Reveal>

            {/* Dropzone */}
            <Reveal delay={280}>
              <div
                onClick={() => fileRef.current?.click()}
                onDragEnter={onDragEnter}
                onDragLeave={onDragLeave}
                onDragOver={onDragOver}
                onDrop={onDrop}
                style={{
                  padding:       '52px 40px',
                  borderRadius:  20,
                  border:        `2px dashed ${drag ? t.accent : t.borderStrong}`,
                  background:    drag ? `${t.accent}08` : t.surface,
                  backdropFilter:'blur(16px)',
                  WebkitBackdropFilter:'blur(16px)',
                  cursor:        'pointer',
                  transition:    'all 0.3s cubic-bezier(0.22,1,0.36,1)',
                  boxShadow:     drag ? `0 20px 60px ${t.accent}20` : 'none',
                }}
              >
                <input
                  ref={fileRef}
                  type="file"
                  accept=".pdf,.docx,.doc"
                  style={{ display: 'none' }}
                  onChange={handleFileInput}
                />

                {/* Icône */}
                <div
                  style={{
                    width:          64, height: 64, borderRadius: 16,
                    background:     `linear-gradient(135deg, ${t.accent}, ${t.accent}bb)`,
                    display:        'flex', alignItems: 'center', justifyContent: 'center',
                    margin:         '0 auto 24px',
                    boxShadow:      `0 12px 40px ${t.accent}30`,
                    transform:      drag ? 'scale(1.1) translateY(-4px)' : 'scale(1)',
                    transition:     'transform 0.3s',
                  }}
                >
                  <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2">
                    <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12" />
                  </svg>
                </div>

                <div style={{ fontSize: 20, fontWeight: 600, color: t.text, marginBottom: 8 }}>
                  {drag ? 'Relâchez pour importer' : 'Déposez votre fichier'}
                </div>
                <div style={{ fontSize: 14, color: t.dim }}>
                  ou cliquez pour parcourir · .pdf .docx
                </div>
              </div>
            </Reveal>

            {/* Erreur */}
            {error && (
              <Reveal delay={0}>
                <div
                  style={{
                    marginTop:    20,
                    padding:      '14px 18px',
                    borderRadius: 12,
                    background:   `${C.ferrari}10`,
                    border:       `1px solid ${C.ferrari}30`,
                    color:        C.ferrari,
                    fontSize:     14,
                  }}
                >
                  {error}
                </div>
              </Reveal>
            )}

            {/* Sélection manuelle */}
            <Reveal delay={380}>
              <button
                onClick={() => navigate('/machine')}
                style={{
                  marginTop:  24,
                  background: 'none',
                  border:     'none',
                  color:      t.dim,
                  fontSize:   14,
                  cursor:     'pointer',
                  fontFamily: 'inherit',
                  display:    'flex',
                  alignItems: 'center',
                  gap:        8,
                  padding:    0,
                  margin:     '24px auto 0',
                  transition: 'color 0.2s',
                }}
                onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.color = t.text }}
                onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.color = t.dim }}
              >
                Sélection manuelle
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M5 12h14M12 5l7 7-7 7" />
                </svg>
              </button>
            </Reveal>
          </div>
        )}
      </main>
    </PageTransition>
  )
}

// ── Écran d'analyse avec barre de progression ─────────────────────────────────
function AnalyzingScreen({ filename, progress }: { filename: string; progress: number }) {
  const { theme: t } = useTheme()

  return (
    <div
      style={{
        display:        'flex',
        flexDirection:  'column',
        alignItems:     'center',
        justifyContent: 'center',
        textAlign:      'center',
        maxWidth:        500,
        gap:            0,
      }}
    >
      {/* Cercles pulsants */}
      <div style={{ position: 'relative', width: 120, height: 120, marginBottom: 40 }}>
        {[0, 1, 2].map(i => (
          <div
            key={i}
            style={{
              position:     'absolute',
              inset:        i * 12,
              borderRadius: '50%',
              border:       `1.5px solid ${t.accent}`,
              opacity:      0.3 - i * 0.08,
              animation:    `pulseRing 2.4s ease-out infinite ${i * 0.6}s`,
            }}
          />
        ))}
        <div
          style={{
            position:       'absolute', inset: 0,
            display:        'flex', alignItems: 'center', justifyContent: 'center',
          }}
        >
          <div
            style={{
              width: 72, height: 72, borderRadius: '50%',
              background:  `linear-gradient(135deg, ${t.accent}, ${t.accent}dd)`,
              display:     'flex', alignItems: 'center', justifyContent: 'center',
              boxShadow:   `0 12px 40px ${t.accent}40`,
            }}
          >
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="1.5">
              <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8zM14 2v6h6M16 13H8M16 17H8M10 9H8" />
            </svg>
          </div>
        </div>
      </div>

      <div
        style={{
          fontFamily:    "'JetBrains Mono', ui-monospace, monospace",
          fontSize:      11, letterSpacing: '0.15em',
          color:         t.muted, textTransform: 'uppercase', marginBottom: 12,
        }}
      >
        Analyse en cours
      </div>
      <h2 style={{ fontSize: 24, fontWeight: 600, color: t.text, marginBottom: 40 }}>
        {filename}
      </h2>

      {/* Barre de progression */}
      <div style={{ width: '100%', maxWidth: 360, display: 'flex', alignItems: 'center', gap: 16 }}>
        <div
          style={{
            flex: 1, height: 2, background: t.border, borderRadius: 2, overflow: 'hidden',
          }}
        >
          <div
            style={{
              height:          '100%',
              background:      `linear-gradient(90deg, ${t.accent}, ${t.accent}bb, ${t.accent})`,
              width:           `${progress}%`,
              transition:      'width 0.15s linear',
              backgroundSize:  '200% 100%',
              animation:       'bgMove 2s linear infinite',
            }}
          />
        </div>
        <div
          style={{
            fontFamily: "'JetBrains Mono', ui-monospace, monospace",
            fontSize:   13, color: t.text, minWidth: 40, textAlign: 'right', fontWeight: 600,
          }}
        >
          {Math.round(progress)}%
        </div>
      </div>
    </div>
  )
}
