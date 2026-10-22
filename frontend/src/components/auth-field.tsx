import { useId, useState } from 'react'

type AuthFieldProps = {
  label: string
  value: string
  onChange: (value: string) => void
  type?: 'text' | 'email' | 'password'
  placeholder?: string
  autoComplete?: string
  autoFocus?: boolean
  /** Show a button that reveals what is typed. Only for passwords. */
  revealable?: boolean
  /** The field holds something the user has to fix. */
  invalid?: boolean
}

/**
 * The oversized auth input. One field at a time on /register, two at once on
 * /login — the height and type size stay constant either way so the page never
 * reflows when the step changes.
 */
export function AuthField({
  label,
  value,
  onChange,
  type = 'text',
  placeholder = '',
  autoComplete,
  autoFocus = false,
  revealable = false,
  invalid = false,
}: AuthFieldProps) {
  const id = useId()
  const [shown, setShown] = useState(false)
  const revealed = revealable && shown
  const inputType = revealed ? 'text' : type

  const boxClass = ['auth-field-box']
  if (revealable) boxClass.push('has-reveal')
  if (invalid) boxClass.push('has-error')

  return (
    <div className="auth-field">
      <label className="sr-only" htmlFor={id}>
        {label}
      </label>
      <div className={boxClass.join(' ')}>
        <input
          id={id}
          type={inputType}
          value={value}
          placeholder={placeholder}
          autoComplete={autoComplete}
          autoFocus={autoFocus}
          aria-invalid={invalid || undefined}
          onChange={(event) => onChange(event.target.value)}
        />
        {revealable && (
          <button
            className="auth-field-reveal"
            type="button"
            onClick={() => setShown((current) => !current)}
            aria-label={revealed ? 'Hide password' : 'Show password'}
            aria-pressed={revealed}
            title={revealed ? 'Hide password' : 'Show password'}
          >
            {revealed ? <EyeOff /> : <Eye />}
          </button>
        )}
      </div>
    </div>
  )
}

/** An open eye. Drawn here rather than pulled from an icon library. */
function Eye() {
  return (
    <svg
      className="auth-field-eye"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      <path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12Z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  )
}

/** The same eye, struck through. */
function EyeOff() {
  return (
    <svg
      className="auth-field-eye"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      <path d="M2.5 12S6 5.5 12 5.5c1.4 0 2.7.3 3.8.8" />
      <path d="M6.7 6.9C4.3 8.5 2.5 12 2.5 12S6 18.5 12 18.5c1.5 0 2.9-.42 4-1.05" />
      <path d="M10.1 10.2a2.9 2.9 0 0 0 3.9 3.9" />
      <path d="M3 3l18 18" />
    </svg>
  )
}
