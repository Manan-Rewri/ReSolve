/**
 * The user's practice state.
 *
 * It lives in **Supabase**, read and written through the API. The browser
 * keeps an in-memory copy so a queue render does not wait for a round trip,
 * and it keeps the old `localStorage` bucket only long enough to upload it
 * once (see `importLocal`).
 *
 * The **rules** are not duplicated here. `applyRating` posts the rating to
 * `/api/v1/practice/schedule`, which runs `app/core/scheduler.py` and stores
 * the card that comes out the other side. The browser only keeps the answer.
 */

import { useEffect, useState } from 'react'

import { apiFetch } from '@/lib/api'

export type Rating = 'medium' | 'hard' | 'extreme'

export type CardState = 'new' | 'learning' | 'review' | 'graduated'

export type Card = {
  slug: string
  state: CardState
  /** Days until recall is predicted to fall to 90%. The interval. */
  stability_days: number
  due_at: string
  reps: number
  lapses: number
  last_rating: Rating | null
  last_reviewed_at: string | null
}

/** One graded review. The dashboard reads these; the scheduler never does. */
export type ReviewEvent = {
  slug: string
  rating: Rating
  at: string
}

export type State = {
  cards: Record<string, Card>
  sheet: string[]
  solved: string[]
  history: ReviewEvent[]
}

const EMPTY: State = { cards: {}, sheet: [], solved: [], history: [] }

/** Keeps the state small enough that a log never grows without bound. */
const HISTORY_LIMIT = 5000

/** The old browser bucket, kept only as a migration source. */
const STORAGE_PREFIX = 'resolve.practice.v2:'

let current = EMPTY

/**
 * Who the state belongs to.
 *
 * The auth provider sets this whenever the Supabase session changes, so each
 * account gets its own sheet and signing out does not leave another user's
 * cards in memory.
 */
let userId: string | null = null

/** Why the last load failed, if it did. `null` means the state is trustworthy. */
let loadError: string | null = null

/**
 * Bumped whenever the user changes. A response that arrives after a switch is
 * dropped rather than written into the new user's bucket.
 */
let generation = 0

export function setUser(id: string | null): void {
  userId = id
  generation += 1
  current = EMPTY
  loadError = null
}

/** Notified whenever the practice state changes, so views can re-render. */
const listeners = new Set<() => void>()

function notify() {
  for (const listener of listeners) listener()
}

