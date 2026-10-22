import { useEffect, useMemo, useState } from 'react'

import { displayName, useAuth } from '@/lib/auth-context'
import type { ViewId } from '@/lib/navigation'
import {
  activity,
  describeInterval,
  history,
  recallOf,
  stats,
  usePracticeState,
} from '@/lib/practice-store'
import type { Card, Rating, ReviewEvent } from '@/lib/practice-store'
import { listProblems } from '@/lib/problems'
import type { ProblemSummary } from '@/lib/problems'

const RATING_LABEL: Record<Rating, string> = {
  medium: 'Medium',
  hard: 'Hard',
  extreme: 'Extreme',
}

const RATING_NOTE: Record<Rating, string> = {
  medium: 'clean solve',
  hard: 'barely got it',
  extreme: 'used the solution',
}

function relativeTime(value: string, now: number): string {
  const minutes = Math.round((now - new Date(value).getTime()) / 60_000)
  if (minutes < 1) return 'just now'
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.round(hours / 24)
  return days === 1 ? 'yesterday' : `${days}d ago`
}

function dueLabel(card: Card, now: number): string {
  const remaining = new Date(card.due_at).getTime() - now
  if (remaining <= 0) return 'Due now'
  return describeInterval(remaining / 86_400_000)
}

/**
 * A problem's title, or a readable name for a slug the catalogue no longer has.
 * A card can outlive a catalogue entry; it must not render as `two-sum`.
 */
function labelFor(slug: string, bySlug: Map<string, ProblemSummary>): string {
  return bySlug.get(slug)?.title ?? slug.replaceAll('-', ' ')
}

/** The 12-week review chart: one cell per day, darkest is busiest. */
function ActivityChart({
  events,
  now,
  weeks = 12,
}: {
  events: readonly ReviewEvent[]
  now: number
  weeks?: number
}) {
  const counts = useMemo(() => activity(events, weeks, now), [events, weeks, now])

  const cells = useMemo(() => {
    const end = new Date(now)
    end.setHours(0, 0, 0, 0)
    const start = new Date(end)
    start.setDate(start.getDate() - (weeks * 7 - 1))

    return Array.from({ length: weeks * 7 }, (_, index) => {
      const date = new Date(start)
      date.setDate(start.getDate() + index)
      const key = `${date.getFullYear()}-${`${date.getMonth() + 1}`.padStart(2, '0')}-${`${date.getDate()}`.padStart(2, '0')}`
      return { date, count: counts.get(key) ?? 0 }
    })
  }, [counts, now, weeks])

  const busiest = Math.max(1, ...cells.map((cell) => cell.count))

  return (
    <div className="activity">
      <div className="activity-grid" role="img" aria-label={`Reviews in the last ${weeks} weeks`}>
        {cells.map((cell) => {
          const level =
            cell.count === 0 ? 0 : Math.max(1, Math.ceil((cell.count / busiest) * 4))
          return (
            <span
              key={cell.date.toISOString()}
              className={level === 0 ? 'activity-cell' : `activity-cell is-${level}`}
              title={`${cell.date.toDateString()} — ${cell.count} review${cell.count === 1 ? '' : 's'}`}
            />
          )
        })}
      </div>
      <div className="activity-foot">
        <span>{weeks} weeks ago</span>
        <span className="activity-scale" aria-hidden="true">
          quiet
          <i className="activity-cell" />
          <i className="activity-cell is-1" />
          <i className="activity-cell is-2" />
          <i className="activity-cell is-3" />
          <i className="activity-cell is-4" />
          busy
        </span>
        <span>today</span>
      </div>
    </div>
  )
}

/**
 * Home: the dashboard.
 *
 * Everything here is computed from the local practice state — the review log
 * the scheduler writes, plus the cards it produces. No round trip, so it is
 * ready the moment the view opens.
 *
 * The AI panel is a statement of intent, not a shipped feature. It says so.
 */
