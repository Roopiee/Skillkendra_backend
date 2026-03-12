from src.core.models import OCREngine, OCRResult, ExtractedEvidence, VerificationResult
from datetime import datetime

# Test 1: Create a valid OCR result
ocr_result = OCRResult(
    engine=OCREngine.PADDLE,
    raw_lines=["Certificate of Completion", "John Doe", "UC-12345"],
    confidence=0.92,
    page_number=0
)
print("✅ OCRResult created:", ocr_result)

# Test 2: Try invalid confidence (should fail)
try:
    bad_result = OCRResult(
        engine=OCREngine.PADDLE,
        raw_lines=["text"],
        confidence=150,  # Invalid!
        page_number=0
    )
except Exception as e:
    print("✅ Pydantic caught invalid data:", e)

# Test 3: Create evidence
evidence = ExtractedEvidence(
    engine=OCREngine.PADDLE,
    issuer="Udemy",
    certificate_ids=["UC-12345"],
    urls=["https://ude.my/UC-12345"],
    names=["John Doe"],
    confidence=0.92,
    page_number=0
)
print("✅ ExtractedEvidence created:", evidence)

# Test 4: Create final result
result = VerificationResult(
    final_verdict="VERIFIED",
    verified_via={"engine": "paddle", "method": "url"},
    confidence=0.95,
    evidence_used=[evidence],
    timestamp=datetime.now().isoformat()
)
print("✅ VerificationResult created:", result)

# Test 5: Convert to JSON
print("\n📄 As JSON:")
print(result.model_dump_json(indent=2))