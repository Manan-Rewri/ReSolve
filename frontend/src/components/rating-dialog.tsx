import type { Rating } from '@/lib/practice-store'

type RatingDialogProps<T extends string = Rating> = {
  title: string
  /** The lines under the title, one per rating. */
  options: { rating: T; label: string; hint: string }[]
  onChoose: (rating: T) => void
  onDismiss: () => void
}

/**
 * The rating popup.
 *
 * It asks how the attempt felt, which is a different axis from the problem's
 * Easy/Medium/Hard tag — and the reason the practice sheet can be scheduled at
 * all. Every option carries a sentence saying what it means, so the choice is
 * not guesswork.
 *
 * Generic over the rating so the Learn page can offer "very easy" — which is a
 * decision not to add the problem to the sheet, not a schedule — while the
 * Practice page offers only the three that are.
 */
export function RatingDialog<T extends string = Rating>({
  title,
  options,
  onChoose,
  onDismiss,
}: RatingDialogProps<T>) {
  return (
    <div className="rating-backdrop" role="presentation" onClick={onDismiss}>
      <div
        className="rating-panel"
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onClick={(event) => event.stopPropagation()}
      >
        <h2 className="rating-title">{title}</h2>

        <ul className="rating-options">
          {options.map((option) => (
            <li key={option.rating}>
              <button
                className="rating-option"
                type="button"
                onClick={() => onChoose(option.rating)}
              >
                <span className="rating-option-label">{option.label}</span>
                <span className="rating-option-hint">{option.hint}</span>
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
