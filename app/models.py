from sqlalchemy import Column, Integer, String, DateTime, Text, Float, UniqueConstraint
from sqlalchemy.sql import func
from .db import Base

class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True)
    source = Column(String(50), index=True)
    source_job_id = Column(String(200), index=True)
    title = Column(String(300), index=True)
    company = Column(String(300), index=True)
    location = Column(String(300), index=True)
    city = Column(String(120), index=True)
    country = Column(String(50), default="CA", index=True)
    url = Column(String(1000))
    description = Column(Text)
    posted_at = Column(DateTime(timezone=True), index=True)
    work_mode = Column(String(20), index=True)
    salary_min = Column(Float, nullable=True)
    salary_max = Column(Float, nullable=True)
    currency = Column(String(10), nullable=True)
    dedup_key = Column(String(300), index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("source", "source_job_id", name="uq_source_job"),
    )
