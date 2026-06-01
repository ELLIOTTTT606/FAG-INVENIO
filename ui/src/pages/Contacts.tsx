import { useEffect, useState }             from 'react'
import { useNavigate }                     from 'react-router-dom'
import { useTheme, C }                     from '../lib/theme'
import {
  loadMachine, loadProject, loadClient, loadSolution,
  saveContacts,
} from '../lib/sessionContext'
import type { DepartmentContacts, Client } from '../api/contacts'
import { fetchDepartmentContacts }         from '../api/contacts'
import {
  Reveal, PageTransition, Avatar, Spinner, MonoLabel,
} from '../components/ui/atoms'
import { BottomBar }                       from '../components/layout/Navigation'
import { getMediumLabel }  from '../lib/machines'
import { FranceMap }       from '../components/FranceMap'
import { NewClientModal }  from '../components/NewClientModal'
import { findDepartment }  from '../data/departments'

// ─────────────────────────────────────────────────────────────────────────────
export default function Contacts() {
  const { theme: t }  = useTheme()
  const navigate      = useNavigate()
  const machine       = loadMachine()
  const project       = loadProject()
  const client        = loadClient()
  const solution      = loadSolution()

  const [contacts,   setContacts]   = useState<DepartmentContacts | null>(null)
  const [loading,    setLoading]    = useState(true)
  const [error,      setError]      = useState<string | null>(null)
  const [dept,       setDept]       = useState(client?.department ?? '')
  const [modalOpen,  setModalOpen]  = useState(false)

  // Charger les contacts depuis Baserow
  useEffect(() => {
    if (!dept) { setLoading(false); return }
    const ctrl = new AbortController()
    setLoading(true)
    setError(null)
    fetchDepartmentContacts(dept, ctrl.signal)
      .then(data => {
        setContacts(data)
        saveContacts(data)
      })
      .catch(err => {
        if (err.name !== 'AbortError') setError('Impossible de charger les contacts.')
      })
      .finally(() => setLoading(false))
    return () => ctrl.abort()
  }, [dept])

  const canNext = !loading && (contacts?.tci != null || contacts?.tcs != null)

  const handleNext = () => {
    navigate('/options')
  }

  // ─────────────────────────────────────────────────────────────────────────
  return (
    <PageTransition pgKey="contacts">
      <main style={{ minHeight: '100vh', padding: '120px 48px 140px' }}>
        <div style={{ maxWidth: 1400, margin: '0 auto' }}>

          {/* ── En-tête ── */}
          <Reveal delay={50}>
            <MonoLabel style={{ marginBottom: 24 }}>
              <span style={{ width: 24, height: 1, background: t.muted }} />
              Étape 03 · Contacts France Air
            </MonoLabel>
          </Reveal>

          <Reveal delay={120}>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 24, flexWrap: 'wrap', marginBottom: 12 }}>
              <h1
                style={{
                  fontSize:      'clamp(40px, 6vw, 80px)',
                  fontWeight:    700,
                  letterSpacing: '-0.035em',
                  lineHeight:    1,
                  color:         t.text,
                  margin:        0,
                }}
              >
                {client?.name || 'Client'}
              </h1>
              {dept && (
                <div
                  style={{
                    fontFamily:    "'JetBrains Mono', ui-monospace, monospace",
                    fontSize:      18, fontWeight: 600,
                    color:         t.accent, letterSpacing: '0.05em',
                  }}
                >
                  · DEPT {dept}
                </div>
              )}
            </div>
          </Reveal>

          <Reveal delay={200}>
            <div
              style={{
                fontFamily:    "'JetBrains Mono', ui-monospace, monospace",
                fontSize:      14, color: t.dim,
                letterSpacing: '0.03em', marginBottom: 60,
              }}
            >
              {machine
                ? `${machine.model} ${machine.size} — ${machine.family ?? ''} ${getMediumLabel(machine.medium)}`
                : '—'}
              {project?.name ? ` · Projet ${project.name}` : ''}
            </div>
          </Reveal>

          {/* ── Carte France ── */}
          <Reveal delay={240}>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 32, flexWrap: 'wrap', marginBottom: 40 }}>
              <div style={{ flex: '0 0 auto' }}>
                <FranceMap selected={dept} onSelect={setDept} />
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12, paddingTop: 8 }}>
                <button
                  data-testid="open-new-client"
                  onClick={() => setModalOpen(true)}
                  style={{
                    padding:      '10px 20px',
                    borderRadius: 10,
                    border:       `1px solid ${t.border}`,
                    background:   t.surface,
                    color:        t.text,
                    fontSize:     13,
                    fontWeight:   600,
                    cursor:       'pointer',
                    fontFamily:   'inherit',
                  }}
                >
                  + Nouveau client
                </button>
              </div>
            </div>
          </Reveal>

          <NewClientModal
            open={modalOpen}
            onClose={() => setModalOpen(false)}
            onSaved={(c: Client) => { setDept(c.department) }}
          />

          {/* ── Heading département ── */}
          {dept && (
            <Reveal delay={250}>
              <h2
                style={{
                  fontSize: 22, fontWeight: 700, color: t.text,
                  marginBottom: 24,
                  fontFamily: "'JetBrains Mono', ui-monospace, monospace",
                }}
              >
                {dept} · {findDepartment(dept)?.name ?? dept}
              </h2>
            </Reveal>
          )}

          {/* ── Contenu ── */}
          {loading ? (
            <div style={{ padding: '60px 0' }}>
              <Spinner label={`Chargement des contacts · Dépt. ${dept}`} />
            </div>
          ) : error ? (
            <ErrorBanner message={error} />
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 32 }}>

              {/* Contact Solution (si présent en session) */}
              {solution && (
                <Reveal delay={280}>
                  <SolutionCard contact={solution} />
                </Reveal>
              )}

              {/* TCI + TCS */}
              <div
                style={{
                  display:             'grid',
                  gridTemplateColumns: 'repeat(auto-fill, minmax(380px, 1fr))',
                  gap:                 20,
                }}
              >
                {contacts?.tci && (
                  <Reveal delay={360}>
                    <ContactCard contact={contacts.tci} role="TCI" dept={dept} />
                  </Reveal>
                )}
                {contacts?.tcs && (
                  <Reveal delay={460}>
                    <ContactCard contact={contacts.tcs} role="TCS" dept={dept} />
                  </Reveal>
                )}
                {contacts?.solution && !solution && (
                  <Reveal delay={560}>
                    <SolutionCard contact={contacts.solution} />
                  </Reveal>
                )}
              </div>

              {/* Aucun contact trouvé */}
              {!contacts?.tci && !contacts?.tcs && (
                <Reveal delay={280}>
                  <div
                    style={{
                      padding:      32,
                      borderRadius: 16,
                      background:   `${C.ferrari}08`,
                      border:       `1px solid ${C.ferrari}25`,
                      color:        C.ferrari,
                      fontSize:     15,
                    }}
                  >
                    Aucun contact TCI/TCS trouvé pour le département {dept}.
                    Vérifiez les données dans Baserow → table « Contacts FORCE DE VENTE ».
                  </div>
                </Reveal>
              )}
            </div>
          )}
        </div>
      </main>

      <BottomBar
        onBack={() => navigate('/projet')}
        onNext={handleNext}
        canNext={canNext}
        nextLabel="Continuer"
        wide
      />
    </PageTransition>
  )
}

