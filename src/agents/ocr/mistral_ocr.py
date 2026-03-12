"""
Enhanced Mistral OCR with Region-Specific Zoom
Performs targeted OCR on certificate IDs and URLs
"""

import base64
import json
import os
from typing import Dict, Any, List, Tuple
try:
    from mistralai.client import Mistral  # older SDK (EC2 Ubuntu)
except ImportError:
    from mistralai import Mistral          # newer SDK (Mac)
from PIL import Image
import io
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

load_dotenv()


class EnhancedMistralOCR:
    """
    Two-pass OCR strategy:
    1. Full image → Extract overall data + locate URL/ID regions
    2. Zoomed regions → Precise OCR on URLs/IDs only
    """
    
    def __init__(self):
        api_key = os.getenv("MISTRAL_API_KEY")
        if not api_key:
            raise ValueError("MISTRAL_API_KEY not found")
        
        self.client = Mistral(api_key=api_key)
        logger.info("[INFO] Enhanced Mistral OCR initialized (2-pass mode)")
    
    def _convert_pdf_to_image(self, pdf_path: str) -> str:
        """Convert PDF at 400 DPI (even higher quality)"""
        try:
            from pdf2image import convert_from_path
            import tempfile
            
            logger.info("[INFO] Converting PDF to ultra-high quality (400 DPI)...")
            
            images = convert_from_path(
                pdf_path, 
                dpi=400,  # Ultra-high quality
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
    
    def _create_zoomed_region(self, image_path: str, region_hint: str) -> str:
        """
        Create a zoomed-in image focusing on URL/ID region.
        
        Strategy: Crop bottom 40% of certificate (where URLs/IDs usually are)
        and upscale 2x for better clarity.
        """
        try:
            img = Image.open(image_path)
            width, height = img.size
            
            # Crop bottom 40% (where certificate IDs and URLs typically are)
            # Adjust this based on your certificate layouts
            crop_top = int(height * 0.6)  # Start at 60% down
            crop_box = (0, crop_top, width, height)
            
            cropped = img.crop(crop_box)
            
            # Upscale 2x for better text clarity
            new_width = width * 2
            new_height = (height - crop_top) * 2
            upscaled = cropped.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Save to temp file
            import tempfile
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='_zoomed.png')
            upscaled.save(temp_file.name, 'PNG', quality=100)
            temp_file.close()
            
            logger.info(f"[INFO] Created zoomed region: {temp_file.name}")
            return temp_file.name
            
        except Exception as e:
            logger.error(f"[ERROR] Region zoom failed: {e}")
            return None
    
    def _ocr_image(self, image_path: str, prompt: str) -> Dict[str, Any]:
        """Run Mistral OCR on an image with custom prompt"""
        
        with open(image_path, "rb") as f:
            image_base64 = base64.b64encode(f.read()).decode()
        
        # Determine MIME type
        file_ext = image_path.lower().split('.')[-1]
        mime_type = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png'
        }.get(file_ext, 'image/png')
        
        try:
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
                                "text": prompt
                            }
                        ]
                    }
                ],
                response_format={"type": "json_object"}
            )
            
            result_text = response.choices[0].message.content
            
            try:
                return json.loads(result_text)
            except json.JSONDecodeError:
                import re
                json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
                return json.loads(json_match.group()) if json_match else {}
                
        except Exception as e:
            logger.error(f"[ERROR] OCR failed: {e}")
            return {}
    
    def extract_certificate_data(self, image_path: str) -> Dict[str, Any]:
        """
        Two-pass extraction:
        1. Full certificate → General data
        2. Zoomed URL/ID region → Precise URLs/IDs
        """
        
        file_ext = image_path.lower().split('.')[-1]
        temp_pdf_image = None
        temp_zoomed_image = None
        
        # Convert PDF if needed
        if file_ext == 'pdf':
            try:
                temp_pdf_image = self._convert_pdf_to_image(image_path)
                image_path = temp_pdf_image
            except Exception as e:
                logger.error(f"[ERROR] PDF conversion failed: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "structured_data": {},
                    "confidence": 0.0
                }
        
        try:
            # ===== PASS 1: Full Certificate =====
            logger.info("[PASS 1/2] Extracting general certificate data...")
            
            full_prompt = """Extract general information from this certificate:

{
  "student_name": "Full name",
  "issuer": "Organization",
  "course_name": "Course name",
  "completion_date": "YYYY-MM-DD",
  "instructor": "Instructor",
  "duration": "Duration"
}

Return ONLY JSON."""
            
            general_data = self._ocr_image(image_path, full_prompt)
            
            # ===== PASS 2: Zoomed URL/ID Region =====
            logger.info("[PASS 2/2] Zooming into URL/ID region for precise extraction...")
            
            temp_zoomed_image = self._create_zoomed_region(image_path, "bottom")
            
            if temp_zoomed_image:
                zoomed_prompt = """This is a ZOOMED-IN section of a certificate showing URLs and certificate IDs.

Read VERY CAREFULLY. Common OCR mistakes:
- 7 looks like Z (especially when underlined)
- 0 looks like O
- 1 looks like I or l
- 5 looks like S
- 8 looks like B

Extract:
{
  "certificate_ids": ["All IDs/reference numbers - read character by character"],
  "urls": ["All URLs - fix spaces like 'ude . my' to 'https://ude.my'"]
}

CRITICAL: If you see underlined text with what looks like 'Z', it's probably '7'.
Read each character individually. Return ONLY JSON."""
                
                precise_data = self._ocr_image(temp_zoomed_image, zoomed_prompt)
                
                # Merge: Use precise IDs/URLs, keep general data for everything else
                general_data['certificate_ids'] = precise_data.get('certificate_ids', general_data.get('certificate_ids', []))
                general_data['urls'] = precise_data.get('urls', general_data.get('urls', []))
                
                logger.info(f"[INFO] Pass 2 complete - Precise IDs: {general_data.get('certificate_ids')}")
                logger.info(f"[INFO] Pass 2 complete - Precise URLs: {general_data.get('urls')}")
            else:
                logger.warning("[WARNING] Pass 2 failed, using Pass 1 results only")
            
            logger.info(f"[INFO] Final extracted data: {general_data.get('student_name')}, {general_data.get('issuer')}")
            
            return {
                "success": True,
                "structured_data": general_data,
                "confidence": 0.95,
                "passes_completed": 2 if temp_zoomed_image else 1
            }
            
        except Exception as e:
            logger.error(f"[ERROR] Enhanced OCR failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "structured_data": {},
                "confidence": 0.0
            }
        
        finally:
            # Cleanup temp files
            if temp_pdf_image and os.path.exists(temp_pdf_image):
                os.unlink(temp_pdf_image)
            if temp_zoomed_image and os.path.exists(temp_zoomed_image):
                os.unlink(temp_zoomed_image)
