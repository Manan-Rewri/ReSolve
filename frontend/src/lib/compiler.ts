import { supabase } from '@/lib/supabase'

export type CompileResponse = {
  stdout: string
  stderr: string
  compile_output: string
  status: number
  status_text: string
  time: string | null
  memory_kb: number | null
}

export type CompileOutcome =
  | { kind: 'ok'; result: CompileResponse }
  | { kind: 'failed'; message: string }

/**
 * Posts to our own API rather than Judge0 directly, so no third-party key is
 * ever exposed in the browser bundle.
 */
export async function runCxx(sourceCode: string, stdin: string): Promise<CompileOutcome> {
  try {
    const { data: sessionData } = await supabase.auth.getSession()
    const token = sessionData.session?.access_token

    const response = await fetch('/api/v1/compile', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ source_code: sourceCode, stdin, language_id: 54 }),
    })

    if (!response.ok) {
      const detail = await response.json().catch(() => null)
      const message =
        typeof detail?.detail === 'string'
          ? detail.detail
          : 'The compiler service is unavailable.'
      return { kind: 'failed', message }
    }

    return { kind: 'ok', result: (await response.json()) as CompileResponse }
  } catch {
    return { kind: 'failed', message: 'Could not reach the server. Check your connection.' }
  }
}
