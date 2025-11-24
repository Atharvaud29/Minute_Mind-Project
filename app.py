from flask import Flask, request, jsonify, Blueprint, abort, send_from_directory, render_template
from flask_sqlalchemy import SQLAlchemy
from datetime import date, datetime, timezone
import os
from flask_cors import CORS
from werkzeug.utils import secure_filename
from tempfile import NamedTemporaryFile
import traceback
import json
import re
import dateparser  # <-- added date parsing
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_cors import CORS
#from your_database_model_file import db, MeetingSummary

# Optional AI inference imports (may be missing in dev env)
try:
    from faster_whisper import WhisperModel
except Exception:
    WhisperModel = None

try:
    import whisperx
    import torch
except Exception:
    whisperx = None
    torch = None

try:
    from llama_cpp import Llama
except Exception:
    Llama = None

# Flask app
app = Flask(__name__, static_folder="frontend/dist", static_url_path="")
app.secret_key = os.environ.get("FLASK_SECRET", "replace-me-for-prod")

# Database config
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mom.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# -----------------------------
# Database Models
# -----------------------------
class Meeting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255))
    summary = db.Column(db.Text)
    date = db.Column(db.Date, default=date.today)
    location = db.Column(db.String(200))
    host = db.Column(db.String(100))
    presentees = db.Column(db.Text)
    absentees = db.Column(db.Text)
    agenda = db.Column(db.Text)
    adjournment_time = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    key_decisions = db.Column(db.PickleType)
    mom_file_path = db.Column(db.String(500))  # Path to generated MoM file
    transcript_segments = db.Column(db.PickleType)  # Store speaker-segmented transcript
    speakers = db.Column(db.Text)  # Comma-separated list of unique speakers

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    person = db.Column(db.String(100))
    task = db.Column(db.String(200))
    deadline = db.Column(db.String(50), default="Not Mentioned")
    status = db.Column(db.String(50), default="Pending")
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    meeting_id = db.Column(db.Integer, db.ForeignKey('meeting.id'), nullable=True)
    speaker_id = db.Column(db.String(50))  # Link to speaker who assigned task

class Conflict(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    issue = db.Column(db.Text)
    raised_by = db.Column(db.String(100))
    resolution = db.Column(db.Text)
    severity = db.Column(db.String(50), default="Medium")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    stance = db.Column(db.Text)  # Stance analysis results (JSON string)
    participants = db.Column(db.Text)  # Comma-separated list of speaker IDs involved
    topic = db.Column(db.String(200))  # Conflict topic/category
    meeting_id = db.Column(db.Integer, db.ForeignKey('meeting.id'), nullable=True)

# ---------- MODELS ----------
class MeetingSummary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    highlights = db.Column(db.Text, nullable=False)
    decisions = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "highlights": self.highlights.split("||"),
            "decisions": self.decisions.split("||"),
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S")
        }

# -----------------------------
# Serialization Helpers
# -----------------------------
def meeting_to_dict(m):
    return {
        "id": m.id,
        "title": m.title,
        "summary": m.summary,
        "date": m.date.isoformat() if m.date else None,
        "location": m.location,
        "host": m.host,
        "presentees": m.presentees,
        "absentees": m.absentees,
        "agenda": m.agenda,
        "adjournment_time": m.adjournment_time,
        "created_at": m.created_at.isoformat() if m.created_at else None,
        "key_decisions": m.key_decisions if isinstance(m.key_decisions, list) else [],
        "mom_file_path": m.mom_file_path if hasattr(m, 'mom_file_path') else None,
        "speakers": m.speakers if hasattr(m, 'speakers') else "",
        "transcript_segments": m.transcript_segments if hasattr(m, 'transcript_segments') else None
    }

def task_to_dict(t):
    return {
        "id": t.id,
        "person": t.person,
        "task": t.task,
        "deadline": t.deadline,
        "status": t.status,
        "notes": t.notes,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "meeting_id": t.meeting_id if hasattr(t, 'meeting_id') else None,
        "speaker_id": t.speaker_id if hasattr(t, 'speaker_id') else None
    }

def conflict_to_dict(c):
    return {
        "id": c.id,
        "issue": c.issue,
        "raised_by": c.raised_by,
        "resolution": c.resolution,
        "severity": c.severity,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "stance": c.stance if hasattr(c, 'stance') else "",
        "participants": c.participants if hasattr(c, 'participants') else "",
        "topic": c.topic if hasattr(c, 'topic') else "",
        "meeting_id": c.meeting_id if hasattr(c, 'meeting_id') else None
    }

# -----------------------------
# Utility: Robust JSON parsing and extraction helpers
# -----------------------------
def safe_json_parse(text):
    """
    Try to parse JSON from text. If direct parse fails, try to extract the first
    JSON array/object substring and parse that. Returns None on failure.
    """
    if not text or not isinstance(text, str):
        return None
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        # try to find a JSON array or object substring (non-greedy)
        match = re.search(r'(\[.*?\]|\{.*?\})', text, re.DOTALL)
        if match:
            candidate = match.group(1)
            try:
                return json.loads(candidate)
            except Exception:
                # try to fix common trailing commas
                candidate_fixed = re.sub(r',\s*([\]}])', r'\1', candidate)
                try:
                    return json.loads(candidate_fixed)
                except Exception:
                    return None
        return None

def parse_deadline(deadline_str: str) -> str:
    """Convert natural-language deadline into ISO date string."""
    if not deadline_str:
        return ""
    dt = dateparser.parse(deadline_str, settings={'PREFER_DATES_FROM': 'future'})
    return dt.date().isoformat() if dt else deadline_str

