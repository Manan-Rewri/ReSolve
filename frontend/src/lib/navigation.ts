/**
 * The sections inside /home.
 *
 * Every page lives under /home as a view, not a route — switching sections
 * does not change the URL. The topbar title comes from `label`.
 */
export type ViewId = 'home' | 'learn' | 'practice' | 'compiler' | 'profile'

export type NavItem = {
  id: ViewId
  label: string
  /** Shown under the title while this view is open. */
  blurb: string
}

export const NAV_ITEMS: readonly NavItem[] = [
  {
    id: 'home',
    label: 'Home',
    blurb: 'Where your practice stands today.',
  },
  {
    id: 'learn',
    label: 'Learn',
    blurb: 'Find problems and add them to your rotation.',
  },
  {
    id: 'practice',
    label: 'Practice',
    blurb: 'Problems due today, waiting on you.',
  },
  {
    id: 'compiler',
    label: 'Compiler',
    blurb: 'Write C++, give it input, read the output.',
  },
  {
    id: 'profile',
    label: 'Profile',
    blurb: 'Your account, your numbers, and a link you can share.',
  },
]
