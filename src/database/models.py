"""
Database models for verification history
"""

import sqlite3
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import List, Dict, Any, Optional
import json


class VerificationHistory:
    """SQLite database for verification history"""
    
    def __init__(self, db_path: str = "verification_history.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database with schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS verifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                filename TEXT,
                student_name TEXT,
                issuer TEXT,
                course_name TEXT,
                certificate_id TEXT,
                is_verified BOOLEAN,
                verification_method TEXT,
                confidence_score REAL,
                is_high_risk BOOLEAN,
                manipulation_score REAL,
                verification_url TEXT,
                raw_data TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    def add_verification(self, data: Dict[str, Any]) -> int:
        """
        Add a verification to history.
        
        Returns:
            ID of inserted record
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Extract fields
        extracted = data.get('extracted_data', {})
        verification = data.get('verification', {})
        forensics = data.get('forensics', {})
        
        cursor.execute("""
            INSERT INTO verifications (
                timestamp, filename, student_name, issuer, course_name,
                certificate_id, is_verified, verification_method,
                confidence_score, is_high_risk, manipulation_score,
                verification_url, raw_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now(ZoneInfo("Asia/Kolkata")).isoformat(),
            data.get('filename'),
            extracted.get('student_name'),
            extracted.get('issuer'),
            extracted.get('course_name'),
            extracted.get('certificate_ids', [None])[0] if extracted.get('certificate_ids') else None,
            verification.get('is_verified'),
            verification.get('method'),
            verification.get('confidence_score'),
            forensics.get('is_high_risk'),
            forensics.get('manipulation_score'),
            verification.get('verification_url'),
            json.dumps(data)  # Store full data as JSON
        ))
        
        record_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return record_id
    
    def get_recent(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent verifications"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM verifications
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get verification statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total verifications
        cursor.execute("SELECT COUNT(*) FROM verifications")
        total = cursor.fetchone()[0]
        
        # Verified count
        cursor.execute("SELECT COUNT(*) FROM verifications WHERE is_verified = 1")
        verified = cursor.fetchone()[0]
        
        # High risk count
        cursor.execute("SELECT COUNT(*) FROM verifications WHERE is_high_risk = 1")
        high_risk = cursor.fetchone()[0]
        
        # Average confidence
        cursor.execute("SELECT AVG(confidence_score) FROM verifications WHERE is_verified = 1")
        avg_confidence = cursor.fetchone()[0] or 0
        
        # Recent activity (last 24h)
        cursor.execute("""
            SELECT COUNT(*) FROM verifications 
            WHERE timestamp > datetime('now', '-1 day')
        """)
        last_24h = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_verifications': total,
            'verified_count': verified,
            'unverified_count': total - verified,
            'high_risk_count': high_risk,
            'success_rate': (verified / total * 100) if total > 0 else 0,
            'average_confidence': round(avg_confidence, 2),
            'last_24h': last_24h
        }
    
    def search(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search verifications by name, issuer, or certificate ID"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        search_term = f"%{query}%"
        cursor.execute("""
            SELECT * FROM verifications
            WHERE student_name LIKE ? 
               OR issuer LIKE ?
               OR certificate_id LIKE ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (search_term, search_term, search_term, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]


class UserSession:
    """SQLite database for user authentication sessions"""
    
    def __init__(self, db_path: str = "verification_history.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database with user_sessions schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_token TEXT UNIQUE NOT NULL,
                didit_session_id TEXT,
                verification_status TEXT,
                user_data TEXT,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 1
            )
        """)
        
        # Create index for faster lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_session_token 
            ON user_sessions(session_token)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_active_sessions 
            ON user_sessions(is_active, expires_at)
        """)
        
        conn.commit()
        conn.close()
    
    def create_session(
        self, 
        session_token: str,
        didit_session_id: str,
        verification_status: str,
        user_data: Dict[str, Any],
        expiry_hours: int = 24
    ) -> int:
        """
        Create a new user session.
        
        Returns:
            ID of inserted session record
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        created_at = datetime.now(ZoneInfo("Asia/Kolkata"))
        expires_at = created_at + __import__('datetime').timedelta(hours=expiry_hours)
        
        cursor.execute("""
            INSERT INTO user_sessions (
                session_token, didit_session_id, verification_status,
                user_data, created_at, expires_at, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            session_token,
            didit_session_id,
            verification_status,
            json.dumps(user_data),
            created_at.isoformat(),
            expires_at.isoformat(),
            True
        ))
        
        session_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return session_id
    
    def get_session(self, session_token: str) -> Optional[Dict[str, Any]]:
        """Get session by token if valid and not expired"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM user_sessions
            WHERE session_token = ? 
            AND is_active = 1
            AND expires_at > ?
        """, (session_token, datetime.now(ZoneInfo("Asia/Kolkata")).isoformat()))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            session = dict(row)
            # Parse user_data JSON
            if session.get('user_data'):
                session['user_data'] = json.loads(session['user_data'])
            return session
        return None
    
    def invalidate_session(self, session_token: str) -> bool:
        """Invalidate a session (logout)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE user_sessions
            SET is_active = 0
            WHERE session_token = ?
        """, (session_token,))
        
        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        return rows_affected > 0
    
    def cleanup_expired_sessions(self):
        """Remove expired sessions from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM user_sessions
            WHERE expires_at < ?
        """, (datetime.now(ZoneInfo("Asia/Kolkata")).isoformat(),))
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        return deleted_count


# Singleton instance
_history_instance: Optional[VerificationHistory] = None
_session_instance: Optional[UserSession] = None

def get_history() -> VerificationHistory:
    global _history_instance
    if _history_instance is None:
        _history_instance = VerificationHistory()
    return _history_instance

def get_sessions() -> UserSession:
    global _session_instance
    if _session_instance is None:
        _session_instance = UserSession()
    return _session_instance
