import uuid
import json
import sqlite3
from typing import Optional, Any, Dict

def log_audit_event(
    conn: sqlite3.Connection,
    tenant_id: str,
    action: str,
    entity_type: str,
    entity_id: str,
    user_id: Optional[str] = None,
    old_values: Optional[Dict[str, Any]] = None,
    new_values: Optional[Dict[str, Any]] = None,
    client_ip: Optional[str] = None
) -> str:
    """
    Appends an immutable audit event to the tenant's audit trail.
    """
    event_id = str(uuid.uuid4())
    conn.execute("""
        INSERT INTO audit_events (
            id, tenant_id, user_id, action, entity_type, entity_id,
            old_values_json, new_values_json, client_ip
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        event_id,
        tenant_id,
        user_id,
        action,
        entity_type,
        entity_id,
        json.dumps(old_values) if old_values else None,
        json.dumps(new_values) if new_values else None,
        client_ip
    ))
    return event_id
