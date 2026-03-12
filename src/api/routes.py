"""API Routes with Triple OCR Verification"""

from fastapi import APIRouter, UploadFile, File, HTTPException
import tempfile
import os
import shutil
import logging

from src.pipeline.complete_verifier import CompleteCertificateVerifier
from src.core.schemas import VerificationResult
from pydantic import BaseModel

class ManualVerificationRequest(BaseModel):
    certificate_id: str
    issuer_url: str

router = APIRouter()
logger = logging.getLogger(__name__)

_verifier = None

def get_verifier():
    global _verifier
    if _verifier is None:
        _verifier = CompleteCertificateVerifier()
    return _verifier

@router.post("/verify/manual", response_model=VerificationResult)
async def manual_verify_certificate(request: ManualVerificationRequest):
    """Manually verify a certificate using ID and URL"""
    try:
        verifier = get_verifier()
        # Access the underlying verification agent from the verifier pipeline
        # Note: Depending on implementation, you might need to adjust this access
        if hasattr(verifier, 'verification_service'):
             result = await verifier.verification_service.manual_verify(
                 request.certificate_id, 
                 request.issuer_url
             )
             return result
        else:
            # Fallback if service not directly accessible
            from src.agents.verification.service import VerificationAgent
            agent = VerificationAgent()
            result = await agent.manual_verify(
                request.certificate_id,
                request.issuer_url
            )
            return result
    except Exception as e:
        logger.exception("Manual verification failed")
        raise HTTPException(status_code=500, detail=f"Manual verification failed: {str(e)}")

@router.post("/verify")
async def verify_certificate(file: UploadFile = File(...)):
    """Verify certificate using OCR + verification pipeline"""

    allowed_types = ["image/jpeg", "image/jpg", "image/png", "application/pdf"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail=f"Invalid file type: {file.content_type}")

    tmp_path = None
    _response_data: dict = {}

    try:
        # -------------------------
        # Save uploaded file
        # -------------------------
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=os.path.splitext(file.filename)[1]
        ) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name

        # -------------------------
        # Run verification
        # -------------------------
        logger.info(f"🔍 [API] Certificate retrieved to {tmp_path}. Starting verification process pipeline...")
        verifier = get_verifier()
        result = await verifier.verify_certificate(tmp_path)

        best_result = result.get("best_result", {})

        response = {
            "success": True,
            "filename": file.filename,
            "data": {
                "ocr": {
                    "engines_used": ["easyocr", "mistral", "tesseract"],
                    "all_results": result.get("ocr_results", []),
                },
                "extracted_data": best_result.get("extracted_data", {}),
                "forensics": result.get("forensics", {}),
                "verification": best_result.get("verification", {}),
                "all_verification_attempts": result.get("verification_attempts", []),
                "summary": result.get("summary", {}),
            },
        }

        # Capture data for the finally block before returning
        _response_data = response.get("data", {})

        if best_result.get("verification", {}).get("is_verified"):
            logger.info(f"✅ [API] Certificate validated successfully!")
        else:
            logger.info(f"❌ [API] Certificate could not be validated.")
            
        return response

    except Exception as e:
        logger.exception("Verification failed")
        raise HTTPException(
            status_code=500,
            detail=f"Verification failed: {str(e)}"
        )

    finally:
        # -------------------------
        # Save verification history (NON-BLOCKING)
        # -------------------------
        try:
            from src.database.models import get_history

            history = get_history()
            history.add_verification({
                "filename": file.filename,
                "extracted_data": _response_data.get("extracted_data", {}),
                "verification": _response_data.get("verification", {}),
                "forensics": _response_data.get("forensics", {}),
            })
            logger.info("[INFO] Verification saved to history")

        except Exception as e:
            logger.warning(f"[WARNING] Failed to save verification history: {e}")

        # -------------------------
        # Cleanup temp file
        # -------------------------
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


@router.get("/health")
async def health():
    return {"status": "healthy", "ocr": "triple"}


