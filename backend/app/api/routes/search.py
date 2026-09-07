# app/api/routes/search.py

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.database.models import SearchJob
from app.schemas.search import SearchRequest, SearchJobRead
from app.processing.query_parser import parse_query
from app.processing.pipeline import run_pipeline

router = APIRouter(prefix="/search", tags=["search"])

@router.post("/", response_model=SearchJobRead)
def create_search(
    request: SearchRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    parsed = parse_query(request.query)

    job = SearchJob(
        query        = request.query,
        country      = parsed.country,
        industry     = parsed.industry,
        employee_min = parsed.employee_min,
        employee_max = parsed.employee_max,
        city         = parsed.city,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # run pipeline in background — doesn't block the HTTP response
    background_tasks.add_task(run_pipeline, job.id, db)

    return job


@router.get("/{job_id}", response_model=SearchJobRead)
def get_job_status(job_id: int, db: Session = Depends(get_db)):
    job = db.query(SearchJob).filter(SearchJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/{job_id}/results")
def get_job_results(job_id: int, db: Session = Depends(get_db)):
    job = db.query(SearchJob).filter(SearchJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    # TODO: return companies associated with this job
    # For now, return all companies matching the job's filters
    from app.database.models import Company
    q = db.query(Company)
    if job.country:      q = q.filter(Company.country == job.country)
    if job.industry:     q = q.filter(Company.industry == job.industry)
    if job.employee_min: q = q.filter(Company.employee_max >= job.employee_min)
    if job.employee_max: q = q.filter(Company.employee_min <= job.employee_max)
    return q.all()