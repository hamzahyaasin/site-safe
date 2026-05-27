import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'

export default function LoginPage() {
  const { login, isAuthenticated } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (isAuthenticated) navigate('/', { replace: true })
  }, [isAuthenticated, navigate])

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(email, password)
      navigate('/', { replace: true })
    } catch {
      setError('Invalid email or password. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      {/* Left hero panel */}
      <div className="login-hero">
        <div className="login-hero__content">
          <div className="login-hero__logo">⛑️</div>
          <h1 className="login-hero__title">Site-Safe</h1>
          <p className="login-hero__subtitle">
            Real-time construction site safety monitoring powered by AI computer vision and IoT smart vests.
          </p>
          <ul className="login-hero__features">
            <li className="login-hero__feature">
              <span className="login-hero__feature-icon">📷</span>
              AI-powered PPE detection via live camera feeds
            </li>
            <li className="login-hero__feature">
              <span className="login-hero__feature-icon">🦺</span>
              IoT smart vest alerts — falls, gas, heat, SOS
            </li>
            <li className="login-hero__feature">
              <span className="login-hero__feature-icon">📊</span>
              Live dashboard with real-time incident tracking
            </li>
            <li className="login-hero__feature">
              <span className="login-hero__feature-icon">👷</span>
              Full worker registry with zone management
            </li>
          </ul>
        </div>
      </div>

      {/* Right form panel */}
      <div className="login-form-side">
        <div className="login-card">
          <p className="login-card__eyebrow">Safety Dashboard</p>
          <h2 className="login-card__title">Welcome back</h2>
          <p className="login-card__subtitle">Sign in with your administrator credentials to continue.</p>

          <form className="login-form" onSubmit={handleSubmit}>
            <label className="field">
              <span className="field__label">Email address</span>
              <input
                className="field__input"
                type="email"
                autoComplete="username"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </label>

            <label className="field">
              <span className="field__label">Password</span>
              <input
                className="field__input"
                type="password"
                autoComplete="current-password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </label>

            {error ? (
              <p className="form-error">
                <span>⚠</span>
                {error}
              </p>
            ) : null}

            <button type="submit" className="btn btn--primary btn--block" disabled={loading}>
              {loading ? 'Signing in…' : 'Sign In'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
