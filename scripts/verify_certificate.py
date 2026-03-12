"""
Complete Certificate Verification Script
Usage: python verify_certificate.py sample_cert.jpg
"""

import asyncio
import sys
from src.pipeline.complete_verifier import CompleteCertificateVerifier


async def verify(image_path: str):
    """Verify a certificate image"""
    verifier = CompleteCertificateVerifier()
    result = await verifier.verify_certificate(image_path)
    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python verify_certificate.py <path_to_certificate>")
        print("Example: python verify_certificate.py sample_cert.jpg")
        sys.exit(1)
    
    cert_path = sys.argv[1]
    result = asyncio.run(verify(cert_path))