def extract_tasks_from_transcript_regex(transcript):
    """
    A heuristic fallback that scans the transcript for lines like:
    - 'John: I'll take X by Friday.'
    - 'Assign John to prepare the report by Oct 20.'
    Returns a list of dicts with keys: task_name, assigned_to, due_date, status
    """
    tasks = []

    # Pattern 1: "Name: ... (I'll|I will|I'll) <task> (by <deadline>)"
    pattern1 = re.compile(r'(?P<speaker>[A-Z][a-z]+):\s*(?:(?:I will|I\'ll|I am going to|I’ll)\s*)(?P<task>.*?)(?:\s+by\s+(?P<deadline>[\w\s\d,/-]+))?[.\n]', re.IGNORECASE)
    for m in pattern1.finditer(transcript + "\n"):
        speaker = m.group('speaker').strip()
        task_text = m.group('task').strip().rstrip('.')
        deadline = (m.group('deadline') or "").strip()
        if task_text:
            tasks.append({
                "task_name": task_text,
                "assigned_to": speaker,
                "due_date": parse_deadline(deadline) if deadline else "",
                "status": "pending"
            })

    # Pattern 2: "Assign <Name> to <task> (by <deadline>)"
    pattern2 = re.compile(r'assign(?:ed)?\s+(?:to\s+)?(?P<name>[A-Z][a-z]+)\s+(?:to\s+)?(?P<task>.*?)(?:\s+by\s+(?P<deadline>[\w\s\d,/-]+))?[.\n]', re.IGNORECASE)
    for m in pattern2.finditer(transcript + "\n"):
        name = m.group('name').strip()
        task_text = m.group('task').strip().rstrip('.')
        deadline = (m.group('deadline') or "").strip()
        if task_text:
            tasks.append({
                "task_name": task_text,
                "assigned_to": name,
                "due_date": parse_deadline(deadline) if deadline else "",
                "status": "pending"
            })

    # Pattern 3: "Can you <task>, <Name>?" or "<Name>, can you <task>?"
    pattern3 = re.compile(r'(?:(?P<name1>[A-Z][a-z]+),\s*can you\s*(?P<task1>.*?)[.\n])|(?:(?:can you)\s*(?P<task2>.*?)\s*,\s*(?P<name2>[A-Z][a-z]+)[.\n])', re.IGNORECASE)
    for m in pattern3.finditer(transcript + "\n"):
        name = (m.group('name1') or m.group('name2') or "").strip()
        task_text = (m.group('task1') or m.group('task2') or "").strip().rstrip('.')
        if task_text and name:
            tasks.append({
                "task_name": task_text,
                "assigned_to": name,
                "due_date": "",
                "status": "pending"
            })

    # deduplicate by (assigned_to, task_name)
    seen = set()
    deduped = []
    for t in tasks:
        key = (t.get("assigned_to", "").lower(), t.get("task_name", "").lower())
        if key not in seen:
            deduped.append(t)
            seen.add(key)
    return deduped

# -----------------------------
# API Blueprint & AI Models
# -----------------------------
api_bp = Blueprint("api", __name__, url_prefix="/api")
_whisper_model, _phi3_model = None, None
_whisperx_model, _align_model, _align_metadata, _diarize_model = None, None, None, None

def get_whisperx_models():
    """Initialize and return WhisperX models (ASR, alignment, diarization)."""
    global _whisperx_model, _align_model, _align_metadata, _diarize_model
    
    if whisperx is None or torch is None:
        raise RuntimeError("whisperx and torch not installed. Install `whisperx` and `torch` or disable transcription endpoints.")
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    compute_type = "float16" if device == "cuda" else "int8"
    language = "en"
    
    # Load ASR model
    if _whisperx_model is None:
        model_dir = os.path.join(os.path.dirname(__file__), "models", "MinuteMind", "faster-whisper")
        if not os.path.exists(model_dir):
            raise RuntimeError(f"Fine-tuned Whisper model not found at: {model_dir}")
        print("Loading WhisperX ASR model...")
        _whisperx_model = whisperx.load_model(model_dir, device, compute_type=compute_type, language=language)
        print("WhisperX ASR model loaded.")
    
    # Load alignment model
    if _align_model is None:
        print("Loading alignment model...")
        _align_model, _align_metadata = whisperx.load_align_model(language_code=language, device=device)
        print("Alignment model loaded.")
    
    # Load diarization model
    if _diarize_model is None:
        hf_token = os.getenv("HF_TOKEN")
        if not hf_token:
            print("Warning: HF_TOKEN not set. Speaker diarization may not work.")
        try:
            print("Loading diarization model...")
            _diarize_model = whisperx.DiarizationPipeline(use_auth_token=hf_token, device=device)
            print("Diarization model loaded.")
        except Exception as e:
            print(f"Warning: Could not load diarization model: {e}")
            _diarize_model = None
    
    return _whisperx_model, _align_model, _align_metadata, _diarize_model, device

def transcribe_with_whisperx(audio_path):
    """
    Transcribe audio using WhisperX with speaker diarization.
    Returns speaker-segmented transcript.
    """
    try:
        model, align_model, align_metadata, diarize_model, device = get_whisperx_models()
        
        # Load audio
        audio = whisperx.load_audio(audio_path)
        
        # Step 1: Transcribe
        print("Transcribing audio...")
        asr_result = model.transcribe(audio, batch_size=16)
        
        # Step 2: Align words
        print("Aligning words...")
        aligned_result = whisperx.align(asr_result["segments"], align_model, align_metadata, audio, device)
        
        # Step 3: Diarize speakers
        segments = []
        if diarize_model is not None:
            print("Diarizing speakers...")
            diarize_segments = diarize_model(audio)
            
            # Step 4: Assign speakers to words
            print("Assigning speakers...")
            result = whisperx.assign_word_speakers(diarize_segments, aligned_result)
            
            # Format segments
            for seg in result["segments"]:
                segments.append({
                    "start": round(seg["start"], 3),
                    "end": round(seg["end"], 3),
                    "speaker": seg.get("speaker", "UNKNOWN"),
                    "text": seg["text"].strip()
                })
        else:
            # Fallback: no diarization, just return segments without speaker labels
            print("Warning: Diarization not available, returning segments without speaker labels")
            for seg in aligned_result["segments"]:
                segments.append({
                    "start": round(seg["start"], 3),
                    "end": round(seg["end"], 3),
                    "speaker": "UNKNOWN",
                    "text": seg["text"].strip()
                })
        
        # Generate full text
        full_text = " ".join([seg["text"] for seg in segments])
        
        return {
            "segments": segments,
            "full_text": full_text
        }
    except Exception as e:
        print(f"WhisperX transcription error: {str(e)}")
        traceback.print_exc()
        raise

def get_whisper_model():
    """Legacy function for backward compatibility. Use transcribe_with_whisperx instead."""
    global _whisper_model
    if _whisper_model is None:
        model_dir = os.path.join(os.path.dirname(__file__), "models", "MinuteMind", "faster-whisper")
        if WhisperModel is None:
            raise RuntimeError("faster-whisper not installed. Install `faster-whisper` or disable transcription endpoints.")
        print("Loading Whisper model (legacy mode)...")
        _whisper_model = WhisperModel(model_dir, compute_type="int8", device="cpu")
        print("Whisper model loaded.")
    return _whisper_model

def get_phi3_model():
    global _phi3_model
    if _phi3_model is None:
        if Llama is None:
            raise RuntimeError("llama-cpp-python not installed. Install `llama-cpp-python` or disable LLM functionality.")
        gguf_path = os.path.join(os.path.dirname(__file__), "models", "phi3-finetuned-Q4_K_M.gguf")
        if not os.path.exists(gguf_path):
            raise RuntimeError(f"Phi-3 model file not found at: {gguf_path}")
        print(f"Loading Phi-3 model from: {gguf_path}")
        _phi3_model = Llama(model_path=gguf_path, n_ctx=4096, n_threads=max(4, os.cpu_count() or 4), verbose=False)
        print("Phi-3 model loaded.")
    return _phi3_model