// ── Carte contact TCI / TCS ────────────────────────────────────────────────────
interface ContactInfo {
  name?:  string | null
  email?: string | null
  phone?: string | null
}

function ContactCard({ contact, role, dept }: { contact: ContactInfo; role: string; dept: string }) {
  const { theme: t } = useTheme()
  const [hov, setHov] = useState(false)

  return (
    <div
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        padding:      '28px 32px',
        borderRadius: 16,
        background:   t.surface,
        backdropFilter: 'blur(16px)',
        WebkitBackdropFilter: 'blur(16px)',
        border:       `1px solid ${hov ? t.accent : t.border}`,
        transition:   'all 0.3s cubic-bezier(0.22,1,0.36,1)',
        transform:    hov ? 'translateY(-2px)' : 'none',
      }}
    >
      {/* Header */}
      <div
        style={{
          display:       'flex',
          justifyContent:'space-between',
          alignItems:    'center',
          marginBottom:  20,
          paddingBottom: 16,
          borderBottom:  `1px solid ${t.border}`,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <Avatar name={contact.name ?? '?'} size={44} />
          <div>
            <h3
              style={{
                fontFamily:    "'JetBrains Mono', ui-monospace, monospace",
                fontSize:      10, letterSpacing: '0.15em',
                color:         t.muted, textTransform: 'uppercase', marginBottom: 4,
                fontWeight:    600, margin: '0 0 4px',
              }}
            >
              {role}
            </h3>
            <div style={{ fontSize: 18, fontWeight: 700, color: t.text }}>
              {contact.name ?? '—'}
            </div>
          </div>
        </div>
        {dept && (
          <span
            style={{
              fontFamily:    "'JetBrains Mono', ui-monospace, monospace",
              fontSize:      13, fontWeight: 600,
              color:         t.accent, letterSpacing: '0.05em',
            }}
          >
            {dept}
          </span>
        )}
      </div>

      {/* Coordonnées */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {contact.phone && <ContactLine icon="phone" value={contact.phone} />}
        {contact.email && <ContactLine icon="email" value={contact.email} />}
      </div>
    </div>
  )
}

// ── Contact Solution ──────────────────────────────────────────────────────────
function SolutionCard({ contact }: { contact: ContactInfo }) {
  const { theme: t } = useTheme()

  return (
    <div
      style={{
        padding:         '24px 32px',
        borderRadius:    16,
        background:      `${t.accent}06`,
        border:          `1px solid ${t.accent}20`,
        display:         'flex',
        alignItems:      'center',
        gap:             20,
      }}
    >
      <Avatar name={contact.name ?? '?'} size={52} />
      <div style={{ flex: 1 }}>
        <div
          style={{
            fontFamily:    "'JetBrains Mono', ui-monospace, monospace",
            fontSize:      10, letterSpacing: '0.15em',
            color:         t.muted, textTransform: 'uppercase', marginBottom: 4,
          }}
        >
          Contact Solution
        </div>
        <h3 style={{ fontSize: 20, fontWeight: 700, color: t.text, margin: 0 }}>{contact.name}</h3>
        <div
          style={{
            fontFamily:    "'JetBrains Mono', ui-monospace, monospace",
            fontSize:      12, color: t.muted, marginTop: 4,
          }}
        >
          {contact.email}
        </div>
      </div>
      {contact.phone && (
        <a
          href={`tel:${contact.phone}`}
          style={{
            padding:      '10px 18px', borderRadius: 10,
            background:   t.surface, border: `1px solid ${t.border}`,
            color:        t.text, fontSize: 13, fontWeight: 600,
            textDecoration: 'none',
            fontFamily:   "'JetBrains Mono', ui-monospace, monospace",
          }}
        >
          {contact.phone}
        </a>
      )}
    </div>
  )
}

// ── Ligne de coordonnée ───────────────────────────────────────────────────────
function ContactLine({ icon, value }: { icon: 'phone' | 'email'; value: string }) {
  const { theme: t } = useTheme()
  const href = icon === 'phone' ? `tel:${value}` : `mailto:${value}`

  return (
    <a
      href={href}
      style={{
        display:    'flex', alignItems: 'center', gap: 12,
        color:      t.dim, textDecoration: 'none',
        fontSize:   14, transition: 'color 0.2s',
      }}
      onMouseEnter={e => { (e.currentTarget as HTMLElement).style.color = t.text }}
      onMouseLeave={e => { (e.currentTarget as HTMLElement).style.color = t.dim }}
    >
      {icon === 'phone'
        ? <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07A19.5 19.5 0 013.07 10.8a19.79 19.79 0 01-3.07-8.68A2 2 0 012 0h3a2 2 0 012 1.72 12.84 12.84 0 00.7 2.81 2 2 0 01-.45 2.11L6.09 7.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45 12.84 12.84 0 002.81.7A2 2 0 0122 14.92v2z" transform="scale(0.9) translate(1,1)"/></svg>
        : <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>
      }
      {value}
    </a>
  )
}

// ── Bannière d'erreur ─────────────────────────────────────────────────────────
function ErrorBanner({ message }: { message: string }) {
  return (
    <div
      style={{
        padding: '20px 24px', borderRadius: 12,
        background: `${C.ferrari}08`, border: `1px solid ${C.ferrari}25`,
        color: C.ferrari, fontSize: 14,
      }}
    >
      {message}
    </div>
  )
}
