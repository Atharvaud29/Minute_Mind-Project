import { Routes, Route, NavLink, Navigate, Outlet, useNavigate } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import PastMeetings from './pages/PastMeetings'
import NewMeeting from './pages/NewMeeting'
import Settings from './pages/Settings'
import Login from './pages/Login'
import Summary from './pages/Summary'
import TaskAssigned from './pages/TaskAssigned'
import ConflictDetection from './pages/ConflictDetection'

function ProtectedLayout() {
  const isAuthed = typeof window !== 'undefined' && (
    sessionStorage.getItem('auth') === 'true' || localStorage.getItem('auth') === 'true'
  )
  const navigate = useNavigate()
  if (!isAuthed) return <Navigate to="/login" replace />
  return (
    <div className="min-h-screen flex">
      <aside className="w-64 bg-gray-900 text-gray-100">
        <div className="p-4 text-xl font-semibold tracking-wide">
          <span className="inline-block w-2 h-2 bg-accent-500 rounded-full mr-2" />
          MoM ✨
        </div>
        <nav className="flex flex-col gap-1 p-2">
          <NavLink to="/" end className={({isActive}) => `px-3 py-2 rounded transition ${isActive ? 'bg-gray-800 text-white' : 'text-gray-300 hover:bg-gray-800 hover:text-white'}`}>🏠 Dashboard</NavLink>
          <NavLink to="/new" className={({isActive}) => `px-3 py-2 rounded transition ${isActive ? 'bg-gray-800 text-white' : 'text-gray-300 hover:bg-gray-800 hover:text-white'}`}>➕ New Meeting</NavLink>
          <NavLink to="/meetings" className={({isActive}) => `px-3 py-2 rounded transition ${isActive ? 'bg-gray-800 text-white' : 'text-gray-300 hover:bg-gray-800 hover:text-white'}`}>📚 Past Meetings</NavLink>
          <NavLink to="/summary" className={({isActive}) => `px-3 py-2 rounded transition ${isActive ? 'bg-gray-800 text-white' : 'text-gray-300 hover:bg-gray-800 hover:text-white'}`}>📝 Summary</NavLink>
          <NavLink to="/task-assigned" className={({isActive}) => `px-3 py-2 rounded transition ${isActive ? 'bg-gray-800 text-white' : 'text-gray-300 hover:bg-gray-800 hover:text-white'}`}>✅ Task Assigned</NavLink>
          <NavLink to="/conflict-detection" className={({isActive}) => `px-3 py-2 rounded transition ${isActive ? 'bg-gray-800 text-white' : 'text-gray-300 hover:bg-gray-800 hover:text-white'}`}>⚠️ Conflict Detection</NavLink>
          <NavLink to="/settings" className={({isActive}) => `px-3 py-2 rounded transition ${isActive ? 'bg-gray-800 text-white' : 'text-gray-300 hover:bg-gray-800 hover:text-white'}`}>⚙️ Settings</NavLink>
          <button onClick={()=>{ sessionStorage.removeItem('auth'); navigate('/login', { replace: true }) }} className="mt-2 text-left px-3 py-2 rounded text-gray-300 hover:bg-gray-800 hover:text-white">🚪 Logout</button>
        </nav>
      </aside>
      <main className="flex-1 p-8">
        <header className="mb-6">
          <div className="rounded-2xl bg-gradient-to-r from-brand-500 to-accent-500 text-white p-6 shadow-card">
            <h1 className="text-2xl font-semibold">📊 Dashboard</h1>
            <p className="opacity-90 text-sm">Meetings, tasks, and conflicts at a glance</p>
          </div>
        </header>
        <div className="space-y-8">
          <Outlet />
        </div>
      </main>
    </div>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<ProtectedLayout />}>
        <Route index element={<Dashboard />} />
        <Route path="/new" element={<NewMeeting />} />
        <Route path="/meetings" element={<PastMeetings />} />
        <Route path="/summary" element={<Summary />} />
        <Route path="/task-assigned" element={<TaskAssigned />} />
        <Route path="/conflict-detection" element={<ConflictDetection />} />
        <Route path="/settings" element={<Settings />} />
      </Route>
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  )
}


