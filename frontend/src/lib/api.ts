import { supabase } from '@/lib/supabase'

/**
 * A request to our own API, carrying the Supabase access token.
 *
 * The backend verifies the token and uses its user id; it no longer trusts a
 * user header. A 401 is retried once after a token refresh, because a tab
 * left open overnight should not report a failure the user can do nothing
 * about.
 */
async function send(path: string, init: RequestInit): Promise<Response> {
  const { data } = await supabase.auth.getSession()
  const headers = new Headers(init.headers)
  const token = data.session?.access_token
  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (init.body !== undefined && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  return fetch(path, { ...init, headers })
}

export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const response = await send(path, init)
  if (response.status !== 401) return response

  const { data, error } = await supabase.auth.refreshSession()
  if (error || !data.session) return response
  return send(path, init)
}
