"""Debug why name isn't being extracted"""

import cv2
from src.agents.ocr.paddle_ocr import SimplePaddleOCR
from src.agents.ocr.easy_ocr import SimpleEasyOCR
from src.agents.reasoning.mistral_agent import MistralReasoning

image = cv2.imread('data/sample_cert.jpg')

print("="*60)
print("DEBUGGING NAME EXTRACTION")
print("="*60)

# Get OCR text
print("\n1. What PaddleOCR extracted:")
print("-"*60)
paddle = SimplePaddleOCR()
paddle_result = paddle.extract_text(image)

lines = paddle_result.get('raw_text', '').split('\n')
for i, line in enumerate(lines, 1):
    print(f"{i:2d}. {line}")

print("\n2. What EasyOCR extracted:")
print("-"*60)
easy = SimpleEasyOCR()
easy_result = easy.extract_text(image)

lines = easy_result.get('raw_text', '').split('\n')
for i, line in enumerate(lines, 1):
    print(f"{i:2d}. {line}")

print("\n3. Testing Mistral with explicit name extraction:")
print("-"*60)

# Build a better prompt specifically for your certificate
full_text = paddle_result.get('raw_text', '')

try:
    from mistralai.client import Mistral  # older SDK (EC2 Ubuntu)
except ImportError:
    from mistralai import Mistral          # newer SDK (Mac)
import os
from dotenv import load_dotenv
import json

load_dotenv()
client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))

prompt = f"""You are extracting data from a Udemy certificate.

OCR Text:
{full_text}

Look for:
1. Student name - typically appears near "Certificate of Completion" or after recipient/holder text
2. Certificate ID - starts with "UC-" 
3. Course name - the course title

Return JSON:
{{
  "student_name": "full name or null",
  "course_name": "course title or null", 
  "certificate_id": "UC-... or null",
  "issuer": "Udemy"
}}

Rules:
- Look carefully for ANY proper name (capitalized words that could be a person's name)
- The name might be split across lines
- It might be near words like "awarded to", "presented to", or just appear between title and course name
- If you see a name, include it even if not 100% sure

Return ONLY the JSON object."""

response = client.chat.complete(
    model="mistral-large-latest",
    messages=[{"role": "user", "content": prompt}],
    response_format={"type": "json_object"}
)

result = json.loads(response.choices[0].message.content)
print(json.dumps(result, indent=2))

print("\n" + "="*60)
