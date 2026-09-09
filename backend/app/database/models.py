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
    website         = Column(String, unique=True, index=True)
    description     = Column(Text)
    country         = Column(String)
    city            = Column(String)
    employee_min    = Column(Integer)
    employee_max    = Column(Integer)
    industry        = Column(String)
    category        = Column(String)              # ← new: specific sub-category
    company_stage   = Column(String)              # ← new: Startup / Growth / etc.
    delivery_models = Column(String)              # ← new: "SaaS,API/SDK" (CSV)
    business_models = Column(String)              # ← new: "B2B,B2B2C" (CSV)
    is_saas         = Column(Boolean)             # ← kept for backward compat
    business_model  = Column(String)              # ← kept for backward compat
    linkedin_url    = Column(String)
    founded_year    = Column(Integer)
    ai_confidence   = Column(Float)
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