import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { decodeProfile, normaliseProfile } from '@/lib/public-profile'
import type { PublicProfile } from '@/lib/public-profile'

const DIFFICULTIES = ['Easy', 'Medium', 'Hard'] as const

function month(value: string | null): string {
  if (!value) return 'Unknown'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'Unknown'
  return new Intl.DateTimeFormat(undefined, { month: 'long', year: 'numeric' }).format(date)
}

function date(value: string): string {
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return 'recently'
  return new Intl.DateTimeFormat(undefined, {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  }).format(parsed)
}

type Loaded =
  | { kind: 'loading' }
  | { kind: 'ok'; profile: PublicProfile }
  | { kind: 'missing' }

/**
 * A profile someone was sent.
 *
 * It is public on purpose: no session, no user id, nothing but the counts the
 * owner chose to share. The token is looked up on the server; an old
 * URL-snapshot link still decodes as a fallback. Every value is rendered as
 * text and clamped.
 */
export default function PublicProfilePage() {
  const { token } = useParams()
  // Keyed on the token so opening another link starts from that link's
  // snapshot rather than briefly showing the previous profile.
  return <PublicProfileLoader key={token ?? 'none'} token={token} />
}

function PublicProfileLoader({ token }: { token: string | undefined }) {
  const [loaded, setLoaded] = useState<Loaded>(() => {
    const snapshot = token ? decodeProfile(token) : null
    if (snapshot) return { kind: 'ok', profile: snapshot }
    return token ? { kind: 'loading' } : { kind: 'missing' }
  })

  useEffect(() => {
    let live = true
    if (!token) return

    const snapshot = decodeProfile(token)

    void (async () => {
      try {
        const response = await fetch(`/api/v1/public/profiles/${encodeURIComponent(token)}`)
        if (response.ok) {
          const profile = normaliseProfile(await response.json())
          if (live) setLoaded(profile ? { kind: 'ok', profile } : { kind: 'missing' })
          return
        }
      } catch {
        // Offline or the API is down: an old snapshot can still render.
      }
      if (live) setLoaded(snapshot ? { kind: 'ok', profile: snapshot } : { kind: 'missing' })
    })()

    return () => {
      live = false
    }
  }, [token])

  if (loaded.kind === 'loading') {
    return (
      <main className="public">
        <header className="public-top">
          <Link className="public-wordmark" to="/">
            ReSolve
          </Link>
        </header>
        <section className="public-card">
          <p className="public-note">Loading profile…</p>
        </section>
      </main>
    )
  }

  if (loaded.kind === 'missing') {
    return (
      <main className="public">
        <header className="public-top">
          <Link className="public-wordmark" to="/">
            ReSolve
          </Link>
        </header>
        <section className="public-card">
          <h1 className="public-title">This link is not a profile.</h1>
          <p className="public-note">
            It may have been cut short when it was copied, or the owner stopped sharing. Ask for
            the link again, or start your own sheet.
          </p>
          <Link className="button button-light button-small" to="/">
            Go to ReSolve
          </Link>
        </section>
      </main>
    )
  }

  const profile = loaded.profile
  const total = Math.max(
    1,
    profile.byDifficulty.Easy + profile.byDifficulty.Medium + profile.byDifficulty.Hard,
  )

  return (
    <main className="public">
      <header className="public-top">
        <Link className="public-wordmark" to="/">
          ReSolve
        </Link>
        <Link className="public-top-link" to="/">
          Start your own
        </Link>
      </header>

      <section className="public-card">
        <div className="public-identity">
          <div className="profile-big-avatar" aria-hidden="true">
            {(profile.name.charAt(0) || 'R').toUpperCase()}
          </div>
          <div>
            <h1 className="public-title">{profile.name}</h1>
            <p className="public-note">
              Joined {month(profile.joined)} ·{' '}
              {profile.live ? 'live profile' : `snapshot ${date(profile.at)}`}
            </p>
          </div>
        </div>

        <ul className="stat-row">
          <li className="stat">
            <span className="stat-value">{profile.solved}</span>
            <span className="stat-label">Solved</span>
          </li>
          <li className="stat">
            <span className="stat-value">{profile.inSheet}</span>
            <span className="stat-label">In rotation</span>
          </li>
          <li className="stat">
            <span className="stat-value">{profile.reviews}</span>
            <span className="stat-label">Reviews</span>
          </li>
          <li className="stat">
            <span className="stat-value">{profile.streak}</span>
            <span className="stat-label">Day streak</span>
          </li>
        </ul>

        <div className="public-columns">
          <section className="public-block">
            <h2 className="panel-title">Memory</h2>
            <p className="public-memory">
              {profile.retention > 0 ? `${profile.retention}%` : '—'}
            </p>
            <p className="public-note">
              Predicted recall across {profile.inSheet} problem
              {profile.inSheet === 1 ? '' : 's'} in rotation.
            </p>
          </section>

          <section className="public-block">
            <h2 className="panel-title">Solved by difficulty</h2>
            <ul className="mix">
              {DIFFICULTIES.map((difficulty) => (
                <li className="mix-row" key={difficulty}>
                  <span className="mix-label">{difficulty}</span>
                  <span className="mix-track">
                    <span
                      className="mix-fill"
                      style={{ width: `${(profile.byDifficulty[difficulty] / total) * 100}%` }}
                    />
                  </span>
                  <span className="mix-value">{profile.byDifficulty[difficulty]}</span>
                </li>
              ))}
            </ul>
          </section>
        </div>

        {profile.topTags.length > 0 && (
          <section className="public-block">
            <h2 className="panel-title">Strongest tags</h2>
            <ul className="tag-list">
              {profile.topTags.map((entry) => (
                <li key={entry.tag}>
                  <span>{entry.tag}</span>
                  <strong>{entry.count}</strong>
                </li>
              ))}
            </ul>
          </section>
        )}

        <p className="public-footnote">
          Shared from ReSolve — solve a problem, rate how it felt, and it comes back before you
          forget it.
        </p>
      </section>
    </main>
  )
}
