"""
ResQAI - Audit & Activity Logging Service
Provides compliance tracking, incident audit trails, and dispatcher activity monitoring.
"""

from datetime import datetime, timezone
import json
from backend.database import get_db, row_to_dict


def log_event(action, entity_type, entity_id=None, details=None, actor="system", conn=None):
    """
    Record an immutable audit log entry.
    Supports either an existing open connection or creates a new connection context.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    detail_str = json.dumps(details) if isinstance(details, (dict, list)) else str(details or "")

    if conn is not None:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO audit_logs (action, entity_type, entity_id, details, timestamp, actor)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (action, entity_type, entity_id, detail_str, now_iso, actor))
    else:
        with get_db() as c:
            cursor = c.cursor()
            cursor.execute("""
                INSERT INTO audit_logs (action, entity_type, entity_id, details, timestamp, actor)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (action, entity_type, entity_id, detail_str, now_iso, actor))


def get_recent_logs(limit=50):
    """
    Retrieve the most recent audit events.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM audit_logs
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        return [row_to_dict(r) for r in rows]
