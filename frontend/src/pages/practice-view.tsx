import { useCallback, useEffect, useState } from 'react'

import { ProblemWorkspace } from '@/components/problem-workspace'
import { RatingDialog } from '@/components/rating-dialog'
import {
  applyRating,
  cardFor,
  describeInterval,
  dueQueue,
  recallOf,
  refresh,
  sheet,
  solvedList,
} from '@/lib/practice-store'
import type { Queue, Rating } from '@/lib/practice-store'

/**
 * Practice, the way Anki works it.
 *
 * One problem at a time, from the ones that are due, most forgotten first.
 * You attempt it, then say how it went, and the answer decides when it comes
 * back.
 *
 * There is no "very easy" here: the sheet is for problems that need practising,
 * and a problem that is going to be months away either way is one the scheduler
 * will have retired on its own.
 */
const OPTIONS: { rating: Rating; label: string; hint: string }[] = [
  { rating: 'medium', label: 'Medium', hint: 'Clean solve. The interval doubles.' },
  { rating: 'hard', label: 'Hard', hint: 'Barely got it. The interval halves.' },
  {
    rating: 'extreme',
    label: 'Extreme',
    hint: 'You used the solution. Back in ten minutes.',
  },
]

export default function PracticeView() {
  const [queue, setQueue] = useState<Queue>({ due: [], upcoming: [] })
  const [current, setCurrent] = useState(0)
  const [loading, setLoading] = useState(true)
  const [asking, setAsking] = useState(false)
  const [notice, setNotice] = useState('')
  /** Practising the problems that are not due yet, ahead of the schedule. */
  const [ahead, setAhead] = useState(false)
  /** The problems already done in this run, so the list always moves on. */
  const [done, setDone] = useState<string[]>([])

  useEffect(() => {
    let live = true
    void (async () => {
      // The state is local, so it is re-read before the queue is built from it.
      await refresh()
      const result = await dueQueue()
      if (!live) return
      setQueue(result)
      setCurrent(0)
      setLoading(false)
    })()
    return () => {
      live = false
    }
  }, [])

  // A problem you got wrong comes back in a minute, so the queue is re-read
  // while the page is open. Without this it would sit there until you
  // reloaded, and the same-day retry would never happen.
  useEffect(() => {
    const tick = setInterval(() => {
      void dueQueue().then((result) => {
        setQueue(result)
        setCurrent(0)
      })
    }, 20_000)
    return () => clearInterval(tick)
  }, [])

  const reload = useCallback(async () => {
    // The queue is rebuilt from the cards, so the problem that was just rated
    // drops out of it unless it is still due.
    setQueue(await dueQueue())
    setCurrent(0)
  }, [])

  // The list is the due problems, or the rest of the sheet when the user has
  // asked to go through it anyway. The ones already done in this run are left
  // out, so the list always moves on.
  const source = ahead ? queue.upcoming : queue.due
  const list = source.filter((slug) => !done.includes(slug))

  async function rate(rating: Rating) {
    const slug = list[current]
    setAsking(false)
    if (!slug) return
    const outcome = await applyRating(slug, rating)
    if (!outcome.ok) {
      setNotice(outcome.message)
      return
    }

    setNotice(
      outcome.card.state === 'graduated'
        ? 'Retired. You have known this one for three months of intervals.'
        : `Saved — back ${describeInterval(outcome.card.stability_days)}.`,
    )
    setDone((previous) => [...previous, slug])
    await reload()
  }

  if (loading) {
    return <p className="app-placeholder">Loading your practice sheet...</p>
  }

  const slug = list[current]

  if (!slug) {
    if (ahead) {
      // The run through the sheet is finished.
      return (
        <div className="practice-empty">
          <p className="practice-empty-title">That is your sheet done.</p>
          <p className="practice-empty-note">
            {sheet().length} problem{sheet().length === 1 ? '' : 's'} in your sheet.
            Come back when they are due.
          </p>
          <button
            className="button button-light"
            type="button"
            onClick={() => {
              setAhead(false)
              setDone([])
              setCurrent(0)
            }}
          >
            Back
          </button>
        </div>
      )
    }

    if (queue.upcoming.length > 0) {
      return (
        <div className="practice-empty">
          <p className="practice-empty-title">Nothing due.</p>
          <p className="practice-empty-note">
            {queue.upcoming.length} problem{queue.upcoming.length === 1 ? '' : 's'} in your
            sheet. You can go through them anyway.
          </p>
          <button
            className="button button-light"
            type="button"
            onClick={() => {
              setAhead(true)
              setDone([])
              setCurrent(0)
            }}
          >
            Practise again
          </button>
        </div>
      )
    }

    // Solved problems, but none in the sheet. Either they were rated very
    // easy, or a rating was lost before it could be saved. Either way, the way
    // to get them back is to say so and offer it.
    const solved = solvedList()
    if (solved.length > 0) {
      return (
        <div className="practice-empty">
          <p className="practice-empty-title">Nothing due.</p>
          <p className="practice-empty-note">
            You have solved {solved.length} problem{solved.length === 1 ? '' : 's'}, but
            none of them are in your practice sheet. Put them back in and they will start
            coming round again.
          </p>
          <button
            className="button button-light"
            type="button"
            onClick={async () => {
              for (const slug of solved) await applyRating(slug, 'medium')
              await reload()
              setAhead(true)
              setDone([])
              setCurrent(0)
            }}
          >
            Put my {solved.length} solved problem{solved.length === 1 ? '' : 's'} back in
          </button>
        </div>
      )
    }

    return (
      <div className="practice-empty">
        <p className="practice-empty-title">Nothing for today.</p>
        <p className="practice-empty-note">
          Solve a problem in Learn and it will be waiting here.
        </p>
      </div>
    )
  }

  const card = cardFor(slug)

  return (
    <div className="practice">
      <div className="practice-bar">
        <span className="practice-count">
          {current + 1} of {list.length} {ahead ? 'to practise' : 'due'}
        </span>
        <span className="practice-count practice-count-quiet">
          {sheet().length} in your sheet
        </span>
        {card && (
          <span className="practice-recall" title="Predicted chance you still remember this">
            {Math.round(recallOf(card) * 100)}% recalled
          </span>
        )}
      </div>

      <ProblemWorkspace slug={slug} onChecked={() => setAsking(true)} />

      {notice && (
        <p className="pv-notice" role="status">
          {notice}
        </p>
      )}

      {asking && (
        <RatingDialog
          title="How did that go?"
          options={OPTIONS}
          onChoose={(rating) => void rate(rating)}
          onDismiss={() => void rate('hard')}
        />
      )}
    </div>
  )
}
