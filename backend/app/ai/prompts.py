# app/ai/prompts.py

from app.scraping.base import ScrapedData


def build_classification_prompt(record: ScrapedData) -> str:
    lines = [
        "You are a company classification system used in a B2B lead generation platform.",
        "",
        "Classify the following company across multiple independent dimensions.",
        "Return ONLY a valid JSON object — no markdown, no explanation, no code fences.",
        "",
        "## Company Information",
        "",
    ]

    if record.name:
        lines.append(f"Name: {record.name}")
    if record.url:
        lines.append(f"Website: {record.url}")
    if record.description:
        lines.append(f"Description: {record.description}")
    if record.tagline:
        lines.append(f"Tagline: {record.tagline}")
    if record.industry:
        lines.append(f"Industry hint (from scraping): {record.industry}")
    if record.country:
        lines.append(f"Country: {record.country}")
    if record.city:
        lines.append(f"City: {record.city}")
    if record.founded_year:
        lines.append(f"Founded: {record.founded_year}")
    if record.employee_range:
        lines.append(f"Employees: {record.employee_range}")

    lines += [
        "",
        "## Classification Dimensions",
        "",

        "### 1. delivery_models",
        "How is the product/service delivered? Pick ALL that apply:",
        "  SaaS, PaaS, IaaS, On-Premise Software, Mobile App, API/SDK,",
        "  Managed Service, Consulting/Services, Hardware, Marketplace, Other",
        "",

        "### 2. business_models",
        "Who are the customers and how does money flow? Pick ALL that apply:",
        "  B2B, B2C, B2B2C, B2G (Government), C2C, D2C (Direct-to-Consumer),",
        "  Marketplace, Franchise, Open Source (commercial), Other",
        "",

        "### 3. industry",
        "The primary industry vertical. Pick the single best match:",
        "  Fintech, EdTech, HealthTech, HRTech, LegalTech, PropTech,",
        "  Logistics/Supply Chain, E-commerce, Cybersecurity, DevTools,",
        "  Marketing Tech, Analytics/BI, ERP/CRM, AI/ML Platform,",
        "  CleanTech, AgriTech, TravelTech, RetailTech, Media/Content,",
        "  Productivity, Communication, Other",
        "",

        "### 4. category",
        "A specific sub-category within the industry.",
        "Examples: 'Payroll Software', 'Learning Management System',",
        "'API Gateway', 'Fleet Management', 'Revenue Intelligence'",
        "",

        "### 5. company_stage",
        "Estimated stage based on available signals. Pick one:",
        "  Startup, Growth, Scale-up, Enterprise, Unknown",
        "",

        "### 6. confidence",
        "A float 0.0–1.0. Lower if the description is vague or missing.",
        "",

        "### 7. reasoning",
        "One sentence explaining the classification.",
        "",

        "## Required JSON format — return exactly this structure:",
        "",
        """{
    "delivery_models": ["string", ...],
    "business_models": ["string", ...],
    "industry": "string",
    "category": "string",
    "company_stage": "string",
    "confidence": float,
    "reasoning": "string"
}""",
    ]

    return "\n".join(lines)