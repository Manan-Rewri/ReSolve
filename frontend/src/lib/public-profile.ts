/**
 * Shared profiles.
 *
 * A link is `/p/<token>`; the token is a random value on the owner's profile
 * row, and the page fetches the live numbers from the API. The older links
 * carried a **snapshot** encoded in the URL; those still decode, so a link
 * sent before the database existed does not rot.
 *
 * Either way the payload is deliberately small and contains nothing private:
 * no email, no user id, no review log. Just the counts a profile shows.
 */

export type PublicProfile = {
  /** Format version, so an old link can be rejected rather than misread. */
  v: 1
  name: string
  /** The month the account was created, if known. */
  joined: string | null
  /** When the numbers were produced. */
  at: string
  solved: number
  inSheet: number
  reviews: number
  streak: number
  /** Memory strength, 0-100. */
  retention: number
  graduated: number
  byDifficulty: { Easy: number; Medium: number; Hard: number }
  topTags: { tag: string; count: number }[]
  /** True when the API assembled these numbers just now from the database. */
  live?: boolean
}

/** Fields are clamped on the way in, so a hostile link cannot blow up a page. */
function count(value: unknown): number {
  return typeof value === 'number' && Number.isFinite(value)
    ? Math.max(0, Math.min(1_000_000, Math.round(value)))
    : 0
}

function text(value: unknown, max: number): string {
  return typeof value === 'string' ? value.slice(0, max) : ''
}

export function encodeProfile(profile: PublicProfile): string {
  const bytes = new TextEncoder().encode(JSON.stringify(profile))
  let binary = ''
  for (const byte of bytes) binary += String.fromCharCode(byte)
  return btoa(binary).replaceAll('+', '-').replaceAll('/', '_').replace(/=+$/, '')
}

/** Clamp a profile from the API or an old snapshot into the page's shape. */
export function normaliseProfile(raw: unknown): PublicProfile | null {
  if (!raw || typeof raw !== 'object') return null
  const value = raw as Record<string, unknown>

  if (value.v !== 1) return null
  if (typeof value.name !== 'string' || !value.name.trim()) return null

  const difficulty = (value.byDifficulty ?? {}) as Record<string, unknown>
  const tags = Array.isArray(value.topTags) ? value.topTags : []

  return {
    v: 1,
    name: text(value.name, 60),
    joined: typeof value.joined === 'string' ? text(value.joined, 40) : null,
    at: text(value.at, 40),
    solved: count(value.solved),
    inSheet: count(value.inSheet),
    reviews: count(value.reviews),
    streak: count(value.streak),
    retention: Math.min(100, count(value.retention)),
    graduated: count(value.graduated),
    byDifficulty: {
      Easy: count(difficulty.Easy),
      Medium: count(difficulty.Medium),
      Hard: count(difficulty.Hard),
    },
    topTags: tags
      .flatMap((entry) => {
        if (!entry || typeof entry !== 'object') return []
        const tag = text((entry as Record<string, unknown>).tag, 24).trim()
        const n = count((entry as Record<string, unknown>).count)
        return tag && n > 0 ? [{ tag, count: n }] : []
      })
      .slice(0, 6),
    live: value.live === true,
  }
}

export function decodeProfile(token: string): PublicProfile | null {
  // A real snapshot is a few hundred bytes. Refuse a giant token before
  // decoding it, so a hostile link cannot make the browser chew on megabytes.
  if (token.length > 4096) return null
  try {
    const padded = token.replaceAll('-', '+').replaceAll('_', '/')
    const binary = atob(padded + '='.repeat((4 - (padded.length % 4)) % 4))
    const bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0))
    return normaliseProfile(JSON.parse(new TextDecoder().decode(bytes)))
  } catch {
    return null
  }
}

/** The absolute link to a shared profile. */
export function profileLink(profile: PublicProfile): string {
  return `${window.location.origin}/p/${encodeProfile(profile)}`
}
