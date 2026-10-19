import { createContext, use } from 'react'
import type { Session, User } from '@supabase/supabase-js'

export type AuthValue = {
  session: Session | null
  user: User | null
  /** True until the first session lookup settles. Route guards wait on this. */
  loading: boolean
  signOut: () => Promise<void>
}

export const AuthContext = createContext<AuthValue | null>(null)

export function useAuth(): AuthValue {
  const value = use(AuthContext)
  if (!value) throw new Error('useAuth must be used inside <AuthProvider>')
  return value
}

/** Best available display name for the signed-in user. */
export function displayName(user: User | null): string {
  if (!user) return ''
  const meta = user.user_metadata
  const candidate = meta?.username ?? meta?.full_name ?? meta?.name
  if (typeof candidate === 'string' && candidate.trim()) return candidate.trim()
  return (user.email ?? '').split('@')[0] || 'there'
}

/**
 * Profile photo URL, if the provider supplied one.
 *
 * Google returns it as `picture`; newer Supabase versions also surface it as
 * `avatar_url`. Email/password signups have neither, so callers fall back to
 * the user's initial.
 */
export function avatarUrl(user: User | null): string {
  const meta = user?.user_metadata
  if (!meta) return ''
  const candidate = meta.avatar_url ?? meta.picture
  return typeof candidate === 'string' ? candidate.trim() : ''
}
