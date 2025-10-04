# MoM Manager - UI Demo (Flask)

A complete Flask-based UI for managing Minutes of Meeting (MoM) with a modern, responsive design.

## Features

- **Login/SignUp**: Simple authentication system
- **Dashboard**: Overview with navigation sidebar
- **New Meeting**: Comprehensive form for meeting details
- **Results Panel**: Interactive tabs for Transcript, Summary, Action Items, Conflicts, Sentiment, and Final MoM
- **Past Meetings**: Searchable table of previous meetings
- **Settings**: Profile and preferences management
- **Download**: Direct download of MoM files (.docx)

## Project Structure

```
mom_ui_flask/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── files/                # Directory for MoM files
│   └── MoM_dinner time.docx  # Your MoM file goes here
├── static/               # Static assets
│   ├── css/
│   │   └── style.css    # Modern CSS styling
│   └── js/
│       └── main.js      # Interactive JavaScript
└── templates/            # HTML templates
    ├── base.html         # Base template
    ├── login.html        # Login page
    ├── dashboard.html    # Main dashboard
    ├── new_meeting.html  # New meeting form
    ├── past_meetings.html # Past meetings table
    └── settings.html     # Settings page
```

## Setup Instructions

### 1. Create Python Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Add Your MoM File
- Place your `MoM_dinner time.docx` file in the `files/` directory
- The filename must match exactly: `MoM_dinner time.docx`

### 4. Run the Application
```bash
# Windows
set FLASK_APP=app.py
flask run

# macOS/Linux
export FLASK_APP=app.py
flask run
```

### 5. Access the Application
Open your browser and go to: `http://127.0.0.1:5000`

## Usage

### Login
- Use any email and password combination (demo mode)
- Click "Login" to access the dashboard

### Dashboard
- Navigate using the left sidebar
- Download sample MoM files directly

### New Meeting
- Fill out the comprehensive meeting form
- Click "Generate Report" to see demo results
- Switch between tabs to view different analysis sections
- Edit the Final MoM text as needed
- Download the final document

### Past Meetings
- View a table of previous meetings
- Search and filter functionality (demo)
- Download/view specific meeting documents

### Settings
- Update profile information
- Change password
- Modify preferences

## Demo Features

- **Generate Report**: Populates demo content in all tabs
- **Interactive Tabs**: Switch between different result views
- **Editable Final MoM**: Modify the final minutes before download
- **Download Functionality**: Serves your actual MoM file

## Technical Notes

- **Authentication**: Minimal demo implementation (no real security)
- **File Handling**: Uses Flask's `send_from_directory` for secure file downloads
- **Responsive Design**: Modern CSS with CSS variables and flexbox
- **JavaScript**: Tab switching and demo content generation
- **Flask Routes**: RESTful API structure for easy backend integration

## Customization

- **Styling**: Modify `static/css/style.css` for visual changes
- **Functionality**: Extend `static/js/main.js` for additional features
- **Backend**: Replace demo functions in `app.py` with real processing logic
- **Templates**: Customize HTML templates in the `templates/` directory

## Production Considerations

- Change the secret key in `app.py`
- Implement proper authentication and session management
- Add database integration for meeting storage
- Implement real audio processing for meeting recordings
- Add proper error handling and logging
- Use environment variables for configuration

## Support

This is a demo application showcasing the UI structure. For production use, implement proper security, database integration, and audio processing capabilities.
