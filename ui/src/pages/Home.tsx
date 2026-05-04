import { Link } from 'react-router-dom'

export default function Home() {
  return (
    <section className="flex flex-col items-start gap-10 py-12 md:py-24">
      <div className="max-w-3xl space-y-6">
        <p className="text-sm uppercase tracking-widest text-accent">
          Solution Habitat · Sélection automatisée
        </p>
        <h1 className="text-4xl font-semibold leading-tight md:text-6xl">
          Générez vos fiches de sélection
          <br />
          en quelques clics.
        </h1>
        <p className="text-lg text-ink-muted">
          INVENIO importe vos fiches GALLETTI (DOCX ou PDF), normalise les données
          techniques, vous laisse choisir contacts et options, et produit un PDF
          au design France Air prêt à envoyer.
        </p>
      </div>

      <Link
        to="/import"
        className="inline-flex items-center gap-3 rounded-full bg-accent px-8 py-4 text-base font-medium text-white transition-all duration-400 ease-smooth hover:bg-accent-hover hover:shadow-lg"
      >
        Générer ma fiche
        <span aria-hidden>→</span>
      </Link>

      <div className="grid w-full gap-6 pt-12 md:grid-cols-3">
        <FeatureCard
          title="Import fiable"
          description="Extraction automatique des tableaux, désignation et données techniques."
        />
        <FeatureCard
          title="Catalogue à jour"
          description="Options et contacts synchronisés depuis Baserow."
        />
        <FeatureCard
          title="Design France Air"
          description="PDF généré avec sommaire cliquable et identité visuelle harmonisée."
        />
      </div>
    </section>
  )
}

function FeatureCard({ title, description }: { title: string; description: string }) {
  return (
    <article className="rounded-2xl border border-ink-muted/15 p-6">
      <h3 className="text-base font-semibold">{title}</h3>
      <p className="mt-2 text-sm text-ink-muted">{description}</p>
    </article>
  )
}
