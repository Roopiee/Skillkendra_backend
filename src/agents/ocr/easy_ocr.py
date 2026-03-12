"""
EasyOCR with PDF Support
Converts PDFs to images first
"""

import easyocr
import numpy as np
import logging
import os
from typing import Dict, Any

logger = logging.getLogger(__name__)


class SimpleEasyOCR:
    """EasyOCR wrapper with PDF conversion"""
    
    def __init__(self):
        try:
            self.reader = easyocr.Reader(['en'], gpu=True)
            logger.info("[INFO] EasyOCR initialized (GPU enabled)")
        except Exception as e:
            logger.error(f"[ERROR] EasyOCR init failed: {e}")
            self.reader = None
    
    def _convert_pdf_to_image(self, pdf_path: str) -> str:
        """Convert PDF to high-quality image"""
        try:
            from pdf2image import convert_from_path
            import tempfile
            
            logger.info("[INFO] Converting PDF for EasyOCR (300 DPI)...")
            
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
        """Extract text (handles PDFs by converting)"""
        
        if not self.reader:
            return {
                "success": False,
                "error": "EasyOCR not initialized",
                "raw_text": "",
                "lines": []
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
                    "lines": []
                }
        
        try:
            logger.info("[INFO] Running EasyOCR...")
            
            # Run OCR
            results = self.reader.readtext(image_path)
            
            # Extract text and confidence
            lines = []
            all_text = []
            confidences = []
            
            for (bbox, text, conf) in results:
                lines.append({
                    "text": text,
                    "confidence": conf
                })
                all_text.append(text)
                confidences.append(conf)
            
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            raw_text = "\n".join(all_text)
            
            logger.info(f"[INFO] EasyOCR complete: {len(lines)} lines, {avg_confidence:.2%} confidence")
            
            return {
                "success": True,
                "raw_text": raw_text,
                "lines": lines,
                "confidence": avg_confidence,
                "total_lines": len(lines)
            }
            
        except Exception as e:
            logger.error(f"[ERROR] EasyOCR failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "raw_text": "",
                "lines": []
            }
        
        finally:
            # Cleanup temp file
            if temp_image and os.path.exists(temp_image):
                os.unlink(temp_image)
