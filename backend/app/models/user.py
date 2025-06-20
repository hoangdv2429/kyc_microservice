from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.models.base import Base

class User(Base):
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False, index=True)
    phone = Column(String, unique=True, nullable=True)
    kyc_status = Column(Integer, default=0)  # 0=none, 1=partial, 2=full
    kyc_updated = Column(DateTime, nullable=True) 