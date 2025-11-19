from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from core.database import Base

class Address(Base):
    __tablename__ = "addresses"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=False)
    rfc = Column(String(13), nullable=True)
    label = Column(String(80), nullable=True)
    street = Column(String(255), nullable=False)
    city = Column(String(120), nullable=False)
    state = Column(String(120), nullable=False)
    postal_code = Column(String(10), nullable=False)
    country = Column(String(80), nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relaciones
    user = relationship("User", back_populates="addresses")
    orders = relationship("Order", back_populates="address")