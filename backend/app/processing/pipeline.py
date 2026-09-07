# app/processing/pipeline.py

from sqlalchemy.orm import Session
from app.database.models import SearchJob, JobStatus

def run_pipeline(job_id: int, db: Session):
    job = db.query(SearchJob).filter(SearchJob.id == job_id).first()
    if not job:
        return

    try:
        _update_job(db, job, status=JobStatus.running, stage="discovery", progress=0)

        # ── STAGE 1: Discovery ──────────────────────────────
        # TODO: plug in discovery providers here
        # candidate_urls = discovery_engine.search(job)
        _update_job(db, job, stage="discovery", progress=20)

        # ── STAGE 2: Scraping ───────────────────────────────
        # TODO: plug in BeautifulSoup scraper here
        # raw_companies = scraper.scrape_all(candidate_urls)
        _update_job(db, job, stage="scraping", progress=40)

        # ── STAGE 3: Cleaning ───────────────────────────────
        # TODO: normalise + deduplicate
        _update_job(db, job, stage="cleaning", progress=60)

        # ── STAGE 4: Enrichment ─────────────────────────────
        # TODO: employee count, LinkedIn, etc.
        _update_job(db, job, stage="enrichment", progress=75)

        # ── STAGE 5: AI Classification ──────────────────────
        # TODO: Claude API call per company
        _update_job(db, job, stage="ai", progress=90)

        _update_job(db, job, status=JobStatus.completed, stage="done", progress=100)

    except Exception as e:
        job.status = JobStatus.failed
        job.error  = str(e)
        db.commit()


def _update_job(db, job, status=None, stage=None, progress=None):
    if status:   job.status   = status
    if stage:    job.stage    = stage
    if progress: job.progress = progress
    db.commit()