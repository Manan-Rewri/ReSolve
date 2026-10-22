import type { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'

import { useAuth } from '@/lib/auth-context'

/** Shown while the first session lookup is in flight, so nothing flashes. */
function Splash() {
  return <main className="auth" aria-busy="true" />
}

/** Gate for signed-in-only routes. Bounces to the landing page. */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { session, loading, practiceReady } = useAuth()
  if (loading) return <Splash />
  if (!session) return <Navigate to="/" replace />
  if (!practiceReady) return <Splash />
  return <>{children}</>
}

/** Gate for public routes. Sends signed-in users straight to their sheet. */
export function RedirectIfAuthed({ children }: { children: ReactNode }) {
  const { session, loading } = useAuth()
  if (loading) return <Splash />
  if (session) return <Navigate to="/home" replace />
  return <>{children}</>
}
