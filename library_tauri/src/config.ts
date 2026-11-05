const raw = import.meta.env.VITE_API_URL as string | undefined

if (import.meta.env.PROD && !raw) {
  throw new Error('VITE_API_URL is not set for this production build.')
}

export const API_BASE: string = (raw || 'http://127.0.0.1:8000').replace(/\/+$/, '')