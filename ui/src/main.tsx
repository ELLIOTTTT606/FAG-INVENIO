import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import '@fontsource-variable/archivo/standard.css'
import '@fontsource-variable/instrument-sans/index.css'
import './styles/index.css'

const container = document.getElementById('root')
if (!container) {
  throw new Error('#root element missing in index.html')
}

createRoot(container).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>,
)
