"""Test prompt engineering with Mistral"""

import os
from dotenv import load_dotenv
try:
    from mistralai.client import Mistral  # older SDK (EC2 Ubuntu)
except ImportError:
    from mistralai import Mistral          # newer SDK (Mac)

load_dotenv()
client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))

# Sample OCR text (messy on purpose)
ocr_text = """
Google
COURSE
CERTIFICATE
Oct 15, 2022
ROOPAK BHUKYA
F
OR
has successfully completed
The Bits and Bytes of Computer Networking
coursera
Certificate ID: ABC123XYZ
ude . my/ABC123XYZ
"""

# Prompt v1: Simple (will fail)
print("="*60)
print("TEST 1: Simple Prompt")
print("="*60)

prompt_v1 = f"Extract data from this certificate text:\n\n{ocr_text}"

response = client.chat.complete(
    model="mistral-large-latest",
    messages=[{"role": "user", "content": prompt_v1}]
)

print(response.choices[0].message.content)

# Prompt v2: Structured (better)
print("\n" + "="*60)
print("TEST 2: Structured Prompt")
print("="*60)

prompt_v2 = f"""You are a certificate data extractor.

Extract the following from this OCR text:
- student_name
- issuer (who issued the certificate)
- course_name
- completion_date (YYYY-MM-DD format)
- certificate_id
- urls (any verification URLs)

OCR Text:
{ocr_text}

Return ONLY a JSON object with these fields. If a field is not found, use null.
"""

response = client.chat.complete(
    model="mistral-large-latest",
    messages=[{"role": "user", "content": prompt_v2}]
)

print(response.choices[0].message.content)

# Prompt v3: With JSON schema (best)
print("\n" + "="*60)
print("TEST 3: Structured Output (JSON mode)")
print("="*60)

prompt_v3 = f"""Extract certificate information from this OCR text.

OCR Text:
{ocr_text}

Return a JSON object with:
- issuer: string or null (e.g., "Coursera", "Udemy")
- student_name: string or null
- course_name: string or null
- completion_date: string or null (YYYY-MM-DD format)
- certificate_ids: array of strings (certificate IDs found)
- urls: array of strings (any verification URLs, fix broken ones)

Rules:
1. Fix broken URLs (e.g., "ude . my" → "ude.my")
2. Combine split words (e.g., "F" + "OR" → "FOR", but this is not needed in output)
3. Recognize issuers from context (e.g., "coursera" text means issuer is "Coursera")
4. If unsure, use null
"""

response = client.chat.complete(
    model="mistral-large-latest",
    messages=[{"role": "user", "content": prompt_v3}],
    response_format={"type": "json_object"}
)

print(response.choices[0].message.content)

