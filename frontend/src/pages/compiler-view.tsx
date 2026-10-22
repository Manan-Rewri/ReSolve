import { lazy, Suspense, useState } from 'react'

import { runCxx } from '@/lib/compiler'
import type { CompileResponse } from '@/lib/compiler'

// Monaco is several megabytes. Loading it on demand keeps it out of the
// initial bundle for every page except the compiler.
const CodeEditor = lazy(() =>
  import('@/components/code-editor').then((m) => ({ default: m.CodeEditor })),
)

const STARTER = `#include <iostream>
#include <vector>

int main() {
    int n;
    std::cin >> n;

    std::vector<int> a(n);
    for (int &x : a) std::cin >> x;

    int sum = 0;
    for (int x : a) sum += x;

    std::cout << sum << std::endl;
    return 0;
}
`

/** Judge0 status 3 is Accepted. */
const ACCEPTED = 3

export default function CompilerView() {
  const [code, setCode] = useState(STARTER)
  const [stdin, setStdin] = useState('4\n3 1 4 1')
  const [result, setResult] = useState<CompileResponse | null>(null)
  const [failure, setFailure] = useState('')
  const [running, setRunning] = useState(false)

  async function run() {
    setRunning(true)
    setFailure('')
    setResult(null)

    const outcome = await runCxx(code, stdin)

    if (outcome.kind === 'failed') setFailure(outcome.message)
    else setResult(outcome.result)

    setRunning(false)
  }

  const accepted = result?.status === ACCEPTED
  const output = result
    ? (result.stdout || result.stderr || result.compile_output || '').trimEnd()
    : ''
  // A compile error is the compiler's complaint, not the program's output.
  const compileFailed = result?.status === 6

  return (
    <div className="compiler">
      {/* Left: the editor. */}
      <section className="compiler-pane">
        <div className="compiler-pane-head">
          <span className="compiler-label">C++</span>
          <div className="compiler-head-actions">
            <button
              className="button button-small button-ghost"
              type="button"
              onClick={() => setCode(STARTER)}
            >
              Reset
            </button>
            <button
              className="button button-small button-light"
              type="button"
              onClick={() => void run()}
              disabled={running}
            >
              {running ? 'Running' : 'Run'}
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

      {/* Right: input over output. */}
      <div className="compiler-side">
        <section className="compiler-pane">
          <div className="compiler-pane-head">
            <span className="compiler-label">Standard input</span>
          </div>
          <textarea
            className="compiler-fill"
            value={stdin}
            onChange={(event) => setStdin(event.target.value)}
            spellCheck={false}
            aria-label="Standard input"
          />
        </section>

        <section className="compiler-pane">
          <div className="compiler-pane-head">
            <span className="compiler-label">Output</span>
            {result && (
              <span className={accepted ? 'compiler-status is-ok' : 'compiler-status is-bad'}>
                {result.status_text}
              </span>
            )}
          </div>

          <div className="compiler-fill compiler-scroll">
            {failure ? (
              <p className="compiler-error">{failure}</p>
            ) : output ? (
              <pre className={compileFailed ? 'compiler-output is-error' : 'compiler-output'}>
                {output}
              </pre>
            ) : (
              <p className="compiler-empty">{running ? 'Running...' : 'Nothing yet.'}</p>
            )}

            {result && (result.time || result.memory_kb) && (
              <p className="compiler-meta">
                {result.time ? `${result.time}s` : ''}
                {result.time && result.memory_kb ? ' · ' : ''}
                {result.memory_kb ? `${result.memory_kb} KB` : ''}
              </p>
            )}
          </div>
        </section>
      </div>
    </div>
  )
}
