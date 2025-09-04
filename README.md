Canada Developer Jobs – Mini Python Project
A small Python web application that collects developer job postings in Canada and provides AI-powered analysis for each job.
The app is built with FastAPI + SQLAlchemy + Jinja2 and deployed on Render.

Features
--Filter jobs by timeframe, location, and work mode
--Job listing with title, company, city, mode, and source link
--AI Button: Analyze each job posting with 4 extracted insights:
Skills required (top 8 technical skills)
Years of Experience Required (parsed from job description)
Type (Remote / Hybrid / Onsite / Not mentioned)
Salary (annual or hourly, if available)

Tech Stack
--Backend: FastAPI, SQLAlchemy, Alembic, APScheduler
--Frontend: Jinja2 templates + Vanilla JS
--AI Processing: OpenAI API + regex fallback (skills, years, type, salary)
Database: SQLite (local) or PostgreSQL (for deployment)
Deployment: Render

Project Structure
app/
 ├── main.py              # FastAPI entrypoint
 ├── models.py            # SQLAlchemy models
 ├── schemas.py           # Pydantic schemas
 ├── services/
 │    ├── ingest.py       # Job ingestion logic
 │    ├── ai.py           # AI analysis (skills, years, type, salary)
 ├── templates/
 │    └── index.html      # UI template
 ├── static/              # CSS / JS files

Setup & Installation
1.Clone repo
git clone https://github.com/YOUR_USERNAME/minipython.git
cd minipython

2. Create virtual environment
python -m venv .venv
source .venv/bin/activate   # macOS/Linux
.venv\Scripts\activate # Windows

3. Install dependencies
pip install -r requirements.txt

4.Set environment variables
Create a .env file:
OPENAI_API_KEY=your_api_key_here

5. Run locally
uvicorn app.main:app --reload

6.Open in browser:
http://127.0.0.1:8000

Deployment(Render)
1. Push code to Github
2. Connect Github repo to Render
3. Add Environment Variables in Render Dashboard:
   OPENAI_API_KEY
4. Set Start Command:
   uvicorn app.main:app --host 0.0.0.0 --port $PORT




