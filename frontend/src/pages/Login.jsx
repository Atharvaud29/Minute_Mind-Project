import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const navigate = useNavigate()
  return (
    <div className="min-h-[70vh] flex items-center justify-center">
      <div className="card p-6 w-full max-w-md">
        <div className="text-center mb-4">
          <div className="inline-flex items-center justify-center w-10 h-10 rounded-full bg-gradient-to-br from-brand-500 to-grape-500 text-white font-bold mb-2">M</div>
          <h1 className="text-xl font-semibold">Welcome to MoM</h1>
          <p className="text-sm text-gray-600">Sign in to continue</p>
        </div>
        <div className="space-y-3">
          <input value={email} onChange={e=>setEmail(e.target.value)} placeholder="Email" className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-grape-400" />
          <input type="password" value={password} onChange={e=>setPassword(e.target.value)} placeholder="Password" className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-grape-400" />
          <button
            className="w-full py-2 rounded bg-gradient-to-r from-brand-600 to-accent-500 text-white font-medium hover:opacity-95"
            onClick={() => { sessionStorage.setItem('auth','true'); navigate('/') }}
          >
            Sign In
          </button>
        </div>
      </div>
    </div>
  )
}


