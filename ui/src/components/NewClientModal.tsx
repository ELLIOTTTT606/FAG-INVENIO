import { useEffect, useMemo, useState } from 'react'
import { ApiError } from '../api/client'
import type { Client } from '../api/contacts'
import { createClient, updateClient } from '../api/contacts'
import { departmentFromPostalCode } from '../lib/postalCode'

interface Props {
  open: boolean
  onClose: () => void
  onSaved: (client: Client) => void
  initial?: Client | null
}

interface FormState {
  client_code: string
  client_name: string
  postal_code: string
  department: string
  departmentTouched: boolean
}

const EMPTY: FormState = {
  client_code: '',
  client_name: '',
  postal_code: '',
  department: '',
  departmentTouched: false,
}

const POSTAL_RE = /^\d{5}$/
const DEPARTMENT_RE = /^(2A|2B|\d{2,3})$/

function fromInitial(initial: Client | null | undefined): FormState {
  if (!initial) return EMPTY
  return {
    client_code: initial.client_code,
    client_name: initial.client_name,
    postal_code: initial.postal_code,
    department: initial.department,
    departmentTouched: true,
  }
}

export function NewClientModal({ open, onClose, onSaved, initial }: Props) {
  const isEdit = Boolean(initial?.id)
  const [form, setForm] = useState<FormState>(() => fromInitial(initial))
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!open) {
      setForm(EMPTY)
      setError(null)
      setSubmitting(false)
      return
    }
    setForm(fromInitial(initial))
    setError(null)
    setSubmitting(false)
  }, [open, initial])

  const derivedDepartment = useMemo(
    () => departmentFromPostalCode(form.postal_code),
    [form.postal_code],
  )

  const department = form.departmentTouched
    ? form.department
    : derivedDepartment ?? form.department

  const errors = useMemo(() => validate(form, department), [form, department])
  const canSubmit = !submitting && Object.keys(errors).length === 0

  if (!open) return null

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!canSubmit) return
    setSubmitting(true)
    setError(null)
    const payload: Client = {
      client_code: form.client_code.trim(),
      client_name: form.client_name.trim(),
      postal_code: form.postal_code.trim(),
      department: department.toUpperCase(),
    }
    try {
      const saved = isEdit && initial?.id
        ? await updateClient(initial.id, payload)
        : await createClient(payload)
      onSaved(saved)
      onClose()
    } catch (err) {
      const message = err instanceof ApiError
        ? err.message
        : isEdit
          ? 'Erreur réseau lors de la modification.'
          : 'Erreur réseau lors de la création.'
      setError(message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="new-client-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink-light/40 px-4 backdrop-blur-sm"
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose()
      }}
    >
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-md space-y-5 rounded-2xl bg-surface-light p-6 shadow-2xl"
      >
        <header className="space-y-1">
          <h2 id="new-client-title" className="text-xl font-semibold">
            {isEdit ? `Modifier ${initial?.client_name ?? 'le client'}` : 'Ajouter un nouveau client'}
          </h2>
          <p className="text-xs text-ink-muted">
            Sera enregistré dans Baserow (table CLIENTS) ou en mémoire selon la
            configuration.
          </p>
        </header>

        <Field label="Code client" htmlFor="client_code" hint="Identifiant unique (sera mis en majuscules)">
          <input
            id="client_code"
            name="client_code"
            value={form.client_code}
            onChange={(event) =>
              setForm((prev) => ({ ...prev, client_code: event.target.value }))
            }
            className="w-full rounded-xl border border-ink-muted/30 bg-transparent px-3 py-2 text-sm focus:border-accent focus:outline-none"
            required
          />
        </Field>

        <Field label="Nom du client" htmlFor="client_name">
          <input
            id="client_name"
            name="client_name"
            value={form.client_name}
            onChange={(event) =>
              setForm((prev) => ({ ...prev, client_name: event.target.value }))
            }
            className="w-full rounded-xl border border-ink-muted/30 bg-transparent px-3 py-2 text-sm focus:border-accent focus:outline-none"
            required
          />
        </Field>

        <div className="grid grid-cols-2 gap-3">
          <Field label="Code postal" htmlFor="postal_code">
            <input
              id="postal_code"
              name="postal_code"
              inputMode="numeric"
              maxLength={5}
              value={form.postal_code}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, postal_code: event.target.value }))
              }
              className="w-full rounded-xl border border-ink-muted/30 bg-transparent px-3 py-2 text-sm focus:border-accent focus:outline-none"
              required
            />
          </Field>
          <Field
            label="Département"
            htmlFor="department"
            hint={
              !form.departmentTouched && derivedDepartment
                ? `Auto-déduit (${derivedDepartment})`
                : undefined
            }
          >
            <input
              id="department"
              name="department"
              maxLength={3}
              value={department}
              onChange={(event) =>
                setForm((prev) => ({
                  ...prev,
                  department: event.target.value.toUpperCase(),
                  departmentTouched: true,
                }))
              }
              className="w-full rounded-xl border border-ink-muted/30 bg-transparent px-3 py-2 text-sm focus:border-accent focus:outline-none"
              required
            />
          </Field>
        </div>

        {error ? (
          <div role="alert" className="rounded-lg border border-danger/30 bg-danger/5 p-3 text-xs text-danger">
            {error}
          </div>
        ) : null}

        {Object.keys(errors).length > 0 ? (
          <ul className="text-xs text-warn">
            {Object.values(errors).map((msg) => (
              <li key={msg}>· {msg}</li>
            ))}
          </ul>
        ) : null}

        <footer className="flex justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            className="rounded-full border border-ink-muted/30 px-5 py-2 text-sm hover:border-accent"
          >
            Annuler
          </button>
          <button
            type="submit"
            disabled={!canSubmit}
            className="rounded-full bg-accent px-5 py-2 text-sm font-medium text-white transition hover:bg-accent-hover disabled:opacity-50"
          >
            {submitting
              ? isEdit
                ? 'Enregistrement…'
                : 'Création…'
              : isEdit
                ? 'Enregistrer'
                : 'Créer le client'}
          </button>
        </footer>
      </form>
    </div>
  )
}

function Field({
  label,
  htmlFor,
  hint,
  children,
}: {
  label: string
  htmlFor: string
  hint?: string
  children: React.ReactNode
}) {
  return (
    <div className="space-y-1">
      <label htmlFor={htmlFor} className="block text-xs font-medium text-ink-muted">
        {label}
      </label>
      {children}
      {hint ? <p className="text-[11px] text-ink-muted">{hint}</p> : null}
    </div>
  )
}

function validate(form: FormState, department: string): Record<string, string> {
  const errors: Record<string, string> = {}
  if (!form.client_code.trim()) errors.client_code = 'Code client requis.'
  if (!form.client_name.trim()) errors.client_name = 'Nom du client requis.'
  if (!POSTAL_RE.test(form.postal_code.trim())) {
    errors.postal_code = 'Code postal invalide (5 chiffres).'
  }
  if (!DEPARTMENT_RE.test(department.trim())) {
    errors.department = "Département invalide (ex. 75, 2A, 971)."
  }
  return errors
}
