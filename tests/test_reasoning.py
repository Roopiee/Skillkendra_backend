"""Test Mistral reasoning with real certificate"""

import cv2
import os
from src.agents.ocr.paddle_ocr import SimplePaddleOCR
from src.agents.ocr.easy_ocr import SimpleEasyOCR
from src.agents.reasoning.mistral_agent import MistralReasoning


def find_certificate():
    """Find certificate file in project directory."""
    possible_files = [
        'data/sample_cert.jpg',
        'data/sample_cert.png',
        'data/sample_cert.pdf',
        'data/certificate.jpg',
        'data/certificate.png'
    ]
    
    for filename in possible_files:
        if os.path.exists(filename):
            return filename
    
    return None


def test_reasoning_with_certificate():
    """Extract structured data from your certificate."""
    
    print("="*60)
    print("MISTRAL REASONING TEST")
    print("="*60)
    
    # Step 1: Find and load certificate
    print("\n1. Finding certificate...")
    cert_file = find_certificate()
    
    if not cert_file:
        print("No certificate found!")
        print("\n Please put a certificate file in the project root:")
        print("   - sample_cert.jpg")
        print("   - sample_cert.png")
        print("   - certificate.jpg")
        return None
    
    print(f"Found: {cert_file}")
    
    image = cv2.imread(cert_file)
    if image is None:
        print(f"Could not read {cert_file}")
        return None
    
    # Step 2: Run OCR (both engines)
    print("\n2. Running OCR...")
    paddle = SimplePaddleOCR()
    easy = SimpleEasyOCR()
    
    paddle_result = paddle.extract_text(image)
    easy_result = easy.extract_text(image)
    
    paddle_lines = paddle_result.get('raw_text', '').split('\n')
    easy_lines = easy_result.get('raw_text', '').split('\n')
    
    print(f"   PaddleOCR: {len(paddle_lines)} lines")
    print(f"   EasyOCR: {len(easy_lines)} lines")
    
    # Step 3: Initialize Mistral
    print("\n3. Initializing Mistral...")
    try:
        mistral = MistralReasoning()
    except ValueError as e:
        print(f"{e}")
        print("\n Make sure you have a .env file with:")
        print("   MISTRAL_API_KEY=your_api_key_here")
        return None
    
    # Step 4: Extract evidence from both
    # MistralReasoning likely expects objects. Wrap them.
    from enum import Enum
    class OCREngine(Enum):
        PADDLE = "paddle"
        EASYOCR = "easyocr"
        
    class MockResult:
        def __init__(self, d, engine):
            self.raw_lines = d.get('raw_text', '').split('\n')
            self.confidence = d.get('confidence', 0.0)
            self.engine = engine
            self.page_number = 0
            
    print("\n4. Extracting structured data...")
    evidence_list = mistral.extract_from_multiple([
        MockResult(paddle_result, OCREngine.PADDLE),
        MockResult(easy_result, OCREngine.EASYOCR)
    ])
    
    # Step 5: Show results
    print("\n" + "="*60)
    print("EXTRACTED EVIDENCE")
    print("="*60)
    
    for i, evidence in enumerate(evidence_list, 1):
        print(f"\nEvidence #{i} (from {evidence.engine.value}):")
        print(f"   Issuer: {evidence.issuer}")
        print(f"   Student: {evidence.names}")
        print(f"   Certificate IDs: {evidence.certificate_ids}")
        print(f"   URLs: {evidence.urls}")
        print(f"   Confidence: {evidence.confidence:.2%}")
    
    # Step 6: Summary
    print("\n" + "="*60)
    print("REASONING COMPLETE!")
    print("="*60)
    
    # Show combined insights
    all_issuers = set(e.issuer for e in evidence_list if e.issuer)
    all_ids = set(id for e in evidence_list for id in e.certificate_ids)
    all_urls = set(url for e in evidence_list for url in e.urls)
    all_names = set(name for e in evidence_list for name in e.names)
    
    print("\n COMBINED INSIGHTS:")
    print(f"   Issuers found: {list(all_issuers)}")
    print(f"   Names found: {list(all_names)}")
    print(f"   Certificate IDs: {list(all_ids)}")
    print(f"   URLs: {list(all_urls)}")
    
    return evidence_list


if __name__ == "__main__":
    evidence = test_reasoning_with_certificate()
