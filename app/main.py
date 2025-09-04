# app/main.py
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, Depends, Query, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from sqlalchemy import or_
from sqlalchemy.orm import Session
from sqlalchemy.engine.url import make_url

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from .config import settings
from .db import Base, engine, SessionLocal
from .models import Job
from .schemas import JobOut, AIAnalyzeIn, AIAnalyzeOut
from .services.ingest import fetch_all, upsert_jobs
from .services.ai import analyze


BASE_DIR = Path(__file__).resolve().parent        # app/
STATIC_DIR = BASE_DIR / "static"                  # app/static
TEMPLATES_DIR = BASE_DIR / "templates"            # app/templates

app = FastAPI(title="Canada Developer Jobs")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
tpl = Jinja2Templates(directory=str(TEMPLATES_DIR))

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.on_event("startup")
async def on_start():
    try:
        url = make_url(str(engine.url))
        if url.get_backend_name() == "sqlite" and url.database:
            db_path = Path(url.database).resolve()
            print(f"[DB] Using SQLite at: {db_path} (exists={db_path.exists()})")
    except Exception as e:
        print("[DB] failed to resolve db path:", e)

    Base.metadata.create_all(bind=engine)

    try:
        await cron_ingest()
    except Exception as e:
        print(f"[ingest] startup ingest failed: {e}")

    sched = AsyncIOScheduler()
    sched.add_job(lambda: asyncio.create_task(cron_ingest()), "interval", hours=6)
    sched.start()


async def cron_ingest():
    items = await fetch_all(city=None, days=3)
    with SessionLocal() as db:
        added = upsert_jobs(db, items)
        print(f"[ingest] added: {added}")


@app.get("/", response_class=HTMLResponse)
async def index(req: Request):
    return tpl.TemplateResponse("index.html", {"request": req, "cities": settings.CITIES})


@app.get("/api/jobs", response_model=list[JobOut])
def api_jobs(
    response: Response,
    days: int = Query(3, ge=1, le=30),
    city: str = Query("Canada (All)"),
    mode: str | None = Query(None),
    q: str | None = Query(None, description="keyword search: title/company/city/description"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    base_q = db.query(Job).filter(Job.country == "CA")

    if city and not city.startswith("Canada"):
        base_q = base_q.filter(Job.city == city.split(",")[0].strip())

    since = datetime.utcnow() - timedelta(days=days)
    base_q = base_q.filter(or_(Job.posted_at.is_(None), Job.posted_at >= since))

    if mode:
        base_q = base_q.filter(Job.work_mode == mode)

    if q:
        kw = f"%{q.strip()}%"
        base_q = base_q.filter(
            or_(
                Job.title.ilike(kw),
                Job.company.ilike(kw),
                Job.city.ilike(kw),
                Job.description.ilike(kw),
            )
        )

    total = base_q.count()
    response.headers["X-Total-Count"] = str(total)

    offset = (page - 1) * page_size
    rows = (
        base_q.order_by(Job.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )
    return [JobOut.model_validate(x) for x in rows]


@app.post("/api/ai/analyze", response_model=AIAnalyzeOut)
def api_ai_analyze(payload: AIAnalyzeIn, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == payload.job_id).first()
    if not job:
        raise HTTPException(404, "job not found")
    res = analyze(
        job.description or f"{job.title} at {job.company}",
        payload.your_skills,
        url=job.url,
    )
    return AIAnalyzeOut(**res)

@app.post("/api/ingest/once")
async def ingest_once(city: str | None = None, days: int = 3, db: Session = Depends(get_db)):
    items = await fetch_all(city=city, days=days)
    added = upsert_jobs(db, items)
    return {"added": added}