function subscribe(listener: () => void) {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

function storageKey(): string | null {
  return userId ? `${STORAGE_PREFIX}${userId}` : null
}

/**
 * A card written by an older version must not poison the queue.
 *
 * Anything without a stability is dropped rather than coerced: a made-up
 * interval is worse than a missing card, because the user would never know.
 */
const CARD_STATES: CardState[] = ['new', 'learning', 'review', 'graduated']
const RATINGS: Rating[] = ['medium', 'hard', 'extreme']

function dateString(value: unknown): string | null {
  if (typeof value !== 'string') return null
  return Number.isNaN(new Date(value).getTime()) ? null : value
}

function normaliseCard(raw: unknown): Card | null {
  if (!raw || typeof raw !== 'object') return null
  const card = raw as Partial<Card>

  if (typeof card.slug !== 'string' || !card.slug) return null
  if (typeof card.stability_days !== 'number' || !Number.isFinite(card.stability_days)) {
    return null
  }
  if (card.stability_days < 0) return null

  const dueAt = dateString(card.due_at)
  if (!dueAt) return null

  return {
    slug: card.slug,
    state: CARD_STATES.includes(card.state as CardState) ? (card.state as CardState) : 'review',
    stability_days: card.stability_days,
    due_at: dueAt,
    reps: typeof card.reps === 'number' ? Math.max(0, Math.round(card.reps)) : 0,
    lapses: typeof card.lapses === 'number' ? Math.max(0, Math.round(card.lapses)) : 0,
    last_rating: RATINGS.includes(card.last_rating as Rating)
      ? (card.last_rating as Rating)
      : null,
    last_reviewed_at: dateString(card.last_reviewed_at),
  }
}

function normaliseHistory(raw: unknown): ReviewEvent[] {
  if (!Array.isArray(raw)) return []
  return raw.flatMap((entry) => {
    if (!entry || typeof entry !== 'object') return []
    const event = entry as Partial<ReviewEvent>
    const at = dateString(event.at)
    if (
      typeof event.slug !== 'string' ||
      !at ||
      !RATINGS.includes(event.rating as Rating)
    ) {
      return []
    }
    return [{ slug: event.slug, rating: event.rating as Rating, at }]
  })
}

function normaliseState(raw: unknown): State {
  if (!raw || typeof raw !== 'object') return EMPTY
  const state = raw as Partial<State>

  const cards: Record<string, Card> = {}
  for (const [slug, value] of Object.entries(state.cards ?? {})) {
    const card = normaliseCard(value)
    if (card) cards[slug] = card
  }

  const sheet = Array.isArray(state.sheet) ? state.sheet : []
  const solved = Array.isArray(state.solved) ? state.solved : []

  return {
    cards,
    sheet: sheet.filter((slug) => typeof slug === 'string'),
    solved: solved.filter((slug) => typeof slug === 'string'),
    history: normaliseHistory(state.history),
  }
}

/** The old local bucket, if this browser still has one. */
function localBucket(): State | null {
  const key = storageKey()
  if (!key) return null
  try {
    const raw = localStorage.getItem(key)
    if (!raw) return null
    return normaliseState(JSON.parse(raw))
  } catch {
    return null
  }
}

function isEmpty(state: State): boolean {
  return (
    Object.keys(state.cards).length === 0 &&
    state.solved.length === 0 &&
    state.history.length === 0
  )
}

async function fetchServerState(): Promise<State | null> {
  try {
    const response = await apiFetch('/api/v1/practice/state')
    if (!response.ok) {
      const detail = await response.json().catch(() => null)
      loadError =
        typeof detail?.detail === 'string'
          ? detail.detail
          : `Could not load your practice sheet (HTTP ${response.status}).`
      return null
    }
    return normaliseState(await response.json())
  } catch {
    loadError = 'Could not reach the server. Your practice sheet was not loaded.'
    return null
  }
}

/**
 * Upload the old localStorage bucket the first time this account is opened
 * against the database.
 *
 * A one-time move, not a sync: the server refuses an import into an account
 * that already has rows, so a reload cannot duplicate the review log. Once the
 * upload succeeds the local bucket is deleted, because two sources of truth
 * is how a sheet ends up disagreeing with itself.
 */
async function importLocal(server: State): Promise<State> {
  if (!userId || !isEmpty(server)) return server

  const local = localBucket()
  if (!local) return server

  const key = storageKey()
  if (isEmpty(local)) {
    if (key) localStorage.removeItem(key)
    return server
  }

  try {
    const response = await apiFetch('/api/v1/practice/import', {
      method: 'POST',
      body: JSON.stringify({
        cards: local.cards,
        solved: local.solved,
        history: local.history,
      }),
    })

    if (response.ok) {
      if (key) localStorage.removeItem(key)
      // Read it back rather than trusting the local copy: the server drops
      // cards for problems it does not know, and derives the sheet itself.
      return (await fetchServerState()) ?? server
    }

    if (response.status === 409) {
      // The account gained rows between the read and the upload (another tab,
      // or an earlier import that did land). The server is now the truth, so
      // stop offering it the stale bucket.
      if (key) localStorage.removeItem(key)
      return (await fetchServerState()) ?? server
    }

    const detail = await response.json().catch(() => null)
    loadError =
      typeof detail?.detail === 'string'
        ? detail.detail
        : `Your saved practice sheet could not be uploaded (HTTP ${response.status}).`
  } catch {
    loadError = 'Could not reach the server. Your saved practice sheet was not uploaded.'
  }

  return server
}

/**
 * Load the state for whoever is signed in.
 *
 * Used when the page opens and whenever the user changes. A failure is kept
 * in `loadError` and shown in the shell; it is never rendered as an empty
 * sheet without an explanation.
 */
export async function refresh(): Promise<State> {
  const mine = generation
  loadError = null

  if (!userId) {
    current = EMPTY
    notify()
    return current
  }

  const server = await fetchServerState()
  if (mine !== generation) return current

  if (server === null) {
    current = EMPTY
    notify()
    return current
  }

  const loaded = await importLocal(server)
  if (mine !== generation) return current

  current = loaded
  notify()
  return current
}

export function cardFor(slug: string): Card | undefined {
  return current.cards[slug]
}

function cards(): Card[] {
  return Object.values(current.cards)
}

function dueCount(now: number): number {
  return cards().filter(
    (card) => card.state !== 'graduated' && new Date(card.due_at).getTime() <= now,
  ).length
}

/** The problems still in the user's practice sheet. */
export function sheet(): string[] {
  return current.sheet.filter((slug) => current.cards[slug]?.state !== 'graduated')
}

/** The problems the user has got fully right. */
export function solvedList(): string[] {
  return current.solved
}

/**
 * The predicted chance the user still remembers a card, between 0 and 1.
 *
 * `recall(t) = 0.9 ** (t / stability)`, exactly what the scheduler assumes.
 * The queue and the dashboard both read it from here so there is one formula.
 */
export function recallOf(card: Card, now = Date.now()): number {
  if (card.last_reviewed_at === null || card.stability_days <= 0) return 1
  const elapsedDays = (now - new Date(card.last_reviewed_at).getTime()) / 86_400_000
  return Math.min(1, Math.max(0, 0.9 ** (elapsedDays / card.stability_days)))
}

/** Trouble in words, for a card's stability. */
export function describeInterval(days: number): string {
  const minutes = Math.round(days * 24 * 60)
  if (minutes < 60) return `in ${Math.max(1, minutes)} minute${minutes === 1 ? '' : 's'}`
  const hours = Math.round(days * 24)
  if (hours < 24) return `in ${hours} hour${hours === 1 ? '' : 's'}`
  if (days < 2) return 'tomorrow'
  if (days < 14) return `in ${Math.round(days)} days`
  if (days < 60) return `in ${Math.round(days / 7)} weeks`
  return `in ${Math.round(days / 30)} months`
}

function dayKey(value: string | Date): string {
  const date = typeof value === 'string' ? new Date(value) : value
  const month = `${date.getMonth() + 1}`.padStart(2, '0')
  const day = `${date.getDate()}`.padStart(2, '0')
  return `${date.getFullYear()}-${month}-${day}`
}

export type PracticeStats = {
  solved: number
  inSheet: number
  due: number
  /** Every rating ever given, from the review log. */
  reviews: number
  reviewsToday: number
  reviewsThisWeek: number
  /** Consecutive days ending today or yesterday with at least one review. */
  streak: number
  lapses: number
  graduated: number
  /** Mean predicted recall across the live sheet, 0..1. */
  retention: number
  byRating: Record<Rating, number>
  byState: Record<'learning' | 'review' | 'graduated', number>
}

/** Everything the dashboard and the profile need, from the loaded state. */
export function stats(now = Date.now()): PracticeStats {
  const live = cards().filter((card) => card.state !== 'graduated')
  const history = current.history
  const today = dayKey(new Date(now))

  const weekAgo = now - 7 * 86_400_000
  const byRating: Record<Rating, number> = { medium: 0, hard: 0, extreme: 0 }
  for (const event of history) byRating[event.rating] += 1

  const days = new Set(history.map((event) => dayKey(event.at)))
  let streak = 0
  const cursor = new Date(now)
  if (!days.has(dayKey(cursor))) cursor.setDate(cursor.getDate() - 1)
  while (days.has(dayKey(cursor))) {
    streak += 1
    cursor.setDate(cursor.getDate() - 1)
  }

  const retention =
    live.length === 0
      ? 0
      : live.reduce((total, card) => total + recallOf(card, now), 0) / live.length

  const byState: PracticeStats['byState'] = { learning: 0, review: 0, graduated: 0 }
  for (const card of cards()) {
    if (card.state === 'graduated') byState.graduated += 1
    else if (card.state === 'learning') byState.learning += 1
    else byState.review += 1
  }

  return {
    solved: current.solved.length,
    inSheet: live.length,
    due: dueCount(now),
    reviews: history.length,
    reviewsToday: history.filter((event) => dayKey(event.at) === today).length,
    reviewsThisWeek: history.filter((event) => new Date(event.at).getTime() >= weekAgo).length,
    streak,
    lapses: cards().reduce((total, card) => total + card.lapses, 0),
    graduated: byState.graduated,
    retention: Number.isFinite(retention) ? retention : 0,
    byRating,
    byState,
  }
}

/** The review log, newest first. */
export function history(limit = 20): ReviewEvent[] {
  return [...current.history]
    .sort((a, b) => b.at.localeCompare(a.at))
    .slice(0, limit)
}

/**
 * Reviews per local day, for the activity chart. Keys are `YYYY-MM-DD`.
 *
 * The events are passed in rather than read from `current` so a caller can
 * memoise on the log it was given.
 */
export function activity(
  events: readonly ReviewEvent[],
  weeks = 12,
  now = Date.now(),
): Map<string, number> {
  const counts = new Map<string, number>()
  const start = new Date(now)
  start.setHours(0, 0, 0, 0)
  start.setDate(start.getDate() - (weeks * 7 - 1))

  for (const event of events) {
    const date = new Date(event.at)
    if (date.getTime() < start.getTime()) continue
    const key = dayKey(date)
    counts.set(key, (counts.get(key) ?? 0) + 1)
  }
  return counts
}

/** The problems the user has solved, as a set for the Learn list. */
export function useSolved(): Set<string> {
  const [solved, setSolved] = useState(() => new Set(current.solved))

  useEffect(() => {
    const update = () => setSolved(new Set(current.solved))
    update()
    return subscribe(update)
  }, [])

  return solved
}

/**
 * The whole state, re-rendering the caller whenever anything is written.
 *
 * The dashboard, the profile and the practice bar all read this.
 */
export function usePracticeState(): State {
  const [state, setState] = useState<State>(current)

  useEffect(() => {
    const update = () => setState(current)
    update()
    return subscribe(update)
  }, [])

  return state
}

/** The load failure, for the shell to show. `null` when the sheet is healthy. */
export function usePracticeError(): string | null {
  const [, bump] = useState(0)

  useEffect(() => {
    const update = () => bump((value) => value + 1)
    update()
    return subscribe(update)
  }, [])

  return loadError
}

/** Record that a problem has been got fully right. */
export async function markSolved(slug: string, solved = true): Promise<boolean> {
  const mine = generation
  try {
    const response = await apiFetch('/api/v1/practice/solved', {
      method: 'POST',
      body: JSON.stringify({ slug, solved }),
    })
    if (!response.ok || mine !== generation) return false
  } catch {
    return false
  }

  current = {
    ...current,
    solved: solved
      ? current.solved.includes(slug)
        ? current.solved
        : [...current.solved, slug]
      : current.solved.filter((s) => s !== slug),
  }
  notify()
  return true
}

/**
 * "Very easy": this problem does not belong in the practice sheet.
 *
 * That is a decision, not a schedule, so the card is removed rather than
 * pushed years out. The solved tick stays, because solving it and scheduling
 * it are different things.
 */
export async function markVeryEasy(slug: string): Promise<boolean> {
  if (!current.cards[slug] && !current.sheet.includes(slug)) return true

  const mine = generation
  try {
    const response = await apiFetch('/api/v1/practice/very-easy', {
      method: 'POST',
      body: JSON.stringify({ slug }),
    })
    if (!response.ok || mine !== generation) return false
  } catch {
    return false
  }

  const cards = { ...current.cards }
  delete cards[slug]
  current = {
    ...current,
    cards,
    sheet: current.sheet.filter((s) => s !== slug),
  }
  notify()
  return true
}

/**
 * Apply a rating, on the server, and keep the card that comes out of it.
 *
 * The previous card is read server-side, not sent by the browser, so two tabs
 * cannot rewind each other. A failure is **never** silent: the caller gets the
 * message and shows it where the user is looking.
 */
export async function applyRating(
  slug: string,
  rating: Rating,
): Promise<{ ok: true; card: Card } | { ok: false; message: string }> {
  const mine = generation
  try {
    const response = await apiFetch('/api/v1/practice/schedule', {
      method: 'POST',
      body: JSON.stringify({ slug, rating }),
    })

    if (!response.ok) {
      const detail = await response.json().catch(() => null)
      const message =
        typeof detail?.detail === 'string'
          ? detail.detail
          : `The rating could not be saved (HTTP ${response.status}).`
      return { ok: false, message }
    }

    if (mine !== generation) {
      return { ok: false, message: 'The account changed before the rating was saved.' }
    }

    const result = (await response.json()) as { card: Card; graduated: boolean }
    const next: State = {
      cards: { ...current.cards, [result.card.slug]: result.card },
      sheet: result.graduated
        ? current.sheet.filter((s) => s !== slug)
        : current.sheet.includes(slug)
          ? current.sheet
          : [...current.sheet, slug],
      solved: current.solved,
      history: [
        ...current.history,
        {
          slug,
          rating,
          at: result.card.last_reviewed_at ?? new Date().toISOString(),
        },
      ].slice(-HISTORY_LIMIT),
    }

    current = next
    notify()
    return { ok: true, card: result.card }
  } catch {
    return { ok: false, message: 'Could not reach the server. The rating was not saved.' }
  }
}

/**
 * The practice queue.
 *
 * `due` are the problems that are due, ordered the way the scheduler orders
 * them: the most forgotten first. `upcoming` are the ones in the sheet that
 * are not due yet — you can practise ahead of the schedule, the way Anki's
 * custom study does, and the page says which is which.
 */
export type Queue = { due: string[]; upcoming: string[] }

export async function dueQueue(now = Date.now()): Promise<Queue> {
  const live = cards().filter((card) => card.state !== 'graduated')
  const forgottenFirst = (a: Card, b: Card) =>
    recallOf(a, now) === recallOf(b, now)
      ? a.slug.localeCompare(b.slug)
      : recallOf(a, now) - recallOf(b, now)

  return {
    due: live
      .filter((card) => new Date(card.due_at).getTime() <= now)
      .sort(forgottenFirst)
      .map((card) => card.slug),
    upcoming: live
      .filter((card) => new Date(card.due_at).getTime() > now)
      .sort(forgottenFirst)
      .map((card) => card.slug),
  }
}
