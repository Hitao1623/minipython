from datetime import datetime
from pydantic import BaseModel
from typing import List

class JobOut(BaseModel):
    id: int
    source: str
    title: str
    company: str | None
    city: str | None
    url: str
    posted_at: datetime | None
    work_mode: str | None

    class Config:
        from_attributes = True

class AIAnalyzeIn(BaseModel):
    job_id: int
    your_skills: List[str] = []


class AIAnalyzeOut(BaseModel):
    skills: List[str] = []
    years_experience_required: str
    type: str
    salary: str
