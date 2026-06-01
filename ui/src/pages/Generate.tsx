import { useState, useEffect, useCallback } from 'react'
import { Link, useNavigate }               from 'react-router-dom'
import { useTheme, C }                     from '../lib/theme'
import {
  readImport, loadOptions, loadContacts, clearSession,
} from '../lib/sessionContext'
import { Reveal, PageTransition, MonoLabel } from '../components/ui/atoms'
import { BottomBar }                         from '../components/layout/Navigation'

const BASE = import.meta.env.VITE_API_URL || ''

export default function Generate() {
  const { theme: t } = useTheme()
  const navigate     = useNavigate()

  const ctx          = readImport()
  const optionCodes  = loadOptions()
  const contacts     = loadContacts()

  const [previewHtml, setPreviewHtml] = useState<string | null>(null)
  const [pdfError,    setPdfError]    = useState<string | null>(null)
  const [downloading, setDownloading] = useState(false)

  useEffect(() => {
    if (!ctx) return
    fetch(`${BASE}/generate/preview`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ record: ctx.record, option_codes: optionCodes }),
    })
      .then(r => r.ok ? r.text() : Promise.reject(r))
      .then(html => setPreviewHtml(html))
      .catch(() => { /* preview unavailable */ })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleDownload = useCallback(async () => {
    if (!ctx) return
    setDownloading(true)
    setPdfError(null)
    try {
      const r = await fetch(`${BASE}/generate/pdf`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ record: ctx.record, option_codes: optionCodes }),
      })
      if (r.status === 503) {
        setPdfError('WeasyPrint non disponible sur ce serveur.')
        return
      }
      if (!r.ok) throw new Error(`Erreur ${r.status}`)
      const disposition = r.headers.get('Content-Disposition') ?? ''
      const filename = disposition.match(/filename="?([^";\s]+)"?/)?.[1] ?? 'INVENIO.pdf'
      const blob = await r.blob()
      const url  = URL.createObjectURL(blob)
      const a    = document.createElement('a')
      a.href     = url
      a.download = filename
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      if (!pdfError) setPdfError(err instanceof Error ? err.message : 'Erreur inconnue')
    } finally {
      setDownloading(false)
    }
  }, [ctx, optionCodes, pdfError])

  const handleReset = () => { clearSession(); navigate('/') }

  // ── État vide ────────────────────────────────────────────────────────────────
  if (!ctx) {
    return (
      <PageTransition pgKey="generate">
        <main style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '120px 24px' }}>
          <p style={{ fontSize: 18, color: t.dim, marginBottom: 24 }}>
            Aucune fiche en cours
          </p>
          <Link
            to="/import"
            style={{
              padding:        '12px 28px',
              borderRadius:   12,
              background:     t.accent,
              color:          t.mode === 'dark' ? t.bg : '#fff',
              textDecoration: 'none',
              fontWeight:     600,
              fontSize:       15,
            }}
          >
            Aller à l'import
          </Link>
        </main>
      </PageTransition>
    )
  }

  const { machine } = ctx
  const machineLabel = [machine.model, machine.size, machine.type].filter(Boolean).join(' ')

  // ── Vue principale ───────────────────────────────────────────────────────────
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
                fontWeight:    700,
                letterSpacing: '-0.035em',
                lineHeight:    1,
                color:         t.text,
                margin:        '0 0 52px',
              }}
            >
              Vérifiez et générez.
            </h1>
          </Reveal>

          {/* Récapitulatif */}
          <Reveal delay={180}>
            <div
              style={{
                padding:      24,
                borderRadius: 16,
                background:   t.surface,
                border:       `1px solid ${t.border}`,
                marginBottom: 32,
                display:      'flex',
                flexDirection:'column',
                gap:          8,
              }}
            >
              <p style={{ margin: 0, fontWeight: 600, color: t.text }}>{machineLabel}</p>
              <p style={{ margin: 0, color: t.dim }}>{optionCodes.length} option(s) retenues</p>
              {contacts?.department && (
                <p style={{ margin: 0, color: t.dim }}>Département {contacts.department}</p>
              )}
            </div>
          </Reveal>

          {/* Bouton télécharger */}
          <Reveal delay={220}>
            <button
              data-testid="download-pdf"
              onClick={handleDownload}
              disabled={downloading}
              style={{
                padding:    '14px 32px',
                borderRadius: 12,
                border:     'none',
                background: t.accent,
                color:      t.mode === 'dark' ? t.bg : '#fff',
                fontSize:   15,
                fontWeight: 700,
                cursor:     downloading ? 'wait' : 'pointer',
                fontFamily: 'inherit',
                marginBottom: 24,
              }}
            >
              {downloading ? 'Génération…' : 'Télécharger la fiche PDF'}
            </button>
          </Reveal>

          {/* Erreur PDF */}
          {pdfError && (
            <div
              role="alert"
              style={{
                padding:      '14px 20px',
                borderRadius: 12,
                background:   `${C.ferrari}08`,
                border:       `1px solid ${C.ferrari}25`,
                color:        C.ferrari,
                fontSize:     14,
                marginBottom: 24,
              }}
            >
              {pdfError}
            </div>
          )}

          {/* Aperçu HTML */}
          {previewHtml && (
            <Reveal delay={260}>
              <iframe
                data-testid="preview-frame"
                srcDoc={previewHtml}
                style={{
                  width:        '100%',
                  height:       800,
                  border:       `1px solid ${t.border}`,
                  borderRadius: 12,
                }}
                title="Aperçu fiche"
              />
            </Reveal>
          )}

        </div>
      </main>

      <BottomBar
        onBack={() => navigate('/options')}
        onReset={handleReset}
        wide
      />
    </PageTransition>
  )
}
