# app/ai/classifier.py

import json
import asyncio
import re
from dataclasses import dataclass, field
from typing import Optional

import google.generativeai as genai

from app.config import settings
from app.scraping.base import ScrapedData
from app.ai.prompts import build_classification_prompt


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class ClassificationResult:
    delivery_models: list[str]     = field(default_factory=list)
    business_models: list[str]     = field(default_factory=list)
    industry:        Optional[str] = None
    category:        Optional[str] = None
    company_stage:   Optional[str] = None
    confidence:      float         = 0.0
    reasoning:       Optional[str] = None
    ai_error:        Optional[str] = None

    def is_type(self, label: str) -> bool:
        """
        Convenience check — works for any label across both lists.
        e.g. result.is_type("SaaS"), result.is_type("B2B")
        """
        label_lower = label.lower()
        combined = [x.lower() for x in self.delivery_models + self.business_models]
        return label_lower in combined


# ── Gemini client ─────────────────────────────────────────────────────────────

_model = None

def _get_model():
    global _model
    if _model is None:
        if not settings.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY is not set in .env")
        genai.configure(api_key=settings.GEMINI_API_KEY)
        _model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config={
                "temperature": 0.1,
                "max_output_tokens": 400,
            },
        )
    return _model


# ── JSON extraction ───────────────────────────────────────────────────────────

def _extract_json(text: str) -> dict:
    text = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("```").strip()
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object in response: {text[:200]}")
    return json.loads(match.group(0))


def _parse_response(raw: dict) -> ClassificationResult:

    def safe_list(val) -> list[str]:
        if isinstance(val, list):
            return [str(x).strip() for x in val if x]
        if isinstance(val, str):
            return [val.strip()] if val.strip() else []
        return []

    def safe_float(val, default=0.0) -> float:
        try:
            return max(0.0, min(1.0, float(val)))
        except (TypeError, ValueError):
            return default

    return ClassificationResult(
        delivery_models = safe_list(raw.get("delivery_models")),
        business_models = safe_list(raw.get("business_models")),
        industry        = str(raw["industry"]).strip()      if raw.get("industry")      else None,
        category        = str(raw["category"]).strip()      if raw.get("category")      else None,
        company_stage   = str(raw["company_stage"]).strip() if raw.get("company_stage") else None,
        confidence      = safe_float(raw.get("confidence"), default=0.5),
        reasoning       = str(raw["reasoning"]).strip()     if raw.get("reasoning")     else None,
    )


# ── Single company ────────────────────────────────────────────────────────────

async def classify_one(record: ScrapedData) -> ClassificationResult:
    try:
        prompt   = build_classification_prompt(record)
        model    = _get_model()
        response = await asyncio.to_thread(model.generate_content, prompt)
        raw      = _extract_json(response.text)
        return _parse_response(raw)

    except Exception as e:
        print(f"[ai] failed for {record.url}: {e}")
        return ClassificationResult(ai_error=str(e))


# ── Batch ─────────────────────────────────────────────────────────────────────

async def classify_all(
    records: list[ScrapedData],
    concurrency: int = 5,
) -> list[ClassificationResult]:

    if not settings.GEMINI_API_KEY:
        print("[ai] GEMINI_API_KEY not set — skipping classification")
        return [ClassificationResult() for _ in records]

    semaphore = asyncio.Semaphore(concurrency)

    async def limited(record: ScrapedData) -> ClassificationResult:
        async with semaphore:
            result = await classify_one(record)
            await asyncio.sleep(0.5)   # Gemini free tier: 15 RPM
            return result

    results = await asyncio.gather(*[limited(r) for r in records])

    classified = sum(1 for r in results if r.ai_error is None and r.industry is not None)
    print(f"[ai] classified {classified}/{len(results)} successfully")
    return list(results)