# JobPilot — Smart Job Application Management System (Final)

A portfolio-ready Flask + MySQL application for managing a real job search.

## Features
- User registration/login with password hashing and session authentication
- CSRF protection for POST actions
- Full application CRUD
- Advanced search and filters (company, role, location, status, job type, favourites, follow-ups)
- Favourite/starred applications
- Application status history timeline
- Recruiter contact details
- Resume-version tracking per application
- Follow-up dates and follow-up status
- Interview scheduling, editing, deletion and countdowns
- Dashboard KPIs and upcoming interview/follow-up visibility
- Analytics charts for status, monthly activity, job types and companies
- Location and pipeline summaries
- CSV export
- Persistent light/dark mode with system-theme detection
- Responsive Bootstrap UI
- Automatic database migration for new v4/final columns so existing JobPilot data is preserved

## Stack
Python · Flask · MySQL · MySQLdb · HTML · CSS · Bootstrap 5 · JavaScript · Chart.js · Werkzeug

## Setup
1. Create a virtual environment:
   `python -m venv venv`
2. Activate it in PowerShell:
   `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`
   `venv\Scripts\activate`
3. Install packages:
   `pip install -r requirements.txt`
4. Create `.env` in the project root using `.env.example`:
   `SECRET_KEY=change-me`
   `MYSQL_HOST=localhost`
   `MYSQL_USER=root`
   `MYSQL_PASSWORD=your_mysql_password`
   `MYSQL_DB=jobtrack`
   `MYSQL_PORT=3306`
5. Run `database/schema.sql` once in MySQL Workbench if setting up a new database. Existing JobPilot databases are migrated automatically when the app starts.
6. Start:
   `python app.py`
7. Open `http://127.0.0.1:5000`

Never commit `.env` or your MySQL password to GitHub.
