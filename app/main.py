# app/main.py
import asyncio
from datetime import datetime, timedelta
from fastapi import FastAPI, Depends, Query, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import or_

from .config import settings
from .db import Base, engine, SessionLocal
from .models import Job
from .schemas import JobOut, AIAnalyzeIn, AIAnalyzeOut
from .services.ingest import fetch_all, upsert_jobs
from .services.ai import analyze

app = FastAPI(title="Canada Developer Jobs")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
tpl = Jinja2Templates(directory="app/templates")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.on_event("startup")
async def on_start():
    Base.metadata.create_all(bind=engine)
    # 启动先抓一批，避免空白
    try:
        await cron_ingest()
    except Exception as e:
        print(f"[ingest] startup ingest failed: {e}")
    # 间隔抓取
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
    days: int = Query(3, ge=1, le=30),
    city: str = Query("Canada (All)"),
    mode: str | None = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Job).filter(Job.country == "CA")
    if city and not city.startswith("Canada"):
        q = q.filter(Job.city == city.split(",")[0].strip())
    since = datetime.utcnow() - timedelta(days=days)
    # posted_at 为 NULL 或 >= since 都保留
    q = q.filter(or_(Job.posted_at.is_(None), Job.posted_at >= since))
    if mode:
        q = q.filter(Job.work_mode == mode)
    q = q.order_by(Job.created_at.desc()).limit(300)
    return [JobOut.model_validate(x) for x in q.all()]

@app.post("/api/ai/analyze", response_model=AIAnalyzeOut)
def api_ai_analyze(payload: AIAnalyzeIn, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == payload.job_id).first()
    if not job:
        raise HTTPException(404, "job not found")
    # 关键改动：把职位页 URL 传给 analyze，让其抓整页文本进行抽取
    res = analyze(
        job.description or f"{job.title} at {job.company}",
        payload.your_skills,
        url=job.url,  # <—— 新增
    )
    return AIAnalyzeOut(**res)

@app.post("/api/ingest/once")
async def ingest_once(city: str | None = None, days: int = 3, db: Session = Depends(get_db)):
    items = await fetch_all(city=city, days=days)
    added = upsert_jobs(db, items)
    return {"added": added}
