from flask import Flask, render_template, request, redirect, url_for, flash, send_file, send_from_directory, jsonify, Blueprint, abort
from flask_sqlalchemy import SQLAlchemy
from datetime import date, datetime
import os
import click
from flask_cors import CORS
from werkzeug.utils import secure_filename
from tempfile import NamedTemporaryFile

# AI inference imports (installed via requirements)
try:
    from faster_whisper import WhisperModel
except Exception:
    WhisperModel = None  # optional at import time

try:
    from llama_cpp import Llama
except Exception:
    Llama = None  # optional at import time

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Required for flash messages

# ✅ SQLite Database Config
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mom.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Enable CORS for API routes in development
CORS(app, resources={r"/api/*": {"origins": "*"}})

# ---------------- Models ----------------
class Meeting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    summary = db.Column(db.Text)
    date = db.Column(db.Date, default=date.today)
    location = db.Column(db.String(200))
    host = db.Column(db.String(100))
    presentees = db.Column(db.Text)
    absentees = db.Column(db.Text)
    agenda = db.Column(db.Text)
    adjournment_time = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    person = db.Column(db.String(100))
    task = db.Column(db.String(200))
    deadline = db.Column(db.String(50))
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

# ---------------- Serialization Helpers ----------------
def meeting_to_dict(meeting: "Meeting"):
    return {
        "id": meeting.id,
        "title": meeting.title,
        "summary": meeting.summary,
        "date": meeting.date.isoformat() if meeting.date else None,
        "location": meeting.location,
        "host": meeting.host,
        "presentees": meeting.presentees,
        "absentees": meeting.absentees,
        "agenda": meeting.agenda,
        "adjournment_time": meeting.adjournment_time,
        "created_at": meeting.created_at.isoformat() if meeting.created_at else None,
        "docxUrl": url_for("api.download_meeting_doc", meeting_id=meeting.id, _external=False),
    }

def task_to_dict(task: "Task"):
    return {
        "id": task.id,
        "person": task.person,
        "task": task.task,
        "deadline": task.deadline,
        "status": task.status,
        "notes": task.notes,
        "created_at": task.created_at.isoformat() if task.created_at else None,
    }

def conflict_to_dict(conflict: "Conflict"):
    return {
        "id": conflict.id,
        "issue": conflict.issue,
        "raised_by": conflict.raised_by,
        "resolution": conflict.resolution,
        "severity": conflict.severity,
        "created_at": conflict.created_at.isoformat() if conflict.created_at else None,
    }

# ---------------- API Blueprint ----------------
api_bp = Blueprint("api", __name__, url_prefix="/api")

@api_bp.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

# ---------------- Lazy-loaded AI Models ----------------
_whisper_model = None
_phi3_model = None

def get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        model_dir = os.path.join(os.path.dirname(__file__), "models", "MinuteMind", "faster-whisper")
        if WhisperModel is None:
            raise RuntimeError("faster-whisper not installed")
        print(f"Loading Whisper model from: {model_dir}")
        # Use int8 for CPU compatibility and add device specification
        _whisper_model = WhisperModel(model_dir, compute_type="int8", device="cpu")
        print("Whisper model loaded successfully")
    return _whisper_model

def get_phi3_model():
    global _phi3_model
    if _phi3_model is None:
        if Llama is None:
            raise RuntimeError("llama-cpp-python not installed")
        gguf_path = os.path.join(os.path.dirname(__file__), "models", "phi3-finetuned-Q4_K_M.gguf")
        _phi3_model = Llama(
            model_path=gguf_path,
            n_ctx=4096,
            n_threads=max(2, os.cpu_count() or 2),
            verbose=False,
        )
    return _phi3_model

