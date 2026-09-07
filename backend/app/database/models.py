from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.db import Base
from sqlalchemy import Enum
import enum

class Company(Base):
    __tablename__ = "companies"

    id              = Column(Integer, primary_key=True, index=True)
    name            = Column(String, nullable=False)
    website         = Column(String, unique=True, index=True)  # domain is dedup key
    description     = Column(Text)
    country         = Column(String)
    city            = Column(String)
    employee_min    = Column(Integer)   # store ranges, not a single number
    employee_max    = Column(Integer)
    industry        = Column(String)
    is_saas         = Column(Boolean)
    business_model  = Column(String)    # B2B / B2C / B2B2C
    linkedin_url    = Column(String)
    founded_year    = Column(Integer)
    ai_confidence   = Column(Float)     # 0.0 – 1.0
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())

    sources         = relationship("Source", back_populates="company")
    enrichments     = relationship("Enrichment", back_populates="company")


class Source(Base):
    __tablename__ = "sources"

    id          = Column(Integer, primary_key=True, index=True)
    company_id  = Column(Integer, ForeignKey("companies.id"), nullable=False)
    source      = Column(String)    # "linkedin", "website", "crunchbase", etc.
    url         = Column(String)
    scraped_at  = Column(DateTime(timezone=True), server_default=func.now())

    company     = relationship("Company", back_populates="sources")


class Enrichment(Base):
    __tablename__ = "enrichments"

    id          = Column(Integer, primary_key=True, index=True)
    company_id  = Column(Integer, ForeignKey("companies.id"), nullable=False)
    field       = Column(String)        # "employee_count", "location", etc.
    value       = Column(String)
    confidence  = Column(Float)
    source      = Column(String)

    company     = relationship("Company", back_populates="enrichments")

class JobStatus(str, enum.Enum):
    pending    = "pending"
    running    = "running"
    completed  = "completed"
    failed     = "failed"

class SearchJob(Base):
    __tablename__ = "search_jobs"

    id             = Column(Integer, primary_key=True, index=True)
    query          = Column(String, nullable=False)       # raw user query
    status         = Column(Enum(JobStatus), default=JobStatus.pending)
    stage          = Column(String, default="queued")    # "discovery", "scraping", "enrichment", "ai", "done"
    progress       = Column(Integer, default=0)          # 0–100
    error          = Column(Text, nullable=True)

    # parsed filters — stored so the worker can use them
    country        = Column(String, nullable=True)
    industry       = Column(String, nullable=True)
    employee_min   = Column(Integer, nullable=True)
    employee_max   = Column(Integer, nullable=True)
    city           = Column(String, nullable=True)

    created_at     = Column(DateTime(timezone=True), server_default=func.now())
    updated_at     = Column(DateTime(timezone=True), onupdate=func.now())