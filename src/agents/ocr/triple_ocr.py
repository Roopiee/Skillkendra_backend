"""
Enhanced Triple OCR with PaddleOCR Fallback
Uses SimplePaddleOCR wrapper for correct v3.3.2 format handling
"""

import logging
import asyncio
from typing import Dict, Any, List
from src.agents.ocr.easy_ocr import SimpleEasyOCR
from src.agents.ocr.mistral_ocr import EnhancedMistralOCR
from src.agents.ocr.tesseract_ocr import TesseractOCR
from src.agents.ocr.paddle_ocr import SimplePaddleOCR
try:
    from mistralai.client import Mistral  # older SDK (EC2 Ubuntu)
except ImportError:
    from mistralai import Mistral          # newer SDK (Mac)
import os
import re

logger = logging.getLogger(__name__)

MISTRAL_EXTRACTION_PROMPT = """Extract structured data from this certificate text (from {engine_name}):

{raw_text}

Return JSON:
{{
  "candidate_name": "Full name",
  "issuer": "Organization",
  "course_name": "Course name",
  "completion_date": "YYYY-MM-DD",
  "certificate_ids": ["All IDs - carefully: 7 not Z, 0 not O, J not missing"],
  "urls": ["All URLs - for Coursera use full format: https://www.coursera.org/account/accomplishments/verify/{{ID}}"],
  "instructor": "Instructor",
  "duration": "Duration"
}}

CRITICAL:
- Read IDs character-by-character: 7≠Z, 0≠O, 1≠I, J≠missing
- For Coursera, use FULL URL: https://www.coursera.org/account/accomplishments/verify/{{ID}}
- Fix spaces in URLs

Return ONLY JSON."""


