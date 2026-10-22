import { useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import type { Session } from '@supabase/supabase-js'

import { AuthContext } from '@/lib/auth-context'
import type { AuthValue } from '@/lib/auth-context'
import { refresh as refreshPractice, setUser as setPracticeUser } from '@/lib/practice-store'
import { supabase } from '@/lib/supabase'

/** Owns the Supabase session and keeps it in sync with sign-in and sign-out. */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(true)
  // Which user's bucket is in memory. `'unset'` means nothing has loaded yet,
  // and `null` is the signed-out bucket. Comparing it with the current session
  // is what stops an empty sheet rendering for a frame when the session lands.
  const [loadedUser, setLoadedUser] = useState<string | null | 'unset'>('unset')

  useEffect(() => {
    let active = true

    supabase.auth.getSession().then(({ data }) => {
      if (!active) return
      setSession(data.session)
      setLoading(false)
    })

    const { data: listener } = supabase.auth.onAuthStateChange((_event, next) => {
      // Deferred on purpose: Supabase warns against doing work synchronously
      // inside this callback.
      setTimeout(() => {
        setSession(next)
        setLoading(false)
      }, 0)
    })

    return () => {
      active = false
      listener.subscription.unsubscribe()
    }
  }, [])

  // The practice state belongs to the user: the API loads the session user's
  // cards, and switching accounts switches sheets. The guard waits until the
  // state in memory is the one for the session, otherwise the dashboard
  // flashes zeros and the profile builds a link from an empty sheet.
  const currentUser = session?.user.id ?? null
  useEffect(() => {
    let active = true
    setPracticeUser(currentUser)
    void refreshPractice().then(() => {
      if (active) setLoadedUser(currentUser)
    })
    return () => {
      active = false
    }
  }, [currentUser])

  const practiceReady = loadedUser === currentUser

  const value = useMemo<AuthValue>(
    () => ({
      session,
      user: session?.user ?? null,
      loading,
      practiceReady,
      signOut: async () => {
        await supabase.auth.signOut()
      },
    }),
    [session, loading, practiceReady],
  )

  return <AuthContext value={value}>{children}</AuthContext>
}