# -----------------------------
# AI Endpoints
# -----------------------------
@api_bp.route("/transcribe", methods=["POST"])
def transcribe_audio():
    audio_path = None
    try:
        if "audio" not in request.files:
            return jsonify({"error": "audio file missing"}), 400
        audio_file = request.files["audio"]
        if not audio_file.filename:
            return jsonify({"error": "empty filename"}), 400

        with NamedTemporaryFile(delete=False, suffix=os.path.splitext(secure_filename(audio_file.filename))[1]) as tmp:
            audio_path = tmp.name
            audio_file.save(audio_path)

        print("Starting WhisperX transcription with speaker diarization...")
        
        # Use WhisperX for transcription with speaker diarization
        result = transcribe_with_whisperx(audio_path)
        
        # Apply temporal normalization
        from utils.temporal_normalization import normalize_temporal_segments
        normalized_segments = normalize_temporal_segments(result["segments"], merge_threshold=0.5)
        
        # Extract unique speakers
        unique_speakers = list(set([seg.get("speaker", "UNKNOWN") for seg in normalized_segments]))
        
        print(f"Transcription complete. Segments: {len(normalized_segments)}, Speakers: {len(unique_speakers)}")
        
        return jsonify({
            "segments": normalized_segments,
            "full_text": result["full_text"],
            "speakers": unique_speakers
        })
    except Exception as e:
        print(f"Transcription error: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        if audio_path and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
            except Exception:
                pass

# -----------------------------
# Internal helper function for transcript processing
# -----------------------------
def process_transcript_internal(transcript, llm):
    """Internal function to process transcript and extract tasks/conflicts."""
    tasks = []
    conflicts = []
    
    try:
        # Task extraction
        task_prompt = f"""
You are an AI assistant specialized in extracting ACTIONABLE TASKS from meeting transcripts.
Extract every task that was assigned or volunteered during the meeting. For each task provide:
- task_name : short description of the action to be taken
- assigned_to : name of the person responsible (if not explicitly mentioned, infer logically)
- due_date : any specific deadline or timeline string (leave empty if none)
- status : use "pending" unless explicitly completed

IMPORTANT: Output MUST be valid JSON array only (no extra commentary). Example output:
[
  {{"task_name":"Prepare quarterly budget", "assigned_to":"Rahul", "due_date":"2025-10-20", "status":"pending"}},
  {{"task_name":"Schedule next client review", "assigned_to":"Priya", "due_date":"", "status":"pending"}}
]

Transcript:
{transcript}
"""
        response = llm(prompt=task_prompt, max_tokens=1024, temperature=0.2)
        raw_text = ""
        if isinstance(response, dict):
            raw_text = response.get("choices", [{}])[0].get("text", "") if response.get("choices") else response.get("text", "") or ""
        elif isinstance(response, str):
            raw_text = response
        raw_text = (raw_text or "").strip()
        
        parsed = safe_json_parse(raw_text)
        if parsed and isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, dict):
                    task_name = item.get("task_name") or item.get("task") or ""
                    assigned_to = item.get("assigned_to") or item.get("assignee") or ""
                    due_date = item.get("due_date") or ""
                    status = item.get("status") or "pending"
                    if task_name:
                        tasks.append({
                            "task_name": task_name.strip(),
                            "assigned_to": assigned_to.strip(),
                            "due_date": parse_deadline(due_date) if due_date else "",
                            "status": status.strip()
                        })
        
        # Conflict extraction with stance analysis
        conflict_prompt = f"""
Analyze this meeting transcript for conflicts and disagreements using stance analysis.
For each conflict, identify:
1. The issue or topic of disagreement
2. Speakers involved and their positions (stance analysis)
3. Severity level (Low, Medium, High)
4. Whether resolution was reached

Return JSON format:
[{{"issue": "description", "raised_by": "speaker name", "participants": ["speaker1", "speaker2"], "stance": "analysis of positions", "severity": "Low/Medium/High", "topic": "category"}}]

Transcript:
{transcript}
"""
        response_conflict = llm(prompt=conflict_prompt, max_tokens=1024, temperature=0.3)
        raw_conflict_text = ""
        if isinstance(response_conflict, dict):
            raw_conflict_text = response_conflict.get("choices", [{}])[0].get("text", "") if response_conflict.get("choices") else response_conflict.get("text", "") or ""
        elif isinstance(response_conflict, str):
            raw_conflict_text = response_conflict
        raw_conflict_text = (raw_conflict_text or "").strip()
        
        parsed_conflicts = safe_json_parse(raw_conflict_text)
        if isinstance(parsed_conflicts, list):
            conflicts = parsed_conflicts
        
    except Exception as e:
        print(f"Error in process_transcript_internal: {e}")
        traceback.print_exc()
    
    return {"tasks": tasks, "conflicts": conflicts}

