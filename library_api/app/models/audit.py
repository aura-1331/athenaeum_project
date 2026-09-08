import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Integer, DateTime, Boolean, JSON, ForeignKey
from app.database import Base

class UserSession(Base):
    """Tracks login/logoff lifecycles, machine details, and total session duration."""
    __tablename__ = "user_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(64), nullable=False, index=True)
    username = Column(String(128), nullable=False)
    role = Column(String(64), nullable=False)                    # e.g., Senior Cataloger
    designation = Column(String(128), nullable=False)             # e.g., Head of Preservation
    machine_name = Column(String(128), nullable=False)            # e.g., TERMINAL-01 / Hostname
    ip_address = Column(String(45), nullable=False)
    
    login_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    logout_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, default=0, nullable=False) # Total active time in seconds
    is_active = Column(Boolean, default=True, nullable=False)


class AuditActivity(Base):
    """Tracks every individual action, edit, diff, and query."""
    __tablename__ = "audit_activities"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("user_sessions.id"), nullable=True, index=True)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    # Operator & Terminal details
    user_id = Column(String(64), nullable=False, index=True)
    username = Column(String(128), nullable=False)
    role = Column(String(64), nullable=False)
    designation = Column(String(128), nullable=False)
    machine_name = Column(String(128), nullable=False)
    ip_address = Column(String(45), nullable=False)

    # Action telemetry
    category = Column(String(32), nullable=False, index=True)    # e.g., AUTH, CATALOG_WRITE, CATALOG_READ
    action_type = Column(String(64), nullable=False, index=True) # e.g., LOGIN, LOGOUT, CREATE, UPDATE, DELETE
    target_entity = Column(String(64), nullable=True)             # e.g., AuthorityRecord
    target_id = Column(String(64), nullable=True)
    endpoint = Column(String(255), nullable=True)
    http_method = Column(String(10), nullable=True)
    
    # Audit details
    justification = Column(Text, nullable=True)
    diff_payload = Column(JSON, nullable=True)                    # Field changes: {"from": "A", "to": "B"}
    extra_metadata = Column(JSON, nullable=True)                  # URL query params, filters used