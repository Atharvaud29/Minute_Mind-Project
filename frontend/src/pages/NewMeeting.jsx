// import { useState, useRef } from 'react'
// import { useMutation, useQueryClient } from '@tanstack/react-query'
// import { createMeeting, uploadAndTranscribe, getFullAnalysis } from '../api/meetings'
// import { createTask } from '../api/tasks'
// import { createConflict } from '../api/conflicts'

// export default function NewMeeting() {
//   const qc = useQueryClient()
//   const [form, setForm] = useState({
//     title: '',
//     summary: '',
//     date: '',
//     start_time: '',
//     end_time: '',
//     location: '',
//     host: '',
//     presentees: '',
//     absentees: '',
//     agenda: ''
//   })  
//   const [audioFile, setAudioFile] = useState(null)
//   const [transcript, setTranscript] = useState('')
//   const [transcriptSegments, setTranscriptSegments] = useState([])
//   const [speakers, setSpeakers] = useState([])
//   const [analysisResult, setAnalysisResult] = useState('')
//   const [isTranscribing, setIsTranscribing] = useState(false)
//   const [isAnalyzing, setIsAnalyzing] = useState(false)
//   const [transcribeError, setTranscribeError] = useState('')
//   const [momFile, setMomFile] = useState(null)
//   const [meetingId, setMeetingId] = useState(null)
//   const hasSavedExtractedTasksRef = useRef(false)
//   const hasSavedExtractedConflictsRef = useRef(false)

//   const extractTasksFromAnalysis = (analysisText) => {
//     if (!analysisText) return []
//     console.log('Extracting tasks from:', analysisText)
//     const lines = analysisText.split(/\r?\n/)
//     const tasks = []
//     let inTable = false
//     let headerIndex = -1
    
//     // Look for task assignment section
//     for (let i = 0; i < lines.length; i++) {
//       const line = lines[i].trim()
      
//       // Check for task assignment heading
//       if (!inTable && line.toLowerCase().includes('task assignment')) {
//         console.log('Found task assignment section at line:', i)
//         // Look for markdown table format
//         for (let j = i + 1; j < Math.min(lines.length, i + 10); j++) {
//           const hdr = lines[j].trim()
//           if (hdr.startsWith('|') && (/task/i.test(hdr) || /owner/i.test(hdr) || /deadline/i.test(hdr))) {
//             console.log('Found table header at line:', j, hdr)
//             inTable = true
//             headerIndex = j
//             i = j + 1
//             break
//           }
//         }
//       }
      
//       if (inTable) {
//         // Skip separator row (---)
//         if (i === headerIndex + 1 && /^\|\s*-/.test(lines[i].trim())) continue
        
//         const row = lines[i].trim()
//         if (!row.startsWith('|')) break
        
//         const cells = row.split('|').map(s => s.trim()).filter(Boolean)
//         console.log('Processing table row:', cells)
        
//         if (cells.length >= 2) {
//           const givenTask = cells[0] || ''
//           const taskOwner = cells[1] || ''
//           const deadline = cells[2] || ''
          
//           // Skip header rows
//           if (/task/i.test(givenTask) && /owner/i.test(taskOwner)) continue
//           if (/given task/i.test(givenTask) && /task owner/i.test(taskOwner)) continue
          
//           // Skip empty rows
//           if (!givenTask && !taskOwner && !deadline) continue
          
//           tasks.push({
//             person: taskOwner,
//             task: givenTask,
//             deadline: deadline,
//           })
//           console.log('Added task:', { person: taskOwner, task: givenTask, deadline: deadline })
//         } else {
//           break
//         }
//       }
//     }
    
//     // If no table found, try to extract from bullet points or simple text
//     if (tasks.length === 0) {
//       console.log('No table found, trying alternative extraction')
//       for (let i = 0; i < lines.length; i++) {
//         const line = lines[i].trim()
//         if (line.toLowerCase().includes('task assignment') || line.toLowerCase().includes('action item')) {
//           // Look for bullet points or numbered lists
//           for (let j = i + 1; j < Math.min(lines.length, i + 20); j++) {
//             const nextLine = lines[j].trim()
//             if (nextLine.startsWith('-') || nextLine.startsWith('*') || /^\d+\./.test(nextLine)) {
//               // Extract task from bullet point
//               const taskText = nextLine.replace(/^[-*]\s*/, '').replace(/^\d+\.\s*/, '')
//               if (taskText.length > 10) { // Only add substantial tasks
//                 tasks.push({
//                   person: '',
//                   task: taskText,
//                   deadline: '',
//                 })
//                 console.log('Added task from bullet point:', taskText)
//               }
//             }
//           }
//           break
//         }
//       }
//     }
    
