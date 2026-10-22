import { useState } from 'react'

import { ProblemWorkspace } from '@/components/problem-workspace'
import { RatingDialog } from '@/components/rating-dialog'
import { applyRating, describeInterval, markSolved, markVeryEasy } from '@/lib/practice-store'
import type { Rating } from '@/lib/practice-store'

/**
 * The four answers to "how did that go?".
 *
 * "Very easy" is not a schedule, it is a decision: this problem does not need
 * to be practised again, so it is not in the practice sheet. The other three
 * put it there and set where it starts on the memory curve.
 */
const OPTIONS: { rating: Rating | 'veryEasy'; label: string; hint: string }[] = [
  {
    rating: 'veryEasy',
    label: 'Very easy',
    hint: 'No need to be in your practice sheet.',
  },
  {
    rating: 'medium',
    label: 'Medium',
    hint: 'You got it. The interval doubles.',
  },
  {
    rating: 'hard',
    label: 'Hard',
    hint: 'You barely got it. The interval halves.',
  },
  {
    rating: 'extreme',
    label: 'Extreme',
    hint: 'You used the solution. Back in ten minutes.',
  },
]

/** The same, without "very easy" — you did not get it, so you do need it. */
const OPTIONS_FAILED: { rating: Rating; label: string; hint: string }[] = OPTIONS.filter(
  (option) => option.rating !== 'veryEasy',
) as { rating: Rating; label: string; hint: string }[]

/**
 * A problem from the Learn page.
 *
 * When you have attempted a problem, the user is asked how it went. The answer
 * decides whether the problem joins the practice sheet.
 *
 * The question is asked **whether or not** the solution passed. A problem you
 * attempted and got wrong is exactly the one you need to practise, so it must
 * not be silently dropped — that was the bug where a session of work left the
 * practice sheet empty.
 */
export default function ProblemView({
  slug,
  onBack,
}: {
  slug: string
  onBack: () => void
}) {
  const [asking, setAsking] = useState(false)
  const [passed, setPassed] = useState(false)
  const [notice, setNotice] = useState('')

  async function rate(rating: Rating | 'veryEasy') {
    setAsking(false)
    setNotice('')

    // Only a problem that was got fully right counts as solved.
    if (passed) await markSolved(slug)

    // "Very easy" means it does not need practising again. If it was already
    // in rotation, the decision takes it out.
    if (rating === 'veryEasy') {
      const ok = await markVeryEasy(slug)
      setNotice(
        ok
          ? 'Not going to come back. It is out of your practice sheet.'
          : 'The browser refused to save that.',
      )
      return
    }

    const outcome = await applyRating(slug, rating)

    // A rating that could not be saved must say so. Silence here is what made
    // a sheet look empty with no explanation.
    if (!outcome.ok) {
      setNotice(outcome.message)
      return
    }
    setNotice(`Saved. Back ${describeInterval(outcome.card.stability_days)}.`)
  }

  return (
    <>
      <ProblemWorkspace
        slug={slug}
        onBack={onBack}
        onChecked={(_results, allPassed) => {
          setPassed(allPassed)
          setAsking(true)
        }}
      />

      {notice && (
        <p className="pv-notice" role="status">
          {notice}
        </p>
      )}

      {asking &&
        (passed ? (
          <RatingDialog
            title="How did that go?"
            options={OPTIONS}
            onChoose={(rating) => void rate(rating)}
            onDismiss={() => setAsking(false)}
          />
        ) : (
          <RatingDialog
            title="Not quite. How was it?"
            options={OPTIONS_FAILED}
            onChoose={(rating) => void rate(rating)}
            onDismiss={() => setAsking(false)}
          />
        ))}
    </>
  )
}
