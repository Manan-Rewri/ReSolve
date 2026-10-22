import { useState } from 'react'
import { Link } from 'react-router-dom'

import { TypeGarden } from '@/components/type-garden'

/**
 * Landing page.
 *
 * Full-bleed Type Garden: the wordmark grows itself on a black canvas that
 * fills the viewport. The intro ends with the final letter withering and
 * growing back — forget, then revisit — which is the product in one gesture.
 * The calls to action sit beneath the word, anchored each frame to wherever
 * the garden reports the baseline.
 */
export default function LandingPage() {
  const [ctaTop, setCtaTop] = useState<number | null>(null)
  const [ready, setReady] = useState(false)

  return (
    <main className="landing">
      <h1 className="sr-only">ReSolve</h1>

      <div className="landing-garden">
        <TypeGarden
          className="absolute inset-0"
          word="ReSolvx"
          correction="ReSolve"
          onReady={() => setReady(true)}
          onCtaOffset={setCtaTop}
        />
      </div>

      <div
        className={`landing-cta reveal ${ready ? 'is-on' : ''}`}
        style={ctaTop != null ? { top: ctaTop } : undefined}
      >
        <span className="landing-rule" aria-hidden="true" />
        <p className="landing-lede">Problems you&rsquo;ve solved come back before you forget them.</p>

        <div className="landing-actions">
          <Link className="button button-light" to="/register">
            Create your account
          </Link>
          <Link className="button button-glass" to="/login">
            I already have an account
          </Link>
        </div>
      </div>
    </main>
  )
}
