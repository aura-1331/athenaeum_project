from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()

# Add your existing tables here so Alembic ignores them during autogenerate
# For now, just add a dummy class if you don't want to copy all of them:
class ExistingTablePlaceholder(Base):
    __tablename__ = 'users' # Replace with a real table name from your DB
    user_id = Column(Integer, primary_key=True)

class LoginAuditLog(Base):
    __tablename__ = 'login_audit_log'
    
    id = Column(Integer, primary_key=True)
    login_id = Column(Integer)
    role = Column(String)
    login_name = Column(String)
    action = Column(String) 
    device_used = Column(String)
    ip_address = Column(String)
    timestamp = Column(DateTime, default=func.now())