# -----------------------------
# Process Transcript
# -----------------------------
@api_bp.route("/process_transcript", methods=["POST"])
def process_transcript():
    try:
        data = request.get_json() or {}
        transcript = data.get("transcript", "")
        if not transcript:
            return jsonify({"error": "No transcript provided"}), 400

        llm = get_phi3_model()

        # --- Task Extraction ---
        print("Extracting tasks with Phi-3...")

        # Stronger instruction prompt with examples; ask for strict JSON
        task_prompt = f"""
You are an AI assistant specialized in extracting ACTIONABLE TASKS from meeting transcripts.
Extract every task that was assigned or volunteered during the meeting. For each task provide:
- task_name : short description of the action to be taken
- assigned_to : name of the person responsible (if not explicitly mentioned, infer logically)
- due_date : any specific deadline or timeline string (leave empty if none)
- status : use "pending" unless explicitly completed

IMPORTANT: Output MUST be valid JSON array only (no extra commentary). Example output:
[
  {{"task_name":"Prepare quarterly budget", "assigned_to":"Rahul", "due_date":"2025-10-20", "status":"pending"}},
  {{"task_name":"Schedule next client review", "assigned_to":"Priya", "due_date":"", "status":"pending"}}
]

Transcript:
{transcript}
"""

        # Call the model
        response = llm(prompt=task_prompt, max_tokens=1024, temperature=0.2)
        raw_text = ""
        # Llama/other runtimes may return different structures — try to normalize
        if isinstance(response, dict):
            raw_text = response.get("choices", [{}])[0].get("text", "") if response.get("choices") else response.get("text", "") or ""
        elif isinstance(response, str):
            raw_text = response
        else:
            # attempt attribute access
            raw_text = getattr(response, "text", "") or ""

        raw_text = (raw_text or "").strip()
        print("🧠 Raw Phi-3 Task Output (first 1000 chars):")
        print(raw_text[:1000])

        # Try robust JSON parse
        parsed = safe_json_parse(raw_text)
        tasks = []
        if parsed and isinstance(parsed, list):
            # Normalize parsed entries to expected keys
            for item in parsed:
                if not isinstance(item, dict):
                    continue
                task_name = item.get("task_name") or item.get("task") or item.get("task_description") or ""
                assigned_to = item.get("assigned_to") or item.get("assignee") or item.get("person") or ""
                due_date = item.get("due_date") or item.get("deadline") or ""
                status = item.get("status") or "pending"
                if task_name:
                    tasks.append({
                        "task_name": task_name.strip(),
                        "assigned_to": assigned_to.strip() if isinstance(assigned_to, str) else assigned_to,
                        "due_date": parse_deadline(due_date) if isinstance(due_date, str) else due_date,
                        "status": status.strip() if isinstance(status, str) else status
                    })
        else:
            # Fallback 1: try to extract JSON-like lines from raw_text
            fallback_parsed = []
            lines = raw_text.splitlines()
            json_like_items = []
            for ln in lines:
                ln = ln.strip().rstrip(',')
                if ln.startswith("{") and ln.endswith("}"):
                    json_like_items.append(ln)
            if json_like_items:
                json_like = "[" + ",".join(json_like_items) + "]"
                candidate = safe_json_parse(json_like)
                if isinstance(candidate, list):
                    fallback_parsed = candidate

            if fallback_parsed:
                for item in fallback_parsed:
                    if isinstance(item, dict):
                        task_name = item.get("task_name") or item.get("task") or item.get("task_description") or ""
                        assigned_to = item.get("assigned_to") or item.get("assignee") or item.get("person") or ""
                        due_date = item.get("due_date") or item.get("deadline") or ""
                        status = item.get("status") or "pending"
                        if task_name:
                            tasks.append({
                                "task_name": task_name.strip(),
                                "assigned_to": assigned_to.strip() if isinstance(assigned_to, str) else assigned_to,
                                "due_date": parse_deadline(due_date) if isinstance(due_date, str) else due_date,
                                "status": status.strip() if isinstance(status, str) else status
                            })

        # Fallback 2: if still no tasks, use regex heuristics on the transcript
        if not tasks:
            print("No tasks from LLM JSON parse — trying regex heuristics on transcript.")
            heuristic_tasks = extract_tasks_from_transcript_regex(transcript)
            if heuristic_tasks:
                tasks.extend(heuristic_tasks)

        # Fallback 3: retry LLM with a simplified explicit format request (if still empty)
        if not tasks:
            print("Retrying LLM with simplified prompt.")
            retry_prompt = f"""
List tasks from the transcript. For each line output EXACTLY as CSV:
task_name ||| assigned_to ||| due_date

Transcript:
{transcript}

Example:
Prepare quarterly budget ||| Rahul ||| 2025-10-20
"""
            retry_resp = llm(prompt=retry_prompt, max_tokens=512, temperature=0.1)
            retry_text = ""
            if isinstance(retry_resp, dict):
                retry_text = retry_resp.get("choices", [{}])[0].get("text", "") if retry_resp.get("choices") else retry_resp.get("text", "") or ""
            elif isinstance(retry_resp, str):
                retry_text = retry_resp
            retry_text = (retry_text or "").strip()
            print("Retry raw output:", retry_text[:800])
            # parse retry CSV-like lines
            for ln in retry_text.splitlines():
                ln = ln.strip()
                if not ln:
                    continue
                parts = [p.strip() for p in re.split(r'\s*\|\|\|\s*', ln)]
                if len(parts) >= 2:
                    task_name = parts[0]
                    assigned_to = parts[1]
                    due_date = parts[2] if len(parts) >= 3 else ""
                    tasks.append({
                        "task_name": task_name,
                        "assigned_to": assigned_to,
                        "due_date": parse_deadline(due_date) if due_date else "",
                        "status": "pending"
                    })

        print(f"✅ Tasks extracted: {len(tasks)}")

        # --- Save tasks to DB ---
        saved_tasks = []
        for t in tasks:
            new_task = Task(
                person=(t.get("assigned_to", "Unassigned") or "Unassigned"),
                task=(t.get("task_name", "Untitled Task") or "Untitled Task"),
                deadline=(t.get("due_date", "Not Mentioned") or "Not Mentioned"),
                status=(t.get("status", "Pending") or "Pending"),
                notes=""
            )
            db.session.add(new_task)
            saved_tasks.append(new_task)
        db.session.commit()

        # --- Conflict Extraction with Stance Analysis ---
        print("Extracting conflicts with stance analysis...")
        conflict_prompt = f"""
Analyze this meeting transcript for conflicts and disagreements using stance analysis.
For each conflict, identify:
1. The issue or topic of disagreement
2. Speakers involved and their positions (stance analysis)
3. Severity level (Low, Medium, High)
4. Whether resolution was reached

Return JSON format:
[{{"issue": "description", "raised_by": "speaker name", "participants": ["speaker1", "speaker2"], "stance": "analysis of positions", "severity": "Low/Medium/High", "topic": "category"}}]

Transcript:
{transcript}
"""
        response_conflict = llm(prompt=conflict_prompt, max_tokens=1024, temperature=0.3)
        raw_conflict_text = ""
        if isinstance(response_conflict, dict):
            raw_conflict_text = response_conflict.get("choices", [{}])[0].get("text", "") if response_conflict.get("choices") else response_conflict.get("text", "") or ""
        elif isinstance(response_conflict, str):
            raw_conflict_text = response_conflict
        raw_conflict_text = (raw_conflict_text or "").strip()
        print(f"Raw conflict output: {raw_conflict_text[:300]}")

        conflicts = []
        if raw_conflict_text:
            parsed_conflicts = safe_json_parse(raw_conflict_text)
            if isinstance(parsed_conflicts, list):
                conflicts = parsed_conflicts
            else:
                # simple heuristic search in transcript
                conflict_matches = re.findall(
                    r"(?i)\b(disagree|conflict|argument|issue|not\s+agree)\b.*?[.!\n]",
                    transcript
                )
                conflicts = [{"issue": m.strip(), "raised_by": "", "participants": [], "stance": "", "severity": "Medium", "topic": ""} for m in conflict_matches]

        # --- Save conflicts to DB ---
        saved_conflicts = []
        for c in conflicts:
            participants_str = ", ".join(c.get("participants", [])) if isinstance(c.get("participants"), list) else str(c.get("participants", ""))
            stance_str = json.dumps(c.get("stance", "")) if isinstance(c.get("stance", dict)) else str(c.get("stance", ""))
            
            new_conflict = Conflict(
                issue=c.get("issue", "") or "",
                raised_by=c.get("raised_by", "") or "",
                resolution="",
                severity=c.get("severity", "Medium") if isinstance(c, dict) else "Medium",
                participants=participants_str,
                stance=stance_str,
                topic=c.get("topic", "") if isinstance(c, dict) else ""
            )
            db.session.add(new_conflict)
            saved_conflicts.append(new_conflict)
        db.session.commit()

        return jsonify({
            "message": "Transcript processed successfully",
            "tasks_extracted": len(saved_tasks),
            "conflicts_extracted": len(saved_conflicts),
            "tasks": [task_to_dict(t) for t in Task.query.order_by(Task.created_at.desc()).limit(10).all()],
            "conflicts": [conflict_to_dict(c) for c in Conflict.query.order_by(Conflict.created_at.desc()).limit(10).all()]
        }), 201

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# -----------------------------
# Unified endpoint for frontend
# -----------------------------
@api_bp.route("/transcribe_and_summarize", methods=["POST"])
def transcribe_and_summarize():
    if "audio" not in request.files:
        return jsonify({"error": "audio file missing"}), 400

    audio_file = request.files["audio"]
    if not audio_file.filename:
        return jsonify({"error": "empty filename"}), 400

    audio_path = None
    try:
        # Step 1: Save temp audio file
        with NamedTemporaryFile(delete=False, suffix=os.path.splitext(secure_filename(audio_file.filename))[1]) as tmp:
            audio_path = tmp.name
            audio_file.save(audio_path)

        # Step 2: Transcribe audio with WhisperX (speaker diarization)
        print("Transcribing with WhisperX...")
        result = transcribe_with_whisperx(audio_path)
        
        # Apply temporal normalization
        from utils.temporal_normalization import normalize_temporal_segments
        normalized_segments = normalize_temporal_segments(result["segments"], merge_threshold=0.5)
        
        # Format transcript with speaker labels for Phi-3
        speaker_transcript = ""
        for seg in normalized_segments:
            speaker = seg.get("speaker", "UNKNOWN")
            text = seg.get("text", "")
            speaker_transcript += f"{speaker}: {text}\n"
        
        full_transcript = result["full_text"]
        unique_speakers = list(set([seg.get("speaker", "UNKNOWN") for seg in normalized_segments]))

        # Step 3: Generate summary using Phi-3 with safe chunking
        llm = get_phi3_model()
        MAX_CHARS = 3000

        def chunk_text(text, max_chars=MAX_CHARS):
            return [text[i:i+max_chars] for i in range(0, len(text), max_chars)]

        transcript_chunks = chunk_text(speaker_transcript)
        chunk_summaries = []

        for chunk in transcript_chunks:
            prompt = f"""
Summarize the following meeting transcript in 5-6 sentences. Note the speaker labels to understand who said what:

{chunk}
"""
            out = llm(
                prompt=prompt,
                max_tokens=1024,
                temperature=0.4,
                stop=None
            )
            # normalize response
            chunk_text_out = ""
            if isinstance(out, dict):
                chunk_text_out = out.get("choices", [{}])[0].get("text", "") if out.get("choices") else out.get("text", "") or ""
            elif isinstance(out, str):
                chunk_text_out = out
            chunk_text_out = (chunk_text_out or "").strip()
            if chunk_text_out:
                chunk_summaries.append(chunk_text_out)

        # Combine chunk summaries into one summary
        summary = " ".join(chunk_summaries)
        
        # Try to create meeting and generate MoM if form data is provided
        mom_file_info = None
        meeting_id_created = None
        
        try:
            form_data = request.form if request.form else {}
            json_data = request.get_json(silent=True) or {}
            all_data = {**form_data, **json_data}
            
            # Only create meeting if title or other meeting data is provided
            if all_data.get("title") or all_data.get("location") or all_data.get("host"):
                # Parse date
                meeting_date = date.today()
                if all_data.get("date"):
                    try:
                        if isinstance(all_data["date"], str):
                            meeting_date = datetime.strptime(all_data["date"], "%Y-%m-%d").date()
                    except:
                        pass
                
                # Create meeting
                meeting = Meeting(
                    title=all_data.get("title", f"Meeting {datetime.now(timezone.utc).isoformat()}"),
                    summary=summary,
                    key_decisions=[],
                    date=meeting_date,
                    location=all_data.get("location", ""),
                    host=all_data.get("host", ""),
                    presentees=all_data.get("presentees", ""),
                    absentees=all_data.get("absentees", ""),
                    agenda=all_data.get("agenda", ""),
                    adjournment_time=all_data.get("adjournment_time", ""),
                    transcript_segments=normalized_segments,
                    speakers=", ".join(unique_speakers)
                )
                db.session.add(meeting)
                db.session.commit()
                meeting_id_created = meeting.id
                
                # Extract and save tasks/conflicts
                process_result = process_transcript_internal(speaker_transcript, llm)
                extracted_tasks = process_result.get("tasks", [])
                extracted_conflicts = process_result.get("conflicts", [])
                
                for task_data in extracted_tasks:
                    task = Task(
                        person=task_data.get("assigned_to", "Unassigned"),
                        task=task_data.get("task_name", "Untitled Task"),
                        deadline=task_data.get("due_date", "Not Mentioned"),
                        status=task_data.get("status", "Pending"),
                        notes="",
                        meeting_id=meeting_id_created
                    )
                    db.session.add(task)
                
                for conflict_data in extracted_conflicts:
                    participants_str = ", ".join(conflict_data.get("participants", [])) if isinstance(conflict_data.get("participants"), list) else str(conflict_data.get("participants", ""))
                    stance_str = json.dumps(conflict_data.get("stance", "")) if isinstance(conflict_data.get("stance", dict)) else str(conflict_data.get("stance", ""))
                    
                    conflict = Conflict(
                        issue=conflict_data.get("issue", "") or "",
                        raised_by=conflict_data.get("raised_by", "") or "",
                        resolution="",
                        severity=conflict_data.get("severity", "Medium"),
                        participants=participants_str,
                        stance=stance_str,
                        topic=conflict_data.get("topic", ""),
                        meeting_id=meeting_id_created
                    )
                    db.session.add(conflict)
                
                db.session.commit()
                
                # Generate MoM
                try:
                    from utils.mom_generator import generate_mom_document
                    meeting_tasks = Task.query.filter_by(meeting_id=meeting_id_created).all()
                    meeting_conflicts = Conflict.query.filter_by(meeting_id=meeting_id_created).all()
                    
                    mom_file_path = generate_mom_document(
                        meeting_data=meeting,
                        tasks=meeting_tasks,
                        conflicts=meeting_conflicts,
                        transcript_segments=normalized_segments
                    )
                    
                    meeting.mom_file_path = mom_file_path
                    db.session.commit()
                    
                    mom_filename = os.path.basename(mom_file_path)
                    mom_file_info = {
                        "path": mom_file_path,
                        "download_url": f"/api/download/{mom_filename}",
                        "filename": mom_filename
                    }
                except Exception as e:
                    print(f"Warning: Failed to generate MoM in transcribe_and_summarize: {e}")
                    traceback.print_exc()
        except Exception as e:
            print(f"Warning: Failed to create meeting in transcribe_and_summarize: {e}")
            traceback.print_exc()

        response_data = {
            "transcript": full_transcript,
            "summary": summary,
            "segments": normalized_segments,
            "speakers": unique_speakers
        }
        
        if meeting_id_created:
            response_data["meeting_id"] = meeting_id_created
        
        if mom_file_info:
            response_data["mom_file"] = mom_file_info

        return jsonify(response_data)

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

    finally:
        if audio_path and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
            except Exception:
                pass

