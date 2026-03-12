"""Test full extraction - see everything Mistral finds"""

import cv2
import os
import json
from src.agents.ocr.easy_ocr import SimpleEasyOCR
from src.agents.reasoning.mistral_agent import MistralReasoning


def test_full_extraction():
    """Extract ALL data from certificate."""
    
    print("="*60)
    print("FULL EXTRACTION TEST")
    print("="*60)
    
    # Load image
    cert_file = 'sample_cert.jpg'
    if not os.path.exists(cert_file):
        print("❌ sample_cert.jpg not found!")
        return
    
    image = cv2.imread(cert_file)
    
    # Run OCR
    print("\n1. Running OCR...")
    easy = SimpleEasyOCR()
    ocr_result = easy.extract_text(image)  # direct call equivalent
    
    lines = ocr_result.get('raw_text', '').split('\n')
    print(f"   ✅ Extracted {len(lines)} lines")
    
    # Show raw text
    print("\n2. Raw OCR Text:")
    print("-"*60)
    for i, line in enumerate(lines, 1):
        print(f"   {i:2d}. {line}")
    
    # Extract everything with Mistral
    print("\n3. Mistral Analysis:")
    print("-"*60)
    mistral = MistralReasoning()
    
    # Mistral reasoning expects object or dict? MistralReasoning needs check.
    # Assuming extract_everything can handle the new dict format or we need to adapt it. 
    # Let's pass the dict directly if possible, or wrap it.
    # MistralReasoning.extract_everything likely expects an object with .raw_lines.
    
    # Quick fix: Pass a dummy object or adapt MistralReasoning.
    # Let's see MistralReasoning.extract_everything signature in a later step if needed.
    # For now, let's just pass the dict and see (or mock an object).
    
    class MockResult:
        def __init__(self, d):
            self.raw_lines = d.get('raw_text', '').split('\n')
            self.confidence = d.get('confidence', 0.0)
            self.engine = "easyocr"
            
    full_data = mistral.extract_everything(MockResult(ocr_result))
    
    # Pretty print ALL extracted data
    print("\n4. ALL EXTRACTED DATA:")
    print("="*60)
    print(json.dumps(full_data, indent=2, ensure_ascii=False))
    
    # Highlight key findings
    print("\n5. KEY FINDINGS:")
    print("-"*60)
    
    if 'student_name' in full_data and full_data['student_name']:
        print(f"   ✅ Student Name: {full_data['student_name']}")
    else:
        print(f"   ⚠️  Student Name: Not found")
    
    if 'issuer' in full_data:
        print(f"   ✅ Issuer: {full_data['issuer']}")
    
    if 'course_name' in full_data:
        print(f"   ✅ Course: {full_data['course_name']}")
    
    if 'certificate_ids' in full_data:
        print(f"   ✅ IDs: {full_data['certificate_ids']}")
    
    if 'urls' in full_data:
        print(f"   ✅ URLs: {full_data['urls']}")
    
    # List ALL fields found
    print(f"\n   📊 Total fields extracted: {len([k for k in full_data.keys() if not k.startswith('_')])}")
    print(f"   📋 Fields: {[k for k in full_data.keys() if not k.startswith('_')]}")
    
    print("\n" + "="*60)
    print("✅ EXTRACTION COMPLETE!")
    print("="*60)
    
    return full_data


if __name__ == "__main__":
    data = test_full_extraction()
