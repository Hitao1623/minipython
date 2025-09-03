from typing import Protocol, Iterable
from datetime import datetime

class JobItem(dict):
    # source, source_job_id, title, company, location, city, country, url, description, posted_at, work_mode, salary_min/max, currency
    pass

class Provider(Protocol):
    name: str
    async def search(self, *, titles: list[str], city: str | None, days: int) -> Iterable[JobItem]:
        ...