//     console.log('Final extracted tasks:', tasks)
//     return tasks
//   }

//   const saveExtractedTasks = async (analysisText) => {
//     if (hasSavedExtractedTasksRef.current) return
//     console.log('Analysis text for task extraction:', analysisText)
//     const parsed = extractTasksFromAnalysis(analysisText)
//     console.log('Extracted tasks:', parsed)
//     if (!parsed.length) {
//       console.log('No tasks found in analysis')
//       hasSavedExtractedTasksRef.current = true
//       return
//     }
//     try {
//       await Promise.allSettled(parsed.map(t => createTask(t)))
//       console.log('Tasks saved successfully')
//       // Ensure Task Assigned page shows newly saved items immediately
//       qc.invalidateQueries({ queryKey: ['tasks'] })
//     } finally {
//       hasSavedExtractedTasksRef.current = true
//     }
//   }

//   const extractConflictsFromAnalysis = (analysisText) => {
//     if (!analysisText) return []
//     console.log('Extracting conflicts from:', analysisText)
//     const lines = analysisText.split(/\r?\n/)
//     const conflicts = []
//     let inSection = false
    
//     for (let i = 0; i < lines.length; i++) {
//       const line = lines[i].trim()
      
//       // Check for conflict detection heading
//       if (!inSection && line.toLowerCase().includes('conflict detection')) {
//         console.log('Found conflict detection section at line:', i)
//         inSection = true
//         continue
//       }
      
//       if (inSection) {
//         if (!line) continue
        
//         // Stop when next heading begins
//         if (/^#{2,3}\s+/.test(line)) break
        
//         // Try parse JSONL line
//         try {
//           const obj = JSON.parse(line)
//           const speaker1 = obj['Name of speaker1'] || ''
//           const speaker2 = obj['Name of speaker2'] || ''
//           const type = obj['conflict type (Orig_type)'] || 'Neutral'
//           const desc = obj['conflict description'] || ''
          
//           let severity = 'Medium'
//           if (/negative/i.test(type)) severity = 'High'
//           else if (/neutral/i.test(type)) severity = 'Low'
//           else severity = 'Medium'
          
//           conflicts.push({
//             issue: desc,
//             raised_by: [speaker1, speaker2].filter(Boolean).join(' vs '),
//             resolution: '',
//             severity,
//           })
//           console.log('Added conflict:', { issue: desc, raised_by: [speaker1, speaker2].filter(Boolean).join(' vs '), severity })
//         } catch (_) {
//           // Try to extract from simple text format
//           if (line.length > 20 && !line.startsWith('#')) {
//             // Look for conflict indicators
//             if (/disagree|conflict|concern|issue|problem/i.test(line)) {
//               conflicts.push({
//                 issue: line,
//                 raised_by: '',
//                 resolution: '',
//                 severity: 'Medium',
//               })
//               console.log('Added conflict from text:', line)
//             }
//           }
//         }
//       }
//     }
    
//     // If no conflicts found in structured format, try to extract from general text
//     if (conflicts.length === 0) {
//       console.log('No structured conflicts found, trying alternative extraction')
//       for (let i = 0; i < lines.length; i++) {
//         const line = lines[i].trim()
//         if (line.length > 30 && /concern|disagree|conflict|issue|problem|dispute/i.test(line)) {
//           conflicts.push({
//             issue: line,
//             raised_by: '',
//             resolution: '',
//             severity: 'Medium',
//           })
//           console.log('Added conflict from general text:', line)
//         }
//       }
//     }
    
//     console.log('Final extracted conflicts:', conflicts)
//     return conflicts
//   }

