"""
Minutes of Meeting (MoM) Document Generator
Generates professional Word documents with all meeting details.
"""

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from datetime import datetime
import os


def add_hyperlink(paragraph, url, text):
    """Add a hyperlink to a paragraph."""
    part = paragraph.part
    r_id = part.relate_to(url, "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink", is_external=True)
    
    hyperlink = OxmlElement('w:hyperlink')
    hyperlink.set(qn('r:id'), r_id)
    
    new_run = OxmlElement('w:r')
    rPr = OxmlElement('w:rPr')
    
    # Set hyperlink style
    c = OxmlElement('w:color')
    c.set(qn('w:val'), '0563C1')
    rPr.append(c)
    
    u = OxmlElement('w:u')
    u.set(qn('w:val'), 'single')
    rPr.append(u)
    
    new_run.append(rPr)
    new_run.text = text
    hyperlink.append(new_run)
    
    paragraph._p.append(hyperlink)
    return hyperlink


def generate_mom_document(meeting_data, tasks=None, conflicts=None, transcript_segments=None):
    """
    Generate a complete Minutes of Meeting document in Word format.
    
    Args:
        meeting_data: Meeting model object with all fields
        tasks: List of Task objects (default: empty list)
        conflicts: List of Conflict objects (default: empty list)
        transcript_segments: List of speaker-segmented transcript segments (default: None)
    
    Returns:
        file_path: Path to generated .docx file
    """
    if tasks is None:
        tasks = []
    if conflicts is None:
        conflicts = []
    
    # Create document
    doc = Document()
    
    # Set document margins
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)
    
    # ========== HEADER SECTION ==========
    title = doc.add_heading('MINUTES OF MEETING', 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_run = title.runs[0]
    title_run.font.size = Pt(18)
    title_run.font.bold = True
    
    doc.add_paragraph()  # Spacing
    
    # Meeting Title
    if meeting_data.title:
        meeting_title = doc.add_paragraph()
        meeting_title_run = meeting_title.add_run(f"Meeting: {meeting_data.title}")
        meeting_title_run.font.size = Pt(14)
        meeting_title_run.font.bold = True
        meeting_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    doc.add_paragraph()  # Spacing
    
    # Meeting Details Table
    details_table = doc.add_table(rows=4, cols=2)
    details_table.style = 'Light Grid Accent 1'
    
    # Date
    details_table.cell(0, 0).text = "Date:"
    details_table.cell(0, 1).text = meeting_data.date.strftime("%B %d, %Y") if meeting_data.date else "Not specified"
    
    # Time
    details_table.cell(1, 0).text = "Time:"
    details_table.cell(1, 1).text = meeting_data.adjournment_time if meeting_data.adjournment_time else "Not specified"
    
    # Location
    details_table.cell(2, 0).text = "Location:"
    details_table.cell(2, 1).text = meeting_data.location if meeting_data.location else "Not specified"
    
    # Host/Chairperson
    details_table.cell(3, 0).text = "Host/Chairperson:"
    details_table.cell(3, 1).text = meeting_data.host if meeting_data.host else "Not specified"
    
    doc.add_paragraph()  # Spacing
    
    # ========== ATTENDEES SECTION ==========
    doc.add_heading('Attendees', level=1)
    
    if meeting_data.presentees:
        presentees_para = doc.add_paragraph("Presentees:", style='List Bullet')
        presentees_list = [p.strip() for p in meeting_data.presentees.split(',') if p.strip()]
        for person in presentees_list:
            doc.add_paragraph(person, style='List Bullet 2')
    else:
        doc.add_paragraph("Presentees: Not specified", style='List Bullet')
    
    if meeting_data.absentees:
        absentees_para = doc.add_paragraph("Absentees:", style='List Bullet')
        absentees_list = [a.strip() for a in meeting_data.absentees.split(',') if a.strip()]
        for person in absentees_list:
            doc.add_paragraph(person, style='List Bullet 2')
    
    doc.add_paragraph()  # Spacing
    
    # ========== AGENDA SECTION ==========
    if meeting_data.agenda:
        doc.add_heading('Agenda', level=1)
        agenda_items = [item.strip() for item in meeting_data.agenda.split('\n') if item.strip()]
        for i, item in enumerate(agenda_items, 1):
            doc.add_paragraph(f"{i}. {item}", style='List Number')
        doc.add_paragraph()  # Spacing
    
    # ========== MEETING SUMMARY SECTION ==========
    if meeting_data.summary:
        doc.add_heading('Meeting Summary', level=1)
        summary_para = doc.add_paragraph(meeting_data.summary)
        summary_para.style = 'Normal'
        doc.add_paragraph()  # Spacing
    
    # ========== KEY DECISIONS SECTION ==========
    if meeting_data.key_decisions:
        doc.add_heading('Key Decisions', level=1)
        decisions = meeting_data.key_decisions
        if isinstance(decisions, list):
            for i, decision in enumerate(decisions, 1):
                if isinstance(decision, dict):
                    decision_text = decision.get('decision', decision.get('text', str(decision)))
                    speaker = decision.get('speaker', decision.get('by', ''))
                    if speaker:
                        doc.add_paragraph(f"{i}. {decision_text} (by {speaker})", style='List Number')
                    else:
                        doc.add_paragraph(f"{i}. {decision_text}", style='List Number')
                else:
                    doc.add_paragraph(f"{i}. {decision}", style='List Number')
        doc.add_paragraph()  # Spacing
    
    # ========== ACTION ITEMS SECTION ==========
    if tasks:
        doc.add_heading('Action Items', level=1)
        
        # Create table for action items
        tasks_table = doc.add_table(rows=1, cols=4)
        tasks_table.style = 'Light Grid Accent 1'
        
        # Header row
        header_cells = tasks_table.rows[0].cells
        header_cells[0].text = "Task Description"
        header_cells[1].text = "Assigned To"
        header_cells[2].text = "Deadline"
        header_cells[3].text = "Status"
        
        # Make header bold
        for cell in header_cells:
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.font.bold = True
        
        # Add task rows
        for task in tasks:
            row_cells = tasks_table.add_row().cells
            row_cells[0].text = task.task if hasattr(task, 'task') else str(task.get('task', ''))
            row_cells[1].text = task.person if hasattr(task, 'person') else str(task.get('person', ''))
            row_cells[2].text = task.deadline if hasattr(task, 'deadline') else str(task.get('deadline', 'Not Mentioned'))
            row_cells[3].text = task.status if hasattr(task, 'status') else str(task.get('status', 'Pending'))
        
        doc.add_paragraph()  # Spacing
    
    # ========== CONFLICTS/ISSUES SECTION ==========
    if conflicts:
        doc.add_heading('Conflicts and Issues', level=1)
        
        # Create table for conflicts
        conflicts_table = doc.add_table(rows=1, cols=5)
        conflicts_table.style = 'Light Grid Accent 1'
        
        # Header row
        header_cells = conflicts_table.rows[0].cells
        header_cells[0].text = "Issue"
        header_cells[1].text = "Raised By"
        header_cells[2].text = "Severity"
        header_cells[3].text = "Participants"
        header_cells[4].text = "Resolution"
        
        # Make header bold
        for cell in header_cells:
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.font.bold = True
        
        # Add conflict rows
        for conflict in conflicts:
            row_cells = conflicts_table.add_row().cells
            row_cells[0].text = conflict.issue if hasattr(conflict, 'issue') else str(conflict.get('issue', ''))
            row_cells[1].text = conflict.raised_by if hasattr(conflict, 'raised_by') else str(conflict.get('raised_by', ''))
            row_cells[2].text = conflict.severity if hasattr(conflict, 'severity') else str(conflict.get('severity', 'Medium'))
            row_cells[3].text = conflict.participants if hasattr(conflict, 'participants') else str(conflict.get('participants', ''))
            row_cells[4].text = conflict.resolution if hasattr(conflict, 'resolution') else str(conflict.get('resolution', 'Pending'))
        
        doc.add_paragraph()  # Spacing
    
    # ========== FULL TRANSCRIPT SECTION ==========
    if transcript_segments:
        doc.add_heading('Full Transcript', level=1)
        doc.add_paragraph("Speaker-segmented transcript of the meeting:", style='Intense Quote')
        doc.add_paragraph()  # Spacing
        
        current_speaker = None
        for seg in transcript_segments:
            speaker = seg.get('speaker', 'UNKNOWN')
            text = seg.get('text', '')
            start_time = seg.get('start', 0)
            
            # Format time
            minutes = int(start_time // 60)
            seconds = int(start_time % 60)
            time_str = f"[{minutes:02d}:{seconds:02d}]"
            
            # Add speaker label if changed
            if speaker != current_speaker:
                speaker_para = doc.add_paragraph()
                speaker_run = speaker_para.add_run(f"{speaker}:")
                speaker_run.font.bold = True
                speaker_run.font.size = Pt(11)
                current_speaker = speaker
            
            # Add text
            text_para = doc.add_paragraph(f"  {time_str} {text}")
            text_para.style = 'Normal'
        
        doc.add_paragraph()  # Spacing
    
    # ========== FOOTER SECTION ==========
    doc.add_paragraph()  # Spacing
    doc.add_paragraph("=" * 50)
    
    footer_para = doc.add_paragraph()
    footer_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer_run = footer_para.add_run("End of Minutes")
    footer_run.font.italic = True
    
    if meeting_data.adjournment_time:
        adj_para = doc.add_paragraph()
        adj_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        adj_para.add_run(f"Meeting adjourned at: {meeting_data.adjournment_time}")
    
    # Generation timestamp
    gen_para = doc.add_paragraph()
    gen_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    gen_run = gen_para.add_run(f"Document generated on: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}")
    gen_run.font.size = Pt(9)
    gen_run.font.italic = True
    gen_run.font.color.rgb = RGBColor(128, 128, 128)
    
    # ========== SAVE DOCUMENT ==========
    # Create files directory if it doesn't exist
    files_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "files")
    os.makedirs(files_dir, exist_ok=True)
    
    # Generate filename
    meeting_id = meeting_data.id if hasattr(meeting_data, 'id') else 'unknown'
    safe_title = "".join(c for c in (meeting_data.title or "Meeting") if c.isalnum() or c in (' ', '-', '_')).rstrip()
    safe_title = safe_title.replace(' ', '_')[:50]  # Limit length
    filename = f"MoM_{meeting_id}_{safe_title}.docx"
    file_path = os.path.join(files_dir, filename)
    
    # Save document
    doc.save(file_path)
    print(f"MoM document saved to: {file_path}")
    
    return file_path

