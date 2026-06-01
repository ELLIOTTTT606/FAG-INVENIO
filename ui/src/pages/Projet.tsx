import { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate }                              from 'react-router-dom'
import { useTheme }                                 from '../lib/theme'
import {
  loadMachine, loadProject, loadClient, loadSolution,
  saveProject, saveClient, saveSolution,
} from '../lib/sessionContext'
import type { ProjectState, ClientState, SolutionContact } from '../lib/sessionContext'
import {
  Reveal, PageTransition, GhostInput, GhostSelect, Avatar, LiveField, MonoLabel,
} from '../components/ui/atoms'
import { BottomBar }                                from '../components/layout/Navigation'
import { searchClients }                            from '../api/contacts'
import type { Client }                              from '../api/contacts'

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────
const SOLUTION_CONTACTS: SolutionContact[] = [
  { name: 'Stéphane MOUREAUX', email: 'stephane.moureaux@france-air.com',  phone: '' },
  { name: 'Pierre-Yves BERCAND', email: 'pyves.bercand@france-air.com',    phone: '' },
  { name: 'Elliot DUMONT',     email: 'elliot.dumont@france-air.com',      phone: '' },
  { name: 'Linda MESSAHEL',    email: 'linda.messahel@france-air.com',     phone: '' },
  { name: 'Corentin PERRARD',  email: 'corentin.perard@france-air.com',    phone: '' },
  { name: 'Clara MISTON',      email: 'clara.miston@france-air.com',       phone: '' },
]

