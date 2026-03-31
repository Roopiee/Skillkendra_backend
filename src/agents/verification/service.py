"""
Verification service integrated with OCR + Mistral pipeline
"""
import logging
import re
from difflib import SequenceMatcher
from typing import Optional, Tuple, Dict, Any

from src.core.schemas import ExtractionResult, VerificationResult, IssuerName
from src.core.config import config
from src.agents.verification.sources import TrustedSourceRegistry
from src.agents.verification.scanner import fetch_page_text
from src.agents.verification.visual import VisualVerifier

logger = logging.getLogger(__name__)

class VerificationService:
    def __init__(self):
        self.registry = TrustedSourceRegistry()
        self.visual = VisualVerifier()

    def _fuzzy_match(self, candidate: str, page_text: str, threshold: float = 0.7) -> Tuple[bool, float]:
        if not candidate or not page_text: 
            return False, 0.0
        cand_clean = re.sub(r'[^a-z0-9\s]', '', candidate.lower())
        text_clean = re.sub(r'[^a-z0-9\s]', '', page_text.lower())
        if cand_clean in text_clean: 
            return True, 1.0
        ratio = SequenceMatcher(None, cand_clean, text_clean).ratio()
        return ratio >= threshold, ratio

    def verify_from_evidence(self, evidence_data: dict) -> ExtractionResult:
        """
        Convert evidence from Mistral to ExtractionResult format
        
        Args:
            evidence_data: Dictionary from Mistral with extracted data
            
        Returns:
            ExtractionResult formatted for verification
        """
        def _to_str(val):
            if isinstance(val, dict):
                return str(next(iter(val.values()))) if val else None
            if isinstance(val, list):
                return str(val[0]) if val else None
            return str(val) if val else None

        # Map issuer string to enum
        raw_issuer = evidence_data.get('issuer')
        issuer_str = (_to_str(raw_issuer) or '').lower()
        issuer_enum = IssuerName.UNKNOWN
        
        for enum_val in IssuerName:
            if enum_val.value.lower() in issuer_str:
                issuer_enum = enum_val
                break
        
        # Get URLs and IDs
        urls = evidence_data.get('urls', [])
        if isinstance(urls, dict):
            urls = list(urls.values())
        
        cert_ids = evidence_data.get('certificate_ids', [])
        if isinstance(cert_ids, dict):
            cert_ids = list(cert_ids.values())
        
        return ExtractionResult(
            candidate_name=_to_str(evidence_data.get('candidate_name')),
            issuer_name=issuer_enum,
            issuer_org=_to_str(raw_issuer),
            issuer_url=urls[0] if urls else None,
            certificate_id=cert_ids[0] if cert_ids else None,
            course_name=_to_str(evidence_data.get('course_name')),
            completion_date=_to_str(evidence_data.get('completion_date'))
        )

    async def verify(self, data: ExtractionResult) -> VerificationResult:
        """Main verification method"""
        # A. Validation
        if not data.candidate_name:
            return VerificationResult(
                is_verified=False, 
                trusted_domain=False, 
                message="No candidate name.", 
                method="validation_error"
            )

        # B. Get URLs
        org_name_str = data.issuer_name.value if data.issuer_name else (data.issuer_org or "")
        urls = self.registry.generate_urls(data.issuer_url, data.certificate_id, org_name_str)
        
        if not urls:
            return VerificationResult(
                is_verified=False, 
                trusted_domain=False, 
                message="No URL generated.", 
                method="url_error"
            )

        # C. Trust Check
        if not self.registry.is_trusted(urls[0]):
            return VerificationResult(
                is_verified=False, 
                trusted_domain=False, 
                verification_url=urls[0], 
                message="Untrusted domain.", 
                method="security_check"
            )

        # D. Smart Verification Loop
        best_score = 0.0
        best_url = urls[0]
        
        for url in urls[:2]:
            logger.info(f"[INFO] Scanning: {url}")
            
            # 1. Attempt Standard Scan (Fast)
            page_text, screenshot_path = await fetch_page_text(url, use_browser=True, force_browser=False)
            
            # 2. Check Text Match
            if page_text:
                is_match, score = self._fuzzy_match(data.candidate_name, page_text)
                if score > best_score: 
                    best_score = score
                
                if is_match:
                    return VerificationResult(
                        is_verified=True, 
                        trusted_domain=True, 
                        confidence_score=round(score, 2), 
                        verification_url=url, 
                        method="dom_text_match", 
                        message=f"Verified via text. Match: {score:.0%}"
                    )
            
            # 3. SMART RETRY
            if best_score < 0.7 and not screenshot_path:
                logger.info("[INFO] Text match failed on fast fetch. Forcing Browser Retry...")
                page_text, screenshot_path = await fetch_page_text(url, force_browser=True)
                
                if page_text:
                    is_match, score = self._fuzzy_match(data.candidate_name, page_text)
                    if score > best_score: 
                        best_score = score
                    if is_match:
                        return VerificationResult(
                            is_verified=True, 
                            trusted_domain=True, 
                            confidence_score=round(score, 2), 
                            verification_url=url, 
                            method="dom_text_match_retry", 
                            message=f"Verified via browser text. Match: {score:.0%}"
                        )

            # 4. Visual Fallback
            if screenshot_path:
                v_match, v_score, _ = self.visual.verify_screenshot(screenshot_path, data.candidate_name)
                if v_score > best_score: 
                    best_score = v_score
                
                if v_match:
                    return VerificationResult(
                        is_verified=True, 
                        trusted_domain=True, 
                        confidence_score=round(v_score, 2), 
                        verification_url=url, 
                        method="visual_ocr", 
                        message=f"Verified via visual OCR. Match: {v_score:.0%}"
                    )

        return VerificationResult(
            is_verified=False, 
            trusted_domain=True, 
            confidence_score=round(best_score, 2), 
            verification_url=best_url, 
            method="failed", 
            message=f"Verification failed. Best Match: {best_score:.0%}"
        )

    async def manual_verify(self, certificate_id: str, issuer_url: str) -> VerificationResult:
        """Manual verification using ID and URL"""
        logger.info(f"Manual Verification: {certificate_id} @ {issuer_url}")
        
        page_text, screenshot_path = await fetch_page_text(issuer_url, force_browser=True)
        
        if not page_text and not screenshot_path:
            return VerificationResult(
                is_verified=False, 
                trusted_domain=False, 
                verification_url=issuer_url, 
                method="manual_failed", 
                message="Could not fetch page content."
            )

        confidence = 0.0
        is_verified = False
        method = "manual_failed"
        message = "Certificate ID not found on page."

        clean_id = re.sub(r'[^a-zA-Z0-9]', '', certificate_id).lower()
        
        if page_text:
            clean_text = re.sub(r'[^a-zA-Z0-9]', '', page_text).lower()
            
            if clean_id in clean_text:
                confidence = 1.0
                is_verified = True
                method = "manual_text_match"
                message = "Certificate ID found in page text."

        if not is_verified and screenshot_path:
            v_match, v_score, _ = self.visual.verify_screenshot(screenshot_path, certificate_id)
            if v_match:
                confidence = v_score
                is_verified = True
                method = "manual_visual_ocr"
                message = f"Certificate ID found in screenshot. Match: {v_score:.0%}"
        
        return VerificationResult(
            is_verified=is_verified,
            trusted_domain=True,
            confidence_score=confidence,
            verification_url=issuer_url,
            method=method,
            message=message
        )

# Singleton
_service_instance: Optional[VerificationService] = None

def get_verification_service() -> VerificationService:
    global _service_instance
    if _service_instance is None: 
        _service_instance = VerificationService()
    return _service_instance
