import { createClient } from '@supabase/supabase-js'

const url = import.meta.env.VITE_SUPABASE_URL?.trim()
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY?.trim()

/**
 * Returns a human-readable problem when Supabase is not configured, or null
 * when it is. Checked at startup so a missing .env shows an explanation
 * instead of a blank white screen mid-demo.
 */
export function supabaseConfigProblem(): string | null {
  if (!url) return 'VITE_SUPABASE_URL is missing from frontend/.env'
  if (!anonKey) return 'VITE_SUPABASE_ANON_KEY is missing from frontend/.env'
  return null
}

/**
 * Browser client. This uses the ANON key and is subject to Row Level Security.
 * The service-role key must never reach the frontend — see backend/app/core/supabase.py.
 */
export const supabase = createClient(
  url ?? 'https://placeholder.supabase.co',
  anonKey ?? 'placeholder-anon-key',
  {
    auth: {
      persistSession: true,
      autoRefreshToken: true,
      // Picks up the tokens Supabase redirects back with after Google OAuth.
      detectSessionInUrl: true,
    },
  },
)

/** Where Google OAuth should send the user back to. Must be absolute. */
export function oauthRedirectTo(): string {
  return `${window.location.origin}/`
}
