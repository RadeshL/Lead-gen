from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.database.models import JobStatus

class SearchRequest(BaseModel):
    query: str

class SearchJobRead(BaseModel):
    id: int
    query: str
    status: JobStatus
    stage: str
    progress: int
    error: Optional[str]
    country: Optional[str]
    industry: Optional[str]
    employee_min: Optional[int]
    employee_max: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True