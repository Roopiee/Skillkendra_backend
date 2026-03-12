"""
Tesseract OCR Wrapper
Fast, local, excellent for clean text
"""

import pytesseract
from PIL import Image
import logging
import os
from typing import Dict, Any

logger = logging.getLogger(__name__)


class TesseractOCR:
    """Tesseract OCR with PDF support"""
    
    def __init__(self):
        try:
            # Verify Tesseract is installed
            pytesseract.get_tesseract_version()
            logger.info("[INFO] Tesseract OCR initialized")
            self.available = True
        except Exception as e:
            logger.error(f"[ERROR] Tesseract not available: {e}")
            self.available = False
    
    def _convert_pdf_to_image(self, pdf_path: str) -> str:
        """Convert PDF to high-quality image"""
        try:
            from pdf2image import convert_from_path
            import tempfile
            
            logger.info("[INFO] Converting PDF for Tesseract (300 DPI)...")
            
            images = convert_from_path(
                pdf_path, 
                dpi=300,
                first_page=1, 
                last_page=1,
                fmt='png'
            )
            
            if not images:
                raise ValueError("PDF conversion failed")
            
            temp_image = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            images[0].save(temp_image.name, 'PNG', quality=100)
            temp_image.close()
            
            return temp_image.name
            
        except Exception as e:
            raise Exception(f"PDF conversion failed: {e}")
    
    def extract_text(self, image_path: str) -> Dict[str, Any]:
        """Extract text using Tesseract (handles PDFs)"""
        
        if not self.available:
            return {
                "success": False,
                "error": "Tesseract not installed",
                "raw_text": "",
                "confidence": 0.0
            }
        
        file_ext = image_path.lower().split('.')[-1]
        temp_image = None
        
        # Convert PDF if needed
        if file_ext == 'pdf':
            try:
                temp_image = self._convert_pdf_to_image(image_path)
                image_path = temp_image
            except Exception as e:
                logger.error(f"[ERROR] PDF conversion failed: {e}")
                return {
                    "success": False,
                    "error": f"PDF conversion failed: {str(e)}",
                    "raw_text": "",
                    "confidence": 0.0
                }
        
        try:
            logger.info("[INFO] Running Tesseract OCR...")
            
            # Open image
            img = Image.open(image_path)
            
            # Extract text with confidence data
            data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
            
            # Get text and confidences
            texts = []
            confidences = []
            
            for i, conf in enumerate(data['conf']):
                if int(conf) > 0:  # Only include confident detections
                    text = data['text'][i].strip()
                    if text:
                        texts.append(text)
                        confidences.append(int(conf))
            
            raw_text = "\n".join(texts)
            avg_confidence = sum(confidences) / len(confidences) / 100.0 if confidences else 0.0
            
            logger.info(f"[INFO] Tesseract complete: {len(texts)} words, {avg_confidence:.2%} confidence")
            
            return {
                "success": True,
                "raw_text": raw_text,
                "confidence": avg_confidence,
                "total_words": len(texts)
            }
            
        except Exception as e:
            logger.error(f"[ERROR] Tesseract failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "raw_text": "",
                "confidence": 0.0
            }
        
        finally:
            # Cleanup temp file
            if temp_image and os.path.exists(temp_image):
                os.unlink(temp_image)
