import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext.jsx'
import Button from '../ui/Button.jsx'
import Alert from '../ui/Alert.jsx'
import Input from '../ui/Input.jsx'
import { IconShield } from '../ui/icons.jsx'

export default function LoginPage() {
  const { login, isAuthenticated } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [showPassword, setShowPassword] = useState(false)

  useEffect(() => {
    if (isAuthenticated) navigate('/', { replace: true })
  }, [isAuthenticated, navigate])

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(email.trim(), password)
      navigate('/', { replace: true })
    } catch (err) {
      setError(
        err.response
          ? err.response.status === 401 || err.response.status === 400
            ? 'Invalid email or password. Please try again.'
            : 'The server could not sign you in right now. Please try again shortly.'
          : 'Cannot reach the Site-Safe server. Check your connection and that the backend is running.',
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-grid-bg flex min-h-screen items-center justify-center p-6">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-amber-400 to-amber-600 text-zinc-950 shadow-lg shadow-amber-900/30">
            <IconShield className="h-6 w-6" strokeWidth={2.25} />
          </div>
          <h1 className="text-2xl font-semibold tracking-tight text-zinc-50">Site-Safe</h1>
          <p className="mt-1 text-sm text-zinc-400">Construction Safety Command</p>
        </div>

        <div className="rounded-xl border border-zinc-800 bg-[#151821]/95 p-6 shadow-2xl shadow-black/40 backdrop-blur sm:p-7">
          <h2 className="text-base font-semibold text-zinc-50">Sign in</h2>
          <p className="mt-1 text-sm text-zinc-400">Enter your credentials to access the dashboard.</p>

          <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
            <Input
              label="Email"
              type="email"
              autoComplete="username"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
            <div className="relative">
              <Input
                label="Password"
                type={showPassword ? 'text' : 'password'}
                autoComplete="current-password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                inputClassName="pr-16"
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword((v) => !v)}
                className="absolute bottom-1.5 right-1.5 rounded px-2 py-1 text-[11px] font-medium text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200 focus-visible:outline focus-visible:outline-2 focus-visible:outline-amber-500"
                aria-label={showPassword ? 'Hide password' : 'Show password'}
                aria-pressed={showPassword}
              >
                {showPassword ? 'Hide' : 'Show'}
              </button>
            </div>

            {error ? <Alert>{error}</Alert> : null}

            <Button type="submit" variant="primary" size="lg" className="w-full" loading={loading}>
              {loading ? 'Signing in…' : 'Sign in'}
            </Button>
          </form>
        </div>

        <p className="mt-6 text-center text-xs text-zinc-500">
          Authorized personnel only · All activity is logged
        </p>
      </div>
    </div>
  )
}
