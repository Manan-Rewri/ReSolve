import { useEffect, useMemo, useState } from 'react'

import { apiFetch } from '@/lib/api'
import { avatarUrl, displayName, useAuth } from '@/lib/auth-context'
import type { ViewId } from '@/lib/navigation'
import { stats, usePracticeState } from '@/lib/practice-store'
import { profileLink } from '@/lib/public-profile'
import { listProblems } from '@/lib/problems'
import type { ProblemSummary } from '@/lib/problems'

function month(value: string | undefined): string {
  if (!value) return 'Unknown'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'Unknown'
  return new Intl.DateTimeFormat(undefined, { month: 'long', year: 'numeric' }).format(date)
}

const DIFFICULTIES = ['Easy', 'Medium', 'Hard'] as const

/**
 * Profile: the account, the numbers, and the link.
 *
 * The link is `/p/<token>`, where the token is a random value on the user's
 * profile row. The public page fetches the numbers from the database, so the
 * link does not go stale when the sheet changes. If the share request fails,
 * the old URL-snapshot link is still offered as a fallback.
 */
export function ProfileView({ onNavigate }: { onNavigate: (view: ViewId) => void }) {
  const { user, signOut } = useAuth()
  const practice = usePracticeState()
  const summary = stats()
  const [problems, setProblems] = useState<ProblemSummary[]>([])
  const [copied, setCopied] = useState<'idle' | 'done' | 'failed'>('idle')
  const [shareToken, setShareToken] = useState<string | null>(null)
  const [shareFailed, setShareFailed] = useState(false)

  useEffect(() => {
    let live = true
    void (async () => {
      try {
        const response = await apiFetch('/api/v1/profile/share', { method: 'POST' })
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        const data = (await response.json()) as { token?: string }
        if (!live) return
        if (data.token) setShareToken(data.token)
        else setShareFailed(true)
      } catch {
        if (live) setShareFailed(true)
      }
    })()
    return () => {
      live = false
    }
  }, [])

  useEffect(() => {
    let live = true
    void listProblems().then((outcome) => {
      if (live && outcome.kind === 'ok') setProblems(outcome.value)
    })
    return () => {
      live = false
    }
  }, [])

  const bySlug = useMemo(
    () => new Map(problems.map((problem) => [problem.slug, problem])),
    [problems],
  )

  const solvedProblems = useMemo(
    () =>
      practice.solved
        .map((slug) => bySlug.get(slug))
        .filter((problem): problem is ProblemSummary => Boolean(problem)),
    [practice.solved, bySlug],
  )

  const byDifficulty = useMemo(
    () => ({
      Easy: solvedProblems.filter((problem) => problem.difficulty === 'Easy').length,
      Medium: solvedProblems.filter((problem) => problem.difficulty === 'Medium').length,
      Hard: solvedProblems.filter((problem) => problem.difficulty === 'Hard').length,
    }),
    [solvedProblems],
  )

  const topTags = useMemo(() => {
    const counts = new Map<string, number>()
    for (const problem of solvedProblems) {
      for (const tag of problem.tags) counts.set(tag, (counts.get(tag) ?? 0) + 1)
    }
    return [...counts.entries()]
      .map(([tag, count]) => ({ tag, count }))
      .sort((a, b) => b.count - a.count || a.tag.localeCompare(b.tag))
      .slice(0, 6)
  }, [solvedProblems])

  const name = displayName(user)
  const photo = avatarUrl(user)
  const joined = month(user?.created_at)

  // The live link is the token, so it never changes as the numbers do. The
  // snapshot is only built if asking for a token failed; it is the same shape
  // the page has always understood.
  const joinedAt = user?.created_at ?? null
  const snapshotLink = useMemo(
    () =>
      profileLink({
        v: 1,
        name,
        joined: joinedAt,
        at: new Date().toISOString(),
        solved: summary.solved,
        inSheet: summary.inSheet,
        reviews: summary.reviews,
        streak: summary.streak,
        retention: Math.round(summary.retention * 100),
        graduated: summary.graduated,
        byDifficulty,
        topTags,
      }),
    [
      byDifficulty,
      joinedAt,
      name,
      summary.graduated,
      summary.inSheet,
      summary.retention,
      summary.reviews,
      summary.solved,
      summary.streak,
      topTags,
    ],
  )
  const link = shareToken
    ? `${window.location.origin}/p/${shareToken}`
    : shareFailed
      ? snapshotLink
      : ''
  const solvedTotal = Math.max(1, byDifficulty.Easy + byDifficulty.Medium + byDifficulty.Hard)

  async function copyLink() {
    if (!link) return
    try {
      await navigator.clipboard.writeText(link)
      setCopied('done')
      window.setTimeout(() => setCopied('idle'), 2200)
    } catch {
      setCopied('failed')
    }
  }

  return (
    <div className="profile">
      <section className="profile-head">
        <div className="profile-big-avatar" aria-hidden="true">
          {photo ? (
            <img src={photo} alt="" referrerPolicy="no-referrer" />
          ) : (
            (name.charAt(0) || 'R').toUpperCase()
          )}
        </div>
        <div className="profile-head-copy">
          <h2 className="profile-name">{name}</h2>
          <p className="profile-sub">
            {user?.email ?? 'No email'} · joined {joined}
          </p>
          <p className="profile-bio">
            {summary.solved > 0
              ? `${summary.solved} solved, ${summary.inSheet} kept in rotation, ${summary.reviews} graded reviews.`
              : 'No attempts yet. The profile fills itself in as you solve.'}
          </p>
        </div>
        <button
          className="button button-light button-small"
          type="button"
          disabled={!link}
          onClick={() => void copyLink()}
        >
          {copied === 'done' ? 'Link copied' : shareToken || shareFailed ? 'Share profile' : 'Creating link…'}
        </button>
      </section>

      {copied === 'failed' && (
        <p className="profile-notice" role="status">
          The browser would not copy for you. Select the link below instead.
        </p>
      )}

      <ul className="stat-row">
        <li className="stat">
          <span className="stat-value">{summary.solved}</span>
          <span className="stat-label">Solved</span>
        </li>
        <li className="stat">
          <span className="stat-value">{summary.inSheet}</span>
          <span className="stat-label">In rotation</span>
        </li>
        <li className="stat">
          <span className="stat-value">{summary.reviews}</span>
          <span className="stat-label">Reviews</span>
        </li>
        <li className="stat">
          <span className="stat-value">{summary.streak}</span>
          <span className="stat-label">Day streak</span>
        </li>
      </ul>

      <div className="dash-panels">
        <section className="dash-panel">
          <header className="panel-head">
            <h3 className="panel-title">Memory</h3>
            <span className="panel-note">from the scheduler</span>
          </header>
          <div className="profile-memory">
            <strong>
              {summary.inSheet === 0 ? '—' : `${Math.round(summary.retention * 100)}%`}
            </strong>
            <span>predicted recall across the sheet</span>
          </div>
          <ul className="profile-facts">
            <li>
              <span>Learning</span>
              <strong>{summary.byState.learning}</strong>
            </li>
            <li>
              <span>Reviewing</span>
              <strong>{summary.byState.review}</strong>
            </li>
            <li>
              <span>Retired</span>
              <strong>{summary.byState.graduated}</strong>
            </li>
            <li>
              <span>Lapses</span>
              <strong>{summary.lapses}</strong>
            </li>
          </ul>
        </section>

        <section className="dash-panel">
          <header className="panel-head">
            <h3 className="panel-title">Solved by difficulty</h3>
            <span className="panel-note">
              {byDifficulty.Easy + byDifficulty.Medium + byDifficulty.Hard} classified
            </span>
          </header>
          <ul className="mix">
            {DIFFICULTIES.map((difficulty) => (
              <li className="mix-row" key={difficulty}>
                <span className="mix-label">{difficulty}</span>
                <span className="mix-track">
                  <span
                    className="mix-fill"
                    style={{ width: `${(byDifficulty[difficulty] / solvedTotal) * 100}%` }}
                  />
                </span>
                <span className="mix-value">{byDifficulty[difficulty]}</span>
              </li>
            ))}
          </ul>
          <p className="panel-foot">
            Community tags, shown for context — the schedule ignores them.
          </p>
        </section>
      </div>

      <section className="dash-panel">
        <header className="panel-head">
          <h3 className="panel-title">Share link</h3>
          <span className="panel-note">
            {shareToken ? 'live from the database' : shareFailed ? 'snapshot fallback' : 'creating…'}
          </span>
        </header>
        <p className="panel-empty">
          {shareToken
            ? 'Anyone with this link sees your current counts — no email, no review log, no account needed.'
            : shareFailed
              ? 'The live link is unavailable, so this link carries a snapshot of the numbers above.'
              : 'Getting a share token for this account.'}
        </p>
        <div className="share-box">
          <input
            className="share-input"
            type="text"
            value={link}
            readOnly
            placeholder={shareFailed ? '' : 'Creating your link…'}
            aria-label="Public profile link"
            onFocus={(event) => event.currentTarget.select()}
          />
          {link && (
            <a className="button button-ghost button-small" href={link} target="_blank" rel="noreferrer">
              Open
            </a>
          )}
        </div>
        {copied === 'failed' && <p className="share-hint">Select the link and copy it.</p>}
      </section>

      <div className="dash-panels">
        <section className="dash-panel">
          <header className="panel-head">
            <h3 className="panel-title">Strongest tags</h3>
            <span className="panel-note">by solved count</span>
          </header>
          {topTags.length === 0 ? (
            <p className="panel-empty">Tags appear once you have solved a problem.</p>
          ) : (
            <ul className="tag-list">
              {topTags.map((entry) => (
                <li key={entry.tag}>
                  <span>{entry.tag}</span>
                  <strong>{entry.count}</strong>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="dash-panel">
          <header className="panel-head">
            <h3 className="panel-title">Account</h3>
            <span className="panel-note">Supabase auth</span>
          </header>
          <ul className="profile-facts">
            <li>
              <span>Email</span>
              <strong className="profile-fact-text">{user?.email ?? '—'}</strong>
            </li>
            <li>
              <span>Provider</span>
              <strong className="profile-fact-text">
                {user?.app_metadata?.provider === 'google' ? 'Google' : 'Email & password'}
              </strong>
            </li>
            <li>
              <span>Member since</span>
              <strong className="profile-fact-text">{joined}</strong>
            </li>
            <li>
              <span>Practice data</span>
              <strong className="profile-fact-text">Supabase</strong>
            </li>
          </ul>
          <div className="profile-actions">
            <button
              className="button button-ghost button-small"
              type="button"
              onClick={() => onNavigate('learn')}
            >
              Browse problems
            </button>
            <button
              className="profile-signout"
              type="button"
              onClick={() => void signOut()}
            >
              Log out
            </button>
          </div>
        </section>
      </div>

      <p className="profile-footnote">
        A shared profile is live: the page reads the database each time the link is opened. It
        carries counts only — no email, no user id, no review log.
      </p>
    </div>
  )
}
