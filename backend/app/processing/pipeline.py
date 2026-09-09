import asyncio
from sqlalchemy.orm import Session
from app.database.models import SearchJob, JobStatus
from app.discovery.engine import DiscoveryEngine
from backend.app.processing.query_process import ParsedQuery
from app.scraping.scraper import scrape_all

def run_pipeline(job_id: int, db: Session):
    job = db.query(SearchJob).filter(SearchJob.id == job_id).first()
    if not job:
        return

    try:
        _update_job(db, job, status=JobStatus.running, stage="discovery", progress=0)

        # ── STAGE 1: Discovery ──────────────────────────────
        parsed = ParsedQuery(
            country=job.country,
            city=job.city,
            industry=job.industry,
            employee_min=job.employee_min,
            employee_max=job.employee_max,
        )
        engine = DiscoveryEngine()
        candidates = asyncio.run(engine.discover(parsed))
        _update_job(db, job, stage="discovery", progress=20)

        print(f"[pipeline] discovered {len(candidates)} candidates")

        # ── STAGE 2: Scraping ───────────────────────────────
        _update_job(db, job, stage="scraping", progress=25)
        scraped = asyncio.run(scrape_all(candidates))
        # Only keep successful scrapes
        successful = [s for s in scraped if s.scrape_success]
        print(f"[pipeline] scraped {len(successful)}/{len(scraped)} successfully")
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