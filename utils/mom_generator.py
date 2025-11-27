"""
Minutes of Meeting (MoM) Generator
Generates Word documents in the SAME FORMAT as the uploaded reference file.
"""
from docx import Document
from datetime import datetime
import os
FILES_DIR = os.path.join(os.getcwd(), "files")
os.makedirs(FILES_DIR, exist_ok=True)
def generate_mom_document(meeting_data, tasks=None, conflicts=None, transcript_segments=None):
    """
    Generate MoM in EXACT structure of user-provided sample.
    """
    if tasks is None:
        tasks = []
    if conflicts is None:
        conflicts = []

    document = Document()
    # -------------------------------------------------
    # HEADER TITLE
    # -------------------------------------------------
    document.add_heading("Minutes of Meeting (MoM)", level=0)
    # -------------------------------------------------
    # BASIC DETAILS
    # -------------------------------------------------
    document.add_paragraph(f"Meeting Name: {meeting_data.title or 'N/A'}")
    document.add_paragraph(f"Meeting Host: {meeting_data.host or 'N/A'}")
    # -------------------------------------------------
    # PRESENT MEMBERS
    # -------------------------------------------------
    present = getattr(meeting_data, "presentees", "") or ""
    present_list = [p.strip() for p in present.split(",") if p.strip()]
    document.add_paragraph("\nPresent Members:")
    if present_list:
        for person in present_list:
            document.add_paragraph(f"{person}", style="List Bullet")
    else:
        document.add_paragraph("None", style="List Bullet")
    # -------------------------------------------------
    # ABSENT MEMBERS
    # -------------------------------------------------
    absent = getattr(meeting_data, "absentees", "") or ""
    absent_list = [a.strip() for a in absent.split(",") if a.strip()]
    document.add_paragraph("\nAbsent Members:")
    if absent_list:
        for person in absent_list:
            document.add_paragraph(f"{person}", style="List Bullet")
    else:
        document.add_paragraph("None", style="List Bullet")
    # -------------------------------------------------
    # DATE & TIME
    # -------------------------------------------------
    meeting_date = (
        meeting_data.date.strftime("%d %B %Y") if meeting_data.date else "N/A"
    )
    time_range = "N/A"
    if hasattr(meeting_data, "start_time") and hasattr(meeting_data, "end_time"):
        if meeting_data.start_time and meeting_data.end_time:
            time_range = f"{meeting_data.start_time} – {meeting_data.end_time} (IST)"
    document.add_paragraph(f"\nDate of Meeting: {meeting_date}")
    document.add_paragraph(f"Time: {time_range}")

    # -------------------------------------------------
    # AGENDA → SUMMARY OF MEETING
    # -------------------------------------------------
    document.add_paragraph("\nAgenda → Summary of Meeting :")

    # If transcript_segments exists, use it as summary (like sample)
    if transcript_segments:
        for seg in transcript_segments:
            text = seg.get("text") if isinstance(seg, dict) else str(seg)
            if text:
                document.add_paragraph(f"\t• {text}", style="List Bullet")
    else:
        # fallback: use meeting_data.summary if exists
        if hasattr(meeting_data, "summary") and meeting_data.summary:
            for line in meeting_data.summary.split("\n"):
                if line.strip():
                    document.add_paragraph(f"\t• {line.strip()}", style="List Bullet")
        else:
            document.add_paragraph("\t• No summary available.", style="List Bullet")

    # -------------------------------------------------
    # ACTION ITEMS → TASKS ASSIGNED
    # -------------------------------------------------
    document.add_paragraph("\nAction Items → Tasks Assigned :")

    if tasks:
        for task in tasks:
            assigned_to = getattr(task, "assigned_to", None) or getattr(task, "person", "") or "N/A"
            description = getattr(task, "description", None) or getattr(task, "task", "") or "N/A"
            status = getattr(task, "status", "") or "Pending"

            document.add_paragraph(
                f"\t• {assigned_to} → {description}. ({status})",
                style="List Bullet",
            )
    else:
        document.add_paragraph("\t• No tasks assigned.", style="List Bullet")

    # -------------------------------------------------
    # CONFLICTS / ISSUES
    # -------------------------------------------------
    document.add_paragraph("\nConflicts / Issues Raised :")
    if conflicts:
        for c in conflicts:
            issue = getattr(c, "issue", "") or "N/A"
            raised_by = getattr(c, "raised_by", "") or "Unknown"
            severity = getattr(c, "severity", "") or "Medium"

            document.add_paragraph(
                f"\t• {issue} — raised by {raised_by} (Severity: {severity})",
                style="List Bullet",
            )
    else:
        document.add_paragraph("\t• No conflicts reported.", style="List Bullet")

    # -------------------------------------------------
    # SAVE FILE
    # -------------------------------------------------
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"MoM_{meeting_data.id}_{timestamp}.docx"
    file_path = os.path.join(FILES_DIR, file_name)

    document.save(file_path)
    return file_path