# -----------------------------
# Meeting Summary + Key Decisions Endpoint (POST)
# -----------------------------
@api_bp.route("/summary", methods=["POST"])
def summary():
    if "audio" not in request.files:
        return jsonify({"error": "audio file missing"}), 400

    audio_file = request.files["audio"]
    if not audio_file.filename:
        return jsonify({"error": "empty filename"}), 400

    audio_path = None
    try:
        # Step 1: Save temp audio file
        with NamedTemporaryFile(delete=False, suffix=os.path.splitext(secure_filename(audio_file.filename))[1]) as tmp:
            audio_path = tmp.name
            audio_file.save(audio_path)

        # Step 2: Transcribe audio with WhisperX (speaker diarization)
        print("Transcribing with WhisperX...")
        result = transcribe_with_whisperx(audio_path)
        
        # Apply temporal normalization
        from utils.temporal_normalization import normalize_temporal_segments
        normalized_segments = normalize_temporal_segments(result["segments"], merge_threshold=0.5)
        
        # Format transcript with speaker labels for Phi-3
        speaker_transcript = ""
        for seg in normalized_segments:
            speaker = seg.get("speaker", "UNKNOWN")
            text = seg.get("text", "")
            speaker_transcript += f"{speaker}: {text}\n"
        
        full_transcript = result["full_text"]
        unique_speakers = list(set([seg.get("speaker", "UNKNOWN") for seg in normalized_segments]))

        # Step 3: Generate summary and key decisions using Phi-3
        llm = get_phi3_model()
        MAX_CHARS = 3000

        def chunk_text(text, max_chars=MAX_CHARS):
            return [text[i:i+max_chars] for i in range(0, len(text), max_chars)]

        transcript_chunks = chunk_text(speaker_transcript)
        summaries, decisions = [], []

        for chunk in transcript_chunks:
            prompt = f"""
You are an AI assistant. 

1️⃣ Summarize the following meeting transcript in 3-4 lines under 'Meeting Highlight'.
2️⃣ Extract all Key Decisions as a list under 'Key Decisions'. Include speaker attribution when possible.

Transcript:
{chunk}

Return output as JSON with keys: 'summary' and 'key_decisions'.
"""
            out = llm(prompt=prompt, max_tokens=1024, temperature=0.3)
            text = ""
            if isinstance(out, dict):
                text = out.get("choices", [{}])[0].get("text", "") if out.get("choices") else out.get("text", "") or ""
            elif isinstance(out, str):
                text = out
            text = (text or "").strip()

            try:
                parsed = json.loads(text)
                summaries.append(parsed.get("summary", ""))
                chunk_decisions = parsed.get("key_decisions", [])
                if isinstance(chunk_decisions, list):
                    decisions.extend(chunk_decisions)
            except Exception:
                # fallback if parsing fails
                if text:
                    summaries.append(text)

        final_summary = " ".join(summaries).strip()
        
        # Step 4: Extract tasks and conflicts for MoM generation
        print("Extracting tasks and conflicts for MoM...")
        # Process transcript to extract tasks and conflicts
        process_result = process_transcript_internal(speaker_transcript, llm)
        extracted_tasks = process_result.get("tasks", [])
        extracted_conflicts = process_result.get("conflicts", [])
        
        # Save tasks and conflicts to database with meeting_id (will be linked after meeting is created)
        # Store them temporarily to link after meeting creation
        temp_tasks = []
        temp_conflicts = []
        
        for task_data in extracted_tasks:
            temp_tasks.append({
                "person": task_data.get("assigned_to", "Unassigned"),
                "task": task_data.get("task_name", "Untitled Task"),
                "deadline": task_data.get("due_date", "Not Mentioned"),
                "status": task_data.get("status", "Pending"),
                "notes": ""
            })
        
        for conflict_data in extracted_conflicts:
            participants_str = ", ".join(conflict_data.get("participants", [])) if isinstance(conflict_data.get("participants"), list) else str(conflict_data.get("participants", ""))
            stance_str = json.dumps(conflict_data.get("stance", "")) if isinstance(conflict_data.get("stance", dict)) else str(conflict_data.get("stance", ""))
            
            temp_conflicts.append({
                "issue": conflict_data.get("issue", "") or "",
                "raised_by": conflict_data.get("raised_by", "") or "",
                "resolution": "",
                "severity": conflict_data.get("severity", "Medium"),
                "participants": participants_str,
                "stance": stance_str,
                "topic": conflict_data.get("topic", "")
            })

        # -----------------------------
        # Persist the summary and key decisions into the Meeting DB
        # -----------------------------
        try:
            meeting_id = None

            # 1) Check form data
            if request.form and request.form.get("meeting_id"):
                try:
                    meeting_id = int(request.form.get("meeting_id"))
                except Exception:
                    meeting_id = None

            # 2) Check JSON body or query params
            if meeting_id is None:
                payload = request.get_json(silent=True) or {}
                mid = payload.get("meeting_id") or request.args.get("meeting_id")
                if mid:
                    try:
                        meeting_id = int(mid)
                    except Exception:
                        meeting_id = None

            # Get meeting details from form or JSON
            form_data = request.form if request.form else {}
            json_data = request.get_json(silent=True) or {}
            all_data = {**form_data, **json_data}
            
            # Parse date if provided
            meeting_date = date.today()
            if all_data.get("date"):
                try:
                    if isinstance(all_data["date"], str):
                        meeting_date = datetime.strptime(all_data["date"], "%Y-%m-%d").date()
                    else:
                        meeting_date = all_data["date"]
                except:
                    meeting_date = date.today()
            
            # Fetch existing meeting or create new
            if meeting_id:
                meeting = Meeting.query.get(meeting_id)
                if meeting:
                    meeting.summary = final_summary
                    meeting.key_decisions = decisions if isinstance(decisions, list) else []
                    meeting.date = meeting.date or meeting_date
                    meeting.transcript_segments = normalized_segments
                    meeting.speakers = ", ".join(unique_speakers)
                    # Update other fields if provided
                    if all_data.get("title"):
                        meeting.title = all_data["title"]
                    if all_data.get("location"):
                        meeting.location = all_data["location"]
                    if all_data.get("host"):
                        meeting.host = all_data["host"]
                    if all_data.get("presentees"):
                        meeting.presentees = all_data["presentees"]
                    if all_data.get("absentees"):
                        meeting.absentees = all_data["absentees"]
                    if all_data.get("agenda"):
                        meeting.agenda = all_data["agenda"]
                    if all_data.get("adjournment_time"):
                        meeting.adjournment_time = all_data["adjournment_time"]
                else:
                    # Meeting ID provided but not found → create new
                    new_title = all_data.get("title") or f"Meeting {datetime.now(timezone.utc).isoformat()}"
                    meeting = Meeting(
                        title=new_title,
                        summary=final_summary,
                        key_decisions=decisions if isinstance(decisions, list) else [],
                        date=meeting_date,
                        location=all_data.get("location", ""),
                        host=all_data.get("host", ""),
                        presentees=all_data.get("presentees", ""),
                        absentees=all_data.get("absentees", ""),
                        agenda=all_data.get("agenda", ""),
                        adjournment_time=all_data.get("adjournment_time", ""),
                        transcript_segments=normalized_segments,
                        speakers=", ".join(unique_speakers)
                    )
                    db.session.add(meeting)
            else:
                # No meeting_id → create new meeting
                new_title = all_data.get("title") or f"Meeting {datetime.now(timezone.utc).isoformat()}"
                meeting = Meeting(
                    title=new_title,
                    summary=final_summary,
                    key_decisions=decisions if isinstance(decisions, list) else [],
                    date=meeting_date,
                    location=all_data.get("location", ""),
                    host=all_data.get("host", ""),
                    presentees=all_data.get("presentees", ""),
                    absentees=all_data.get("absentees", ""),
                    agenda=all_data.get("agenda", ""),
                    adjournment_time=all_data.get("adjournment_time", ""),
                    transcript_segments=normalized_segments,
                    speakers=", ".join(unique_speakers)
                )
                db.session.add(meeting)

            db.session.commit()
            saved_meeting_id = meeting.id if meeting else None
            
            # Step 5: Save tasks and conflicts with meeting_id
            if saved_meeting_id:
                for task_data in temp_tasks:
                    task = Task(
                        person=task_data["person"],
                        task=task_data["task"],
                        deadline=task_data["deadline"],
                        status=task_data["status"],
                        notes=task_data["notes"],
                        meeting_id=saved_meeting_id
                    )
                    db.session.add(task)
                
                for conflict_data in temp_conflicts:
                    conflict = Conflict(
                        issue=conflict_data["issue"],
                        raised_by=conflict_data["raised_by"],
                        resolution=conflict_data["resolution"],
                        severity=conflict_data["severity"],
                        participants=conflict_data["participants"],
                        stance=conflict_data["stance"],
                        topic=conflict_data["topic"],
                        meeting_id=saved_meeting_id
                    )
                    db.session.add(conflict)
                
                db.session.commit()
            
            # Step 6: Auto-generate MoM document
            mom_file_path = None
            mom_download_url = None
            if saved_meeting_id:
                try:
                    print("Auto-generating MoM document...")
                    from utils.mom_generator import generate_mom_document
                    
                    # Get tasks and conflicts for this meeting
                    meeting_tasks = Task.query.filter_by(meeting_id=saved_meeting_id).all()
                    meeting_conflicts = Conflict.query.filter_by(meeting_id=saved_meeting_id).all()
                    
                    # Generate MoM
                    mom_file_path = generate_mom_document(
                        meeting_data=meeting,
                        tasks=meeting_tasks,
                        conflicts=meeting_conflicts,
                        transcript_segments=normalized_segments
                    )
                    
                    # Update meeting with MoM file path
                    meeting.mom_file_path = mom_file_path
                    db.session.commit()
                    
                    # Generate download URL
                    mom_filename = os.path.basename(mom_file_path)
                    mom_download_url = f"/api/download/{mom_filename}"
                    print(f"MoM generated successfully: {mom_file_path}")
                    
                except Exception as e:
                    print(f"Warning: Failed to generate MoM document: {e}")
                    traceback.print_exc()

        except Exception as e:
            print("Warning: failed to save summary/key_decisions to DB:", e)
            traceback.print_exc()
            saved_meeting_id = None
            mom_file_path = None
            mom_download_url = None

        response_data = {
            "transcript": full_transcript,
            "meeting_highlight": final_summary,
            "key_decisions": decisions,
            "meeting_id": saved_meeting_id,
            "segments": normalized_segments,
            "speakers": unique_speakers
        }
        
        if mom_download_url:
            response_data["mom_file"] = {
                "path": mom_file_path,
                "download_url": mom_download_url,
                "filename": os.path.basename(mom_file_path) if mom_file_path else None
            }
        
        return jsonify(response_data)

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

    finally:
        if audio_path and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
            except Exception:
                pass

