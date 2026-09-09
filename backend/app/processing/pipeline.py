# app/processing/pipeline.py

import asyncio
from urllib.parse import urlparse
from sqlalchemy.orm import Session

from app.database.models  import SearchJob, JobStatus, Company, Source
from app.database.db      import SessionLocal
from app.discovery.engine import DiscoveryEngine
from app.processing.query_process import ParsedQuery
from app.scraping.scraper         import scrape_all
from app.processing.cleaner       import clean
from app.processing.deduplicator  import deduplicate
from app.enrichment.engine        import enrich_all
from app.ai.classifier            import classify_all
from app.scraping.base            import ScrapedData
from app.ai.classifier            import ClassificationResult


def run_pipeline(job_id: int, db: Session):
    job = db.query(SearchJob).filter(SearchJob.id == job_id).first()
    if not job:
        return

    try:
        _update_job(db, job, status=JobStatus.running, stage="discovery", progress=0)

        # ── STAGE 1: Discovery ──────────────────────────────
        parsed     = ParsedQuery(job.query)                  # ← use the actual parser
        engine     = DiscoveryEngine()
        candidates = asyncio.run(engine.discover(parsed))
        _update_job(db, job, stage="discovery", progress=20)
        print(f"[pipeline] discovered {len(candidates)} candidates")

        # ── STAGE 2: Scraping ───────────────────────────────
        _update_job(db, job, stage="scraping", progress=25)
        scraped    = asyncio.run(scrape_all(candidates))
        successful = [s for s in scraped if s.scrape_success]
        print(f"[pipeline] scraped {len(successful)}/{len(scraped)} successfully")
        _update_job(db, job, stage="scraping", progress=40)

        # ── STAGE 3: Cleaning ───────────────────────────────
        _update_job(db, job, stage="cleaning", progress=41)
        cleaned      = clean(successful)
        deduplicated = deduplicate(cleaned)
        print(f"[pipeline] after cleaning: {len(deduplicated)} companies")
        _update_job(db, job, stage="cleaning", progress=60)

        # ── STAGE 4: Enrichment ─────────────────────────────
        _update_job(db, job, stage="enrichment", progress=61)
        enriched = asyncio.run(enrich_all(deduplicated))
        print(f"[pipeline] enrichment done: {len(enriched)} companies")
        _update_job(db, job, stage="enrichment", progress=75)

        # ── STAGE 5: AI Classification ──────────────────────
        _update_job(db, job, stage="ai", progress=76)
        classifications = asyncio.run(classify_all(enriched))
        print(f"[pipeline] AI classification done")
        _update_job(db, job, stage="ai", progress=90)

        # ── STAGE 6: Save to database ───────────────────────
        _update_job(db, job, stage="saving", progress=91)
        saved = _save_companies(db, enriched, classifications)
        print(f"[pipeline] saved {saved} companies to database")

        _update_job(db, job, status=JobStatus.completed, stage="done", progress=100)

    except Exception as e:
        print(f"[pipeline] fatal error: {e}")
        job.status = JobStatus.failed
        job.error  = str(e)
        db.commit()


# ── DB save ───────────────────────────────────────────────────────────────────

def _save_companies(
    db: Session,
    records: list[ScrapedData],
    classifications: list[ClassificationResult],
) -> int:
    from urllib.parse import urlparse

    saved = 0

    for record, cl in zip(records, classifications):
        try:
            domain   = _extract_domain(record.url)
            existing = db.query(Company).filter(Company.website == domain).first()
            company  = existing or Company(website=domain)

            if not existing:
                db.add(company)

            # ── Scraping + enrichment fields ──────────────────
            company.name         = record.name
            company.description  = record.description
            company.country      = record.country
            company.city         = record.city
            company.employee_min = record.employee_min
            company.employee_max = record.employee_max
            company.linkedin_url = record.linkedin_url
            company.founded_year = record.founded_year

            # ── AI classification fields ───────────────────────
            if cl.ai_error is None:
                company.industry        = cl.industry
                company.category        = cl.category
                company.company_stage   = cl.company_stage
                company.ai_confidence   = cl.confidence

                # Store lists as CSV strings — simple, queryable
                company.delivery_models = ",".join(cl.delivery_models)
                company.business_models = ",".join(cl.business_models)

                # Backward-compat helpers
                company.is_saas        = "SaaS" in cl.delivery_models
                company.business_model = cl.business_models[0] if cl.business_models else None

            db.flush()

            # ── Source row ────────────────────────────────────
            db.add(Source(
                company_id = company.id,
                source     = record.source_name or "scraper",
                url        = record.url,
            ))

            # ── Enrichment provenance rows ────────────────────
            _save_enrichments(db, company.id, record, cl)

            saved += 1

        except Exception as e:
            print(f"[pipeline] failed to save {record.url}: {e}")
            db.rollback()
            continue

    db.commit()
    return saved


def _save_enrichments(db, company_id, record, cl):
    from app.database.models import Enrichment

    rows = []

    if record.employee_min is not None:
        rows.append(Enrichment(
            company_id = company_id,
            field      = "employee_count",
            value      = record.employee_range or f"{record.employee_min}-{record.employee_max}",
            confidence = 0.85,
            source     = "linkedin/glassdoor",
        ))

    if cl.ai_error is None:
        if cl.delivery_models:
            rows.append(Enrichment(
                company_id = company_id,
                field      = "delivery_models",
                value      = ", ".join(cl.delivery_models),
                confidence = cl.confidence,
                source     = "gemini-1.5-flash",
            ))
        if cl.business_models:
            rows.append(Enrichment(
                company_id = company_id,
                field      = "business_models",
                value      = ", ".join(cl.business_models),
                confidence = cl.confidence,
                source     = "gemini-1.5-flash",
            ))
        if cl.reasoning:
            rows.append(Enrichment(
                company_id = company_id,
                field      = "ai_reasoning",
                value      = cl.reasoning,
                confidence = cl.confidence,
                source     = "gemini-1.5-flash",
            ))

    for row in rows:
        db.add(row)


def _extract_domain(url: str) -> str:
    try:
        host = urlparse(url.lower()).netloc or url
        return host.removeprefix("www.").split("/")[0]
    except Exception:
        return url.lower()


def _update_job(db, job, status=None, stage=None, progress=None):
    if status:              job.status   = status
    if stage:               job.stage    = stage
    if progress is not None: job.progress = progress
    db.commit()