//   const saveExtractedConflicts = async (analysisText) => {
//     if (hasSavedExtractedConflictsRef.current) return
//     console.log('Analysis text for conflict extraction:', analysisText)
//     const parsed = extractConflictsFromAnalysis(analysisText)
//     console.log('Extracted conflicts:', parsed)
//     if (!parsed.length) {
//       console.log('No conflicts found in analysis')
//       hasSavedExtractedConflictsRef.current = true
//       return
//     }
//     try {
//       await Promise.allSettled(parsed.map(c => createConflict(c)))
//       console.log('Conflicts saved successfully')
//       // Ensure Conflict Detection page shows newly saved items immediately
//       qc.invalidateQueries({ queryKey: ['conflicts'] })
//     } finally {
//       hasSavedExtractedConflictsRef.current = true
//     }
//   }

//   const { mutate, isPending } = useMutation({
//     mutationFn: createMeeting,
//     onSuccess: () => {
//       qc.invalidateQueries({ queryKey: ['meetings'] })
//       setForm({
//         title: '',
//         summary: '',
//         date: '',
//         start_time: '',
//         end_time: '',
//         location: '',
//         host: '',
//         presentees: '',
//         absentees: '',
//         agenda: ''
//       })      
//       setTranscript('')
//       setAnalysisResult('')
//       setAudioFile(null)
//       alert('Meeting created successfully!')
//     }
//   })

//   const handleTranscribe = async () => {
//     if (!audioFile) return alert('Select an audio file first')

//     setIsTranscribing(true)
//     setTranscribeError('')
//     setTranscript('')
//     setAnalysisResult('')
    
//     // Reset extraction flags for new transcription
//     hasSavedExtractedTasksRef.current = false
//     hasSavedExtractedConflictsRef.current = false

//     try {
//       // Pass form data to transcribe so meeting can be created with all details
//       const res = await uploadAndTranscribe(audioFile, form)
      
//       // Handle new speaker-segmented format
//       if (res.segments && Array.isArray(res.segments)) {
//         setTranscriptSegments(res.segments)
//         setSpeakers(res.speakers || [])
//         // Format transcript with speaker labels for display
//         const formattedTranscript = res.segments.map(seg => {
//           const speaker = seg.speaker || 'UNKNOWN'
//           const text = seg.text || ''
//           return `${speaker}: ${text}`
//         }).join('\n')
//         setTranscript(formattedTranscript)
//       } else {
//         // Fallback to old format
//         setTranscript(res.transcript || res.text || '')
//         setTranscriptSegments([])
//         setSpeakers([])
//       }
      
//       // Populate summary produced after transcription from unified endpoint
//       const combined = res.analysis || res.summary || ''
//       setAnalysisResult(combined)
      
//       // Store meeting ID and MoM file info if available
//       if (res.meeting_id) {
//         setMeetingId(res.meeting_id)
//       }
//       if (res.mom_file) {
//         setMomFile(res.mom_file)
//       }
      
//       // Auto-save extracted tasks and conflicts so they appear in their pages
//       saveExtractedTasks(combined)
//       saveExtractedConflicts(combined)
//     } catch (error) {
//       console.error('Transcription error:', error)
//       let errorMessage = 'Transcription failed'
      
//       if (error.code === 'ECONNABORTED') {
//         errorMessage = 'Request timed out. The audio file may be too long or the server is overloaded. Please try again.'
//       } else if (error?.response?.data?.error) {
//         errorMessage = error.response.data.error
//       } else if (error?.message) {
//         errorMessage = error.message
//       }
      
//       setTranscribeError(errorMessage)
//     } finally {
//       setIsTranscribing(false)
//     }
//   }

//   const handleGenerateAnalysis = async () => {
//     if (!transcript) return alert('You must transcribe the audio first.')

//     setIsAnalyzing(true)
//     setAnalysisResult('')

//     try {
//       const res = await getFullAnalysis(transcript)
//       console.log('Analysis response:', res) // Debug log
      
//       // Handle both possible response structures
//       const combined = res.analysis || res.summary || 'Analysis failed.'
//       console.log('Setting analysis result:', combined) // Debug log
      
//       setAnalysisResult(combined)
//       saveExtractedTasks(combined)
//       saveExtractedConflicts(combined)
//     } catch (error) {
//       console.error('Analysis error:', error)
//       let errorMessage = 'Analysis failed'
      
//       if (error.code === 'ECONNABORTED') {
//         errorMessage = 'Request timed out. The analysis may be taking too long. Please try again.'
//       } else if (error?.response?.data?.error) {
//         errorMessage = error.response.data.error
//       } else if (error?.message) {
//         errorMessage = error.message
//       }
      
