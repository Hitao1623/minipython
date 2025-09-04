from __future__ import annotations
from sqlalchemy.orm import Session
from rapidfuzz import fuzz
import hashlib
from ..config import settings
from ..models import Job
from ..providers.adzuna import AdzunaProvider

async def fetch_all(city: str | None, days: int) -> list[dict]:

    provider = AdzunaProvider()
    items = await provider.search(
        titles=settings.DEFAULT_TITLES,
        city=city,
        days=days,
    )
    return items

def make_dedup_key(title: str | None, company: str | None, city: str | None) -> str:
    s = f"{(title or '').lower()}|{(company or '').lower()}|{(city or '').lower()}"
    return hashlib.sha1(s.encode()).hexdigest()


def similar(a: str | None, b: str | None) -> bool:
    return fuzz.token_set_ratio(a or "", b or "") > 92


def _unique_by_source_id(items: list[dict]) -> list[dict]:
    seen: set[tuple[str | None, str | None]] = set()
    out: list[dict] = []
    for it in items:
        key = (it.get("source"), it.get("source_job_id"))
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out


def upsert_jobs(db: Session, items: list[dict]) -> int:
    if not items:
        return 0

    items = _unique_by_source_id(items)

    src_ids = [
        (it["source"], it["source_job_id"])
        for it in items
        if it.get("source") and it.get("source_job_id")
    ]
    existing_keys: set[tuple[str, str]] = set()
    if src_ids:
        CHUNK = 500
        for i in range(0, len(src_ids), CHUNK):
            chunk = src_ids[i : i + CHUNK]
            sources = [c[0] for c in chunk]
            ids = [c[1] for c in chunk]
            q = (
                db.query(Job.source, Job.source_job_id)
                .filter(Job.source.in_(sources), Job.source_job_id.in_(ids))
            )
            existing_keys.update((s, sid) for s, sid in q.all())

    added = 0
    for it in items:
        src = it.get("source")
        sid = it.get("source_job_id")
        if not src or not sid:
            continue
        if (src, sid) in existing_keys:
            continue

        dedup = make_dedup_key(it.get("title"), it.get("company"), it.get("city"))
        if db.query(Job.id).filter(Job.dedup_key == dedup).first():
            continue

        job = Job(
            source=src,
            source_job_id=sid,
            title=it.get("title"),
            company=it.get("company"),
            location=it.get("location"),
            city=it.get("city"),
            country=it.get("country", "CA"),
            url=it.get("url"),
            description=it.get("description"),
            posted_at=it.get("posted_at"),
            work_mode=it.get("work_mode", "unknown"),
            salary_min=it.get("salary_min"),
            salary_max=it.get("salary_max"),
            currency=it.get("currency"),
            dedup_key=dedup,
        )
        db.add(job)
        added += 1

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    return added
