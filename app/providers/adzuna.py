# app/providers/adzuna.py
import httpx
from datetime import datetime, timedelta, timezone
from tenacity import retry, wait_exponential, stop_after_attempt
from .base import JobItem, Provider
from ..config import settings

ADZUNA_ENDPOINT = "https://api.adzuna.com/v1/api/jobs/ca/search/1"

def _norm_city(loc: str | None) -> str | None:
    if not loc:
        return None
    return loc.split(",")[0].strip()

def _work_mode_from_text(text: str) -> str:
    t = (text or "").lower()
    if "remote" in t or "work from home" in t:
        return "remote"
    if "hybrid" in t:
        return "hybrid"
    if "on-site" in t or "onsite" in t:
        return "onsite"
    return "unknown"

def _parse_created(val):
    if isinstance(val, (int, float)):
        return datetime.fromtimestamp(val, tz=timezone.utc)
    if isinstance(val, str):
        try:
            return datetime.fromisoformat(val.replace("Z", "+00:00"))
        except Exception:
            return None
    return None

class AdzunaProvider(Provider):
    name = "adzuna"

    @retry(wait=wait_exponential(min=1, max=8), stop=stop_after_attempt(3))
    async def _fetch(self, params: dict) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(ADZUNA_ENDPOINT, params=params)
            r.raise_for_status()
            return r.json()

    async def search(self, *, titles: list[str], city: str | None, days: int):
        results: list[JobItem] = []
        where_val = None if (not city or city.startswith("Canada")) else city
        since = datetime.now(timezone.utc) - timedelta(days=days)

        seen_ids = set()

        for title in titles:
            params = {
                "app_id": settings.ADZUNA_APP_ID,
                "app_key": settings.ADZUNA_APP_KEY,
                "what": title,
                "results_per_page": 50,
                "sort_by": "date",
                "content-type": "application/json",
            }
            if where_val:
                params["where"] = where_val

            data = await self._fetch(params)
            for it in data.get("results", []):
                sid = str(it.get("id"))
                if sid in seen_ids:
                    continue
                seen_ids.add(sid)

                created = _parse_created(it.get("created"))
                if created and created < since:
                    continue

                desc = it.get("description") or ""
                results.append(JobItem(
                    source=self.name,
                    source_job_id=sid,
                    title=it.get("title"),
                    company=(it.get("company") or {}).get("display_name"),
                    location=it.get("location", {}).get("display_name"),
                    city=_norm_city(it.get("location", {}).get("display_name")),
                    country="CA",
                    url=it.get("redirect_url") or "",
                    description=desc,
                    posted_at=created,
                    work_mode=_work_mode_from_text(desc),
                    salary_min=it.get("salary_min"),
                    salary_max=it.get("salary_max"),
                    currency="CAD",
                ))
        return results
