import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchConflicts, createConflict, updateConflict } from '../api/conflicts'

export default function ConflictDetection() {
  const qc = useQueryClient()
  const { data: conflicts = [] } = useQuery({ queryKey: ['conflicts'], queryFn: fetchConflicts })
  const addConflict = useMutation({
    mutationFn: createConflict,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['conflicts'] })
  })

  const [form, setForm] = React.useState({ issue: '', raised_by: '', resolution: '', severity: 'Low' })
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Conflict Detection</h1>

      <div className="card p-4 space-y-3">
        <div className="grid md:grid-cols-2 gap-3">
          <input value={form.issue} onChange={e=>setForm({...form,issue:e.target.value})} placeholder="Issue" className="border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-rose-400" />
          <input value={form.raised_by} onChange={e=>setForm({...form,raised_by:e.target.value})} placeholder="Raised by" className="border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-rose-400" />
          <select value={form.severity} onChange={e=>setForm({...form,severity:e.target.value})} className="border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-rose-400">
            <option>Low</option>
            <option>Medium</option>
            <option>High</option>
          </select>
          <button onClick={()=>addConflict.mutate(form)} className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded">Add Conflict</button>
        </div>
        <input value={form.resolution} onChange={e=>setForm({...form,resolution:e.target.value})} placeholder="Resolution (optional)" className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-rose-400" />
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        {conflicts.map(c => (
          <div key={c.id} className="card p-4">
            <div className="flex items-start justify-between">
              <div>
                <div className="font-medium text-gray-900">{c.issue}</div>
                <div className="text-sm text-gray-600">Raised by: {c.raised_by}</div>
              </div>
              <span className={`badge ${c.severity === 'High' ? 'bg-rose-100 text-rose-700' : c.severity === 'Medium' ? 'bg-accent-100 text-accent-700' : 'bg-mint-100 text-mint-700'}`}>{c.severity}</span>
            </div>
            <div className="text-sm text-gray-600 mt-2">Resolution: {c.resolution || '-'}</div>
          </div>
        ))}
        {conflicts.length === 0 && (
          <div className="text-sm text-gray-500">No conflicts found.</div>
        )}
      </div>
    </div>
  )
}


