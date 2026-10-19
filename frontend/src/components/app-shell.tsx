import { useEffect } from 'react'
import type { ReactNode } from 'react'

import { avatarUrl, displayName, useAuth } from '@/lib/auth-context'
import { NAV_ITEMS } from '@/lib/navigation'
import type { ViewId } from '@/lib/navigation'

type AppShellProps = {
  view: ViewId
  onViewChange: (view: ViewId) => void
  navOpen: boolean
  onNavOpenChange: (open: boolean) => void
  /**
   * Fill the viewport instead of scrolling, and drop the page title (the
   * topbar already names the section). Used by the compiler, which needs
   * every pixel of height for the editor.
   */
  flush?: boolean
  children: ReactNode
}

/**
 * Chrome for everything under /home: a fixed topbar with the section title,
 * and a drawer that slides in from the left.
 */
export function AppShell({
  view,
  onViewChange,
  navOpen,
  onNavOpenChange,
  flush = false,
  children,
}: AppShellProps) {
  const { user, signOut } = useAuth()
  const name = displayName(user)
  const photo = avatarUrl(user)
  const current = NAV_ITEMS.find((item) => item.id === view) ?? NAV_ITEMS[0]

  // Escape closes the drawer, and the page behind it must not scroll.
  useEffect(() => {
    if (!navOpen) return
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onNavOpenChange(false)
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [navOpen, onNavOpenChange])

  function pick(next: ViewId) {
    onViewChange(next)
    onNavOpenChange(false)
  }

  return (
    <div className="app-shell">
      <header className="app-topbar">
        <button
          className="app-menu-button"
          type="button"
          aria-label="Open navigation"
          aria-expanded={navOpen}
          onClick={() => onNavOpenChange(true)}
        >
          <span />
          <span />
          <span />
        </button>
        <span className="app-page-title">{current.label}</span>
        <span />
      </header>

      <button
        className={navOpen ? 'app-backdrop is-visible' : 'app-backdrop'}
        type="button"
        tabIndex={navOpen ? 0 : -1}
        aria-label="Close navigation"
        onClick={() => onNavOpenChange(false)}
      />

      <aside className={navOpen ? 'app-sidebar is-open' : 'app-sidebar'}>
        <div className="sidebar-top">
          <span>Signed in as</span>
          <strong>{name}</strong>
        </div>

        <nav className="sidebar-navigation" aria-label="Sections">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              className={item.id === view ? 'sidebar-link is-active' : 'sidebar-link'}
              type="button"
              aria-current={item.id === view ? 'page' : undefined}
              onClick={() => pick(item.id)}
            >
              {item.label}
            </button>
          ))}
        </nav>

        <div className="sidebar-profile">
          <div className="profile-identity">
            <div className="profile-avatar" aria-hidden="true">
              {photo ? (
                <img src={photo} alt="" referrerPolicy="no-referrer" />
              ) : (
                (name.charAt(0) || 'L').toUpperCase()
              )}
            </div>
            <div className="profile-copy">
              <strong>{name}</strong>
              <span>{user?.email ?? ''}</span>
            </div>
          </div>
          <button className="profile-logout" type="button" onClick={() => void signOut()}>
            Log out
          </button>
        </div>
      </aside>

      <main className={flush ? 'app-page is-full' : 'app-page'}>
        <div className="app-page-inner">
          {!flush && (
            <>
              <h1 className="app-view-title">{current.label}</h1>
              <p className="app-view-blurb">{current.blurb}</p>
            </>
          )}
          {children}
        </div>
      </main>
    </div>
  )
}
