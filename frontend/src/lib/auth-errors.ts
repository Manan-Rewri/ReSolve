/**
 * Turns a Supabase auth error into something a person can act on.
 * Says what went wrong and how to fix it. Never apologises, never vague.
 */
export function authMessage(raw: string): string {
  const message = raw.toLowerCase()

  if (message.includes('invalid login credentials')) {
    return 'That email and password do not match.'
  }
  if (message.includes('email not confirmed')) {
    return 'Confirm your email address first, then log in.'
  }
  if (message.includes('user already registered') || message.includes('already been registered')) {
    return 'That email is already registered. Log in instead.'
  }
  if (message.includes('password should be at least')) {
    return 'Use at least eight characters.'
  }
  if (message.includes('unable to validate email') || message.includes('invalid email')) {
    return 'That does not look like an email address.'
  }
  if (message.includes('rate limit') || message.includes('too many')) {
    return 'Too many attempts. Wait a moment and try again.'
  }
  if (message.includes('fetch')) {
    return 'Could not reach the server. Check your connection.'
  }

  return raw
}
