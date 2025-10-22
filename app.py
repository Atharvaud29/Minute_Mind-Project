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

# AI inference imports
try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None

try:
    from llama_cpp import Llama
except ImportError:
    Llama = None

app = Flask(__name__, static_folder="frontend/dist", static_url_path="")
app.secret_key = 'your-secret-here'

# Database Config
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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    key_decisions = db.Column(db.PickleType)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    person = db.Column(db.String(100))
    task = db.Column(db.String(200))
    deadline = db.Column(db.String(50), default="Not Mentioned")
    status = db.Column(db.String(50), default="Pending")
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Conflict(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    issue = db.Column(db.Text)
    raised_by = db.Column(db.String(100))
    resolution = db.Column(db.Text)
    severity = db.Column(db.String(50), default="Medium")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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
        "created_at": m.created_at.isoformat() if m.created_at else None
    }

def task_to_dict(t):
    return {
        "id": t.id,
        "person": t.person,
        "task": t.task,
        "deadline": t.deadline,
        "status": t.status,
        "notes": t.notes,
        "created_at": t.created_at.isoformat() if t.created_at else None
    }

def conflict_to_dict(c):
    return {
        "id": c.id,
        "issue": c.issue,
        "raised_by": c.raised_by,
        "resolution": c.resolution,
        "severity": c.severity,
        "created_at": c.created_at.isoformat() if c.created_at else None
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
        # try to find a JSON array or object substring
        match = re.search(r'(\[.*\]|\{.*\})', text, re.DOTALL)
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
                "due_date": deadline,
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
                "due_date": deadline,
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

def get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        model_dir = os.path.join(os.path.dirname(__file__), "models", "MinuteMind", "faster-whisper")
        if WhisperModel is None:
            raise RuntimeError("faster-whisper not installed")
        print("Loading Whisper model...")
        _whisper_model = WhisperModel(model_dir, compute_type="int8", device="cpu")
        print("Whisper model loaded.")
    return _whisper_model

def get_phi3_model():
    global _phi3_model
    if _phi3_model is None:
        if Llama is None:
            raise RuntimeError("llama-cpp-python not installed")
        gguf_path = os.path.join(os.path.dirname(__file__), "models", "phi3-finetuned-Q4_K_M.gguf")
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

        print("Starting transcription...")
        model = get_whisper_model()
        segments, _ = model.transcribe(audio_path)
        text = "".join(seg.text for seg in segments)
        print(f"Transcription complete. Length: {len(text)}")
        return jsonify({"text": text.strip()})
    except Exception as e:
        print(f"Transcription error: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)


# -----------------------------
# Process Transcript
# -----------------------------
@api_bp.route("/process_transcript", methods=["POST"])
def process_transcript():
    try:
        data = request.get_json()
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
        raw_text = response.get("choices", [{}])[0].get("text", "")
        if raw_text is None:
            raw_text = ""
        raw_text = raw_text.strip()
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
                assigned_to = item.get("assigned_to") or item.get("assigned_to") or item.get("assigned_to") or item.get("assignee") or item.get("person") or ""
                due_date = item.get("due_date") or item.get("deadline") or ""
                status = item.get("status") or "pending"
                if task_name:
                    tasks.append({
                        "task_name": task_name.strip(),
                        "assigned_to": assigned_to.strip() if isinstance(assigned_to, str) else assigned_to,
                        "due_date": due_date.strip() if isinstance(due_date, str) else due_date,
                        "status": status.strip() if isinstance(status, str) else status
                    })
        else:
            # Fallback 1: try to extract JSON-like lines from raw_text
            fallback_parsed = []
            lines = raw_text.splitlines()
            json_like = "[" + ",".join([ln.strip().rstrip(",") for ln in lines if ln.strip().startswith("{") or ln.strip().startswith('["') or ln.strip().startswith('"')]) + "]"
            try:
                candidate = safe_json_parse(json_like)
                if isinstance(candidate, list):
                    fallback_parsed = candidate
            except Exception:
                fallback_parsed = []

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
                                "due_date": due_date.strip() if isinstance(due_date, str) else due_date,
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
            retry_text = retry_resp.get("choices", [{}])[0].get("text", "") or ""
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
                        "due_date": due_date,
                        "status": "pending"
                    })

        print(f"✅ Tasks extracted: {len(tasks)}")

        # --- Save tasks to DB ---
        for t in tasks:
            new_task = Task(
                person=t.get("assigned_to", "Unassigned") or "Unassigned",
                task=t.get("task_name", "Untitled Task") or "Untitled Task",
                deadline=t.get("due_date", "Not Mentioned") or "Not Mentioned",
                status=t.get("status", "Pending") or "Pending",
                notes=""
            )
            db.session.add(new_task)
        db.session.commit()

        # --- Conflict Extraction ---
        print("Extracting conflicts...")
        conflict_prompt = f"""
Identify disagreements or conflicts in this meeting transcript.
Return a JSON list of:
[{{"issue": "description", "raised_by": "person involved"}}]

Transcript:
{transcript}
"""
        response_conflict = llm(prompt=conflict_prompt, max_tokens=1024, temperature=0.3)
        raw_conflict_text = response_conflict.get("choices", [{}])[0].get("text", "").strip()
        print(f"Raw conflict output: {raw_conflict_text[:300]}")

        conflicts = []
        if raw_conflict_text:
            try:
                parsed_conflicts = safe_json_parse(raw_conflict_text)
                if isinstance(parsed_conflicts, list):
                    conflicts = parsed_conflicts
                else:
                    # heuristic search
                    conflict_matches = re.findall(
                        r"(?i)\b(disagree|conflict|argument|issue|not\s+agree)\b.*?\.?",
                        transcript
                    )
                    conflicts = [{"issue": m.strip(), "raised_by": ""} for m in conflict_matches]
            except Exception:
                conflict_matches = re.findall(
                    r"(?i)\b(disagree|conflict|argument|issue|not\s+agree)\b.*?\.?",
                    transcript
                )
                conflicts = [{"issue": m.strip(), "raised_by": ""} for m in conflict_matches]

        # --- Save conflicts to DB ---
        for c in conflicts:
            new_conflict = Conflict(
                issue=c.get("issue", ""),
                raised_by=c.get("raised_by", ""),
                resolution="",
                severity="Medium"
            )
            db.session.add(new_conflict)
        db.session.commit()

        return jsonify({
            "message": "Transcript processed successfully",
            "tasks_extracted": len(tasks),
            "conflicts_extracted": len(conflicts),
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

        # Step 2: Transcribe audio
        whisper_model = get_whisper_model()
        segments, _ = whisper_model.transcribe(audio_path)
        full_transcript = "".join(seg.text for seg in segments).strip()

        # Step 3: Generate summary using Phi-3 with safe chunking
        llm = get_phi3_model()
        MAX_CHARS = 3000

        def chunk_text(text, max_chars=MAX_CHARS):
            return [text[i:i+max_chars] for i in range(0, len(text), max_chars)]

        transcript_chunks = chunk_text(full_transcript)
        chunk_summaries = []

        for chunk in transcript_chunks:
            prompt = f"""
Summarize the following meeting transcript in 5-6 sentences:

{chunk}
"""
            out = llm(
                prompt=prompt,
                max_tokens=1024,
                temperature=0.4,
                stop=None
            )
            text = out.get("choices", [{}])[0].get("text", "").strip()
            if text:
                chunk_summaries.append(text)

        # Combine chunk summaries into one summary
        summary = " ".join(chunk_summaries)

        return jsonify({
            "transcript": full_transcript,
            "summary": summary
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

    finally:
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)


# -----------------------------
# Meeting Summary + Key Decisions Endpoint
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

        # Step 2: Transcribe audio
        whisper_model = get_whisper_model()
        segments, _ = whisper_model.transcribe(audio_path)
        full_transcript = "".join(seg.text for seg in segments).strip()

        # Step 3: Generate summary and key decisions using Phi-3
        llm = get_phi3_model()
        MAX_CHARS = 3000

        # Chunk transcript if too long
        def chunk_text(text, max_chars=MAX_CHARS):
            return [text[i:i+max_chars] for i in range(0, len(text), max_chars)]

        transcript_chunks = chunk_text(full_transcript)
        summaries, decisions = [], []

        for chunk in transcript_chunks:
            prompt = f"""
You are an AI assistant. 

1️⃣ Summarize the following meeting transcript in 3-4 lines under 'Meeting Highlight'.
2️⃣ Extract all Key Decisions as a list under 'Key Decisions'.

Transcript:
{chunk}

Return output as JSON with keys: 'summary' and 'key_decisions'.
"""
            out = llm(prompt=prompt, max_tokens=1024, temperature=0.3)
            text = out.get("choices", [{}])[0].get("text", "").strip()

            try:
                parsed = json.loads(text)
                summaries.append(parsed.get("summary", ""))
                chunk_decisions = parsed.get("key_decisions", [])
                if isinstance(chunk_decisions, list):
                    decisions.extend(chunk_decisions)
            except Exception:
                # fallback if parsing fails
                summaries.append(text)

        final_summary = " ".join(summaries).strip()

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

            # Fetch existing meeting or create new
            if meeting_id:
                meeting = Meeting.query.get(meeting_id)
                if meeting:
                    meeting.summary = final_summary
                    meeting.key_decisions = decisions if isinstance(decisions, list) else []
                    meeting.date = meeting.date or date.today()
                else:
                    # Meeting ID provided but not found → create new
                    new_title = request.form.get("title") or payload.get("title") or f"Meeting {datetime.utcnow().isoformat()}"
                    meeting = Meeting(
                        title=new_title,
                        summary=final_summary,
                        key_decisions=decisions if isinstance(decisions, list) else [],
                        date=date.today()
                    )
                    db.session.add(meeting)
            else:
                # No meeting_id → create new meeting
                new_title = request.form.get("title") or (request.get_json(silent=True) or {}).get("title") or f"Meeting {datetime.utcnow().isoformat()}"
                meeting = Meeting(
                    title=new_title,
                    summary=final_summary,
                    key_decisions=decisions if isinstance(decisions, list) else [],
                    date=date.today()
                )
                db.session.add(meeting)

            db.session.commit()
            saved_meeting_id = meeting.id if meeting else None

        except Exception as e:
            print("Warning: failed to save summary/key_decisions to DB:", e)
            traceback.print_exc()
            saved_meeting_id = None

        return jsonify({
            "transcript": full_transcript,
            "meeting_highlight": final_summary,
            "key_decisions": decisions,
            "meeting_id": saved_meeting_id
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

    finally:
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)


# -----------------------------
# 🔹 Added: Server-side Summary Page (optional)
# This route renders a simple Jinja template 'summary.html' (create templates/summary.html).
# If you prefer SPA, you can ignore this and use the existing /api/meetings GET JSON endpoint.
# -----------------------------
@app.route("/summary_page", methods=["GET"])
def summary_page():
    try:
        meetings = Meeting.query.order_by(Meeting.created_at.desc()).all()
        return render_template("summary.html", meetings=meetings)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


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
# Serve frontend
# -----------------------------
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, "index.html")

# -----------------------------
# Register Blueprint
# -----------------------------
app.register_blueprint(api_bp)

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
