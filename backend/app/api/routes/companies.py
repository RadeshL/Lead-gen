from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.database.models import Company
from app.schemas.company import CompanyCreate, CompanyRead

router = APIRouter(prefix="/companies", tags=["companies"])

@router.get("/", response_model=list[CompanyRead])
def list_companies(
    country: str | None = None,
    industry: str | None = None,
    employee_min: int | None = None,
    employee_max: int | None = None,
    db: Session = Depends(get_db)
):
    q = db.query(Company)
    if country:
        q = q.filter(Company.country.ilike(f"%{country}%"))
    if industry:
        q = q.filter(Company.industry.ilike(f"%{industry}%"))
    if employee_min:
        q = q.filter(Company.employee_max >= employee_min)
    if employee_max:
        q = q.filter(Company.employee_min <= employee_max)
    return q.all()

@router.get("/{company_id}", response_model=CompanyRead)
def get_company(company_id: int, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company