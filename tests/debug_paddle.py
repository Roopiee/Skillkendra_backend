"""Deep debug - access OCRResult as dict"""

import cv2
from paddleocr import PaddleOCR

print("="*60)
print("PADDLEOCR 3.3.2 - Accessing Results")
print("="*60)

image = cv2.imread('data/sample_cert.jpg')
print(f"\n1. Image loaded: {image.shape}")

print("\n2. Initializing PaddleOCR...")
ocr = PaddleOCR(lang='en')  # Removed use_angle_cls (deprecated)
print("   ✅ Initialized")

print("\n3. Running OCR...")
result = ocr.ocr(image)  # Removed cls parameter

print("\n4. Accessing as dictionary:")
ocr_result = result[0]

# Try to access keys
print(f"   Keys: {list(ocr_result.keys())}")

# Try to access common keys
for key in ['input_path', 'page_index', 'dt_polys', 'dt_scores', 'rec_text', 'rec_score']:
    if key in ocr_result:
        value = ocr_result[key]
        if isinstance(value, list) and len(value) > 5:
            print(f"   {key}: List with {len(value)} items")
            print(f"      First 3: {value[:3]}")
        else:
            print(f"   {key}: {value}")

# Show all keys and their types
print("\n5. All keys and types:")
for key, value in ocr_result.items():
    value_type = type(value).__name__
    if isinstance(value, list):
        print(f"   {key}: {value_type} (length: {len(value)})")
    else:
        print(f"   {key}: {value_type}")

print("\n" + "="*60)
