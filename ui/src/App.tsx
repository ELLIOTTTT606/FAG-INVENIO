import {
  lazy,
  Suspense,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type CSSProperties,
} from 'react'
import { Link, NavLink, Route, Routes, useLocation, type Location } from 'react-router-dom'
import { AirflowBackground } from './components/AirflowBackground'
import { BaserowBadge } from './components/BaserowBadge'
import { LoaderStage } from './components/LoaderStage'
import { prefersReducedMotion } from './lib/motion'

const Contacts = lazy(() => import('./pages/Contacts'))
const Generate = lazy(() => import('./pages/Generate'))
const Home = lazy(() => import('./pages/Home'))
const Import = lazy(() => import('./pages/Import'))
const LoaderDemo = lazy(() => import('./pages/LoaderDemo'))
const Options = lazy(() => import('./pages/Options'))

const NAV = [
  { to: '/', label: 'Accueil' },
  { to: '/import', label: 'Importer une fiche' },
  { to: '/options', label: 'Options' },
  { to: '/contacts', label: 'Contacts' },
  { to: '/generate', label: 'Générer' },
] as const

const EXIT_MS = 180

/**
 * Keeps the outgoing page on screen while it fades out, then swaps in the
 * new one. Only a change of pathname is animated; query-string updates are
 * applied immediately.
 */
function useTransitionedLocation(): { shown: Location; leaving: boolean } {
  const location = useLocation()
  const [shown, setShown] = useState(location)
  const pathChanged = location.pathname !== shown.pathname

  useEffect(() => {
    if (!pathChanged || prefersReducedMotion()) {
      setShown(location)
      return
    }
    const timer = window.setTimeout(() => {
      setShown(location)
      window.scrollTo({ top: 0 })
    }, EXIT_MS)
    return () => window.clearTimeout(timer)
  }, [location, pathChanged])

  return { shown, leaving: pathChanged }
}

export default function App() {
  const { shown, leaving } = useTransitionedLocation()

  return (
    <div className="min-h-full">
      <AirflowBackground />
      <Header />
      <main className="mx-auto max-w-page px-6 py-12 md:px-20">
        <div key={shown.pathname} className={leaving ? 'page-exit' : 'page-enter'}>
          <Suspense fallback={<LoaderStage label="Chargement de la page" className="min-h-[60vh]" />}>
            <Routes location={shown}>
              <Route path="/" element={<Home />} />
              <Route path="/import" element={<Import />} />
              <Route path="/options" element={<Options />} />
              <Route path="/contacts" element={<Contacts />} />
              <Route path="/generate" element={<Generate />} />
              <Route path="/loader" element={<LoaderDemo />} />
              <Route path="*" element={<NotFound />} />
            </Routes>
          </Suspense>
        </div>
      </main>
    </div>
  )
}

function Header() {
  const { pathname } = useLocation()
  const navRef = useRef<HTMLElement | null>(null)
  const [pill, setPill] = useState<CSSProperties>({ opacity: 0 })

  // Slide the highlight under whichever link matches the current route.
  useLayoutEffect(() => {
    const active = navRef.current?.querySelector<HTMLElement>('[aria-current="page"]')
    setPill(
      active
        ? { opacity: 1, width: active.offsetWidth, transform: `translateX(${active.offsetLeft}px)` }
        : { opacity: 0 },
    )
  }, [pathname])

  return (
    <header className="glass sticky top-0 z-30 border-b border-black/[0.06]">
      <div className="mx-auto flex max-w-page items-center justify-between px-6 py-3 md:px-20">
        <Link to="/" className="flex items-center gap-3 text-[17px] font-semibold tracking-tight">
          <span>
            INVENIO <span className="font-normal text-ink-muted">· France Air</span>
          </span>
          <BaserowBadge />
        </Link>
        <nav ref={navRef} className="relative flex items-center text-[13px]">
          <span
            aria-hidden
            className="nav-pill absolute left-0 top-0 h-full rounded-full bg-black/[0.06]"
            style={pill}
          />
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `relative rounded-full px-3.5 py-1.5 ${
                  isActive ? 'text-ink-light' : 'text-ink-muted hover:text-ink-light'
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
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
