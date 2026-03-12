"""Didit Authentication Routes"""

from fastapi import APIRouter, HTTPException, Response, Request, Cookie
from fastapi.responses import JSONResponse
from typing import Optional
import jwt
import os
import secrets
from datetime import datetime, timedelta
from dotenv import load_dotenv

from src.database.models import get_sessions

# Load environment variables
load_dotenv()

router = APIRouter()

# Configuration from Didit SDK
DIDIT_APP_ID = os.getenv("NEXT_PUBLIC_DIDIT_APP_ID")
DIDIT_WORKFLOW_ID = os.getenv("NEXT_PUBLIC_DIDIT_WORKFLOW_ID")
DIDIT_REDIRECT_URI = os.getenv("NEXT_PUBLIC_DIDIT_REDIRECT_URI", "https://verify.didit.me/session/aMQ5m-NzLk9X?step=start")
DIDIT_API_KEY = os.getenv("DIDIT_API_KEY")
DIDIT_SHARED_SECRET_KEY = os.getenv("DIDIT_SHARED_SECRET_KEY")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "default-secret-key-change-this")
SESSION_EXPIRY_HOURS = int(os.getenv("SESSION_EXPIRY_HOURS", "24"))
COOKIE_NAME = "skillkendra_session"

# Build Didit verification URL with redirect URI
if DIDIT_WORKFLOW_ID:
    from urllib.parse import urlencode
    params = {"redirect_uri": DIDIT_REDIRECT_URI}
    DIDIT_VERIFICATION_URL = "https://verify.didit.me/verify/cUUfbikLuVDviVn4HQzR_Q"
else:
    DIDIT_VERIFICATION_URL = None


def create_jwt_token(data: dict) -> str:
    """Create a JWT token"""
    expiry = datetime.utcnow() + timedelta(hours=SESSION_EXPIRY_HOURS)
    payload = {
        **data,
        "exp": expiry,
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm="HS256")


def verify_jwt_token(token: str) -> Optional[dict]:
    """Verify and decode a JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


@router.post("/start")
async def start_didit():
    """
    Start Didit authentication flow.
    Returns the Didit verification URL.
    """
    if not DIDIT_VERIFICATION_URL:
        raise HTTPException(
            status_code=500,
            detail="Didit configuration is missing. Please set DIDIT_WORKFLOW_ID in .env"
        )
    
    return {
        "success": True,
        "verification_url": DIDIT_VERIFICATION_URL,
        "app_id": DIDIT_APP_ID,
        "workflow_id": DIDIT_WORKFLOW_ID,
        "message": "Redirect user to this URL for verification"
    }


@router.post("/callback")
async def didit_callback(
    request: Request,
    response: Response,
    verificationSessionId: Optional[str] = None,
    status: Optional[str] = None
):
    """
    Handle Didit verification callback.
    Creates a session and sets a cookie.
    
    Expected query parameters from Didit:
    - verificationSessionId: The session ID from Didit
    - status: Verification status (Approved, Declined, In Review)
    """
    
    # Get parameters from query string or request body
    if not verificationSessionId or not status:
        # Try to get from request body
        try:
            body = await request.json()
            verificationSessionId = body.get("verificationSessionId")
            status = body.get("status")
        except:
            pass
    
    if not verificationSessionId or not status:
        raise HTTPException(
            status_code=400,
            detail="Missing verificationSessionId or status"
        )
    
    # Only create session if verification was approved
    if status != "Approved":
        return {
            "success": False,
            "message": f"Verification {status.lower()}. Please try again.",
            "status": status
        }
    
    # Create session token
    session_token = secrets.token_urlsafe(32)
    
    # Store user data (in production, you'd fetch more data from Didit API)
    user_data = {
        "didit_session_id": verificationSessionId,
        "verification_status": status,
        "verified_at": datetime.utcnow().isoformat()
    }
    
    # Create JWT token
    jwt_token = create_jwt_token({
        "session_token": session_token,
        "didit_session_id": verificationSessionId
    })
    
    # Store session in database
    sessions = get_sessions()
    sessions.create_session(
        session_token=session_token,
        didit_session_id=verificationSessionId,
        verification_status=status,
        user_data=user_data,
        expiry_hours=SESSION_EXPIRY_HOURS
    )
    
    # Set HTTP-only cookie
    response.set_cookie(
        key=COOKIE_NAME,
        value=jwt_token,
        httponly=True,
        max_age=SESSION_EXPIRY_HOURS * 3600,
        samesite="lax",
        secure=False  # Set to True in production with HTTPS
    )
    
    return {
        "success": True,
        "message": "Authentication successful",
        "user": user_data
    }


@router.get("/session")
async def get_session(
    skillkendra_session: Optional[str] = Cookie(None)
):
    """
    Get current session information.
    Returns user data if authenticated.
    """
    if not skillkendra_session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Verify JWT token
    payload = verify_jwt_token(skillkendra_session)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    
    # Get session from database
    sessions = get_sessions()
    session = sessions.get_session(payload.get("session_token"))
    
    if not session:
        raise HTTPException(status_code=401, detail="Session not found or expired")
    
    return {
        "authenticated": True,
        "user": session.get("user_data"),
        "verification_status": session.get("verification_status"),
        "expires_at": session.get("expires_at")
    }


@router.post("/logout")
async def logout(
    response: Response,
    skillkendra_session: Optional[str] = Cookie(None)
):
    """
    Logout user and invalidate session.
    """
    if skillkendra_session:
        # Verify and get session token
        payload = verify_jwt_token(skillkendra_session)
        if payload:
            # Invalidate session in database
            sessions = get_sessions()
            sessions.invalidate_session(payload.get("session_token"))
    
    # Clear cookie
    response.delete_cookie(key=COOKIE_NAME)
    
    return {
        "success": True,
        "message": "Logged out successfully"
    }
