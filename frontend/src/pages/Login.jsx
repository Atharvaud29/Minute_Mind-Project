import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const navigate = useNavigate()

  // Optional: Redirect if already logged in
  useEffect(() => {
    if (sessionStorage.getItem('auth') === 'true' || localStorage.getItem('auth') === 'true') {
      navigate('/')
    }
  }, [navigate])

  const handleSubmit = (e) => {
    if (e && typeof e.preventDefault === 'function') {
      e.preventDefault()
    }
    // TODO: Add real authentication here
    sessionStorage.setItem('auth', 'true')
    localStorage.setItem('auth', 'true')
    try {
      navigate('/', { replace: true })
      // Fallback: ensure navigation even if client-side routing fails
      setTimeout(() => {
        if (!window.location.pathname || window.location.pathname === '/login') {
          window.location.assign('/')
        }
      }, 50)
    } catch (_) {
      window.location.assign('/')
    }
  }

  return (
    <div className="min-h-[70vh] flex items-center justify-center">
      <div className="card p-6 w-full max-w-md">
        <div className="text-center mb-4">
          <div className="inline-flex items-center justify-center w-10 h-10 rounded-full bg-gradient-to-br from-brand-500 to-grape-500 text-white font-bold mb-2">M</div>
          <h1 className="text-xl font-semibold">Welcome to MoM</h1>
          <p className="text-sm text-gray-600">Sign in to continue</p>
        </div>
        <form className="space-y-3" onSubmit={handleSubmit} noValidate>
          <input value={email} onChange={e=>setEmail(e.target.value)} placeholder="Email" className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-grape-400" />
          <input type="password" value={password} onChange={e=>setPassword(e.target.value)} placeholder="Password" className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-grape-400" />
          <button type="submit" onClick={handleSubmit} className="w-full py-2 rounded bg-gradient-to-r from-brand-600 to-accent-500 text-white font-medium hover:opacity-95">
            Sign In
          </button>
        </form>
      </div>
    </div>
  )
}


