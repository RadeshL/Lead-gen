from fastapi import FastAPI
from app.api.routes import companies, search, export

app = FastAPI(title="LeadGen API")
app.include_router(companies.router, prefix="/api")

app.include_router(companies.router, prefix="/api")
app.include_router(search.router,    prefix="/api")
app.include_router(export.router,    prefix="/api")

@app.get("/")
def root():
    return {
        "message": "LeadGen API is running!",
        "docs": "/docs",
        "health": "/health",
        "api": "/api"
    }
    
@app.get("/health")
def health():
    return {"status": "ok"}