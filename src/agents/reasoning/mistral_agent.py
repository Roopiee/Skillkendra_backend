"""
Mistral Reasoning Agent - Production version without emojis
"""

import os
import json
from typing import Optional, Dict, Any
from dotenv import load_dotenv
try:
    from mistralai.client import Mistral  # older SDK (EC2 Ubuntu)
except ImportError:
    from mistralai import Mistral          # newer SDK (Mac)

from core.models import OCRResult, ExtractedEvidence, OCREngine


class MistralReasoning:
    """AI reasoning layer that extracts structured data from OCR text."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize Mistral client."""
        load_dotenv()
        
        if api_key is None:
            api_key = os.getenv("MISTRAL_API_KEY")
        
        if not api_key:
            raise ValueError(
                "Mistral API key not found! Set MISTRAL_API_KEY environment variable."
            )
        
        self.client = Mistral(api_key=api_key)
        self.model = "mistral-large-latest"
        
        print("[INFO] Mistral reasoning agent initialized")
    
    def extract_everything(self, ocr_result: OCRResult) -> Dict[str, Any]:
        """Extract ALL information from OCR text."""
        full_text = "\n".join(ocr_result.raw_lines)
        prompt = self._build_flexible_prompt(full_text, ocr_result.raw_lines)
        
        try:
            response = self.client.chat.complete(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            result_text = response.choices[0].message.content
            data = json.loads(result_text)
            
            # Add metadata
            data['_ocr_engine'] = ocr_result.engine.value
            data['_ocr_confidence'] = ocr_result.confidence
            data['_raw_text'] = full_text
            
            return data
            
        except Exception as e:
            print(f"[WARNING] Mistral extraction error: {e}")
            return {
                '_error': str(e),
                '_ocr_engine': ocr_result.engine.value,
                '_raw_text': full_text
            }
    
    def extract_evidence(self, ocr_result: OCRResult) -> ExtractedEvidence:
        """Extract evidence and map to ExtractedEvidence format."""
        data = self.extract_everything(ocr_result)
        
        # Extract names
        names = []
        for key in ['student_name', 'recipient', 'holder', 'certificate_holder']:
            if key in data and data[key]:
                if isinstance(data[key], list):
                    names.extend(data[key])
                else:
                    names.append(data[key])
        
        # Extract certificate IDs
        certificate_ids = []
        if 'certificate_ids' in data:
            if isinstance(data['certificate_ids'], dict):
                certificate_ids = list(data['certificate_ids'].values())
            elif isinstance(data['certificate_ids'], list):
                certificate_ids = data['certificate_ids']
        
        # Extract URLs
        urls = []
        if 'urls' in data:
            if isinstance(data['urls'], dict):
                urls = list(data['urls'].values())
            elif isinstance(data['urls'], list):
                urls = data['urls']
        
        issuer = data.get('issuer') or data.get('platform')
        
        return ExtractedEvidence(
            engine=ocr_result.engine,
            issuer=issuer,
            certificate_ids=certificate_ids,
            urls=urls,
            names=names,
            confidence=ocr_result.confidence,
            page_number=ocr_result.page_number
        )
    
    def _build_flexible_prompt(self, ocr_text: str, lines: list) -> str:
        """Build extraction prompt with platform-specific logic."""
        
        # Detect platform
        is_udemy = 'udemy' in ocr_text.lower() or 'ude.my' in ocr_text.lower()
        
        udemy_hint = ""
        if is_udemy:
            udemy_hint = """
SPECIAL RULE FOR UDEMY CERTIFICATES:
Udemy certificates show "Instructors" label with multiple names:
- FIRST name = Course instructor (who created the course)
- LAST name = Student (who earned the certificate)

Example:
"Instructors
Vlad Budnitski    <- This is the instructor
Roopak Krishna"   <- This is the STUDENT

So when multiple names appear after "Instructors", put the LAST name in "student_name".
"""
        
        return f"""You are analyzing text extracted from a certificate via OCR.

OCR Text:
{ocr_text}

Extract ALL information. Return a JSON object.

FIELDS (use null if not found):
- issuer: Platform/organization (Udemy, Coursera, edX, etc.)
- student_name: Person who EARNED/RECEIVED this certificate
- course_name: Course/program title
- completion_date: When completed (YYYY-MM-DD format)
- certificate_ids: All IDs (UC-xxx, reference numbers, etc.)
- urls: All URLs (fix broken ones: "ude_my" → "https://ude.my")
- instructor: Who taught/created the course
- duration: Course length
- any_other_info: Anything else notable

{udemy_hint}

RULES:
1. Student name = certificate holder (not instructor)
2. Fix broken URLs (add https://, remove spaces/underscores)
3. Extract ALL identifiers
4. Normalize dates to YYYY-MM-DD
5. Identify issuer from domain names or platform text

Return ONLY the JSON object."""
    
    def extract_from_multiple(self, ocr_results: list[OCRResult]) -> list[ExtractedEvidence]:
        """Extract evidence from multiple OCR results."""
        evidence_list = []
        
        for ocr_result in ocr_results:
            print(f"\n[INFO] Reasoning over {ocr_result.engine.value} output...")
            
            full_data = self.extract_everything(ocr_result)
            
            print(f"[INFO] Found fields: {list([k for k in full_data.keys() if not k.startswith('_')])}")
            if 'student_name' in full_data and full_data['student_name']:
                print(f"[INFO] Student: {full_data['student_name']}")
            if 'issuer' in full_data:
                print(f"[INFO] Issuer: {full_data['issuer']}")
            if 'certificate_ids' in full_data:
                print(f"[INFO] IDs: {full_data['certificate_ids']}")
            if 'urls' in full_data:
                print(f"[INFO] URLs: {full_data['urls']}")
            
            evidence = self.extract_evidence(ocr_result)
            evidence_list.append(evidence)
        
        return evidence_list
