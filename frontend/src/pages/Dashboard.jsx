import React from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchMeetings } from '../api/meetings'
import { fetchTasks, createTask } from '../api/tasks'
import { fetchConflicts, createConflict } from '../api/conflicts'

export default function Dashboard() {
  const qc = useQueryClient()
  const { data: meetings = [] } = useQuery({ queryKey: ['meetings'], queryFn: fetchMeetings })
  const { data: tasks = [] } = useQuery({ queryKey: ['tasks'], queryFn: fetchTasks })
  const { data: conflicts = [] } = useQuery({ queryKey: ['conflicts'], queryFn: fetchConflicts })

  const [taskForm, setTaskForm] = React.useState({ person: '', task: '', deadline: '', notes: '' })
  const addTask = useMutation({
    mutationFn: createTask,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['tasks'] })
      setTaskForm({ person: '', task: '', deadline: '', notes: '' })
    }
  })

  const [confForm, setConfForm] = React.useState({ issue: '', raised_by: '', resolution: '', severity: 'Low' })
  const addConflict = useMutation({
    mutationFn: createConflict,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['conflicts'] })
      setConfForm({ issue: '', raised_by: '', resolution: '', severity: 'Low' })
    }
  })

  return (
    <div className="space-y-8">
      <section>
        <h2 className="text-lg font-semibold text-gray-800 mb-3">🗂️ Recent Meetings</h2>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {meetings.slice(0,6).map(m => (
            <div key={m.id} className="card p-4">
              <div className="flex items-start justify-between">
                <div>
                  <div className="font-medium text-gray-900">{m.title}</div>
                  <div className="text-sm text-gray-600">{m.date}</div>
                </div>
                <span className="badge badge-info">Meeting</span>
              </div>
            </div>
          ))}
          {meetings.length === 0 && (
            <div className="text-sm text-gray-500">No meetings yet.</div>
          )}
        </div>
      </section>
      <section>
        <h2 className="text-lg font-semibold text-gray-800 mb-3">✅ Tasks</h2>
        <div className="card p-4 mb-3">
          <div className="grid md:grid-cols-4 gap-3">
            <input value={taskForm.person} onChange={e=>setTaskForm({...taskForm,person:e.target.value})} placeholder="Assignee" className="border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-mint-400" />
            <input value={taskForm.task} onChange={e=>setTaskForm({...taskForm,task:e.target.value})} placeholder="Task" className="border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-mint-400" />
            <input type="date" value={taskForm.deadline} onChange={e=>setTaskForm({...taskForm,deadline:e.target.value})} className="border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-mint-400" />
            <button onClick={()=>addTask.mutate(taskForm)} className="px-4 py-2 bg-mint-600 hover:bg-mint-700 text-white rounded">Add Task</button>
          </div>
          <input value={taskForm.notes} onChange={e=>setTaskForm({...taskForm,notes:e.target.value})} placeholder="Notes (optional)" className="mt-3 w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-mint-400" />
        </div>
        <ul className="card divide-y">
          {tasks.slice(0,8).map(t => (
            <li key={t.id} className="px-4 py-3 flex items-center justify-between">
              <div>
                <div className="font-medium text-gray-900">{t.task}</div>
                <div className="text-sm text-gray-600">{t.person}</div>
              </div>
              <div className="flex items-center gap-3">
                <span className={`badge capitalize ${t.status === 'Done' ? 'badge-success' : t.status === 'In Progress' ? 'badge-info' : 'badge-warn'}`}>{t.status}</span>
                <span className="text-xs text-gray-500">{t.deadline}</span>
              </div>
            </li>
          ))}
          {tasks.length === 0 && (
            <li className="px-4 py-3 text-sm text-gray-500">No tasks yet.</li>
          )}
        </ul>
      </section>

      <section>
        <h2 className="text-lg font-semibold text-gray-800 mb-3">⚠️ Conflicts</h2>
        <div className="card p-4 mb-3 space-y-3">
          <div className="grid md:grid-cols-4 gap-3">
            <input value={confForm.issue} onChange={e=>setConfForm({...confForm,issue:e.target.value})} placeholder="Issue" className="border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-rose-400" />
            <input value={confForm.raised_by} onChange={e=>setConfForm({...confForm,raised_by:e.target.value})} placeholder="Raised by" className="border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-rose-400" />
            <select value={confForm.severity} onChange={e=>setConfForm({...confForm,severity:e.target.value})} className="border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-rose-400">
              <option>Low</option>
              <option>Medium</option>
              <option>High</option>
            </select>
            <button onClick={()=>addConflict.mutate(confForm)} className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded">Add Conflict</button>
          </div>
          <input value={confForm.resolution} onChange={e=>setConfForm({...confForm,resolution:e.target.value})} placeholder="Resolution (optional)" className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-rose-400" />
        </div>
        <div className="grid md:grid-cols-2 gap-4">
          {conflicts.slice(0,6).map(c => (
            <div key={c.id} className="card p-4">
              <div className="flex items-start justify-between">
                <div>
                  <div className="font-medium text-gray-900">{c.issue}</div>
                  <div className="text-sm text-gray-600">Raised by: {c.raised_by}</div>
                </div>
                <span className={`badge ${c.severity === 'High' ? 'badge-high' : c.severity === 'Medium' ? 'badge-medium' : 'badge-low'}`}>{c.severity}</span>
              </div>
              <div className="text-sm text-gray-600 mt-2">Resolution: {c.resolution || '-'}</div>
            </div>
          ))}
          {conflicts.length === 0 && (
            <div className="text-sm text-gray-500">No conflicts reported.</div>
          )}
        </div>
      </section>
    </div>
  )
}


