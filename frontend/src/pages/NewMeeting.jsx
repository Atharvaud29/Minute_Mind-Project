import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createMeeting, uploadAndTranscribe, generateWithPhi3 } from '../api/meetings'

export default function NewMeeting() {
  const qc = useQueryClient()
  const [form, setForm] = useState({
    title: '',
    summary: '',
    date: '',
    time: '',
    location: '',
    host: '',
    presentees: '',
    absentees: '',
    agenda: ''
  })
  const { mutate, isPending } = useMutation({
    mutationFn: createMeeting,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['meetings'] })
      setForm({ title: '', summary: '', date: '', time: '', location: '', host: '', presentees: '', absentees: '', agenda: '' })
      alert('Meeting created')
    }
  })

  const [audioFile, setAudioFile] = useState(null)
  const [transcript, setTranscript] = useState('')
  const [genSummary, setGenSummary] = useState('')
  const [isTranscribing, setIsTranscribing] = useState(false)
  const [transcribeError, setTranscribeError] = useState('')

  const handleTranscribe = async () => {
    if (!audioFile) return alert('Select an audio file first')
    
    setIsTranscribing(true)
    setTranscribeError('')
    
    try {
      console.log('Starting transcription...')
      const res = await uploadAndTranscribe(audioFile)
      console.log('Transcription response:', res)
      setTranscript(res.text || '')
      setForm({ ...form, summary: res.text || form.summary })
    } catch (error) {
      console.error('Transcription error:', error)
      setTranscribeError(error.response?.data?.error || error.message || 'Transcription failed')
    } finally {
      setIsTranscribing(false)
    }
  }

  const handleGenerateSummary = async () => {
    const base = transcript || form.summary
    if (!base) return alert('Need transcript or description to summarize')
    const prompt = `Summarize the following meeting transcript in 6-10 bullet points focusing on decisions and action items.\n\n${base}`
    const res = await generateWithPhi3({ prompt, max_tokens: 512, temperature: 0.6, top_p: 0.9 })
    setGenSummary(res.text || '')
  }

  return (
    <div className="max-w-xl">
      <h1 className="text-2xl font-semibold mb-4">New Meeting</h1>
      <div className="card p-4 space-y-4">
        <div className="grid md:grid-cols-2 gap-3">
          <input value={form.title} onChange={e=>setForm({...form,title:e.target.value})} className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-400" placeholder="Title" />
          <input value={form.location} onChange={e=>setForm({...form,location:e.target.value})} className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-400" placeholder="Location" />
          <input type="date" value={form.date} onChange={e=>setForm({...form,date:e.target.value})} className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-400" />
          <input type="time" value={form.time} onChange={e=>setForm({...form,time:e.target.value})} className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-400" />
          <input value={form.host} onChange={e=>setForm({...form,host:e.target.value})} className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-400" placeholder="Host" />
        </div>

        <textarea value={form.summary} onChange={e=>setForm({...form,summary:e.target.value})} className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-400" placeholder="Description / Objective" rows={3} />

        <div className="grid md:grid-cols-2 gap-3">
          <input value={form.presentees} onChange={e=>setForm({...form,presentees:e.target.value})} className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-400" placeholder="Present members (comma separated)" />
          <input value={form.absentees} onChange={e=>setForm({...form,absentees:e.target.value})} className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-400" placeholder="Absent members (comma separated)" />
        </div>

        <textarea value={form.agenda} onChange={e=>setForm({...form,agenda:e.target.value})} className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-400" placeholder="Agenda of meeting" rows={3} />

        <div className="grid md:grid-cols-3 gap-3 items-center">
          <input type="file" accept="audio/*" onChange={e=>setAudioFile(e.target.files?.[0] || null)} className="w-full" />
          <button 
            type="button" 
            onClick={handleTranscribe} 
            disabled={isTranscribing || !audioFile}
            className="px-4 py-2 bg-mint-600 hover:bg-mint-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white rounded"
          >
            {isTranscribing ? 'Transcribing...' : 'Transcribe Audio'}
          </button>
          <button type="button" onClick={handleGenerateSummary} className="px-4 py-2 bg-grape-600 hover:bg-grape-700 text-white rounded">Generate Summary</button>
        </div>

        {transcribeError && (
          <div className="text-red-600 bg-red-50 border border-red-200 rounded p-3">
            Error: {transcribeError}
          </div>
        )}

        {isTranscribing && (
          <div className="text-blue-600 bg-blue-50 border border-blue-200 rounded p-3">
            Transcribing audio... This may take a few minutes for longer files.
          </div>
        )}

        {transcript && (
          <div className="text-sm text-gray-700 bg-mint-50 border border-mint-200 rounded p-3 whitespace-pre-wrap">{transcript}</div>
        )}
        {genSummary && (
          <div className="text-sm text-gray-700 bg-grape-50 border border-grape-200 rounded p-3 whitespace-pre-wrap">{genSummary}</div>
        )}

        <button
          disabled={isPending}
          onClick={()=>mutate({
            title: form.title,
            summary: genSummary || form.summary,
            date: form.date,
            location: form.location,
            host: form.host,
            presentees: form.presentees,
            absentees: form.absentees,
            agenda: form.agenda,
            adjournment_time: form.time
          })}
          className="px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white rounded shadow"
        >
          {isPending ? 'Saving…' : 'Create Meeting'}
        </button>
      </div>
    </div>
  )
}


