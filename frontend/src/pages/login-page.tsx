import { useState } from 'react'
import { Link } from 'react-router-dom'

import { AuthField } from '@/components/auth-field'
import { AuthShell, GoogleButton } from '@/components/auth-shell'
import { authMessage } from '@/lib/auth-errors'
import { oauthRedirectTo, supabase } from '@/lib/supabase'

function problemWith(email: string, password: string): string {
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
    return 'That does not look like an email address.'
  }
  if (!password) return 'Enter your password.'
  return ''
}

/** Sign in. Both fields are visible at once — there is nothing to sequence. */
export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit() {
    const problem = problemWith(email, password)
    if (problem) {
      setError(problem)
      return
    }

    setBusy(true)
    const { error: failure } = await supabase.auth.signInWithPassword({
      email: email.trim(),
      password,
    })
    setBusy(false)

    if (failure) {
      setError(authMessage(failure.message))
      return
    }
    // On success <RedirectIfAuthed> moves us to /home on its own.
  }

  async function signInWithGoogle() {
    setError('')
    const { error: failure } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo: oauthRedirectTo() },
    })
    if (failure) setError(authMessage(failure.message))
  }

  return (
    <AuthShell>
      <form
        className="auth-panel"
        onSubmit={(event) => {
          event.preventDefault()
          submit()
        }}
      >
        <h1 className="auth-question">Welcome back</h1>
        <p className="auth-hint">Sign in to pick up your practice sheet.</p>

        <div className="auth-fields">
          <AuthField
            label="Email"
            type="email"
            placeholder="you@example.com"
            autoComplete="email"
            autoFocus
            invalid={!!error}
            value={email}
            onChange={(value) => {
              setEmail(value)
              if (error) setError('')
            }}
          />
          <AuthField
            label="Password"
            type="password"
            placeholder="Your password"
            autoComplete="current-password"
            revealable
            invalid={!!error}
            value={password}
            onChange={(value) => {
              setPassword(value)
              if (error) setError('')
            }}
          />
        </div>

        <div className="auth-slot">
          {error && (
            <p className="auth-error" role="alert">
              {error}
            </p>
          )}
        </div>

        <div className="auth-actions">
          <button className="button button-light auth-submit" type="submit" disabled={busy}>
            {busy ? 'Logging in' : 'Log in'}
          </button>
        </div>
      </form>

      <div className="auth-foot">
        <GoogleButton onClick={() => void signInWithGoogle()} />

        <p className="auth-switch">
          New here? <Link to="/register">Create an account</Link>
        </p>
      </div>
    </AuthShell>
  )
}
