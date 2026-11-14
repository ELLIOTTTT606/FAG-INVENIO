import { Link } from 'react-router-dom'

const FEATURES = [
  {
    step: '01',
    title: 'Import fiable',
    description: 'Extraction automatique des tableaux, désignation et données techniques.',
  },
  {
    step: '02',
    title: 'Catalogue à jour',
    description: 'Options et contacts synchronisés depuis Baserow.',
  },
  {
    step: '03',
    title: 'Design France Air',
    description: 'PDF généré avec sommaire cliquable et identité visuelle harmonisée.',
  },
] as const

export default function Home() {
  return (
    <section className="py-10 md:py-20">
      <div className="stagger mx-auto flex max-w-4xl flex-col items-center text-center">
        <p className="text-sm font-medium text-ink-muted">
          Solution Habitat · Sélection automatisée
        </p>
        <h1 className="mt-5 text-5xl font-semibold leading-[1.05] md:text-7xl">
          Générez vos fiches de sélection
          <br />
          <span className="text-ink-muted">en quelques clics.</span>
        </h1>
        <p className="mt-7 max-w-2xl text-lg leading-relaxed text-ink-muted md:text-xl">
          INVENIO importe vos fiches GALLETTI (DOCX ou PDF), normalise les données
          techniques, vous laisse choisir contacts et options, et produit un PDF
          au design France Air prêt à envoyer.
        </p>
        <Link
          to="/import"
          className="group mt-10 inline-flex items-center gap-2 rounded-full bg-ink-light px-8 py-4 text-base font-medium text-white hover:bg-black hover:shadow-xl"
        >
          Générer ma fiche
          <span
            aria-hidden
            className="transition-transform duration-400 ease-smooth group-hover:translate-x-1"
          >
            →
          </span>
        </Link>
      </div>

      <div className="stagger mt-20 grid w-full gap-5 md:mt-28 md:grid-cols-3">
        {FEATURES.map((feature) => (
          <article
            key={feature.step}
            className="lift rounded-3xl bg-white p-8 shadow-[0_1px_2px_rgb(0_0_0/0.03),0_8px_24px_-12px_rgb(0_0_0/0.08)]"
          >
            <p className="text-xs font-medium tabular-nums text-ink-muted">{feature.step}</p>
            <h3 className="mt-6 text-xl font-semibold">{feature.title}</h3>
            <p className="mt-2 text-[15px] leading-relaxed text-ink-muted">{feature.description}</p>
          </article>
        ))}
      </div>
    </section>
  )
}
