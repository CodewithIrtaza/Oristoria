/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Backend base URL in production, e.g. https://oristoria-backend.onrender.com */
  readonly VITE_API_BASE_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
