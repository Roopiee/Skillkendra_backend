# Import statements - bring in tools we need
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from enum import Enum
from datetime import datetime

class OCREngine(str, Enum):
    PADDLE = "paddle"
    EASY = "easy"
    TESSERACT = "tesseract"

class OCRResult(BaseModel):
    """
    Normalized output from any OCR engine.
    
    This is what EVERY OCR engine must return,
    regardless of its internal format.
    """
    engine: OCREngine           # Which OCR produced this
    raw_lines: List[str]        # Extracted text, line by line
    confidence: float = Field(ge=0.0, le=1.0)  # Between 0 and 1
    page_number: int            # Which page of the document

class ExtractedEvidence(BaseModel):
    """
    Structured information extracted by Mistral from OCR text.
    
    This is what Mistral produces after reasoning over raw OCR output.
    """
    engine: OCREngine                          # Source OCR engine
    issuer: Optional[str] = None               # E.g., "Udemy", "Coursera"
    certificate_ids: List[str] = Field(default_factory=list)
    urls: List[str] = Field(default_factory=list)
    names: List[str] = Field(default_factory=list)
    confidence: float
    page_number: int

class VerificationResult(BaseModel):
    """
    Final output of the entire pipeline.
    
    This is what you return to the user/API caller.
    """
    final_verdict: Literal["VERIFIED", "UNVERIFIED", "ERROR"]
    verified_via: Optional[dict] = None
    confidence: float
    evidence_used: List[ExtractedEvidence]
    timestamp: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "final_verdict": "VERIFIED",
                "verified_via": {
                    "engine": "paddle",
                    "method": "url_check",
                    "value": "https://ude.my/UC-12345"
                },
                "confidence": 0.95,
                "evidence_used": [],
                "timestamp": "2025-12-16T10:30:00"
            }
        }