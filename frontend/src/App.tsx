import { BrowserRouter, Route, Routes } from 'react-router-dom'

import { RedirectIfAuthed, RequireAuth } from '@/components/guards'
import { AuthProvider } from '@/lib/auth-provider'
import HomePage from '@/pages/home-page'
import LandingPage from '@/pages/landing-page'
import LoginPage from '@/pages/login-page'
import NotFoundPage from '@/pages/not-found-page'
import PublicProfilePage from '@/pages/public-profile-page'
import RegisterPage from '@/pages/register-page'

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Signed-in users skip the landing page entirely. */}
          <Route
            path="/"
            element={
              <RedirectIfAuthed>
                <LandingPage />
              </RedirectIfAuthed>
            }
          />
          <Route
            path="/register"
            element={
              <RedirectIfAuthed>
                <RegisterPage />
              </RedirectIfAuthed>
            }
          />
          <Route
            path="/login"
            element={
              <RedirectIfAuthed>
                <LoginPage />
              </RedirectIfAuthed>
            }
          />
          <Route
            path="/home"
            element={
              <RequireAuth>
                <HomePage />
              </RequireAuth>
            }
          />
          <Route path="/p/:token" element={<PublicProfilePage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