class TripleOCR:
    """
    Combines EasyOCR, Mistral OCR, and Tesseract.
    Falls back to PaddleOCR if needed.
    """
    
    def __init__(self):
        self.easy_ocr = SimpleEasyOCR()
        self.mistral_ocr = EnhancedMistralOCR()
        self.tesseract_ocr = TesseractOCR()
        
        # Initialize PaddleOCR lazily
        self.paddle_ocr = None
        
        # Mistral client for structuring
        api_key = os.getenv("MISTRAL_API_KEY")
        self.mistral_client = Mistral(api_key=api_key) if api_key else None
        
        logger.info("[INFO] Enhanced Triple OCR initialized (+ PaddleOCR fallback)")
    
    def _init_paddle_ocr(self):
        """Lazy load PaddleOCR"""
        if self.paddle_ocr is None:
            try:
                self.paddle_ocr = SimplePaddleOCR()
                logger.info("[INFO] PaddleOCR fallback ready")
            except Exception as e:
                logger.error(f"[ERROR] PaddleOCR init failed: {e}")
                self.paddle_ocr = False
    
    def _extract_and_validate_urls(self, structured_data: Dict[str, Any]) -> List[str]:
        """Extract and validate URLs"""
        urls = structured_data.get('urls', [])
        
        if isinstance(urls, dict):
            urls = list(urls.values())
        
        valid_urls = []
        url_pattern = r'https?://(?:[a-zA-Z0-9]|[-._~:/?#\[\]@!$&\'()*+,;=])+'
        
        for url in urls:
            if not url:
                continue
            
            if re.match(url_pattern, str(url), re.IGNORECASE):
                if any(tld in str(url).lower() for tld in ['.com', '.org', '.edu', '.net', '.gov', '.io']):
                    valid_urls.append(url)
        
        return valid_urls
    
    def _has_valid_verification_url(self, results: List[Dict[str, Any]]) -> bool:
        """Check if any result has valid URLs"""
        for result in results:
            if not result.get('success'):
                continue
            
            structured = result.get('structured_data', {})
            valid_urls = self._extract_and_validate_urls(structured)
            
            if valid_urls:
                logger.info(f"[INFO] {result['engine']} found {len(valid_urls)} valid URL(s)")
                return True
        
        logger.warning("[WARNING] No valid URLs in any OCR result")
        return False
    
    def _structure_raw_text(self, raw_text: str, engine_name: str) -> Dict[str, Any]:
        """Use Mistral to structure raw text"""
        if not self.mistral_client or not raw_text:
            return {}
        
        try:
            import json
            response = self.mistral_client.chat.complete(
                model="mistral-large-latest",
                messages=[{
                    "role": "user",
                    "content": MISTRAL_EXTRACTION_PROMPT.format(engine_name=engine_name, raw_text=raw_text)
                }],
                response_format={"type": "json_object"}
            )
            
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"[ERROR] Structuring failed: {e}")
            return {}
    
    def run_paddle_fallback(self, image_path: str) -> Dict[str, Any]:
        """Run PaddleOCR as fallback"""
        self._init_paddle_ocr()
        
        if not self.paddle_ocr or self.paddle_ocr is False:
            return {
                "engine": "paddleocr",
                "success": False,
                "error": "PaddleOCR not available",
                "structured_data": {},
                "confidence": 0.0
            }
        
        logger.info("[FALLBACK] Running PaddleOCR...")
        
        try:
            paddle_result = self.paddle_ocr.extract_text(image_path)
            
            if not paddle_result.get("success"):
                logger.error(f"[FALLBACK FAILED] {paddle_result.get('error')}")
                return {
                    "engine": "paddleocr",
                    "success": False,
                    "error": paddle_result.get("error"),
                    "structured_data": {},
                    "confidence": 0.0,
                    "is_fallback": True
                }
            
            raw_text = paddle_result.get("raw_text", "")
            logger.info(f"[FALLBACK] PaddleOCR extracted: {len(raw_text)} chars")
            logger.info(f"[FALLBACK] Preview: {raw_text[:200]}")
            
            # Structure the text
            structured = self._structure_raw_text(raw_text, "PaddleOCR")
            
            if structured:
                logger.info(f"[FALLBACK] Structured: {structured.get('candidate_name')}, {structured.get('issuer')}")
                urls = self._extract_and_validate_urls(structured)
                if urls:
                    logger.info(f"[FALLBACK SUCCESS] ✅ PaddleOCR found {len(urls)} URL(s): {urls}")
                else:
                    logger.warning("[FALLBACK] ⚠️ PaddleOCR extracted data but no valid URLs")
            
            return {
                "engine": "paddleocr",
                "success": True,
                "structured_data": structured,
                "confidence": paddle_result.get("confidence", 0.0),
                "raw_text_preview": raw_text[:300],
                "total_lines": paddle_result.get("total_lines", 0),
                "is_fallback": True
            }
            
        except Exception as e:
            logger.error(f"[FALLBACK ERROR] {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "engine": "paddleocr",
                "success": False,
                "error": str(e),
                "structured_data": {},
                "confidence": 0.0,
                "is_fallback": True
            }
    
    async def _structure_raw_text_async(self, raw_text: str, engine_name: str) -> Dict[str, Any]:
        """Async wrapper for structuring"""
        return await asyncio.to_thread(self._structure_raw_text, raw_text, engine_name)

    async def _process_easy_ocr(self, image_path: str) -> Dict[str, Any]:
        """Async wrapper for EasyOCR process"""
        logger.info("[OCR] Starting EasyOCR...")
        logger.info("[OCR] EasyOCR launched")
        try:
            # Run blocking OCR in thread
            result = await asyncio.to_thread(self.easy_ocr.extract_text, image_path)
            
            if not result.get("success"):
                logger.warning("[OCR] EasyOCR failed")
                return {
                    "engine": "easyocr",
                    "success": False,
                    "error": result.get("error"),
                    "structured_data": {},
                    "confidence": 0.0
                }
            
            raw_text = result.get("raw_text", "")
            structured = await self._structure_raw_text_async(raw_text, "EasyOCR")
            
            logger.info(f"[OCR] EasyOCR complete. Found: {structured.get('candidate_name')}")
            return {
                "engine": "easyocr",
                "success": True,
                "structured_data": structured,
                "confidence": result.get("confidence", 0.0),
                "raw_text_preview": raw_text[:300],
                "total_lines": result.get("total_lines", 0)
            }
        except Exception as e:
            logger.error(f"[OCR] EasyOCR exception: {e}")
            return {"engine": "easyocr", "success": False, "error": str(e)}

    async def _process_mistral_ocr(self, image_path: str) -> Dict[str, Any]:
        """Async wrapper for Mistral OCR process"""
        logger.info("[OCR] Starting Mistral OCR...")
        logger.info("[OCR] Mistral launched")
        try:
            # Mistral OCR might do network I/O, safer to thread it if sync client
            result = await asyncio.to_thread(self.mistral_ocr.extract_certificate_data, image_path)
            
            if not result.get("success"):
                logger.warning("[OCR] Mistral OCR failed")
                return {
                    "engine": "mistral",
                    "success": False,
                    "error": result.get("error"),
                    "structured_data": {},
                    "confidence": 0.0
                }
            
            structured = result.get("structured_data", {})
            logger.info(f"[OCR] Mistral complete. Found: {structured.get('candidate_name')}")
            return {
                "engine": "mistral",
                "success": True,
                "structured_data": structured,
                "confidence": result.get("confidence", 0.0),
                "passes_completed": result.get("passes_completed", 1)
            }
        except Exception as e:
            logger.error(f"[OCR] Mistral exception: {e}")
            return {"engine": "mistral", "success": False, "error": str(e)}

    async def _process_tesseract_ocr(self, image_path: str) -> Dict[str, Any]:
        """Async wrapper for Tesseract process"""
        logger.info("[OCR] Starting Tesseract...")
        logger.info("[OCR] Tesseract launched")
        try:
            # Run blocking OCR in thread
            result = await asyncio.to_thread(self.tesseract_ocr.extract_text, image_path)
            
            if not result.get("success"):
                logger.warning("[OCR] Tesseract failed")
                return {
                    "engine": "tesseract",
                    "success": False,
                    "error": result.get("error"),
                    "structured_data": {},
                    "confidence": 0.0
                }
            
            raw_text = result.get("raw_text", "")
            structured = await self._structure_raw_text_async(raw_text, "Tesseract")
            
            logger.info(f"[OCR] Tesseract complete. Found: {structured.get('candidate_name')}")
            return {
                "engine": "tesseract",
                "success": True,
                "structured_data": structured,
                "confidence": result.get("confidence", 0.0),
                "raw_text_preview": raw_text[:300],
                "total_words": result.get("total_words", 0)
            }
        except Exception as e:
            logger.error(f"[OCR] Tesseract exception: {e}")
            return {"engine": "tesseract", "success": False, "error": str(e)}
        
    async def extract_all(self, image_path: str) -> List[Dict[str, Any]]:
        """Extract with all engines in PARALLEL + PaddleOCR fallback if needed"""
        
        logger.info("="*60)
        logger.info("🚀 STARTING PARALLEL OCR (Async)")
        logger.info("="*60)
        
        # Run all 3 engines concurrently
        tasks = [
            self._process_easy_ocr(image_path),
            self._process_mistral_ocr(image_path),
            self._process_tesseract_ocr(image_path)
        ]
        
        results = list(await asyncio.gather(*tasks))
        
        successful = sum(1 for r in results if r['success'])
        logger.info(f"[PARALLEL OCR] {successful}/3 engines succeeded")
        
        # === PADDLEOCR FALLBACK ===
        if not self._has_valid_verification_url(results):
            logger.warning("="*80)
            logger.warning("[CRITICAL] NO VALID URLS - ACTIVATING PADDLEOCR FALLBACK")
            logger.warning("="*80)
            
            paddle_result = self.run_paddle_fallback(image_path)
            results.append(paddle_result)
            
            if paddle_result['success']:
                successful += 1
        else:
            logger.info("[INFO] Valid URLs found - PaddleOCR not needed")
        
        logger.info(f"[FINAL] {successful}/{len(results)} total engines succeeded")
        
        return results