// ─────────────────────────────────────────────────────────────────────────────
export default function Projet() {
  const { theme: t } = useTheme()
  const navigate     = useNavigate()
  const machine      = loadMachine()

  // ── État du formulaire ────────────────────────────────────────────────────
  const savedProject  = loadProject()
  const savedClient   = loadClient()
  const savedSolution = loadSolution()

  const [projectNumber, setProjectNumber] = useState(savedProject?.number ?? '')
  const [projectName,   setProjectName]   = useState(savedProject?.name   ?? '')
  const [clientQuery,   setClientQuery]   = useState(savedClient?.name    ?? '')
  const [client,        setClient]        = useState<ClientState | null>(savedClient ?? null)
  const [solutionName,  setSolutionName]  = useState(savedSolution?.name  ?? '')

  // ── Autocomplete client ───────────────────────────────────────────────────
  const [suggestions,   setSuggestions]  = useState<Client[]>([])
  const [showDropdown,  setShowDropdown] = useState(false)
  const [loadingSearch, setLoadingSearch] = useState(false)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)

  const handleClientInput = useCallback((value: string) => {
    setClientQuery(value)
    setClient(null) // désélectionne si on retape

    if (debounceRef.current) clearTimeout(debounceRef.current)

    if (value.length < 2) {
      setSuggestions([])
      setShowDropdown(false)
      return
    }

    debounceRef.current = setTimeout(async () => {
      setLoadingSearch(true)
      try {
        const results = await searchClients(value)
        setSuggestions(results)
        setShowDropdown(true)
      } catch {
        setSuggestions([])
      } finally {
        setLoadingSearch(false)
      }
    }, 300)
  }, [])

  const selectClient = (c: Client) => {
    const dept = c.department ?? c.postal_code?.slice(0, 2) ?? ''
    const cs: ClientState = {
      id:         c.id ?? null,
      code:       c.client_code,
      name:       c.client_name,
      postalCode: c.postal_code ?? '',
      department: dept,
    }
    setClient(cs)
    setClientQuery(c.client_name)
    setSuggestions([])
    setShowDropdown(false)
  }

  // Fermer le dropdown en cliquant ailleurs
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setShowDropdown(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  // ── Navigation ────────────────────────────────────────────────────────────
  const canNext =
    projectName.trim().length > 0 &&
    (client !== null) &&
    solutionName.length > 0

  const handleNext = () => {
    if (!canNext) return
    saveProject({ number: projectNumber, name: projectName })
    saveClient(client!)
    const sol = SOLUTION_CONTACTS.find(c => c.name === solutionName)
    if (sol) saveSolution(sol)
    navigate('/contacts')
  }

  const selectedSolution = SOLUTION_CONTACTS.find(c => c.name === solutionName)

  // ─────────────────────────────────────────────────────────────────────────
  return (
    <PageTransition pgKey="projet">
      <main style={{ minHeight: '100vh', padding: '120px 48px 140px' }}>
        <div
          style={{
            maxWidth:            1400,
            margin:              '0 auto',
            display:             'grid',
            gridTemplateColumns: '1.1fr 1fr',
            gap:                 100,
            alignItems:          'start',
          }}
        >
          {/* ── Formulaire gauche ── */}
          <div>
            <Reveal delay={50}>
              <MonoLabel style={{ marginBottom: 24 }}>
                <span style={{ width: 24, height: 1, background: t.muted }} />
                Étape 02 · Projet &amp; client
              </MonoLabel>
            </Reveal>

            <Reveal delay={150}>
              <h1
                style={{
                  fontSize:      'clamp(44px, 6vw, 88px)',
                  fontWeight:    700,
                  letterSpacing: '-0.03em',
                  lineHeight:    0.95,
                  color:         t.text,
                  margin:        '0 0 56px',
                }}
              >
                Parlez-nous<br />du projet.
              </h1>
            </Reveal>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 36 }}>

              {/* 01 · Projet */}
              <Reveal delay={280}>
                <div>
                  <MonoLabel style={{ marginBottom: 16 }}>01 · Projet</MonoLabel>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 32 }}>
                    <GhostInput
                      value={projectNumber}
                      onChange={e => setProjectNumber(e.target.value)}
                      placeholder="N° projet — 2026-0142"
                    />
                    <GhostInput
                      value={projectName}
                      onChange={e => setProjectName(e.target.value)}
                      placeholder="Nom du projet"
                    />
                  </div>
                </div>
              </Reveal>

              {/* 02 · Client avec autocomplete */}
              <Reveal delay={380}>
                <div>
                  <MonoLabel style={{ marginBottom: 16 }}>02 · Client</MonoLabel>

                  {/* Champ de recherche avec dropdown */}
                  <div ref={dropdownRef} style={{ position: 'relative', marginBottom: 16 }}>
                    <GhostInput
                      value={clientQuery}
                      onChange={e => handleClientInput(e.target.value)}
                      placeholder="Nom ou code client (2 caractères min.)"
                      style={{ paddingRight: loadingSearch ? 32 : 0 }}
                    />

                    {/* Indicateur chargement */}
                    {loadingSearch && (
                      <div
                        style={{
                          position: 'absolute', right: 8, top: '50%', transform: 'translateY(-50%)',
                          width: 16, height: 16, borderRadius: '50%',
                          border: `2px solid ${t.border}`, borderTopColor: t.accent,
                          animation: 'spin 0.7s linear infinite',
                        }}
                      />
                    )}

                    {/* Dropdown suggestions */}
                    {showDropdown && suggestions.length > 0 && (
                      <div
                        style={{
                          position:     'absolute',
                          top:          'calc(100% + 8px)',
                          left:         0, right: 0,
                          zIndex:       50,
                          background:   t.mode === 'dark' ? '#0f172a' : '#ffffff',
                          border:       `1px solid ${t.border}`,
                          borderRadius: 12,
                          boxShadow:    '0 16px 48px rgba(0,0,0,0.12)',
                          overflow:     'hidden',
                          maxHeight:    240,
                          overflowY:    'auto',
                        }}
                      >
                        {suggestions.map((c, i) => (
                          <SuggestionRow
                            key={c.id ?? i}
                            client={c}
                            onSelect={() => selectClient(c)}
                          />
                        ))}
                      </div>
                    )}

                    {showDropdown && !loadingSearch && suggestions.length === 0 && clientQuery.length >= 2 && (
                      <div
                        style={{
                          position:     'absolute',
                          top:          'calc(100% + 8px)',
                          left:         0, right: 0,
                          padding:      '16px 20px',
                          background:   t.mode === 'dark' ? '#0f172a' : '#ffffff',
                          border:       `1px solid ${t.border}`,
                          borderRadius: 12,
                          fontSize:     14, color: t.muted,
                          fontStyle:    'italic',
                        }}
                      >
                        Aucun client trouvé pour « {clientQuery} »
                      </div>
                    )}
                  </div>

                  {/* Client sélectionné */}
                  {client && (
                    <div
                      style={{
                        padding:      '14px 18px',
                        borderRadius: 12,
                        background:   `${t.accent}08`,
                        border:       `1px solid ${t.accent}25`,
                        display:      'flex',
                        alignItems:   'center',
                        justifyContent: 'space-between',
                        gap:          12,
                      }}
                    >
                      <div>
                        <div style={{ fontWeight: 600, color: t.text, fontSize: 15 }}>{client.name}</div>
                        <div
                          style={{
                            fontFamily: "'JetBrains Mono', ui-monospace, monospace",
                            fontSize:   11, color: t.muted, marginTop: 4,
                          }}
                        >
                          {client.code} · {client.postalCode} · Dép. {client.department}
                        </div>
                      </div>
                      <button
                        onClick={() => { setClient(null); setClientQuery('') }}
                        style={{
                          background: 'none', border: 'none', cursor: 'pointer',
                          color: t.muted, fontSize: 18, lineHeight: 1, padding: 4,
                        }}
                        title="Changer de client"
                      >
                        ×
                      </button>
                    </div>
                  )}
                </div>
              </Reveal>

              {/* 03 · Contact Solution */}
              <Reveal delay={480}>
                <div>
                  <MonoLabel style={{ marginBottom: 16 }}>03 · Contact solution</MonoLabel>
                  <GhostSelect
                    value={solutionName}
                    onChange={e => setSolutionName(e.target.value)}
                  >
                    <option value="">Choisir un collaborateur —</option>
                    {SOLUTION_CONTACTS.map(c => (
                      <option key={c.name} value={c.name}>{c.name}</option>
                    ))}
                  </GhostSelect>

                  {selectedSolution && (
                    <div
                      style={{
                        marginTop:  16,
                        display:    'flex',
                        alignItems: 'center',
                        gap:        14,
                        padding:    '14px 18px',
                        borderRadius: 12,
                        background: t.surface,
                        border:     `1px solid ${t.border}`,
                      }}
                    >
                      <Avatar name={selectedSolution.name} size={36} />
                      <div>
                        <div style={{ fontSize: 14, fontWeight: 600, color: t.text }}>
                          {selectedSolution.name}
                        </div>
                        <div
                          style={{
                            fontFamily: "'JetBrains Mono', ui-monospace, monospace",
                            fontSize:   11, color: t.muted, marginTop: 2,
                          }}
                        >
                          {selectedSolution.email}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </Reveal>
            </div>
          </div>

          {/* ── Aperçu temps réel droite ── */}
          <Reveal delay={350} y={30}>
            <div
              style={{
                position:            'sticky',
                top:                 120,
                padding:             40,
                borderRadius:        20,
                background:          t.surface,
                backdropFilter:      'blur(20px)',
                WebkitBackdropFilter:'blur(20px)',
                border:              `1px solid ${t.border}`,
                aspectRatio:         '1/1.25',
                display:             'flex',
                flexDirection:       'column',
              }}
            >
              <MonoLabel style={{ marginBottom: 8 }}>Aperçu · fiche</MonoLabel>
              <p style={{ fontSize: 12, color: t.muted, marginBottom: 28 }}>Mise à jour en temps réel</p>

              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 16 }}>
                {machine && (
                  <>
                    <LiveField label="Machine" mono>
                      {machine.model} {machine.size}
                    </LiveField>
                    <LiveField label="Type" mono>
                      {machine.family ?? '—'}
                    </LiveField>
                    <div style={{ height: 1, background: t.border }} />
                  </>
                )}
                <LiveField label="N° projet" mono>{projectNumber || '—'}</LiveField>
                <LiveField label="Projet">{projectName  || '—'}</LiveField>
                <LiveField label="Client">{client?.name || '—'}</LiveField>
                <LiveField label="Dept." mono>{client?.department || '—'}</LiveField>
                {selectedSolution && (
                  <>
                    <div style={{ height: 1, background: t.border }} />
                    <LiveField label="Solution">{selectedSolution.name}</LiveField>
                  </>
                )}
              </div>
            </div>
          </Reveal>

        </div>
      </main>

      <BottomBar
        onBack={() => navigate('/machine')}
        onNext={handleNext}
        canNext={canNext}
        wide
      />

      <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
    </PageTransition>
  )
}

