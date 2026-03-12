"""
Simple PaddleOCR Wrapper for v3.3.2 with detailed debugging
"""

from paddleocr import PaddleOCR
import logging
from typing import Dict, Any
import os

logger = logging.getLogger(__name__)


class SimplePaddleOCR:
    """PaddleOCR wrapper for v3.3.2 with debug output"""
    
    def __init__(self):
        try:
            os.environ['DISABLE_MODEL_SOURCE_CHECK'] = 'True'
            self.reader = PaddleOCR(lang='en', use_gpu=True)
            logger.info("[INFO] PaddleOCR v3.3.2 initialized (GPU enabled)")
            self.available = True
        except Exception as e:
            logger.error(f"[ERROR] PaddleOCR init failed: {e}")
            self.available = False
    
    def _convert_pdf_to_image(self, pdf_path: str) -> str:
        """Convert PDF to image"""
        try:
            from pdf2image import convert_from_path
            import tempfile
            
            logger.info("[INFO] Converting PDF for PaddleOCR (400 DPI)...")
            
            images = convert_from_path(pdf_path, dpi=400, first_page=1, last_page=1, fmt='png')
            
            if not images:
                raise ValueError("PDF conversion failed")
            
            temp_image = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            images[0].save(temp_image.name, 'PNG', quality=100)
            temp_image.close()
            
            return temp_image.name
            
        except Exception as e:
            raise Exception(f"PDF conversion failed: {e}")
    
    def extract_text(self, image_path: str) -> Dict[str, Any]:
        """Extract text using PaddleOCR v3.3.2 with detailed debugging"""
        
        if not self.available:
            return {"success": False, "error": "PaddleOCR not available", "raw_text": "", "confidence": 0.0}
        
        file_ext = image_path.lower().split('.')[-1]
        temp_image = None
        
        # Convert PDF if needed
        if file_ext == 'pdf':
            try:
                temp_image = self._convert_pdf_to_image(image_path)
                image_path = temp_image
            except Exception as e:
                logger.error(f"[ERROR] PDF conversion failed: {e}")
                return {"success": False, "error": f"PDF conversion failed: {str(e)}", "raw_text": "", "confidence": 0.0}
        
        try:
            logger.info(f"[INFO] Running PaddleOCR on: {image_path}")
            
            # Run OCR
            result = self.reader.ocr(image_path)
            
            # DEBUG: Show what we got
            logger.info(f"[DEBUG] Result type: {type(result)}")
            logger.info(f"[DEBUG] Result length: {len(result) if result else 0}")
            
            if not result or len(result) == 0:
                logger.warning("[WARNING] PaddleOCR returned empty/None")
                return {"success": False, "error": "No result returned", "raw_text": "", "confidence": 0.0}
            
            # Get first element
            ocr_result = result[0]
            logger.info(f"[DEBUG] OCR result type: {type(ocr_result)}")
            
            # Check if it's None
            if ocr_result is None:
                logger.warning("[WARNING] OCR result is None")
                return {"success": False, "error": "OCR result is None", "raw_text": "", "confidence": 0.0}
            
            # Try different access methods
            texts = None
            scores = None
            
            # Method 1: Try as attributes
            if hasattr(ocr_result, 'rec_texts'):
                texts = ocr_result.rec_texts
                scores = ocr_result.rec_scores if hasattr(ocr_result, 'rec_scores') else []
                logger.info("[DEBUG] Accessed via attributes")
            
            # Method 2: Try as dict
            elif hasattr(ocr_result, 'get'):
                texts = ocr_result.get('rec_texts', [])
                scores = ocr_result.get('rec_scores', [])
                logger.info("[DEBUG] Accessed via dict.get()")
            
            # Method 3: Try as dict keys
            elif isinstance(ocr_result, dict):
                texts = ocr_result.get('rec_texts', [])
                scores = ocr_result.get('rec_scores', [])
                logger.info("[DEBUG] Accessed via dict keys")
            
            # Method 4: Maybe it's a list of detections (old format)
            elif isinstance(ocr_result, list):
                logger.info(f"[DEBUG] OCR result is a list with {len(ocr_result)} items")
                
                # Old format: [[[bbox], (text, score)], ...]
                texts = []
                scores = []
                for detection in ocr_result:
                    if isinstance(detection, (list, tuple)) and len(detection) >= 2:
                        bbox, text_conf = detection[0], detection[1]
                        if isinstance(text_conf, (list, tuple)) and len(text_conf) >= 2:
                            texts.append(str(text_conf[0]))
                            scores.append(float(text_conf[1]))
                
                logger.info("[DEBUG] Parsed old-style list format")
            
            logger.info(f"[DEBUG] Texts found: {len(texts) if texts else 0}")
            logger.info(f"[DEBUG] Scores found: {len(scores) if scores else 0}")
            
            if texts:
                logger.info(f"[DEBUG] First few texts: {texts[:3]}")
            
            if not texts:
                logger.warning("[WARNING] No text extracted")
                logger.warning(f"[DEBUG] OCR result attributes: {dir(ocr_result)}")
                logger.warning(f"[DEBUG] OCR result repr: {repr(ocr_result)[:500]}")
                
                return {"success": False, "error": "Could not extract text from result", "raw_text": "", "confidence": 0.0}
            
            # Success!
            raw_text = "\n".join(str(t) for t in texts)
            avg_confidence = sum(scores) / len(scores) if scores else 0.0
            
            logger.info(f"[SUCCESS] PaddleOCR: {len(texts)} lines, {avg_confidence:.2%} confidence")
            logger.info(f"[SUCCESS] Preview: {raw_text[:200]}")
            
            return {
                "success": True,
                "raw_text": raw_text,
                "confidence": avg_confidence,
                "total_lines": len(texts)
            }
            
        except Exception as e:
            logger.error(f"[ERROR] PaddleOCR failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {"success": False, "error": str(e), "raw_text": "", "confidence": 0.0}
        
        finally:
            if temp_image and os.path.exists(temp_image):
                os.unlink(temp_image)