//       setAnalysisResult(`Error: ${errorMessage}`)
//     } finally {
//       setIsAnalyzing(false)
//     }
//   }

//   return (
//     <div className="max-w-xl">
//       <h1 className="text-2xl font-semibold mb-4">New Meeting</h1>
//       <div className="card p-4 space-y-4">
//         <div className="grid md:grid-cols-2 gap-3">
//           <input
//             value={form.title}
//             onChange={e => setForm({ ...form, title: e.target.value })}
//             className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-400"
//             placeholder="Title"
//           />
//           <input
//             value={form.location}
//             onChange={e => setForm({ ...form, location: e.target.value })}
//             className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-400"
//             placeholder="Location"
//           />
//           <input
//             type="date"
//             value={form.date}
//             onChange={e => setForm({ ...form, date: e.target.value })}
//             className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-400"
//           />
//           <input
//             type="time"
//             value={form.start_time}
//             onChange={e => setForm({ ...form, start_time: e.target.value })}
//             className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-400"
//             placeholder="Start Time"
//           />
//           <input
//             type="time"
//             value={form.end_time}
//             onChange={e => setForm({ ...form, end_time: e.target.value })}
//             className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-400"
//             placeholder="End Time"
//           />
//           <input
//             value={form.host}
//             onChange={e => setForm({ ...form, host: e.target.value })}
//             className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-400"
//             placeholder="Host"
//           />
//         </div>

//         <div className="grid md:grid-cols-2 gap-3">
//           <input
//             value={form.presentees}
//             onChange={e => setForm({ ...form, presentees: e.target.value })}
//             className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-400"
//             placeholder="Present members (comma separated)"
//           />
//           <input
//             value={form.absentees}
//             onChange={e => setForm({ ...form, absentees: e.target.value })}
//             className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-400"
//             placeholder="Absent members (comma separated)"
//           />
//         </div>

//         <textarea
//           value={form.agenda}
//           onChange={e => setForm({ ...form, agenda: e.target.value })}
//           className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-400"
//           placeholder="Agenda of meeting"
//           rows={3}
//         />

//         <div className="grid md:grid-cols-3 gap-3 items-center">
//           <input
//             type="file"
//             accept="audio/*"
//             onChange={e => setAudioFile(e.target.files?.[0] || null)}
//             className="w-full"
//           />
//           <button
//             type="button"
//             onClick={handleTranscribe}
//             disabled={isTranscribing || !audioFile}
//             className="px-4 py-2 bg-mint-600 hover:bg-mint-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white rounded"
//           >
//             {isTranscribing ? 'Transcribing...' : 'Transcribe Audio'}
//           </button>
//           <button
//             type="button"
//             onClick={handleGenerateAnalysis}
//             disabled={isAnalyzing || !transcript}
//             className="px-4 py-2 bg-grape-600 hover:bg-grape-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white rounded"
//           >
//             {isAnalyzing ? 'Analyzing...' : 'Generate Analysis'}
//           </button>
//         </div>

//         {transcribeError && (
//           <div className="text-red-600 bg-red-50 border border-red-200 rounded p-3">
//             Error: {transcribeError}
//           </div>
//         )}

//         {speakers.length > 0 && (
//           <div className="bg-blue-50 border border-blue-200 rounded p-3">
//             <p className="text-sm text-blue-800">
//               <strong>Speakers detected:</strong> {speakers.join(', ')}
//             </p>
//           </div>
//         )}

//         {momFile && (
//           <div className="bg-green-50 border border-green-200 rounded p-3">
//             <p className="text-sm text-green-800 mb-2">
//               <strong>✓ MoM Document Generated!</strong>
//             </p>
//             <a
//               href={`http://127.0.0.1:5000${momFile.download_url}`}
//               download
//               className="inline-block px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded"
//             >
//               📄 Download MoM Document
//             </a>
//             {momFile.filename && (
//               <p className="text-xs text-green-600 mt-2">File: {momFile.filename}</p>
//             )}
//           </div>
//         )}

