import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import App from '@/App'
import { supabaseConfigProblem } from '@/lib/supabase'
import './index.css'

const host = document.getElementById('root')
if (!host) throw new Error('Missing #root element in index.html')

const root = createRoot(host)

const problem = supabaseConfigProblem()

if (problem) {
  // Better a readable explanation than a white screen mid-demo.
  root.render(
    <main className="auth">
      <div className="auth-shell">
        <h1 className="auth-question">Supabase is not configured</h1>
        <p className="auth-hint">{problem}</p>
        <div className="auth-slot" />
        <div className="auth-notice">
          Copy <code>frontend/.env.example</code> to <code>frontend/.env</code>, fill it in
          from Supabase &rarr; Project Settings &rarr; API, then restart the dev server.
        </div>
      </div>
    </main>,
  )
} else {
  root.render(
    <StrictMode>
      <App />
    </StrictMode>,
  )
}
