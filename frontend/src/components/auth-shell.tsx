import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

type AuthShellProps = {
  /** Omit on single-form screens like /login. */
  progress?: { current: number; total: number }
  children: ReactNode
}

/** Shared chrome for the auth screens: wordmark, step indicator, panel. */
export function AuthShell({ progress, children }: AuthShellProps) {
  return (
    <main className="auth">
      <div className="auth-shell">
        <header className="auth-head">
          <Link className="auth-wordmark" to="/">
            ReSolve
          </Link>

          {progress && (
            <div
              className="auth-progress"
              role="progressbar"
              aria-valuemin={1}
              aria-valuemax={progress.total}
              aria-valuenow={progress.current + 1}
              aria-label={`Step ${progress.current + 1} of ${progress.total}`}
            >
              {Array.from({ length: progress.total }, (_, i) => (
                <span key={i} className={i <= progress.current ? 'is-active' : ''} />
              ))}
            </div>
          )}
        </header>

        {children}
      </div>
    </main>
  )
}

/**
 * The Google "G". This is the one place a colour appears on the site — it is a
 * third-party brand mark, not our UI, so the monochrome rule does not apply.
 */
function GoogleMark() {
  return (
    <svg className="google-mark" viewBox="0 0 48 48" aria-hidden="true" focusable="false">
      <path
        fill="#4285F4"
        d="M45.12 24.5c0-1.56-.14-3.06-.4-4.5H24v8.51h11.84c-.51 2.75-2.06 5.08-4.39 6.64v5.52h7.11c4.16-3.83 6.56-9.47 6.56-16.17z"
      />
      <path
        fill="#34A853"
        d="M24 46c5.94 0 10.92-1.97 14.56-5.33l-7.11-5.52c-1.97 1.32-4.49 2.1-7.45 2.1-5.73 0-10.58-3.87-12.31-9.07H4.34v5.7C7.96 41.07 15.4 46 24 46z"
      />
      <path
        fill="#FBBC05"
        d="M11.69 28.18A13.2 13.2 0 0 1 11 24c0-1.45.25-2.86.69-4.18v-5.7H4.34A22 22 0 0 0 2 24c0 3.55.85 6.91 2.34 9.88l7.35-5.7z"
      />
      <path
        fill="#EA4335"
        d="M24 10.75c3.23 0 6.13 1.11 8.41 3.29l6.31-6.31C34.91 4.18 29.93 2 24 2 15.4 2 7.96 6.93 4.34 14.12l7.35 5.7c1.73-5.2 6.58-9.07 12.31-9.07z"
      />
    </svg>
  )
}

type GoogleButtonProps = {
  onClick: () => void
}

/** Social sign-in. */
export function GoogleButton({ onClick }: GoogleButtonProps) {
  return (
    <button className="button button-ghost auth-google" type="button" onClick={onClick}>
      <GoogleMark />
      Continue with Google
    </button>
  )
}
