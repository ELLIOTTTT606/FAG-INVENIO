import { Link, Route, Routes } from 'react-router-dom'
import Home from './pages/Home'
import Import from './pages/Import'

export default function App() {
  return (
    <div className="min-h-full">
      <Header />
      <main className="mx-auto max-w-page px-6 py-12 md:px-20">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/import" element={<Import />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
    </div>
  )
}

function Header() {
  return (
    <header className="border-b border-ink-muted/20">
      <div className="mx-auto flex max-w-page items-center justify-between px-6 py-4 md:px-20">
        <Link to="/" className="text-lg font-semibold tracking-tight">
          INVENIO <span className="text-ink-muted">· France Air</span>
        </Link>
        <nav className="flex items-center gap-6 text-sm">
          <Link to="/" className="hover:text-accent">
            Accueil
          </Link>
          <Link to="/import" className="hover:text-accent">
            Importer une fiche
          </Link>
        </nav>
      </div>
    </header>
  )
}

function NotFound() {
  return (
    <div className="py-24 text-center">
      <h1 className="text-3xl font-semibold">Page introuvable</h1>
      <p className="mt-3 text-ink-muted">Cette page n'existe pas (encore).</p>
    </div>
  )
}
