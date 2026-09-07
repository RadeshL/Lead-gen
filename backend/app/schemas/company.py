from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CompanyBase(BaseModel):
    name: str
    website: Optional[str]
    description: Optional[str]
    country: Optional[str]
    city: Optional[str]
    employee_min: Optional[int]
    employee_max: Optional[int]
    industry: Optional[str]
    is_saas: Optional[bool]
    business_model: Optional[str]
    linkedin_url: Optional[str]
    ai_confidence: Optional[float]

class CompanyCreate(CompanyBase):
    pass

class CompanyRead(CompanyBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True  # lets Pydantic read SQLAlchemy objects