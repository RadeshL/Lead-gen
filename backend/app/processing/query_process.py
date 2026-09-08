import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from gliner import GLiNER

MODEL_ID = "urchade/gliner_medium-v2.1"
MODEL_CACHE_DIR = (
    Path(os.getenv("HF_HOME", Path.home() / ".cache" / "huggingface"))
    / "hub"
    / "models--urchade--gliner_medium-v2.1"
)

ENTITY_LABELS = [
    "country",
    "city",
    "industry",
    "employee count",
    "employee range",
    "company name",
    "business model",
    "founded year",
    "location",
    "website",
]

_model: Optional[GLiNER] = None


@dataclass(frozen=True)
class ClassifiedEntity:
    text: str
    label: str
    score: float
    start: int
    end: int


@dataclass
class ParsedQuery:
    country: Optional[str] = None
    city: Optional[str] = None
    industry: Optional[str] = None
    employee_min: Optional[int] = None
    employee_max: Optional[int] = None
    entities: list[ClassifiedEntity] = field(default_factory=list)


def parse_query(query: str) -> ParsedQuery:
    """Classify every entity in a lead-generation query with GLiNER.

    Entity types are supplied to GLiNER at inference time. No project-specific
    keyword dictionaries or model training are used.
    """
    if not query or not query.strip():
        return ParsedQuery()

    predictions = _get_model().predict_entities(
        query,
        ENTITY_LABELS,
        threshold=0.50,
    )
    entities = [_to_entity(prediction) for prediction in predictions]
    return _to_parsed_query(entities)


def _get_model() -> GLiNER:
    global _model
    if _model is None:
        _model = GLiNER.from_pretrained(
            MODEL_ID,
            cache_dir=str(MODEL_CACHE_DIR.parent),
            local_files_only=True,
            map_location="cpu",
        )
        _model.eval()
    return _model


def _to_entity(prediction: dict[str, Any]) -> ClassifiedEntity:
    return ClassifiedEntity(
        text=str(prediction["text"]),
        label=str(prediction["label"]).lower(),
        score=float(prediction["score"]),
        start=int(prediction["start"]),
        end=int(prediction["end"]),
    )


def _to_parsed_query(entities: list[ClassifiedEntity]) -> ParsedQuery:
    result = ParsedQuery(entities=entities)
    for entity in entities:
        if entity.label == "country" and result.country is None:
            result.country = entity.text
        elif entity.label == "city" and result.city is None:
            result.city = entity.text
        elif entity.label == "industry" and result.industry is None:
            result.industry = entity.text
        elif entity.label in {"employee count", "employee range"}:
            _set_employee_bounds(result, entity.text)
    return result


def _set_employee_bounds(result: ParsedQuery, value: str) -> None:
    """Read numeric bounds from the text selected by GLiNER."""
    numbers = [int(part) for part in value.replace("-", " ").split() if part.isdigit()]
    if len(numbers) >= 2:
        result.employee_min, result.employee_max = numbers[0], numbers[1]
    elif numbers:
        result.employee_min = numbers[0]
