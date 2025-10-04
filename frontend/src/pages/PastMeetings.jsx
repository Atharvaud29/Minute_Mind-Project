import { useQuery } from '@tanstack/react-query'
import { fetchMeetings } from '../api/meetings'

export default function PastMeetings() {
  const { data: meetings = [] } = useQuery({ queryKey: ['meetings'], queryFn: fetchMeetings })
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Past Meetings</h1>
      <div className="overflow-x-auto card">
        <table className="min-w-full text-left">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-2">Title</th>
              <th className="px-4 py-2">Date & Time</th>
              <th className="px-4 py-2">Host</th>
              <th className="px-4 py-2">Description</th>
              <th className="px-4 py-2">Agenda</th>
              <th className="px-4 py-2 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {meetings.map(m => (
              <tr key={m.id} className="align-top">
                <td className="px-4 py-2 font-medium text-gray-900">{m.title}</td>
                <td className="px-4 py-2 whitespace-nowrap">{m.date}{m.adjournment_time ? ` • ${m.adjournment_time}` : ''}</td>
                <td className="px-4 py-2">{m.host}</td>
                <td className="px-4 py-2 max-w-xs">
                  <div className="truncate" title={m.summary || ''}>{m.summary || '-'}</div>
                </td>
                <td className="px-4 py-2 max-w-xs">
                  <div className="truncate" title={m.agenda || ''}>{m.agenda || '-'}</div>
                </td>
                <td className="px-4 py-2 text-right">
                  <a href={m.docxUrl} className="inline-flex items-center gap-1 px-3 py-1.5 rounded text-white bg-brand-600 hover:bg-brand-700 text-sm">
                    ⬇️ <span>Download</span>
                  </a>
                </td>
              </tr>
            ))}
            {meetings.length === 0 && (
              <tr>
                <td className="px-4 py-3 text-sm text-gray-500" colSpan={6}>No meetings found.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}


