import { useEffect, useMemo, useState } from 'react'

import { filterProblems, listProblems } from '@/lib/problems'
import type { ProblemSummary } from '@/lib/problems'

/**
 * Learn: the problem catalogue. Search filters the list as you type, and
 * clicking a problem opens it beside the compiler.
 */
export default function LearnView({ onOpen }: { onOpen: (slug: string) => void }) {
  const [problems, setProblems] = useState<ProblemSummary[]>([])
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let live = true
    void listProblems().then((outcome) => {
      if (!live) return
      if (outcome.kind === 'ok') setProblems(outcome.value)
      else setError(outcome.message)
      setLoading(false)
    })
    return () => {
      live = false
    }
  }, [])

  const matches = useMemo(() => filterProblems(problems, query), [problems, query])

  return (
    <div className="lc">
      <div className="lc-search">
        <input
          className="lc-search-input"
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search problems, tags, or difficulty"
          aria-label="Search problems"
          autoFocus
        />
        <span className="lc-search-count">
          {loading ? '...' : `${matches.length} of ${problems.length}`}
        </span>
      </div>

      {error ? (
        <p className="lc-empty">{error}</p>
      ) : loading ? (
        <p className="lc-empty">Loading the catalogue...</p>
      ) : matches.length === 0 ? (
        <p className="lc-empty">Nothing matches that.</p>
      ) : (
        <ul className="lc-list">
          {matches.map((problem) => (
            <li key={problem.slug}>
              <button className="lc-row" type="button" onClick={() => onOpen(problem.slug)}>
                <span className="lc-row-title">{problem.title}</span>
                <span className="lc-row-tags">{problem.tags.slice(0, 3).join(' · ')}</span>
                <span className="lc-row-diff" data-difficulty={problem.difficulty}>
                  {problem.difficulty}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
