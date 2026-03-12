"""Data schemas for verification system"""
from pydantic import BaseModel
from typing import Optional
from enum import Enum


class IssuerName(str, Enum):
    UDEMY = "Udemy"
    COURSERA = "Coursera"
    EDX = "edX"
    LINKEDIN = "LinkedIn Learning"
    GOOGLE = "Google"
    IBM = "IBM"
    MICROSOFT = "Microsoft"
    CREDLY = "Credly"
    UNKNOWN = "Unknown"


class ExtractionResult(BaseModel):
    """Data extracted from certificate (from Mistral)"""
    candidate_name: Optional[str] = None
    issuer_name: Optional[IssuerName] = None
    issuer_org: Optional[str] = None
    issuer_url: Optional[str] = None
    certificate_id: Optional[str] = None
    course_name: Optional[str] = None
    completion_date: Optional[str] = None


class VerificationResult(BaseModel):
    """Result from verification agent"""
    is_verified: bool
    trusted_domain: bool
    confidence_score: float = 0.0
    verification_url: Optional[str] = None
    method: str
    message: str
