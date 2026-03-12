"""
Complete Verification Pipeline
Triple OCR with confidence-based PaddleOCR fallback
"""

import asyncio
from typing import Dict, Any, List
from src.agents.ocr.triple_ocr import TripleOCR
from src.agents.forensics.mistral_forensics import MistralForensics
from src.agents.verification.service import get_verification_service
import logging

logger = logging.getLogger(__name__)


class CompleteCertificateVerifier:
    """Verification with triple OCR + PaddleOCR rescue"""
    
    def __init__(self, use_paddle: bool = False):
        self.ocr = TripleOCR()
        self.forensics = MistralForensics()
        self.verifier = get_verification_service()
        
        logger.info("[INFO] Pipeline: Triple OCR + PaddleOCR Fallback + Forensics")
        
    async def _verify_single_candidate(self, idx: int, ocr_result: Dict[str, Any], total: int) -> Dict[str, Any]:
        """
        Verify a single OCR candidate (Async helper).
        Returns the 'verification_attempts' dictionary item.
        """
        engine = ocr_result["engine"]
        structured_data = ocr_result.get("structured_data", {})
        is_fallback = ocr_result.get("is_fallback", False)
        
        engine_label = f"{engine.upper()}" + (" [FALLBACK]" if is_fallback else "")
        # logger.info(f"[VERIFY {idx+1}/{total}] Trying {engine_label}...") # Log spam reduction?
        
        try:
            # 1. Verification Service Logic
            extraction_result = self.verifier.verify_from_evidence(structured_data)
            verification_result = await self.verifier.verify(extraction_result)
            
            status = "✅ VERIFIED" if verification_result.is_verified else "❌ UNVERIFIED"
            logger.info(f"[VERIFY {idx+1}/{total}] {engine_label}: {status} ({verification_result.confidence_score:.2%})")
            
            return {
                "engine": engine,
                "is_fallback": is_fallback,
                "extracted_data": structured_data,
                "verification": {
                    "is_verified": verification_result.is_verified,
                    "trusted_domain": verification_result.trusted_domain,
                    "confidence_score": round(verification_result.confidence_score * 100, 2),
                    "method": verification_result.method,
                    "message": verification_result.message,
                    "verification_url": verification_result.verification_url
                },
                "ocr_confidence": round(ocr_result.get("confidence", 0.0) * 100, 2)
            }
            
        except Exception as e:
            logger.error(f"[ERROR] {engine_label} verification failed: {e}")
            return {
                "engine": engine,
                "is_fallback": is_fallback,
                "extracted_data": structured_data,
                "error": str(e),
                "verification": {
                    "is_verified": False,
                    "message": f"Error: {str(e)}"
                }
            }
    
    async def verify_certificate(self, image_path: str) -> Dict[str, Any]:
        """
        Complete verification with PARALLEL execution
        """
        
        # === PHASE 1: Parallel OCR & Forensics ===
        logger.info("="*60)
        logger.info("🚀 PHASE 1: Parallel OCR + Forensics")
        logger.info("="*60)
        
        # Launch both tasks
        ocr_task = self.ocr.extract_all(image_path)
        forensics_task = asyncio.to_thread(self.forensics.analyze_certificate, image_path)
        
        # Wait for both
        ocr_results, forensics_result = await asyncio.gather(ocr_task, forensics_task)
        
        forensics_data = forensics_result.get("forensics", {})
        
        # Check OCR success
        successful_results = [r for r in ocr_results if r.get("success")]
        
        if not successful_results:
            return {
                'success': False,
                'error': 'All OCR engines failed',
                'stage': 'ocr',
                'ocr_results': ocr_results,
                'forensics': forensics_data
            }
        
        logger.info(f"[PHASE 1 COMPLETE] {len(successful_results)}/{len(ocr_results)} OCR engines succeeded")
        
        # === PHASE 2: Parallel Verification ===
        logger.info("="*60)
        logger.info("🚀 PHASE 2: Parallel Verification Candidates")
        logger.info("="*60)
        
        # Create verification tasks
        verification_tasks = [
            self._verify_single_candidate(idx, res, len(successful_results))
            for idx, res in enumerate(successful_results)
        ]
        
        # Run all verifications in parallel
        verification_attempts = await asyncio.gather(*verification_tasks)
        
        # Identify best result
        best_confidence = 0.0
        for attempt in verification_attempts:
            conf = attempt.get("verification", {}).get("confidence_score", 0.0)
            if conf > best_confidence:
                best_confidence = conf
        
        # Check if we need PaddleOCR rescue
        verified_attempts = [a for a in verification_attempts if a.get("verification", {}).get("is_verified")]
        
        # PADDLEOCR RESCUE: If best confidence < 70% and not verified yet
        if not verified_attempts and best_confidence < 70.0:
            logger.warning("="*80)
            logger.warning(f"[FALLBACK TRIGGER] Best confidence {best_confidence}% < 70.0% threshold")
            logger.warning("[PADDLE RESCUE] Attempting PaddleOCR extraction as last resort...")
            logger.warning("="*80)
            
            try:
                # Run PaddleOCR fallback - FIXED METHOD NAME
                paddle_result = self.ocr.run_paddle_fallback(image_path)
                
                if paddle_result.get('success'):
                    logger.info("[PADDLE RESCUE] ✅ PaddleOCR extraction succeeded")
                    
                    # Try verification with PaddleOCR result
                    paddle_structured = paddle_result.get('structured_data', {})
                    
                    try:
                        extraction_result = self.verifier.verify_from_evidence(paddle_structured)
                        verification_result = await self.verifier.verify(extraction_result)
                        
                        verification_attempts.append({
                            "engine": "paddleocr",
                            "is_fallback": True,
                            "extracted_data": paddle_structured,
                            "verification": {
                                "is_verified": verification_result.is_verified,
                                "trusted_domain": verification_result.trusted_domain,
                                "confidence_score": round(verification_result.confidence_score * 100, 2),
                                "method": verification_result.method,
                                "message": verification_result.message,
                                "verification_url": verification_result.verification_url
                            },
                            "ocr_confidence": round(paddle_result["confidence"] * 100, 2)
                        })
                        
                        if verification_result.is_verified:
                            logger.info("[PADDLE RESCUE] 🎉 VERIFICATION SUCCESSFUL!")
                            verified_attempts.append(verification_attempts[-1])
                        else:
                            logger.warning(f"[PADDLE RESCUE] ⚠️ Verified but low confidence: {verification_result.confidence_score:.2%}")
                    
                    except Exception as e:
                        logger.error(f"[PADDLE RESCUE] ❌ Verification failed: {e}")
                else:
                    logger.error("[PADDLE RESCUE] ❌ PaddleOCR extraction failed")
            
            except Exception as e:
                logger.error(f"[PADDLE RESCUE] ❌ Error during fallback: {e}")
        
        # Determine final verdict
        is_verified = len(verified_attempts) > 0
        
        if verified_attempts:
            best_attempt = max(verified_attempts, key=lambda x: x.get("verification", {}).get("confidence_score", 0))
            final_verdict = "VERIFIED"
            engine_label = best_attempt['engine'].upper() + (" [PADDLE RESCUE]" if best_attempt.get('is_fallback') else "")
            final_message = f"✅ Verified via {engine_label}: {best_attempt['verification']['message']}"
        else:
            best_attempt = max(verification_attempts, key=lambda x: x.get("verification", {}).get("confidence_score", 0))
            final_verdict = "UNVERIFIED"
            final_message = f"❌ Could not verify. Best: {best_attempt['engine'].upper()} ({best_attempt.get('verification', {}).get('confidence_score', 0)}%)"
        
        logger.info(f"[FINAL] {final_verdict}: {len(verified_attempts)}/{len(verification_attempts)} attempts verified")
        
        return {
            'success': True,
            'final_verdict': final_verdict,
            'is_verified': is_verified,
            'verification_attempts': verification_attempts,
            'best_result': best_attempt,
            'ocr_results': ocr_results,
            'forensics': forensics_data,
            'summary': {
                'total_ocr_engines': len(ocr_results),
                'successful_ocr': len(successful_results),
                'verification_attempts': len(verification_attempts),
                'verified_count': len(verified_attempts),
                'paddle_rescue_used': any(a.get('is_fallback') for a in verification_attempts),
                'final_message': final_message
            }
        }
