import { useCallback } from 'react'
import { BrowserRouter, Routes, Route, useNavigate, useLocation } from 'react-router-dom'
import { ThemeProvider, useTheme } from './lib/theme'
import { clearSession } from './lib/sessionContext'
import { AnimatedBackground } from './components/layout/AnimatedBackground'
import { TopBar } from './components/layout/Navigation'
import Home     from './pages/Home'
import Machine  from './pages/Machine'
import Projet   from './pages/Projet'
import Contacts from './pages/Contacts'
import Options  from './pages/Options'
import Generate from './pages/Generate'

function AppShell() {
  const { theme: t } = useTheme()
  const navigate     = useNavigate()
  const location     = useLocation()

  const handleHome = useCallback(() => {
    clearSession()
    navigate('/')
  }, [navigate])

  return (
    <div style={{
      minHeight: '100vh',
      background: t.bg,
      color: t.text,
      fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
      position: 'relative',
      overflow: 'hidden',
      transition: 'background 0.6s ease, color 0.4s ease',
    }}>
      <link
        href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap"
        rel="stylesheet"
      />
      <style>{`
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0 }
        ::selection { background: ${t.accent}40; color: ${t.text} }
        input::placeholder { font-family: inherit; color: ${t.muted} }
        button { font-family: inherit }
      `}</style>
      <AnimatedBackground />
      <div style={{ position: 'relative', zIndex: 1 }}>
        <TopBar pathname={location.pathname} onHome={handleHome} />
        <Routes>
          <Route path="/"         element={<Home />} />
          <Route path="/machine"  element={<Machine />} />
          <Route path="/projet"   element={<Projet />} />
          <Route path="/contacts" element={<Contacts />} />
          <Route path="/options"  element={<Options />} />
          <Route path="/generate" element={<Generate />} />
          <Route path="*"         element={<Home />} />
        </Routes>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <AppShell />
      </BrowserRouter>
    </ThemeProvider>
  )
}