//         {transcript && (
//           <div className="space-y-2">
//             <h3 className="font-semibold text-gray-800">Transcript:</h3>
//             <div className="text-sm text-gray-700 bg-gray-50 border border-gray-200 rounded p-3 whitespace-pre-wrap max-h-64 overflow-y-auto">
//               {transcriptSegments.length > 0 ? (
//                 transcriptSegments.map((seg, idx) => (
//                   <div key={idx} className="mb-2">
//                     <span className="font-semibold text-blue-600">{seg.speaker || 'UNKNOWN'}:</span>{' '}
//                     <span className="text-gray-800">{seg.text}</span>
//                     {seg.start !== undefined && (
//                       <span className="text-xs text-gray-500 ml-2">
//                         [{Math.floor(seg.start / 60)}:{(seg.start % 60).toFixed(0).padStart(2, '0')}]
//                       </span>
//                     )}
//                   </div>
//                 ))
//               ) : (
//                 transcript
//               )}
//             </div>
//           </div>
//         )}

//         {analysisResult && (
//           <div className="space-y-2">
//             <h3 className="font-semibold text-gray-800">Analysis:</h3>
//             <div className="text-sm text-gray-700 bg-grape-50 border border-grape-200 rounded p-3 whitespace-pre-wrap">
//               {analysisResult}
//             </div>
//           </div>
//         )}
//         <button
//           disabled={isPending}   // <-- allow creation even without analysis
//           onClick={() =>
//             mutate({
//               title: form.title,
//               summary: analysisResult || form.summary || "",   // fallback if no analysis
//               date: form.date,
//               start_time: form.start_time,
//               end_time: form.end_time,
//               location: form.location,
//               host: form.host,
//               presentees: form.presentees,
//               absentees: form.absentees,
//               agenda: form.agenda
//             })
//           }
//           className="px-4 py-2 bg-brand-600 hover:bg-brand-700 disabled:bg-gray-400 text-white rounded shadow"
//         >
//           {isPending ? 'Saving…' : 'Create Meeting'}
//         </button>
//       </div>
//     </div>
//   )
// }

// import { useState } from "react";
// import { useMutation, useQueryClient } from "@tanstack/react-query";
// import { createMeeting, uploadAndTranscribe, getFullAnalysis } from "../api/meetings";

// export default function NewMeeting() {
//   const qc = useQueryClient();

//   // ------------------------------
//   // Form & State
//   // ------------------------------
//   const [form, setForm] = useState({
//     title: "",
//     summary: "",
//     date: "",
//     start_time: "",
//     end_time: "",
//     location: "",
//     host: "",
//     presentees: "",
//     absentees: "",
//     agenda: "",
//   });

//   const [audioFile, setAudioFile] = useState(null);
//   const [transcript, setTranscript] = useState("");
//   const [transcriptSegments, setTranscriptSegments] = useState([]);
//   const [speakers, setSpeakers] = useState([]);
//   const [analysisResult, setAnalysisResult] = useState("");
//   const [extractedTasks, setExtractedTasks] = useState([]);
//   const [extractedConflicts, setExtractedConflicts] = useState([]);
//   const [isTranscribing, setIsTranscribing] = useState(false);
//   const [isAnalyzing, setIsAnalyzing] = useState(false);
//   const [transcribeError, setTranscribeError] = useState("");
//   const [momFile, setMomFile] = useState(null);

//   // ------------------------------
//   // Create Meeting Mutation
//   // ------------------------------
//   const { mutate, isPending } = useMutation({
//     mutationFn: createMeeting,
//     onSuccess: (data) => {
//       qc.invalidateQueries({ queryKey: ["meetings"] });

//       if (data.mom_file) {
//         setMomFile(data.mom_file); // Show download button
//       }

//       alert("Meeting created successfully!");

//       // Reset UI
//       setForm({
//         title: "",
//         summary: "",
//         date: "",
//         start_time: "",
//         end_time: "",
//         location: "",
//         host: "",
//         presentees: "",
//         absentees: "",
//         agenda: "",
//       });
//       setTranscript("");
//       setAnalysisResult("");
//       setTranscriptSegments([]);
//       setSpeakers([]);
//       setExtractedTasks([]);
//       setExtractedConflicts([]);
//       setMomFile(null);
//       setAudioFile(null);
//     },
//   });

//   // ------------------------------
//   // TRANSCRIBE AUDIO
//   // ------------------------------
//   const handleTranscribe = async () => {
//     if (!audioFile) return alert("Select an audio file first");

//     setIsTranscribing(true);
//     setTranscribeError("");
//     setTranscript("");
//     setAnalysisResult("");
//     setTranscriptSegments([]);
//     setSpeakers([]);
//     setExtractedTasks([]);
//     setExtractedConflicts([]);

