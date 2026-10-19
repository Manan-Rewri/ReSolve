import { useState } from 'react'

import { AppShell } from '@/components/app-shell'
import CompilerView from '@/pages/compiler-view'
import LearnView from '@/pages/learn-view'
import ProblemView from '@/pages/problem-view'
import type { ViewId } from '@/lib/navigation'

/**
 * The shell for everything under /home.
 *
 * Home is the default view: a signed-in user lands here whether they opened
 * the site or just signed in. It has no content yet — the analytics it was
 * going to carry come later.
 *
 * Only the Compiler has content for now. Practice and Settings are navbar
 * entries that render nothing.
 */
export default function HomePage() {
  const [view, setView] = useState<ViewId>('home')
  const [navOpen, setNavOpen] = useState(false)
  const [problem, setProblem] = useState<string | null>(null)

  // A problem screen replaces the section entirely, so the section chrome goes too.
  if (problem) {
    return <ProblemView slug={problem} onBack={() => setProblem(null)} />
  }

  return (
    <AppShell
      view={view}
      onViewChange={setView}
      navOpen={navOpen}
      onNavOpenChange={setNavOpen}
      flush={view === 'compiler'}
    >
      {view === 'learn' && <LearnView onOpen={setProblem} />}
      {view === 'compiler' && <CompilerView />}
    </AppShell>
  )
}
