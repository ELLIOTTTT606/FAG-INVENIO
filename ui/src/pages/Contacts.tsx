import { useEffect, useState } from 'react'
import type { Client, DepartmentContacts } from '../api/contacts'
import { fetchDepartmentContacts } from '../api/contacts'
import { ClientSearch } from '../components/ClientSearch'
import { ContactCard } from '../components/ContactCard'
import { DepartmentPicker } from '../components/DepartmentPicker'
import { findDepartment } from '../data/departments'
import { rememberContacts } from '../lib/sessionContext'

type LoadStatus = 'idle' | 'loading' | 'ready' | 'error'

export default function Contacts() {
  const [department, setDepartment] = useState<string | null>(null)
  const [client, setClient] = useState<Client | null>(null)
  const [contacts, setContacts] = useState<DepartmentContacts | null>(null)
  const [status, setStatus] = useState<LoadStatus>('idle')

  useEffect(() => {
    if (!department) {
      setContacts(null)
      setStatus('idle')
      return
    }
    const controller = new AbortController()
    setStatus('loading')
    fetchDepartmentContacts(department, controller.signal)
      .then((next) => {
        if (controller.signal.aborted) return
        setContacts(next)
        rememberContacts(next)
        setStatus('ready')
      })
      .catch((err) => {
        if (controller.signal.aborted) return
        // eslint-disable-next-line no-console
        console.error(err)
        setStatus('error')
      })
    return () => controller.abort()
  }, [department])

  const handleClient = (selected: Client) => {
    setClient(selected)
    setDepartment(selected.department)
  }

  const departmentLabel = department
    ? `${department} · ${findDepartment(department)?.name ?? 'Département'}`
    : 'Sélectionnez un département'

  return (
    <section className="space-y-10">
      <div>
        <p className="text-sm uppercase tracking-widest text-accent">Étape 2 · Contacts</p>
        <h1 className="mt-2 text-3xl font-semibold md:text-4xl">
          Choisissez le client et les contacts France Air
        </h1>
        <p className="mt-3 max-w-2xl text-ink-muted">
          Recherchez un client existant ou sélectionnez un département. INVENIO
          renseigne automatiquement le TCI, le TCS et le contact Solution Habitat
          correspondants.
        </p>
      </div>

      <div className="grid gap-10 lg:grid-cols-[minmax(0,1fr),360px]">
        <div className="space-y-8">
          <ClientSearch onSelect={handleClient} />

          {client ? (
            <div className="rounded-2xl border border-accent/30 bg-accent-subtle/30 p-4 text-sm">
              <p className="font-medium">{client.client_name}</p>
              <p className="text-ink-muted">
                <code>{client.client_code}</code> · {client.postal_code} · département{' '}
                {client.department}
              </p>
            </div>
          ) : null}

          <DepartmentPicker selected={department} onSelect={setDepartment} />
        </div>

        <aside className="space-y-4">
          <header>
            <h2 className="text-lg font-semibold">{departmentLabel}</h2>
            <p className="text-xs text-ink-muted">
              Contacts France Air rattachés au département.
            </p>
          </header>

          {status === 'loading' ? (
            <p role="status" className="text-sm text-ink-muted">
              Chargement des contacts…
            </p>
          ) : null}
          {status === 'error' ? (
            <p role="alert" className="text-sm text-danger">
              Impossible de charger les contacts.
            </p>
          ) : null}

          {contacts ? (
            <div className="space-y-4">
              <ContactCard role="TCI" contact={contacts.tci} />
              <ContactCard role="TCS" contact={contacts.tcs} />
              <ContactCard role="Solution Habitat" contact={contacts.solution} />
            </div>
          ) : (
            <p className="rounded-2xl border border-dashed border-ink-muted/30 p-6 text-sm italic text-ink-muted">
              Aucun département sélectionné.
            </p>
          )}
        </aside>
      </div>
    </section>
  )
}
