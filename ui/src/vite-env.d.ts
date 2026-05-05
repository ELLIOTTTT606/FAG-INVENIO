/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Base URL of the INVENIO backend (empty string in dev: relative URLs go through the Vite/Netlify proxy). */
  readonly VITE_API_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
