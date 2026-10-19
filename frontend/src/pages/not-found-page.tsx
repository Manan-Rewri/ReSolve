import { useState } from 'react'
import { Link } from 'react-router-dom'

import { TypeGarden } from '@/components/type-garden'

/**
 * 404. Same garden as the landing page — the brand's one idea, reused.
 * The status is the wordmark; everything else is one way out.
 */
export default function NotFoundPage() {
  const [ctaTop, setCtaTop] = useState<number | null>(null)
  const [ready, setReady] = useState(false)

  return (
    <main className="landing">
      <h1 className="sr-only">Page not found</h1>

      <div className="landing-garden">
        <TypeGarden
          className="absolute inset-0"
          word="405"
          correction="404"
          onReady={() => setReady(true)}
          onCtaOffset={setCtaTop}
        />
      </div>

      <div
        className={`landing-cta reveal ${ready ? 'is-on' : ''}`}
        style={ctaTop != null ? { top: ctaTop } : undefined}
      >
        <span className="landing-rule" aria-hidden="true" />
        <p className="landing-lede">That page does not exist.</p>

        <div className="landing-actions">
          <Link className="button button-light" to="/">
            Go home
          </Link>
        </div>
      </div>
    </main>
  )
}
