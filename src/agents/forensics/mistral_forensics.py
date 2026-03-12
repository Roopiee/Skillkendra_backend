"""
Mistral Forensics with PDF Support
Converts PDFs to images before analysis
"""

import base64
import json
import os
from typing import Dict, Any
from mistralai import Mistral
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

load_dotenv()


class MistralForensics:
    """Certificate Forensics with PDF conversion"""
    
    def __init__(self):
        api_key = os.getenv("MISTRAL_API_KEY")
        if not api_key:
            raise ValueError("MISTRAL_API_KEY not found")
        
        self.client = Mistral(api_key=api_key)
        logger.info("[INFO] Mistral Forensics initialized")
    
    def _convert_pdf_to_image(self, pdf_path: str) -> str:
        """Convert PDF to image for analysis"""
        try:
            from pdf2image import convert_from_path
            import tempfile
            
            logger.info("[INFO] Converting PDF for forensics (300 DPI)...")
            
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
            
        except ImportError:
            raise ImportError("pdf2image not installed. Run: pip install pdf2image")
        except Exception as e:
            raise Exception(f"PDF conversion failed: {e}")
    
    def analyze_certificate(self, image_path: str) -> Dict[str, Any]:
        """Forensics analysis (handles PDFs by converting)"""
        
        file_ext = image_path.lower().split('.')[-1]
        temp_image = None
        
        # Convert PDF if needed
        if file_ext == 'pdf':
            try:
                temp_image = self._convert_pdf_to_image(image_path)
                image_path = temp_image
                file_ext = 'png'
            except Exception as e:
                logger.error(f"[ERROR] PDF conversion failed: {e}")
                return {
                    "success": False,
                    "error": f"PDF conversion for forensics failed: {str(e)}",
                    "forensics": self._default_forensics()
                }
        
        # Read image
        try:
            with open(image_path, "rb") as f:
                image_base64 = base64.b64encode(f.read()).decode()
        finally:
            # Cleanup temp file
            if temp_image and os.path.exists(temp_image):
                os.unlink(temp_image)
        
        mime_type = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png'
        }.get(file_ext, 'image/jpeg')
        
        try:
            logger.info("[INFO] Running forensics...")
            
            response = self.client.chat.complete(
                model="pixtral-12b-2409",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": f"data:{mime_type};base64,{image_base64}"
                            },
                            {
                                "type": "text",
                                "text": """Forensics expert: Analyze this certificate for authenticity.

Return JSON:
{
  "is_high_risk": true/false,
  "manipulation_score": 0.0-1.0,
  "anomalies_detected": ["Specific issues"],
  "authenticity_indicators": ["Positive signs"],
  "visual_quality": "excellent/good/fair/poor",
  "status": "Summary",
  "confidence": 0.0-1.0,
  "details": "Detailed report"
}

Check: fonts, layout, logos, text quality, colors, compression, overlays, official elements, IDs/URLs, professionalism.

Score: 0.0=pristine, 1.0=manipulated. is_high_risk=true if score>0.5."""
                            }
                        ]
                    }
                ],
                response_format={"type": "json_object"}
            )
            
            result_text = response.choices[0].message.content
            
            try:
                forensics = json.loads(result_text)
            except json.JSONDecodeError:
                import re
                json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
                forensics = json.loads(json_match.group()) if json_match else self._default_forensics()
            
            forensics = self._normalize_forensics(forensics)
            
            logger.info(f"[INFO] Forensics: Risk={forensics['is_high_risk']}, Score={forensics['manipulation_score']}")
            
            return {
                "success": True,
                "forensics": forensics
            }
            
        except Exception as e:
            logger.error(f"[ERROR] Forensics failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "forensics": self._default_forensics()
            }
    
    def _default_forensics(self) -> Dict[str, Any]:
        return {
            "is_high_risk": False,
            "manipulation_score": 0.0,
            "anomalies_detected": [],
            "authenticity_indicators": [],
            "visual_quality": "unknown",
            "status": "Analysis unavailable",
            "confidence": 0.0,
            "details": "Could not analyze"
        }
    
    def _normalize_forensics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        defaults = self._default_forensics()
        for key, value in defaults.items():
            if key not in data:
                data[key] = value
        return data