# ---------------- AI Endpoints ----------------
@api_bp.route("/transcribe", methods=["POST"])
def transcribe_audio():
    audio_path = None
    try:
        if "audio" not in request.files:
            return jsonify({"error": "audio file missing (field name: audio)"}), 400
        audio_file = request.files["audio"]
        if audio_file.filename == "":
            return jsonify({"error": "empty filename"}), 400

        print(f"Processing audio file: {audio_file.filename}")

        # Save to a temp file to pass to faster-whisper
        with NamedTemporaryFile(delete=False, suffix=os.path.splitext(secure_filename(audio_file.filename))[1]) as tmp:
            audio_path = tmp.name
            audio_file.save(audio_path)

        print(f"Saved to temp file: {audio_path}")
        
        # Check file size and properties
        file_size = os.path.getsize(audio_path)
        print(f"Audio file size: {file_size} bytes")
        
        if file_size == 0:
            return jsonify({"error": "Audio file is empty"}), 400

        model = get_whisper_model()
        print("Whisper model loaded successfully")
        
        print("Starting transcription...")
        
        # The Windows-incompatible timeout logic has been removed here.
        
        print(f"Calling model.transcribe with audio_path: {audio_path}")
        print(f"Language parameter: {request.form.get('language')}")
        segments, info = model.transcribe(audio_path, language=request.form.get("language"))
        
        print("Transcription segments generated, processing...")
        text = "".join(seg.text for seg in segments)
        print(f"Transcription completed, length: {len(text)}")

        result = {
            "text": text.strip(),
            "language": getattr(info, "language", None),
            "duration": getattr(info, "duration", None),
        }
        return jsonify(result)
    except Exception as e:
        print(f"Transcription error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        try:
            if audio_path and os.path.exists(audio_path):
                os.remove(audio_path)
                print(f"Cleaned up temp file: {audio_path}")
        except Exception as e:
            print(f"Error cleaning up temp file: {e}")

@api_bp.route("/phi3/generate", methods=["POST"])
def phi3_generate():
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "").strip()
    if not prompt:
        return jsonify({"error": "prompt is required"}), 400
    try:
        llm = get_phi3_model()
        # Simple generation; adjust params to taste
        out = llm(
            prompt=prompt,
            max_tokens=data.get("max_tokens", 512),
            temperature=float(data.get("temperature", 0.7)),
            top_p=float(data.get("top_p", 0.9)),
        )
        text = out.get("choices", [{}])[0].get("text", "").strip()
        return jsonify({"text": text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route("/meetings", methods=["GET"])
def list_meetings():
    meetings = Meeting.query.order_by(Meeting.created_at.desc()).all()
    return jsonify([meeting_to_dict(m) for m in meetings])

@api_bp.route("/meetings", methods=["POST"])
def create_meeting_api():
    data = request.get_json(silent=True) or {}
    try:
        meeting = Meeting(
            title=data.get("title") or data.get("name") or "Untitled Meeting",
            summary=data.get("summary") or data.get("objective"),
            date=datetime.fromisoformat(data["date"]).date() if data.get("date") else date.today(),
            location=data.get("location"),
            host=data.get("host"),
            presentees=data.get("presentees"),
            absentees=data.get("absentees"),
            agenda=data.get("agenda"),
            adjournment_time=data.get("adjournment_time") or data.get("adj_time"),
        )
        db.session.add(meeting)
        db.session.commit()
        return jsonify(meeting_to_dict(meeting)), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

@api_bp.route("/meetings/<int:meeting_id>", methods=["GET"])
def get_meeting(meeting_id: int):
    meeting = Meeting.query.get_or_404(meeting_id)
    result = meeting_to_dict(meeting)
    # Attach recent tasks and conflicts for convenience
    result["tasks"] = [task_to_dict(t) for t in Task.query.order_by(Task.created_at.desc()).limit(10)]
    result["conflicts"] = [conflict_to_dict(c) for c in Conflict.query.order_by(Conflict.created_at.desc()).limit(10)]
    return jsonify(result)

@api_bp.route("/meetings/<int:meeting_id>/doc", methods=["GET"])
def download_meeting_doc(meeting_id: int):
    # Placeholder: Use the sample file until per-meeting docs exist
    file_path = os.path.join("files", "MoM_dinner time.docx")
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True, download_name=f"meeting_{meeting_id}.docx")
    return jsonify({"error": "Document not found"}), 404

@api_bp.route("/tasks", methods=["GET"])
def list_tasks():
    tasks = Task.query.order_by(Task.created_at.desc()).all()
    return jsonify([task_to_dict(t) for t in tasks])

@api_bp.route("/tasks", methods=["POST"])
def create_task_api():
    data = request.get_json(silent=True) or {}
    try:
        new_task = Task(
            person=data.get("person", ""),
            task=data.get("task", ""),
            deadline=data.get("deadline", ""),
            notes=data.get("notes", ""),
        )
        if not new_task.person or not new_task.task:
            return jsonify({"error": "person and task are required"}), 400
        db.session.add(new_task)
        db.session.commit()
        return jsonify(task_to_dict(new_task)), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

@api_bp.route("/tasks/<int:task_id>", methods=["PATCH"])
def update_task_api(task_id: int):
    task = Task.query.get_or_404(task_id)
    data = request.get_json(silent=True) or {}
    try:
        if "status" in data:
            task.status = data["status"]
        if "person" in data:
            task.person = data["person"]
        if "task" in data:
            task.task = data["task"]
        if "deadline" in data:
            task.deadline = data["deadline"]
        if "notes" in data:
            task.notes = data["notes"]
        db.session.commit()
        return jsonify(task_to_dict(task))
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

@api_bp.route("/conflicts", methods=["GET"])
def list_conflicts():
    conflicts = Conflict.query.order_by(Conflict.created_at.desc()).all()
    return jsonify([conflict_to_dict(c) for c in conflicts])

@api_bp.route("/conflicts", methods=["POST"])
def create_conflict_api():
    data = request.get_json(silent=True) or {}
    try:
        if not data.get("issue") or not data.get("raised_by"):
            return jsonify({"error": "issue and raised_by are required"}), 400
        conflict = Conflict(
            issue=data.get("issue", ""),
            raised_by=data.get("raised_by", ""),
            resolution=data.get("resolution", ""),
            severity=data.get("severity", "Medium"),
        )
        db.session.add(conflict)
        db.session.commit()
        return jsonify(conflict_to_dict(conflict)), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

@api_bp.route("/conflicts/<int:conflict_id>", methods=["PATCH"])
def update_conflict_api(conflict_id: int):
    conflict = Conflict.query.get_or_404(conflict_id)
    data = request.get_json(silent=True) or {}
    try:
        if "resolution" in data:
            conflict.resolution = data["resolution"]
        if "severity" in data:
            conflict.severity = data["severity"]
        db.session.commit()
        return jsonify(conflict_to_dict(conflict))
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

# Register API blueprint
app.register_blueprint(api_bp)

# ---------------- React SPA Static Serving (Production) ----------------
# Serve files from frontend/dist if present
DIST_DIR = os.path.join(os.path.dirname(__file__), "frontend", "dist")

def spa_file_path(path: str) -> str:
    return os.path.join(DIST_DIR, path)

@app.route("/")
def spa_index():
    index_path = spa_file_path("index.html")
    if os.path.exists(index_path):
        return send_from_directory(DIST_DIR, "index.html")
    # Fallback: if no build yet, simple message
    return "React app not built yet. Run 'npm run build' inside frontend/.", 200

@app.route('/assets/<path:path>')
def spa_assets(path):
    assets_dir = os.path.join(DIST_DIR, 'assets')
    if os.path.exists(os.path.join(assets_dir, path)):
        return send_from_directory(assets_dir, path)
    abort(404)

@app.route('/<path:path>')
def spa_catch_all(path):
    # If the requested file exists in dist, serve it; otherwise return index.html for SPA routing
    candidate = spa_file_path(path)
    if os.path.isfile(candidate):
        # Serve static file directly
        directory = os.path.dirname(candidate)
        filename = os.path.basename(candidate)
        return send_from_directory(directory, filename)
    # Otherwise, SPA fallback
    index_path = spa_file_path("index.html")
    if os.path.exists(index_path):
        return send_from_directory(DIST_DIR, "index.html")
    abort(404)
# Initialize database tables
def init_db():
    with app.app_context():
        db.create_all()
        print("✅ Database tables created successfully!")

# CLI command to create tables
@app.cli.command("init-db")
def init_db_command():
    """Clear the existing data and create new tables."""
    init_db()
    click.echo('Initialized the database.')

# Call init_db when the app is created
init_db()

# ---------------- Routes ----------------
@app.route("/")
def home():
    return redirect("/")

@app.route("/login", methods=["GET", "POST"])
def login():
    # UI handled by React SPA
    return redirect("/")

@app.route("/dashboard")
def dashboard():
    # UI handled by React SPA
    return redirect("/")

@app.route("/new-meeting", methods=["GET", "POST"])
def new_meeting():
    # UI handled by React SPA
    return redirect("/")

@app.route("/add-task", methods=["POST"])
def add_task():
    try:
        person = request.form.get("person", "")
        task = request.form.get("task", "")
        deadline = request.form.get("deadline", "")
        notes = request.form.get("notes", "")
        
        if not person or not task:
            flash("Person and task are required!", "error")
            return redirect(url_for("dashboard"))
        
        new_task = Task(
            person=person,
            task=task,
            deadline=deadline,
            notes=notes
        )
        
        db.session.add(new_task)
        db.session.commit()
        
        flash(f"Task assigned to {person} successfully!", "success")
        
    except Exception as e:
        db.session.rollback()
        flash(f"Error adding task: {str(e)}", "error")
    
    return redirect(url_for("dashboard"))

@app.route("/add-conflict", methods=["POST"])
def add_conflict():
    try:
        issue = request.form.get("issue", "")
        raised_by = request.form.get("raised_by", "")
        resolution = request.form.get("resolution", "")
        severity = request.form.get("severity", "Medium")
        
        if not issue or not raised_by:
            flash("Issue and raised by are required!", "error")
            return redirect(url_for("dashboard"))
        
        conflict = Conflict(
            issue=issue,
            raised_by=raised_by,
            resolution=resolution,
            severity=severity
        )
        
        db.session.add(conflict)
        db.session.commit()
        
        flash(f"Conflict logged successfully!", "success")
        
    except Exception as e:
        db.session.rollback()
        flash(f"Error adding conflict: {str(e)}", "error")
    
    return redirect(url_for("dashboard"))

@app.route("/past-meetings")
def past_meetings():
    # UI handled by React SPA
    return redirect("/")

@app.route("/settings")
def settings():
    # UI handled by React SPA
    return redirect("/")

@app.route("/download-mom")
def download_mom():
    # Check if the sample file exists
    file_path = os.path.join("files", "MoM_dinner time.docx")
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        flash("Sample MoM file not found!", "error")
        return redirect(url_for("dashboard"))

@app.route("/delete-task/<int:task_id>")
def delete_task(task_id):
    try:
        task = Task.query.get_or_404(task_id)
        db.session.delete(task)
        db.session.commit()
        flash("Task deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting task: {str(e)}", "error")
    
    return redirect(url_for("dashboard"))

@app.route("/delete-conflict/<int:conflict_id>")
def delete_conflict(conflict_id):
    try:
        conflict = Conflict.query.get_or_404(conflict_id)
        db.session.delete(conflict)
        db.session.commit()
        flash("Conflict deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting conflict: {str(e)}", "error")
    
    return redirect(url_for("dashboard"))

@app.route("/update-task-status/<int:task_id>")
def update_task_status(task_id):
    try:
        task = Task.query.get_or_404(task_id)
        # Cycle through statuses: Pending -> In Progress -> Done -> Pending
        if task.status == "Pending":
            task.status = "In Progress"
        elif task.status == "In Progress":
            task.status = "Done"
        else:
            task.status = "Pending"
        
        db.session.commit()
        flash(f"Task status updated to {task.status}!", "success")
        
    except Exception as e:
        db.session.rollback()
        flash(f"Error updating task status: {str(e)}", "error")
    
    return redirect(url_for("dashboard"))

if __name__ == "__main__":
    app.run(debug=True)