export function DashboardView({
  onNavigate,
  onOpen,
}: {
  onNavigate: (view: ViewId) => void
  onOpen: (slug: string) => void
}) {
  const { user } = useAuth()
  const practice = usePracticeState()
  const [problems, setProblems] = useState<ProblemSummary[]>([])
  // A clock for "due now" and "2h ago". Read in one place so the render is
  // pure, and ticked slowly — nothing here needs to be second-accurate.
  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    const tick = window.setInterval(() => setNow(Date.now()), 30_000)
    return () => window.clearInterval(tick)
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

  /**
   * The tags that keep showing up in shaky attempts.
   *
   * A hard or extreme rating is the only evidence of trouble the product has,
   * so this is the honest version of "weak spots": count those against each
   * problem's tags, not against the problem's own difficulty.
   */
  const weakSpots = useMemo(() => {
    const counts = new Map<string, number>()
    for (const event of practice.history) {
      if (event.rating === 'medium') continue
      for (const tag of bySlug.get(event.slug)?.tags ?? []) {
        counts.set(tag, (counts.get(tag) ?? 0) + 1)
      }
    }
    return [...counts.entries()]
      .map(([tag, count]) => ({ tag, count }))
      .sort((a, b) => b.count - a.count || a.tag.localeCompare(b.tag))
      .slice(0, 6)
  }, [practice.history, bySlug])

  const summary = stats(now)
  const recent = history(6)
  const name = displayName(user)
  const today = new Date(now)

  const liveCards = Object.values(practice.cards).filter(
    (card) => card.state !== 'graduated',
  )
  const upNext = [...liveCards]
    .sort((a, b) => recallOf(a, now) - recallOf(b, now))
    .slice(0, 4)
  const nextDue = liveCards
    .map((card) => new Date(card.due_at).getTime())
    .filter((at) => at > now)
    .sort((a, b) => a - b)[0]

  const memory = summary.inSheet === 0 ? null : Math.round(summary.retention * 100)

  const headline =
    summary.due > 0
      ? `${summary.due} problem${summary.due === 1 ? '' : 's'} due today.`
      : summary.inSheet > 0
        ? 'Nothing due today.'
        : summary.solved > 0
          ? 'Your sheet is empty.'
          : 'Start with one problem.'

  const note =
    summary.due > 0
      ? 'Most forgotten first. Rate how the attempt felt and the interval adjusts.'
      : summary.inSheet > 0
        ? nextDue
          ? `Next review ${describeInterval((nextDue - now) / 86_400_000)}. You can go through the sheet anyway.`
          : 'The whole sheet is ready to practise ahead of schedule.'
        : summary.solved > 0
          ? 'Pick a problem in Learn, rate it, and it joins the rotation.'
          : 'Solve something in Learn. Rate it. We decide when it comes back.'

  const totalRatings =
    summary.byRating.medium + summary.byRating.hard + summary.byRating.extreme

  return (
    <div className="dash">
      <section className="dash-summary">
        <div className="dash-status">
          <p className="dash-date">
            {new Intl.DateTimeFormat(undefined, {
              weekday: 'long',
              day: 'numeric',
              month: 'long',
            }).format(today)}
          </p>
          <h2 className="dash-headline">
            {name ? `${name}, ` : ''}
            {headline}
          </h2>
          <p className="dash-note">{note}</p>
          <button
            className="button button-light button-small"
            type="button"
            onClick={() =>
              onNavigate(summary.due > 0 || summary.inSheet > 0 ? 'practice' : 'learn')
            }
          >
            {summary.due > 0
              ? 'Start practice'
              : summary.inSheet > 0
                ? 'Practise ahead'
                : 'Browse problems'}
          </button>
        </div>

        <div className="dash-memory">
          <span className="dash-memory-label">Memory strength</span>
          <strong className="dash-memory-value">{memory === null ? '—' : `${memory}%`}</strong>
          <span className="meter" aria-hidden="true">
            <span
              className="meter-fill"
              style={{ width: memory === null ? '0%' : `${memory}%` }}
            />
          </span>
          <span className="dash-memory-note">
            {memory === null
              ? 'No problems in rotation yet.'
              : `Predicted recall across ${summary.inSheet} problem${summary.inSheet === 1 ? '' : 's'}.`}
          </span>
        </div>
      </section>

      <ul className="stat-row">
        <li className="stat">
          <span className="stat-value">{summary.due}</span>
          <span className="stat-label">Due today</span>
        </li>
        <li className="stat">
          <span className="stat-value">{summary.inSheet}</span>
          <span className="stat-label">In rotation</span>
        </li>
        <li className="stat">
          <span className="stat-value">{summary.solved}</span>
          <span className="stat-label">Solved</span>
        </li>
        <li className="stat">
          <span className="stat-value">{summary.streak}</span>
          <span className="stat-label">Day streak</span>
        </li>
      </ul>

      <div className="dash-panels">
        <section className="dash-panel">
          <header className="panel-head">
            <h3 className="panel-title">Reviews</h3>
            <span className="panel-note">{summary.reviews} all time</span>
          </header>
          <ActivityChart events={practice.history} now={now} />
          <p className="panel-foot">
            {summary.reviewsToday > 0
              ? `${summary.reviewsToday} today · ${summary.reviewsThisWeek} this week`
              : summary.reviewsThisWeek > 0
                ? `${summary.reviewsThisWeek} this week. Nothing today yet.`
                : 'No reviews in the last seven days.'}
          </p>
        </section>

        <section className="dash-panel">
          <header className="panel-head">
            <h3 className="panel-title">Up next</h3>
            <span className="panel-note">most forgotten first</span>
          </header>
          {upNext.length === 0 ? (
            <p className="panel-empty">
              Nothing scheduled. Solve a problem in Learn to start the rotation.
            </p>
          ) : (
            <ul className="mini-list">
              {upNext.map((card) => (
                <li key={card.slug}>
                  <button
                    className="mini-row"
                    type="button"
                    onClick={() => onOpen(card.slug)}
                  >
                    <span className="mini-row-name">
                      {labelFor(card.slug, bySlug)}
                    </span>
                    <span
                      className={
                        new Date(card.due_at).getTime() <= now
                          ? 'mini-row-when is-due'
                          : 'mini-row-when'
                      }
                    >
                      {dueLabel(card, now)}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <div className="dash-panels">
        <section className="dash-panel">
          <header className="panel-head">
            <h3 className="panel-title">How it felt</h3>
            <span className="panel-note">{totalRatings} ratings</span>
          </header>
          {totalRatings === 0 ? (
            <p className="panel-empty">Your rating mix appears here after the first attempt.</p>
          ) : (
            <ul className="mix">
              {(['medium', 'hard', 'extreme'] as Rating[]).map((rating) => {
                const value = summary.byRating[rating]
                const percent = Math.round((value / totalRatings) * 100)
                return (
                  <li className="mix-row" key={rating}>
                    <span className="mix-label">
                      {RATING_LABEL[rating]}
                      <em>{RATING_NOTE[rating]}</em>
                    </span>
                    <span className="mix-track">
                      <span className="mix-fill" style={{ width: `${percent}%` }} />
                    </span>
                    <span className="mix-value">
                      {value} ({percent}%)
                    </span>
                  </li>
                )
              })}
            </ul>
          )}
        </section>

        <section className="dash-panel">
          <header className="panel-head">
            <h3 className="panel-title">Recent reviews</h3>
            <span className="panel-note">latest first</span>
          </header>
          {recent.length === 0 ? (
            <p className="panel-empty">Nothing reviewed yet.</p>
          ) : (
            <ul className="mini-list">
              {recent.map((event) => (
                <li key={`${event.slug}-${event.at}`}>
                  <div className="recent-row">
                    <span className="mini-row-name">
                      {labelFor(event.slug, bySlug)}
                    </span>
                    <span className="recent-meta">
                      {RATING_LABEL[event.rating]} · {relativeTime(event.at, now)}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <section className="dash-panel">
        <header className="panel-head">
          <h3 className="panel-title">Tags to revisit</h3>
          <span className="panel-note">from hard and extreme ratings</span>
        </header>
        {weakSpots.length === 0 ? (
          <p className="panel-empty">
            Nothing shaky yet. Every rating so far has been a clean solve.
          </p>
        ) : (
          <ul className="tag-list">
            {weakSpots.map((entry) => (
              <li key={entry.tag}>
                <span>{entry.tag}</span>
                <strong>{entry.count}</strong>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="ai-card">
        <div className="ai-copy">
          <span className="ai-badge">Not in this build</span>
          <h3 className="ai-title">AI coach</h3>
          <p className="ai-note">
            Coming soon. The scheduler already records everything a coach would need — every
            rating, every interval, every lapse — so these will read the same review log rather
            than guessing.
          </p>
        </div>
        <ul className="ai-list">
          <li>
            <strong>Weak-spot report</strong>
            <span>Which topics your lapses cluster in.</span>
          </li>
          <li>
            <strong>Revision plan</strong>
            <span>A week of practice built from the due queue.</span>
          </li>
          <li>
            <strong>Explain my rating</strong>
            <span>Why an interval moved the way it did.</span>
          </li>
        </ul>
      </section>
    </div>
  )
}