# ------------------------------------------------------------------
# 🔽🔽🔽 NEW: GET /api/summary (aggregated highlights & decisions)
# ------------------------------------------------------------------
@api_bp.route("/summary", methods=["GET"])
def get_summary_data():
    """
    Provides aggregated highlights and key decisions from ALL meetings.
    This is for the main "Summary" dashboard page in React.
    """
    try:
        all_meetings = Meeting.query.order_by(Meeting.created_at.desc()).all()

        all_highlights = []
        all_decisions = []

        for meeting in all_meetings:
            if meeting.summary:
                all_highlights.append(meeting.summary)

            if meeting.key_decisions and isinstance(meeting.key_decisions, list):
                all_decisions.extend(meeting.key_decisions)

        return jsonify({
            'highlights': all_highlights,
            'decisions': all_decisions
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
# ------------------------------------------------------------------
# 🔼🔼🔼 END NEW
# ------------------------------------------------------------------

from datetime import datetime

@api_bp.route("/meetings", methods=["POST"])
def post_meeting():
    data = request.get_json(silent=True) or {}

    # ✅ Convert string to date if necessary
    date_str = data.get("date")
    meeting_date = None
    if date_str:
        try:
            meeting_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            meeting_date = None  # fallback if wrong format

    meeting = Meeting(
        title=data.get("title"),
        summary=data.get("summary"),
        date=meeting_date,  # ✅ use parsed date object
        location=data.get("location"),
        host=data.get("host"),
        presentees=data.get("presentees"),
        absentees=data.get("absentees"),
        agenda=data.get("agenda"),
        adjournment_time=data.get("adjournment_time"),
    )

    db.session.add(meeting)
    db.session.commit()
    return jsonify(meeting_to_dict(meeting)), 201


# -----------------------------
# Meeting CRUD Endpoints
# -----------------------------
@api_bp.route("/meetings", methods=["GET"])
def get_meetings():
    meetings = Meeting.query.order_by(Meeting.created_at.desc()).all()
    return jsonify([meeting_to_dict(m) for m in meetings])

@api_bp.route("/meetings", methods=["POST"])
def post_meeting():
    data = request.get_json(silent=True) or {}
    meeting = Meeting(
        title=data.get("title"),
        summary=data.get("summary"),
        date=data.get("date"),
        location=data.get("location"),
        host=data.get("host"),
        presentees=data.get("presentees"),
        absentees=data.get("absentees"),
        agenda=data.get("agenda"),
        adjournment_time=data.get("adjournment_time")
    )
    db.session.add(meeting)
    db.session.commit()
    return jsonify(meeting_to_dict(meeting)), 201

# -----------------------------
# Task CRUD Endpoints
# -----------------------------
@api_bp.route("/tasks", methods=["GET"])
def get_tasks():
    return jsonify([task_to_dict(t) for t in Task.query.order_by(Task.created_at.desc()).all()])

@api_bp.route("/tasks", methods=["POST"])
def post_task():
    data = request.get_json(silent=True) or {}
    task = Task(
        person=data.get("person", ""),
        task=data.get("task", ""),
        deadline=data.get("deadline", "Not Mentioned"),
        notes=data.get("notes", "")
    )
    db.session.add(task)
    db.session.commit()
    return jsonify(task_to_dict(task)), 201

@api_bp.route("/tasks/<int:id>", methods=["PATCH"])
def patch_task(id):
    task = Task.query.get_or_404(id)
    data = request.get_json(silent=True) or {}
    for key in ["person", "task", "deadline", "status", "notes"]:
        if key in data:
            setattr(task, key, data[key])
    db.session.commit()
    return jsonify(task_to_dict(task))

# -----------------------------
# Conflict CRUD Endpoints
# -----------------------------
@api_bp.route("/conflicts", methods=["GET"])
def get_conflicts():
    return jsonify([conflict_to_dict(c) for c in Conflict.query.order_by(Conflict.created_at.desc()).all()])

@api_bp.route("/conflicts", methods=["POST"])
def post_conflict():
    data = request.get_json(silent=True) or {}
    conflict = Conflict(
        issue=data.get("issue", ""),
        raised_by=data.get("raised_by", ""),
        resolution=data.get("resolution", ""),
        severity=data.get("severity", "Medium")
    )
    db.session.add(conflict)
    db.session.commit()
    return jsonify(conflict_to_dict(conflict)), 201

@api_bp.route("/conflicts/<int:id>", methods=["PATCH"])
def patch_conflict(id):
    conflict = Conflict.query.get_or_404(id)
    data = request.get_json(silent=True) or {}
    for key in ["issue", "raised_by", "resolution", "severity"]:
        if key in data:
            setattr(conflict, key, data[key])
    db.session.commit()
    return jsonify(conflict_to_dict(conflict))

# -----------------------------
# Meeting Summary Endpoints
# -----------------------------
@api_bp.route("/summary", methods=["GET"])
def get_latest_summary():
    """Return the most recent meeting summary."""
    latest_summary = MeetingSummary.query.order_by(MeetingSummary.created_at.desc()).first()
    if latest_summary:
        return jsonify(latest_summary.to_dict()), 200
    else:
        return jsonify({"highlights": [], "decisions": []}), 200


@api_bp.route("/summary", methods=["POST"])
def add_summary():
    """Add a new meeting summary (for testing or UI posting)."""
    data = request.get_json(silent=True) or {}
    highlights = "||".join(data.get("highlights", []))
    decisions = "||".join(data.get("decisions", []))
    new_summary = MeetingSummary(highlights=highlights, decisions=decisions)
    db.session.add(new_summary)
    db.session.commit()
    return jsonify({"message": "Summary added successfully"}), 201


# -------------------------------------------------------
# TEMP ROUTE: Add dummy meeting summary for testing
# -------------------------------------------------------
@api_bp.route("/add_dummy_summary", methods=["POST"])
def add_dummy_summary():
    """Insert a dummy summary record into MeetingSummary for testing."""
    try:
        dummy_summary = MeetingSummary(
            highlights="Discussed UI changes||Budget approval||Marketing plan",
            decisions="Launch beta next week||Reduce cost by 10%"
        )
        db.session.add(dummy_summary)
        db.session.commit()
        return jsonify({"message": "Dummy summary added!"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------------------------------------------
# MoM Document Generation Endpoint
# -------------------------------------------------------
@api_bp.route("/generate_mom/<int:meeting_id>", methods=["POST"])
def generate_mom(meeting_id):
    """Generate MoM document for a specific meeting."""
    try:
        meeting = Meeting.query.get_or_404(meeting_id)
        
        # Get tasks and conflicts for this meeting
        tasks = Task.query.filter_by(meeting_id=meeting_id).all()
        conflicts = Conflict.query.filter_by(meeting_id=meeting_id).all()
        
        # Get transcript segments
        transcript_segments = meeting.transcript_segments if hasattr(meeting, 'transcript_segments') and meeting.transcript_segments else None
        
        # Generate MoM document
        from utils.mom_generator import generate_mom_document
        mom_file_path = generate_mom_document(
            meeting_data=meeting,
            tasks=tasks,
            conflicts=conflicts,
            transcript_segments=transcript_segments
        )
        
        # Update meeting with MoM file path
        meeting.mom_file_path = mom_file_path
        db.session.commit()
        
        # Generate download URL
        mom_filename = os.path.basename(mom_file_path)
        mom_download_url = f"/api/download/{mom_filename}"
        
        return jsonify({
            "message": "MoM document generated successfully",
            "file_path": mom_file_path,
            "download_url": mom_download_url,
            "filename": mom_filename
        }), 200
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# -------------------------------------------------------
# File Download Route (for MoM documents)
# -------------------------------------------------------
from flask import send_from_directory, jsonify
import os

FILES_DIR = os.path.join(os.getcwd(), "files")

@api_bp.route("/download/<filename>", methods=["GET"])
def download_file(filename):
    """Allow users to download MoM documents by filename."""
    try:
        return send_from_directory(FILES_DIR, filename, as_attachment=True)
    except FileNotFoundError:
        return jsonify({"error": "File not found"}), 404

# -----------------------------
# Serve frontend static files
# -----------------------------
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    # fallback to index.html for SPA
    return send_from_directory(app.static_folder, "index.html")

# -----------------------------
# Register Blueprint
# -----------------------------
app.register_blueprint(api_bp, url_prefix="/api")
# -----------------------------
# Init DB
# -----------------------------
with app.app_context():
    db.create_all()

# -----------------------------
# Run Server
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True, port=5000)
