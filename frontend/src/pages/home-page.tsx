import { useState } from 'react'

import { AppShell } from '@/components/app-shell'
import CompilerView from '@/pages/compiler-view'
import { DashboardView } from '@/pages/dashboard-view'
import LearnView from '@/pages/learn-view'
import PracticeView from '@/pages/practice-view'
import ProblemView from '@/pages/problem-view'
import { ProfileView } from '@/pages/profile-view'
import type { ViewId } from '@/lib/navigation'

/**
 * The shell for everything under /home.
 *
 * Home is the default view: a signed-in user lands here whether they opened
 * the site or just signed in. It is the dashboard — the due queue, memory
 * strength, activity and what is next.
 *
 * Learn is the catalogue. Practice is the queue. Profile is the account.
 *
 * The view is in the URL, because a sheet of problems is a link worth sending
 * someone: `/home?view=learn&sheet=arrays-and-hashing`.
 */
export default function HomePage() {
  const [view, setView] = useState<ViewId>(() => {
    const requested = new URLSearchParams(window.location.search).get('view')
    return (['home', 'learn', 'practice', 'compiler', 'profile'] as ViewId[]).includes(
      requested as ViewId,
    )
      ? (requested as ViewId)
      : 'home'
  })
  const [navOpen, setNavOpen] = useState(false)
  const [problem, setProblem] = useState<string | null>(null)

  function go(next: ViewId) {
    const params = new URLSearchParams(window.location.search)
    params.set('view', next)
    if (next !== 'learn') params.delete('sheet')
    window.history.pushState({}, '', `?${params.toString()}`)
    setView(next)
  }

  // A problem screen replaces the section entirely, so the section chrome goes too.
  if (problem) {
    return <ProblemView slug={problem} onBack={() => setProblem(null)} />
  }

  return (
    <AppShell
      view={view}
      onViewChange={go}
      navOpen={navOpen}
      onNavOpenChange={setNavOpen}
      flush={view === 'compiler' || view === 'practice'}
    >
      {view === 'home' && <DashboardView onNavigate={go} onOpen={setProblem} />}
      {view === 'learn' && <LearnView onOpen={setProblem} />}
      {view === 'practice' && <PracticeView />}
      {view === 'compiler' && <CompilerView />}
      {view === 'profile' && <ProfileView onNavigate={go} />}
    </AppShell>
  )
}