//     try {
//       const res = await uploadAndTranscribe(audioFile, form);

//       // Handle segments & speakers
//       if (Array.isArray(res.segments)) {
//         setTranscriptSegments(res.segments);
//         setSpeakers(res.speakers || []);

//         const formatted = res.segments
//           .map((seg) => `${seg.speaker || "UNKNOWN"}: ${seg.text}`)
//           .join("\n");

//         setTranscript(formatted);
//       } else {
//         setTranscript(res.transcript || "");
//       }

//       // Store analysis/summary
//       const combined = res.summary || res.analysis || "";
//       setAnalysisResult(combined);

//       // ------------------------------
//       // Store extracted tasks/conflicts (NOT saved to DB yet)
//       // ------------------------------
//       setExtractedTasks(res.tasks || []);
//       setExtractedConflicts(res.conflicts || []);
//     } catch (error) {
//       console.error("Transcription error:", error);
//       setTranscribeError(error.message || "Transcription failed");
//     } finally {
//       setIsTranscribing(false);
//     }
//   };

//   // ------------------------------
//   // MANUAL ANALYSIS (backup)
//   // ------------------------------
//   const handleGenerateAnalysis = async () => {
//     if (!transcript) return alert("Transcribe first!");

//     setIsAnalyzing(true);
//     setAnalysisResult("");

//     try {
//       const res = await getFullAnalysis(transcript);

//       const combined = res.analysis || res.summary || "";
//       setAnalysisResult(combined);

//       // Tasks/conflicts extracted from manual LLM analysis
//       setExtractedTasks(res.tasks || []);
//       setExtractedConflicts(res.conflicts || []);
//     } catch (error) {
//       setAnalysisResult("Error generating analysis");
//     } finally {
//       setIsAnalyzing(false);
//     }
//   };

//   // ------------------------------
//   // CREATE MEETING (final step)
//   // ------------------------------
//   const handleCreateMeeting = () => {
//     mutate({
//       ...form,
//       summary: analysisResult || form.summary || "",
//       transcript_segments: transcriptSegments,
//       speakers,
//       tasks: extractedTasks,
//       conflicts: extractedConflicts,
//     });
//   };

//   // ------------------------------
//   // UI
//   // ------------------------------
//   return (
//     <div className="max-w-xl">
//       <h1 className="text-2xl font-semibold mb-4">New Meeting</h1>

//       <div className="card p-4 space-y-4">

//         {/* ================= FORM INPUTS ================= */}
//         <div className="grid md:grid-cols-2 gap-3">
//           <input value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} placeholder="Title" className="input" />
//           <input value={form.location} onChange={e => setForm({ ...form, location: e.target.value })} placeholder="Location" className="input" />
//           <input type="date" value={form.date} onChange={e => setForm({ ...form, date: e.target.value })} className="input" />
//           <input type="time" value={form.start_time} onChange={e => setForm({ ...form, start_time: e.target.value })} className="input" />
//           <input type="time" value={form.end_time} onChange={e => setForm({ ...form, end_time: e.target.value })} className="input" />
//           <input value={form.host} onChange={e => setForm({ ...form, host: e.target.value })} placeholder="Host" className="input" />
//         </div>

//         {/* Present/Absent */}
//         <div className="grid md:grid-cols-2 gap-3">
//           <input value={form.presentees} onChange={e => setForm({ ...form, presentees: e.target.value })} placeholder="Present members" className="input" />
//           <input value={form.absentees} onChange={e => setForm({ ...form, absentees: e.target.value })} placeholder="Absent members" className="input" />
//         </div>

//         <textarea value={form.agenda} onChange={e => setForm({ ...form, agenda: e.target.value })} rows={3} placeholder="Agenda" className="input" />

//         {/* ================= AUDIO + TRANSCRIBE ================= */}
//         <div className="grid md:grid-cols-3 gap-3 items-center">
//           <input type="file" accept="audio/*" onChange={(e) => setAudioFile(e.target.files?.[0] || null)} />
//           <button disabled={!audioFile || isTranscribing} onClick={handleTranscribe} className="btn-green">
//             {isTranscribing ? "Transcribing..." : "Transcribe Audio"}
//           </button>
//           <button disabled={!transcript || isAnalyzing} onClick={handleGenerateAnalysis} className="btn-purple">
//             {isAnalyzing ? "Analyzing..." : "Generate Analysis"}
//           </button>
//         </div>

