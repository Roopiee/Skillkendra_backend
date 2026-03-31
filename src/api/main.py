"""
FastAPI Application for OCR Pipeline
"""

import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(
    title="SkillKendra OCR Pipeline",
    description="OCR and Playwright processing pipeline for certificates",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import routes
from src.api import routes

app.include_router(routes.router, prefix="/api", tags=["verification"])

@app.get("/")
async def root():
    return {
        "message": "SkillKendra OCR Pipeline",
        "features": ["OCR", "Forensics", "Verification"],
        "docs": "/docs"
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
