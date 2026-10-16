# C:\Users\Aura\athenaeum_project\library_api\app\models\audit.py


import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)

from app.database import Base


class UserSession(Base):
    """Tracks login/logoff lifecycles, machine details, and session duration."""

    __tablename__ = "user_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(64), nullable=False, index=True)
    username = Column(String(128), nullable=False)
    role = Column(String(64), nullable=False)
    designation = Column(String(128), nullable=False)
    machine_name = Column(String(128), nullable=False)
    ip_address = Column(String(45), nullable=False)

    login_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    logout_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)


class AuditActivity(Base):
    """Stores action telemetry and cryptographic audit-ledger fields."""

    __tablename__ = "audit_activities"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("user_sessions.id"), nullable=True, index=True)
    timestamp = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    # Operator and terminal details
    user_id = Column(String(64), nullable=False, index=True)
    username = Column(String(128), nullable=False)
    role = Column(String(64), nullable=False)
    designation = Column(String(128), nullable=False)
    machine_name = Column(String(128), nullable=False)
    ip_address = Column(String(45), nullable=False)

    # Action telemetry
    category = Column(String(32), nullable=False, index=True)
    action_type = Column(String(64), nullable=False, index=True)
    target_entity = Column(String(64), nullable=True)
    target_id = Column(String(64), nullable=True)
    endpoint = Column(String(255), nullable=True)
    http_method = Column(String(10), nullable=True)

    # Audit details
    justification = Column(Text, nullable=True)
    diff_payload = Column(JSON, nullable=True)
    extra_metadata = Column(JSON, nullable=True)

    # Hash-chain fields used by app.services.audit_service.
    # Nullable values allow existing legacy/unhashed records to be represented
    # and detected by ledger verification rather than hidden by the ORM model.
    sequence_id = Column(Integer, nullable=True, unique=True, index=True)
    prev_hash = Column(String(64), nullable=True)
    record_hash = Column(String(64), nullable=True, index=True)