//         {transcribeError && <div className="error-box">Error: {transcribeError}</div>}

//         {/* ================= SPEAKERS ================= */}
//         {speakers.length > 0 && (
//           <div className="info-box">
//             <strong>Speakers detected:</strong> {speakers.join(", ")}
//           </div>
//         )}

//         {/* ================= TRANSCRIPT ================= */}
//         {transcript && (
//           <div>
//             <h3 className="font-semibold">Transcript:</h3>
//             <pre className="transcript-box">{transcript}</pre>
//           </div>
//         )}

//         {/* ================= ANALYSIS ================= */}
//         {analysisResult && (
//           <div>
//             <h3 className="font-semibold">Analysis:</h3>
//             <pre className="analysis-box">{analysisResult}</pre>
//           </div>
//         )}

//         {/* ================= MOM FILE ================= */}
//         {momFile && (
//           <div className="success-box">
//             <p>✓ MoM Document Generated!</p>
//             <a href={`http://127.0.0.1:5000${momFile.download_url}`} download className="btn-green">
//               📄 Download MoM
//             </a>
//           </div>
//         )}

//         {/* ================= CREATE MEETING ================= */}
//         <button disabled={isPending} onClick={handleCreateMeeting} className="btn-primary">
//           {isPending ? "Saving..." : "Create Meeting"}
//         </button>

//       </div>
//     </div>
//   );
// }

// /* Utility Tailwind classes */
// const input = "w-full border rounded px-3 py-2 focus:ring-2 focus:ring-brand-400";
import { useState, useRef } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createMeeting, uploadAndTranscribe } from "../api/meetings";
import { createTask } from "../api/tasks";
import { createConflict } from "../api/conflicts";

