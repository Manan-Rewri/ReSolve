/**
 * The problem catalogue, over the API.
 *
 * The catalogue lives on the server in `backend/data/problems.json` and will
 * move into Postgres. The browser only ever sees what it needs to render.
 */

export type Difficulty = 'Easy' | 'Medium' | 'Hard'

export type ProblemSummary = {
  slug: string
  title: string
  difficulty: Difficulty
  tags: string[]
}

export type Example = {
  input: string
  output: string
}

export type Problem = {
  slug: string
  title: string
  difficulty: Difficulty
  tags: string[]
  statement: string
  examples: Example[]
  constraints: string[]
  signature: string
  /** What the editor starts as: the signature and an empty body. */
  editor_start: string
}

export type TestCase = {
  /** One entry per parameter. */
  args: string[]
  expected: string
}

export type CaseResult = {
  args: string[]
  expected: string
  actual: string
  passed: boolean
}

export type JudgeResponse = {
  slug: string
  passed: number
  total: number
  cases: CaseResult[]
  compile_output: string
  status_text: string
}

export type Outcome<T> = { kind: 'ok'; value: T } | { kind: 'failed'; message: string }

async function request<T>(path: string, init?: RequestInit): Promise<Outcome<T>> {
  try {
    const response = await fetch(path, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...init?.headers },
    })

    if (!response.ok) {
      const payload = await response.json().catch(() => null)
      const message =
        typeof payload?.detail === 'string' ? payload.detail : 'The server refused that.'
      return { kind: 'failed', message }
    }

    return { kind: 'ok', value: (await response.json()) as T }
  } catch {
    return { kind: 'failed', message: 'Could not reach the server. Check your connection.' }
  }
}

export function listProblems(): Promise<Outcome<ProblemSummary[]>> {
  return request<ProblemSummary[]>('/api/v1/problems')
}

export function getProblem(slug: string): Promise<Outcome<Problem>> {
  return request<Problem>(`/api/v1/problems/${slug}`)
}

export function getCases(slug: string): Promise<Outcome<TestCase[]>> {
  return request<{ slug: string; cases: TestCase[] }>(`/api/v1/problems/${slug}/cases`).then(
    (outcome) => (outcome.kind === 'ok' ? { kind: 'ok', value: outcome.value.cases } : outcome),
  )
}

export function judge(slug: string, code: string): Promise<Outcome<JudgeResponse>> {
  return request<JudgeResponse>('/api/v1/judge', {
    method: 'POST',
    body: JSON.stringify({ slug, code }),
  })
}

/**
 * Filter the list as the user types. Matches the title, the difficulty, the
 * tags and the first worked example, so "array" or "9" both find something.
 */
export function filterProblems(
  problems: ProblemSummary[],
  query: string,
): ProblemSummary[] {
  const needle = query.trim().toLowerCase()
  if (!needle) return problems

  return problems.filter((problem) =>
    [problem.title, problem.difficulty, ...problem.tags]
      .join(' ')
      .toLowerCase()
      .includes(needle),
  )
}
