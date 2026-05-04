import type { ContactInfo } from '../api/contacts'

interface Props {
  role: 'TCI' | 'TCS' | 'Solution Habitat'
  contact: ContactInfo | null
}

export function ContactCard({ role, contact }: Props) {
  return (
    <article className="rounded-2xl border border-ink-muted/15 p-5">
      <header className="mb-3 flex items-baseline justify-between">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-accent">{role}</h3>
        {contact ? (
          <span className="text-xs text-success">disponible</span>
        ) : (
          <span className="text-xs text-warn">non assigné</span>
        )}
      </header>
      {contact ? (
        <dl className="space-y-1 text-sm">
          {contact.name ? (
            <div>
              <dt className="sr-only">Nom</dt>
              <dd className="font-medium">{contact.name}</dd>
            </div>
          ) : null}
          {contact.email ? (
            <div className="flex items-baseline gap-2">
              <dt className="text-xs text-ink-muted">email</dt>
              <dd>
                <a className="hover:text-accent" href={`mailto:${contact.email}`}>
                  {contact.email}
                </a>
              </dd>
            </div>
          ) : null}
          {contact.phone ? (
            <div className="flex items-baseline gap-2">
              <dt className="text-xs text-ink-muted">tél</dt>
              <dd>
                <a className="hover:text-accent" href={`tel:${contact.phone.replace(/\s+/g, '')}`}>
                  {contact.phone}
                </a>
              </dd>
            </div>
          ) : null}
        </dl>
      ) : (
        <p className="text-sm italic text-ink-muted">
          Aucun contact dédié pour ce département.
        </p>
      )}
    </article>
  )
}