// ── Ligne de suggestion client ─────────────────────────────────────────────────
function SuggestionRow({ client, onSelect }: { client: Client; onSelect: () => void }) {
  const { theme: t } = useTheme()
  const [hov, setHov] = useState(false)
  const dept = client.department ?? client.postal_code?.slice(0, 2) ?? ''

  return (
    <button
      onClick={onSelect}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        width:          '100%',
        padding:        '12px 20px',
        background:     hov ? `${t.accent}10` : 'transparent',
        border:         'none',
        cursor:         'pointer',
        textAlign:      'left',
        display:        'flex',
        alignItems:     'center',
        justifyContent: 'space-between',
        gap:            12,
        fontFamily:     'inherit',
        transition:     'background 0.15s',
      }}
    >
      <div>
        <div style={{ fontSize: 14, fontWeight: 500, color: t.text }}>{client.client_name}</div>
        <div
          style={{
            fontFamily: "'JetBrains Mono', ui-monospace, monospace",
            fontSize:   11, color: t.muted, marginTop: 2,
          }}
        >
          {client.client_code}
        </div>
      </div>
      {dept && (
        <span
          style={{
            fontFamily:    "'JetBrains Mono', ui-monospace, monospace",
            fontSize:      11,
            padding:       '3px 8px',
            borderRadius:  6,
            background:    `${t.accent}15`,
            color:         t.accent,
            flexShrink:    0,
          }}
        >
          Dép. {dept}
        </span>
      )}
    </button>
  )
}
