// import React, { useState } from 'react'
// import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
// import { fetchTasks, createTask, updateTask } from '../api/tasks'

// export default function TaskAssigned() {
//   const qc = useQueryClient()
//   const { data: tasks = [] } = useQuery({ queryKey: ['tasks'], queryFn: fetchTasks })
//   const addTask = useMutation({
//     mutationFn: createTask,
//     onSuccess: () => qc.invalidateQueries({ queryKey: ['tasks'] })
//   })

//   const [form, setForm] = useState({ person: '', task: '', deadline: '', notes: '' })
//   return (
//     <div className="space-y-4">
//       <h1 className="text-2xl font-semibold">Task Assigned</h1>

//       <div className="card p-4">
//         <div className="grid md:grid-cols-4 gap-3">
//           <input value={form.person} onChange={e=>setForm({...form,person:e.target.value})} placeholder="Assignee" className="border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-mint-400" />
//           <input value={form.task} onChange={e=>setForm({...form,task:e.target.value})} placeholder="Task" className="border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-mint-400" />
//           <input type="date" value={form.deadline} onChange={e=>setForm({...form,deadline:e.target.value})} className="border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-mint-400" />
//           <div className="flex items-center">
//             <button onClick={()=> addTask.mutate(form)} className="px-4 py-2 bg-mint-600 hover:bg-mint-700 text-white rounded">Add Task</button>
//           </div>
//         </div>
//         <input value={form.notes} onChange={e=>setForm({...form,notes:e.target.value})} placeholder="Notes (optional)" className="mt-3 w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-mint-400" />
//       </div>

//       <ul className="card divide-y">
//         {tasks.map(t => (
//           <li key={t.id} className="px-4 py-3 flex items-center justify-between">
//             <div>
//               <div className="font-medium text-gray-900">{t.task}</div>
//               <div className="text-sm text-gray-600">{t.person}</div>
//             </div>
//             <span className={`badge capitalize ${t.status === 'Done' ? 'badge-success' : t.status === 'In Progress' ? 'badge-info' : 'badge-warn'}`}>{t.status}</span>
//           </li>
//         ))}
//         {tasks.length === 0 && <li className="px-4 py-3 text-sm text-gray-500">No tasks.</li>}
//       </ul>
//     </div>
//   )
// }

import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchTasks, createTask, updateTask } from '../api/tasks'

export default function TaskAssigned() {
  const qc = useQueryClient()
  const { data: tasks = [] } = useQuery({ queryKey: ['tasks'], queryFn: fetchTasks })
  
  const addTask = useMutation({
    mutationFn: createTask,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tasks'] })
  })

  const updateTaskMutation = useMutation({
    mutationFn: ({ id, payload }) => updateTask(id, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tasks'] })
  })

  const [form, setForm] = useState({ person: '', task: '', deadline: '', notes: '' })

  const handleAddTask = () => {
    if (!form.task || !form.person) return alert('Please enter both task and assignee.')
    addTask.mutate(form)
    setForm({ person: '', task: '', deadline: '', notes: '' })
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Task Assigned</h1>

      <div className="card p-4">
        <div className="grid md:grid-cols-4 gap-3">
          <input
            value={form.person}
            onChange={e => setForm({ ...form, person: e.target.value })}
            placeholder="Assignee"
            className="border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-mint-400"
          />
          <input
            value={form.task}
            onChange={e => setForm({ ...form, task: e.target.value })}
            placeholder="Task"
            className="border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-mint-400"
          />
          <input
            type="date"
            value={form.deadline}
            onChange={e => setForm({ ...form, deadline: e.target.value })}
            className="border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-mint-400"
          />
          <div className="flex items-center">
            <button
              onClick={handleAddTask}
              className="px-4 py-2 bg-mint-600 hover:bg-mint-700 text-white rounded"
            >
              Add Task
            </button>
          </div>
        </div>

        <input
          value={form.notes}
          onChange={e => setForm({ ...form, notes: e.target.value })}
          placeholder="Notes (optional)"
          className="mt-3 w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-mint-400"
        />
      </div>

      <ul className="card divide-y">
        {tasks.map(t => (
          <li key={t.id} className="px-4 py-3 flex items-center justify-between">
            <div>
              <div className="font-medium text-gray-900">{t.task}</div>
              <div className="text-sm text-gray-600">{t.person}</div>
            </div>
            <span
              className={`badge capitalize ${
                t.status === 'Done' ? 'badge-success' :
                t.status === 'In Progress' ? 'badge-info' :
                'badge-warn'
              }`}
            >
              {t.status || 'Pending'}
            </span>
          </li>
        ))}
        {tasks.length === 0 && (
          <li className="px-4 py-3 text-sm text-gray-500">No tasks.</li>
        )}
      </ul>
    </div>
  )
}
