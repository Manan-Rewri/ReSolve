import { lazy, Suspense, useEffect, useState } from 'react'

import { Markdown } from '@/components/markdown'
import { getCases, getProblem, judge } from '@/lib/problems'
import type { CaseResult, Problem, TestCase } from '@/lib/problems'

const CodeEditor = lazy(() =>
  import('@/components/code-editor').then((m) => ({ default: m.CodeEditor })),
)

type ProblemWorkspaceProps = {
  slug: string
  /** Called after a check, with the result. `null` when the check failed. */
  onChecked?: (result: CaseResult[] | null, passed: boolean) => void
  /** Buttons shown in the editor's head, next to Reset and Check. */
  actions?: React.ReactNode
  /** Shown at the left of the statement's head. */
  onBack?: () => void
}

/**
 * A problem, read and solved side by side: the statement on the left, the
 * editor and the test cases on the right.
 *
 * The editor holds only the function. It is seeded with the signature and an
 * empty body:
 *
 *     vector<int> twoSum(vector<int>& nums, int target) {
 *
 *     }
 *
 * The includes, the printers and the `main` that drives every case are stored
 * with the problem and spliced around the function on the server, so there is
 * no `main` to write and no include to remember.
 *
 * Both the Learn page and the Practice page use this. The difference between
 * them is what happens after a check, and that belongs to the page.
 */
export function ProblemWorkspace({ slug, onChecked, actions, onBack }: ProblemWorkspaceProps) {
  const [problem, setProblem] = useState<Problem | null>(null)
  const [cases, setCases] = useState<TestCase[]>([])
  const [code, setCode] = useState('')
  const [loadError, setLoadError] = useState('')

  const [results, setResults] = useState<CaseResult[] | null>(null)
  const [checking, setChecking] = useState(false)
  const [checkError, setCheckError] = useState('')
  const [compileOutput, setCompileOutput] = useState('')

  useEffect(() => {
    let live = true

    void getProblem(slug).then((outcome) => {
      if (!live) return
      if (outcome.kind === 'failed') {
        setLoadError(outcome.message)
        return
      }
      setProblem(outcome.value)
      setCode(outcome.value.editor_start)
    })

    void getCases(slug).then((outcome) => {
      if (!live) return
      if (outcome.kind === 'ok') setCases(outcome.value)
    })

    return () => {
      live = false
    }
  }, [slug])

  async function check() {
    if (!problem) return

    setChecking(true)
    setCheckError('')
    setCompileOutput('')

    const outcome = await judge(problem.slug, code)

    if (outcome.kind === 'failed') {
      setCheckError(outcome.message)
      setResults(null)
      onChecked?.(null, false)
    } else {
      setResults(outcome.value.cases)
      setCompileOutput(outcome.value.compile_output)
      onChecked?.(outcome.value.cases, outcome.value.passed === outcome.value.total)
    }

    setChecking(false)
  }

  if (loadError) {
    return (
      <div className="pv">
        <section className="pv-pane pv-statement">
          <div className="compiler-pane-head">
            <span className="compiler-label">Problem</span>
          </div>
          <div className="pv-scroll">
            <p className="compiler-error">{loadError}</p>
          </div>
        </section>
      </div>
    )
  }

  if (!problem) {
    return (
      <div className="pv">
        <section className="pv-pane pv-statement">
          <div className="compiler-pane-head">
            <span className="compiler-label">Problem</span>
          </div>
          <div className="pv-scroll">
            <p className="compiler-empty">Loading the problem...</p>
          </div>
        </section>
      </div>
    )
  }

  const passed = results?.filter((c) => c.passed).length ?? 0
  const total = results?.length ?? cases.length

  return (
    <div className="pv">
      <section className="pv-pane pv-statement">
        <div className="compiler-pane-head">
          {onBack && (
            <button className="pv-back" type="button" onClick={onBack}>
              <span aria-hidden="true">&larr;</span> Back
            </button>
          )}
          <span className="pv-title">{problem.title}</span>
          <span className="lc-row-diff" data-difficulty={problem.difficulty}>
            {problem.difficulty}
          </span>
        </div>

        <div className="pv-scroll">
          <div className="pv-meta">{problem.tags.join(' · ')}</div>
          <Markdown source={problem.statement} />

          {problem.examples.length > 0 && (
            <section className="pv-block">
              <h2 className="pv-block-title">Examples</h2>
              {problem.examples.map((example, index) => (
                <div key={index} className="pv-example">
                  <p className="pv-example-io">
                    <span className="pv-example-label">Input</span>
                    <code>{example.input}</code>
                  </p>
                  <p className="pv-example-io">
                    <span className="pv-example-label">Output</span>
                    <code>{example.output}</code>
                  </p>
                </div>
              ))}
            </section>
          )}

          {problem.constraints.length > 0 && (
            <section className="pv-block">
              <h2 className="pv-block-title">Constraints</h2>
              <ul className="pv-constraints">
                {problem.constraints.map((constraint, index) => (
                  <li key={index}>{constraint}</li>
                ))}
              </ul>
            </section>
          )}
        </div>
      </section>

      <div className="pv-side">
        <section className="pv-pane">
          <div className="compiler-pane-head">
            <span className="compiler-label">C++</span>
            <div className="compiler-head-actions">
              <button
                className="button button-small button-ghost"
                type="button"
                onClick={() => setCode(problem.editor_start)}
              >
                Reset
              </button>
              {actions}
              <button
                className="button button-small button-light"
                type="button"
                onClick={() => void check()}
                disabled={checking}
              >
                {checking ? 'Checking' : 'Check'}
              </button>
            </div>
          </div>

          <div className="compiler-pane-body">
            <Suspense
              fallback={<div className="compiler-pane-body compiler-loading">Loading editor...</div>}
            >
              <CodeEditor value={code} onChange={setCode} />
            </Suspense>
          </div>
        </section>

        <section className="pv-pane">
          <div className="compiler-pane-head">
            <span className="compiler-label">Test cases</span>
            {results && (
              <span
                className={
                  passed === total ? 'compiler-status is-ok' : 'compiler-status is-bad'
                }
              >
                {passed === total ? `All ${total} passed` : `${passed} of ${total} passed`}
              </span>
            )}
          </div>

          <div className="compiler-fill compiler-scroll">
            {compileOutput ? (
              <pre className="compiler-output is-error">{compileOutput}</pre>
            ) : checkError ? (
              <p className="compiler-error">{checkError}</p>
            ) : results ? (
              <CaseTable cases={results} />
            ) : (
              <p className="compiler-empty">
                {cases.length} test cases ready. Write the function and press Check.
              </p>
            )}
          </div>
        </section>
      </div>
    </div>
  )
}

/**
 * Every case, with the expected output and what the submission produced.
 * Nothing is hidden: the user can see exactly what they are measured against.
 */
function CaseTable({ cases }: { cases: CaseResult[] }) {
  return (
    <table className="case-table">
      <thead>
        <tr>
          <th className="case-col-n">#</th>
          <th>Input</th>
          <th>Expected</th>
          <th>Got</th>
        </tr>
      </thead>
      <tbody>
        {cases.map((problemCase, index) => (
          <tr key={index} className={problemCase.passed ? undefined : 'case-row-bad'}>
            <td className="case-col-n">{index + 1}</td>
            <td className="case-col-in">{problemCase.args.join('  ')}</td>
            <td className="case-col-out">{problemCase.expected}</td>
            <td
              className={
                problemCase.passed ? 'case-col-out case-col-ok' : 'case-col-out case-col-bad'
              }
            >
              {problemCase.actual || <span className="case-none">not reached</span>}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