export default function NewMeeting() {
  const qc = useQueryClient();

  // ------------------------------
  // FORM STATE
  // ------------------------------
  const [form, setForm] = useState({
    title: "",
    location: "",
    date: "",
    start_time: "",
    end_time: "",
    host: "",
    presentees: "",
    absentees: "",
    agenda: "",
  });

  const createMeetingMutation = useMutation({
    mutationFn: createMeeting,
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ["meetings"] });
      setMeetingId(res.id);
      alert("Meeting created successfully!");
    },
  });
  
  // AUDIO & ANALYSIS STATES
  const [audioFile, setAudioFile] = useState(null);
  const [transcript, setTranscript] = useState("");
  const [segments, setSegments] = useState([]);
  const [speakers, setSpeakers] = useState([]);
  const [summary, setSummary] = useState("");

  const [momFile, setMomFile] = useState(null);

  const [isTranscribing, setIsTranscribing] = useState(false);
  const [transcribeError, setTranscribeError] = useState("");

  // Prevent duplicate task/conflict saving
  const savedTasksRef = useRef(false);
  const savedConflictsRef = useRef(false);

  const [meetingId, setMeetingId] = useState(null);

  // ------------------------------
  // CREATE MEETING (NO AUDIO)
  // ------------------------------


  // ------------------------------
  // SAVE TASKS → DB
  // ------------------------------
  const saveTasks = async (tasks) => {
    if (savedTasksRef.current) return;
    savedTasksRef.current = true;

    await Promise.allSettled(
      tasks.map((t) =>
        createTask({
          person: t.assigned_to || "Unassigned",
          task: t.task_name || "Untitled Task",
          deadline: t.due_date || "Not Mentioned",
          status: "Pending",
          meeting_id: meetingId || null,
        })
      )
    );

    qc.invalidateQueries({ queryKey: ["tasks"] });
  };

  // ------------------------------
  // SAVE CONFLICTS → DB
  // ------------------------------
  const saveConflicts = async (conflicts) => {
    if (savedConflictsRef.current) return;
    savedConflictsRef.current = true;

    await Promise.allSettled(
      conflicts.map((c) =>
        createConflict({
          issue: c.issue,
          raised_by: c.raised_by,
          severity: c.severity || "Medium",
          meeting_id: meetingId || null,
        })
      )
    );

    qc.invalidateQueries({ queryKey: ["conflicts"] });
  };

  // ------------------------------
  // HANDLE TRANSCRIPTION + ANALYSIS
  // ------------------------------
  const handleTranscribe = async () => {
    if (!audioFile) return alert("Please upload an audio file first.");

    setIsTranscribing(true);
    setTranscribeError("");

    savedTasksRef.current = false;
    savedConflictsRef.current = false;

    try {
      const res = await uploadAndTranscribe(audioFile, form);
      console.log("API Response:", res);

      setTranscript(res.transcript || res.full_text || "");
      setSegments(res.segments || []);
      setSpeakers(res.speakers || []);
      setSummary(res.summary || "");

      if (res.meeting_id) setMeetingId(res.meeting_id);

      // Save tasks/conflicts if backend extracted them
      if (res.extracted_tasks) await saveTasks(res.extracted_tasks);
      if (res.extracted_conflicts) await saveConflicts(res.extracted_conflicts);

      if (res.mom_file) setMomFile(res.mom_file);
    } catch (err) {
      console.error("Error:", err);
      setTranscribeError(err.message || "Transcription failed");
    } finally {
      setIsTranscribing(false);
    }
  };

  // ------------------------------
  // UI
  // ------------------------------
  return (
    <div className="max-w-xl">
      <h1 className="text-2xl font-bold mb-4">New Meeting</h1>

      <div className="card p-4 space-y-4">
        {/* FORM INPUTS */}
        <div className="grid md:grid-cols-2 gap-3">
          <input
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
            placeholder="Title"
            className="input"
          />
          <input
            value={form.location}
            onChange={(e) => setForm({ ...form, location: e.target.value })}
            placeholder="Location"
            className="input"
          />
          <input
            type="date"
            value={form.date}
            onChange={(e) => setForm({ ...form, date: e.target.value })}
            className="input"
          />
          <input
            type="time"
            value={form.start_time}
            onChange={(e) => setForm({ ...form, start_time: e.target.value })}
            className="input"
          />
          <input
            type="time"
            value={form.end_time}
            onChange={(e) => setForm({ ...form, end_time: e.target.value })}
            className="input"
          />
          <input
            value={form.host}
            onChange={(e) => setForm({ ...form, host: e.target.value })}
            placeholder="Host"
            className="input"
          />
        </div>

        <div className="grid md:grid-cols-2 gap-3">
          <input
            value={form.presentees}
            onChange={(e) =>
              setForm({ ...form, presentees: e.target.value })
            }
            placeholder="Present members"
            className="input"
          />
          <input
            value={form.absentees}
            onChange={(e) =>
              setForm({ ...form, absentees: e.target.value })
            }
            placeholder="Absent members"
            className="input"
          />
        </div>

        <textarea
          value={form.agenda}
          onChange={(e) => setForm({ ...form, agenda: e.target.value })}
          placeholder="Agenda"
          className="input"
          rows={3}
        />

        {/* CREATE MEETING BEFORE AUDIO */}
        <button
          className="btn-primary"
          onClick={() => createMeetingMutation.mutate(form)}
        >
          Create Meeting (No Audio)
        </button>

        {/* AUDIO + TRANSCRIBE */}
        <input
          type="file"
          accept="audio/*"
          onChange={(e) => setAudioFile(e.target.files[0] || null)}
        />

        <button
          disabled={!audioFile || isTranscribing}
          onClick={handleTranscribe}
          className="btn-secondary"
        >
          {isTranscribing ? "Processing..." : "Transcribe + Analyze"}
        </button>

        {transcribeError && (
          <div className="text-red-600">{transcribeError}</div>
        )}

        {/* TRANSCRIPT */}
        {transcript && (
          <div className="bg-gray-100 p-3 rounded whitespace-pre-wrap text-sm">
            <strong>Transcript:</strong>
            <br />
            {transcript}
          </div>
        )}

        {/* SUMMARY */}
        {summary && (
          <div className="bg-purple-100 p-3 rounded whitespace-pre-wrap text-sm">
            <strong>Summary:</strong>
            <br />
            {summary}
          </div>
        )}

        {/* MOM DOWNLOAD */}
        {momFile && (
          <div className="bg-green-100 p-3 rounded">
            <strong>✓ MoM Generated</strong>
            <br />
            <a
              href={`http://127.0.0.1:5000${momFile.download_url}`}
              download
              className="btn-primary mt-2 inline-block"
            >
              Download MoM
            </a>
          </div>
        )}
      </div>
    </div>
  );
}
