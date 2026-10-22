import { useCallback, useEffect, useMemo, useState } from 'react'

import { listProblems, listSheets, matchesQuery } from '@/lib/problems'
import type { ProblemSummary, Sheet } from '@/lib/problems'
import { useSolved } from '@/lib/practice-store'

type DoneFilter = 'all' | 'done' | 'todo'
type DifficultyFilter = 'all' | 'Easy' | 'Medium' | 'Hard'

const DIFFICULTIES: { id: DifficultyFilter; label: string }[] = [
  { id: 'all', label: 'All' },
  { id: 'Easy', label: 'Easy' },
  { id: 'Medium', label: 'Medium' },
  { id: 'Hard', label: 'Hard' },
]

const DONE_FILTERS: { id: DoneFilter; label: string }[] = [
  { id: 'all', label: 'All' },
  { id: 'done', label: 'Done' },
  { id: 'todo', label: 'Not done' },
]

/**
 * Learn: the problem catalogue, grouped into sheets.
 *
 * The sheets first, each with how far through it you are. Open one and you get
 * its problems **in order**, numbered, because a sheet is a course and a course
 * has a sequence.
 *
 * The open sheet lives in the URL, so the back button closes it.
 */
export default function LearnView({ onOpen }: { onOpen: (slug: string) => void }) {
  const [sheets, setSheets] = useState<Sheet[]>([])
  const [problems, setProblems] = useState<ProblemSummary[]>([])
  const [done, setDone] = useState<DoneFilter>('all')
  const [difficulty, setDifficulty] = useState<DifficultyFilter>('all')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const solved = useSolved()

  // The open sheet and the search both live in the URL, so a search is a link
  // worth sending and the back button closes the sheet.
  const [open, setOpen] = useState<string | null>(
    () => new URLSearchParams(window.location.search).get('sheet'),
  )
  const [query, setQuery] = useState(
    () => new URLSearchParams(window.location.search).get('q') ?? '',
  )

  useEffect(() => {
    const sync = () => {
      const params = new URLSearchParams(window.location.search)
      setOpen(params.get('sheet'))
      setQuery(params.get('q') ?? '')
    }
    window.addEventListener('popstate', sync)
    return () => window.removeEventListener('popstate', sync)
  }, [])

  function showSheet(id: string | null) {
    const params = new URLSearchParams(window.location.search)
    if (id) params.set('sheet', id)
    else params.delete('sheet')
    window.history.pushState({}, '', `?${params.toString()}`)
    setOpen(id)
  }

  function search(text: string) {
    setQuery(text)
    // replaceState, not pushState: typing should not fill the back history.
    const params = new URLSearchParams(window.location.search)
    if (text) params.set('q', text)
    else params.delete('q')
    window.history.replaceState({}, '', `?${params.toString()}`)
  }

  useEffect(() => {
    let live = true
    void listSheets().then((outcome) => {
      if (!live) return
      if (outcome.kind === 'ok') setSheets(outcome.value)
      else setError(outcome.message)
    })
    void listProblems().then((outcome) => {
      if (!live) return
      if (outcome.kind === 'ok') setProblems(outcome.value)
      setLoading(false)
    })
    return () => {
      live = false
    }
  }, [])

  const bySlug = useMemo(
    () => new Map(problems.map((problem) => [problem.slug, problem])),
    [problems],
  )

  const sheet = open ? sheets.find((s) => s.id === open) : undefined

  const sheetDone = sheet ? sheet.problems.filter((slug) => solved.has(slug)).length : 0
  const sheetPercent = sheet && sheet.total ? Math.round((sheetDone / sheet.total) * 100) : 0
  const nextProblem = sheet
    ? sheet.problems
        .map((slug) => bySlug.get(slug))
        .find(
          (problem): problem is ProblemSummary =>
            problem !== undefined && !solved.has(problem.slug),
        )
    : undefined

  /**
   * Does this problem match what the user typed?
   *
   * Used twice: to narrow the sheets down to the ones that contain the
   * question, and to narrow a sheet's questions down to the matching ones.
   */
  const matches = useCallback(
    (problem: ProblemSummary | undefined) =>
      Boolean(problem) && matchesQuery(problem as ProblemSummary, query),
    [query],
  )

  // The sheets that contain a question matching the search. Searching "two
  // sum" shows the sheet that has Two Sum, not every sheet.
  const visibleSheets = useMemo(
    () => sheets.filter((item) => item.problems.some((slug) => matches(bySlug.get(slug)))),
    [sheets, bySlug, matches],
  )

  // The problems of the open sheet, in order, after the search and the filters.
  const rows = useMemo(() => {
    if (!sheet) return []
    const list = sheet.problems
      .map((slug) => bySlug.get(slug))
      .filter((problem): problem is ProblemSummary => Boolean(problem))
      .filter(matches)

    return list.filter((problem) => {
      if (difficulty !== 'all' && problem.difficulty !== difficulty) return false
      if (done === 'done' && !solved.has(problem.slug)) return false
      if (done === 'todo' && solved.has(problem.slug)) return false
      return true
    })
  }, [sheet, bySlug, matches, done, difficulty, solved])

  if (loading) {
    return <p className="app-placeholder">Loading the catalogue...</p>
  }

  // The sheets.
  if (!sheet) {
    return (
      <div className="lc">
        <div className="lc-search">
          <input
            className="lc-search-input"
            type="search"
            value={query}
            onChange={(event) => search(event.target.value)}
            placeholder="Search problems, tags, or difficulty"
            aria-label="Search problems"
          />
          <span className="lc-search-count">
            {visibleSheets.length} sheet{visibleSheets.length === 1 ? '' : 's'}
          </span>
        </div>

        {error ? (
          <p className="lc-empty">{error}</p>
        ) : visibleSheets.length === 0 ? (
          <p className="lc-empty">Nothing matches that.</p>
        ) : (
          <ul className="sheet-list">
            {visibleSheets.map((item) => {
              const doneCount = item.problems.filter((slug) => solved.has(slug)).length
              const percent = item.total ? Math.round((doneCount / item.total) * 100) : 0
              return (
                <li key={item.id}>
                  <button className="sheet-row" type="button" onClick={() => showSheet(item.id)}>
                    <span className="sheet-row-head">
                      <span className="sheet-row-name">{item.name}</span>
                      <span className="sheet-row-count">
                        {doneCount} of {item.total}
                      </span>
                    </span>
                    <span className="sheet-row-blurb">{item.blurb}</span>
                    <span className="sheet-bar" aria-hidden="true">
                      <span className="sheet-bar-fill" style={{ width: `${percent}%` }} />
                    </span>
                  </button>
                </li>
              )
            })}
          </ul>
        )}
      </div>
    )
  }

  // The problems of one sheet, in order.
  return (
    <div className="lc">
      <div className="lc-search">
        <button className="lc-back" type="button" onClick={() => showSheet(null)}>
          <span aria-hidden="true">&larr;</span> Sheets
        </button>
        <span className="lc-sheet-name">{sheet.name}</span>
        <input
          className="lc-search-input"
          type="search"
          value={query}
          onChange={(event) => search(event.target.value)}
          placeholder="Search this sheet"
          aria-label="Search this sheet"
          autoFocus
        />
        <span className="lc-search-count">
          {rows.length} of {sheet.total}
        </span>
      </div>

      <div className="lc-sheet">
        <div className="lc-sheet-progress">
          <span className="sheet-bar" aria-hidden="true">
            <span className="sheet-bar-fill" style={{ width: `${sheetPercent}%` }} />
          </span>
          <span className="lc-sheet-meta">
            {sheetDone} of {sheet.total} done
          </span>
        </div>
        <button
          className="button button-light button-small"
          type="button"
          disabled={!nextProblem}
          onClick={() => nextProblem && onOpen(nextProblem.slug)}
        >
          {nextProblem ? 'Continue' : 'Sheet complete'}
        </button>
      </div>

      <div className="lc-filters">
        <div className="lc-filter-group" role="group" aria-label="Filter by status">
          {DONE_FILTERS.map((option) => (
            <button
              key={option.id}
              className={done === option.id ? 'lc-filter is-on' : 'lc-filter'}
              type="button"
              onClick={() => setDone(option.id)}
            >
              {option.label}
            </button>
          ))}
        </div>

        <div className="lc-filter-group" role="group" aria-label="Filter by difficulty">
          {DIFFICULTIES.map((option) => (
            <button
              key={option.id}
              className={difficulty === option.id ? 'lc-filter is-on' : 'lc-filter'}
              type="button"
              onClick={() => setDifficulty(option.id)}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      {rows.length === 0 ? (
        <p className="lc-empty">Nothing matches that.</p>
      ) : (
        <ol className="lc-list lc-list-ordered">
          {rows.map((problem) => (
            <li key={problem.slug}>
              <button className="lc-row" type="button" onClick={() => onOpen(problem.slug)}>
                <span className="lc-row-n">
                  {sheet.problems.indexOf(problem.slug) + 1}
                </span>
                <span className="lc-row-name">
                  <span className="lc-row-title">{problem.title}</span>
                  {solved.has(problem.slug) && (
                    <span className="lc-row-done" title="Solved" aria-label="Solved">
                      ✓
                    </span>
                  )}
                </span>
                <span className="lc-row-tags">{problem.tags.slice(0, 3).join(' · ')}</span>
                <span className="lc-row-diff" data-difficulty={problem.difficulty}>
                  {problem.difficulty}
                </span>
              </button>
            </li>
          ))}
        </ol>
      )}
    </div>
  )
}
