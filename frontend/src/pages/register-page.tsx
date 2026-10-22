import { useState } from 'react'
import { Link } from 'react-router-dom'

import { AuthField } from '@/components/auth-field'
import { AuthShell, GoogleButton } from '@/components/auth-shell'
import { oauthRedirectTo, supabase } from '@/lib/supabase'
import { authMessage } from '@/lib/auth-errors'

type Form = {
  username: string
  email: string
  password: string
  confirm: string
}

const EMPTY: Form = { username: '', email: '', password: '', confirm: '' }

/** One question per screen. The order is the order you think in them. */
const STEPS = [
  {
    key: 'username' as const,
    question: 'What should we call you?',
    hint: 'Something you will recognise in your own practice sheet.',
    type: 'text' as const,
    placeholder: 'ada',
    autoComplete: 'username',
  },
  {
    key: 'email' as const,
    question: 'What is your email?',
    hint: 'We use it to sign you in.',
    type: 'email' as const,
    placeholder: 'you@example.com',
    autoComplete: 'email',
  },
  {
    key: 'password' as const,
    question: 'Choose a password',
    hint: 'Eight characters or more.',
    type: 'password' as const,
    placeholder: 'Your password',
    autoComplete: 'new-password',
  },
  {
    key: 'confirm' as const,
    question: 'Confirm your password',
    hint: 'Type it once more.',
    type: 'password' as const,
    placeholder: 'Type it again',
    autoComplete: 'new-password',
  },
]

/** Returns an empty string when valid, otherwise what to fix. */
function problemWith(step: number, form: Form): string {
  switch (step) {
    case 0: {
      const value = form.username.trim()
      if (value.length < 3) return 'Use at least three characters.'
      if (/\s/.test(value)) return 'Remove the spaces.'
      return ''
    }
    case 1: {
      const value = form.email.trim()
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
        return 'That does not look like an email address.'
      }
      return ''
    }
    case 2:
      if (form.password.length < 8) return 'Use at least eight characters.'
      return ''
    case 3:
      if (form.confirm !== form.password) return 'Those two do not match.'
      return ''
    default:
      return ''
  }
}

export default function RegisterPage() {
  const [step, setStep] = useState(0)
  const [travel, setTravel] = useState(1)
  const [form, setForm] = useState<Form>(EMPTY)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)

  const current = STEPS[step]
  const isLast = step === STEPS.length - 1

  function goTo(next: number) {
    setTravel(next > step ? 1 : -1)
    setStep(next)
    setError('')
    setNotice('')
  }

  async function createAccount() {
    setBusy(true)
    const { data, error: failure } = await supabase.auth.signUp({
      email: form.email.trim(),
      password: form.password,
      options: { data: { username: form.username.trim() } },
    })
    setBusy(false)

    if (failure) {
      setError(authMessage(failure.message))
      return
    }

    // No session means Supabase is waiting on email confirmation.
    if (!data.session) {
      setNotice('Check your email to confirm the account, then log in.')
    }
    // With a session, <RedirectIfAuthed> moves us to /home on its own.
  }

  function advance() {
    const problem = problemWith(step, form)
    if (problem) {
      setError(problem)
      return
    }
    if (isLast) {
      void createAccount()
      return
    }
    goTo(step + 1)
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
    <AuthShell progress={{ current: step, total: STEPS.length }}>
      {/* `key` remounts the panel so the entrance animation replays each step.
          It is a real <form> so Enter submits and advances. */}
      <form
        className="auth-panel"
        key={step}
        data-travel={travel}
        onSubmit={(event) => {
          event.preventDefault()
          advance()
        }}
      >
        <h1 className="auth-question">{current.question}</h1>
        <p className="auth-hint">{current.hint}</p>

        <AuthField
          label={current.question}
          type={current.type}
          placeholder={current.placeholder}
          autoComplete={current.autoComplete}
          autoFocus
          revealable={current.type === 'password'}
          invalid={!!error}
          value={form[current.key]}
          onChange={(value) => {
            setForm((f) => ({ ...f, [current.key]: value }))
            if (error) setError('')
          }}
        />

        <div className="auth-slot">
          {error && (
            <p className="auth-error" role="alert">
              {error}
            </p>
          )}
        </div>

        <div className="auth-actions">
          {step > 0 && (
            <button className="button button-ghost" type="button" onClick={() => goTo(step - 1)}>
              Back
            </button>
          )}
          <button className="button button-light" type="submit" disabled={busy}>
            {busy ? 'Creating account' : isLast ? 'Create account' : 'Continue'}
          </button>
        </div>
      </form>

      <div className="auth-foot">
        {notice && (
          <p className="auth-notice" role="status">
            {notice}
          </p>
        )}

        <GoogleButton onClick={() => void signInWithGoogle()} />

        <p className="auth-switch">
          Already learning with us? <Link to="/login">Log in</Link>
        </p>
      </div>
    </AuthShell>
  )
}
