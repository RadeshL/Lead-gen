# app/api/routes/export.py

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.database.models import Company
import csv, io

router = APIRouter(prefix="/export", tags=["export"])

@router.get("/companies")
def export_companies(db: Session = Depends(get_db)):
    companies = db.query(Company).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "name", "website", "country", "city",
        "employee_min", "employee_max", "industry",
        "is_saas", "business_model", "linkedin_url",
        "ai_confidence"
    ])
    for c in companies:
        writer.writerow([
            c.name, c.website, c.country, c.city,
            c.employee_min, c.employee_max, c.industry,
            c.is_saas, c.business_model, c.linkedin_url,
            c.ai_confidence
        ])

    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=companies.csv"}
    )