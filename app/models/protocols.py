"""
Modelos para Protocolos (Productos digitales educativos).
Los protocolos son productos 100% digitales con contenido estructurado en fases.
Los usuarios obtienen acceso después de comprar.
"""
from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, ForeignKey, Text, Enum as SQLEnum, UniqueConstraint, Table
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from core.database import Base
import enum

# Tabla de asociación muchos-a-muchos: protocolos ↔ productos relacionados
protocol_product_association = Table(
    'protocol_products',
    Base.metadata,
    Column('protocol_id', Integer, ForeignKey('protocols.id', ondelete='CASCADE'), primary_key=True),
    Column('product_id', Integer, ForeignKey('products.id', ondelete='CASCADE'), primary_key=True)
)


class ProtocolCategory(Base):
    """
    Categorías de Protocolos (Sistema respiratorio, Sistema endocrino, Sistema nervioso, etc).
    Las categorías se crean dinámicamente y los protocolos se asocian a ellas.
    """
    __tablename__ = "protocol_categories"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    slug = Column(String(100), nullable=False, unique=True, index=True)
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relaciones
    protocols = relationship("Protocol", back_populates="category")
    
    def __repr__(self):
        return f"<ProtocolCategory(id={self.id}, name={self.name})>"


class Protocol(Base):
    """
    Modelo principal de Protocolos.
    Un protocolo es un producto digital con contenido estructurado en fases.
    """
    __tablename__ = "protocols"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Información básica
    name = Column(String(255), nullable=False, index=True)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text)  # Descripción breve (resumen para listing)
    long_description = Column(Text)  # Descripción larga (en la página del protocolo)
    
    # Precio e imagen propios del protocolo (es una entidad vendible independiente)
    price = Column(Numeric(10, 2), nullable=False, default=0)
    image_url = Column(Text, nullable=True)

    # Categoría del protocolo
    category_id = Column(Integer, ForeignKey("protocol_categories.id"), nullable=False, index=True)
    
    # Información del protocolo
    author = Column(String(255))  # Autor del protocolo
    version = Column(String(50), default="1.0")  # Versión del protocolo
    is_published = Column(Boolean, default=False)  # Solo protocolos publicados son vendibles
    is_featured = Column(Boolean, default=False)  # Destacado en la tienda
    
    # Metadatos
    estimated_duration_hours = Column(Integer)  # Duración estimada en horas    
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relaciones
    # NOTA: la ÚNICA relación con Product es de recomendación ("productos para seguir
    # este protocolo"). El protocolo NO depende de ningún producto para venderse.
    associated_products = relationship("Product", secondary=protocol_product_association, lazy="selectin")
    category = relationship("ProtocolCategory", back_populates="protocols", foreign_keys=[category_id])
    phases = relationship("ProtocolPhase", back_populates="protocol", cascade="all, delete-orphan", order_by="ProtocolPhase.order")
    user_accesses = relationship("ProtocolAccess", back_populates="protocol", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Protocol(id={self.id}, name={self.name}, is_published={self.is_published})>"


class ProtocolPhase(Base):
    """
    Fases dentro de un protocolo.
    Cada fase es un paso o sección del protocolo.
    """
    __tablename__ = "protocol_phases"
    
    __table_args__ = (UniqueConstraint('protocol_id', 'slug', name='uq_phase_protocol_slug'),)

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    protocol_id = Column(Integer, ForeignKey("protocols.id"), nullable=False, index=True)
    
    # Información de la fase
    title = Column(String(255), nullable=False)
    slug = Column(String(100), nullable=False, index=True)
    description = Column(Text)  # Descripción breve de la fase
    order = Column(Integer, nullable=False)  # Orden en que aparece (1, 2, 3...)
    
    # Contenido
    content = Column(Text, nullable=False)  # HTML con el contenido de la fase
    duration_minutes = Column(Integer)  # Duración estimada en minutos
    
    # Metadatos
    is_required = Column(Boolean, default=True)  # Si es obligatoria completarla
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relaciones
    protocol = relationship("Protocol", back_populates="phases", foreign_keys=[protocol_id])
    resources = relationship("ProtocolResource", back_populates="phase", cascade="all, delete-orphan", order_by="ProtocolResource.order")
    
    class Config:
        pass
    
    def __repr__(self):
        return f"<ProtocolPhase(id={self.id}, title={self.title}, order={self.order})>"


class ProtocolResource(Base):
    """
    Recursos adicionales en cada fase (imágenes, PDFs, videos, enlaces).
    """
    __tablename__ = "protocol_resources"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    phase_id = Column(Integer, ForeignKey("protocol_phases.id"), nullable=False, index=True)
    
    # Tipo de recurso
    resource_type = Column(String(50), nullable=False)  # image, pdf, video, link, download
    title = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Contenido del recurso
    url = Column(Text, nullable=False)  # URL de la imagen, video, PDF, etc
    file_path = Column(String(500))  # Ruta local si está almacenado localmente
    
    # Orden y visibilidad
    order = Column(Integer, nullable=False)  # Orden en que aparece en la fase
    is_visible = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relaciones
    phase = relationship("ProtocolPhase", back_populates="resources", foreign_keys=[phase_id])
    
    def __repr__(self):
        return f"<ProtocolResource(id={self.id}, type={self.resource_type}, title={self.title})>"


class ProtocolProgress(Base):
    """
    Registro del progreso del usuario en cada protocolo.
    Trackea qué fases ha completado el usuario.
    """
    __tablename__ = "protocol_progress"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    protocol_id = Column(Integer, ForeignKey("protocols.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Progreso
    current_phase_order = Column(Integer, default=0)  # Orden de la fase actual (0-indexed)
    completed_phases = Column(Integer, default=0)  # Número de fases completadas
    total_phases = Column(Integer, default=0)  # Total de fases al momento de crear
    
    # Timestamps
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    last_accessed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relaciones
    protocol = relationship("Protocol", foreign_keys=[protocol_id])
    user = relationship("User", foreign_keys=[user_id])
    
    def __repr__(self):
        return f"<ProtocolProgress(user_id={self.user_id}, protocol_id={self.protocol_id}, progress={self.current_phase_order}/{self.total_phases})>"


class ProtocolAccess(Base):
    """
    Registro de acceso: Qué usuarios tienen acceso a qué protocolos (después de comprar).
    Se crea automáticamente cuando se completa una orden con un protocolo.
    """
    __tablename__ = "protocol_accesses"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    protocol_id = Column(Integer, ForeignKey("protocols.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Referencia a la orden/compra
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    order_item_id = Column(Integer, ForeignKey("order_items.id"), nullable=False, index=True)
    
    # Control de acceso
    is_active = Column(Boolean, default=True)  # Puede desactivarse si se revoca el acceso
    access_until = Column(DateTime(timezone=True), nullable=True)  # Acceso limitado en el tiempo (opcional)
    
    # Timestamps
    granted_at = Column(DateTime(timezone=True), server_default=func.now())
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    last_accessed_at = Column(DateTime(timezone=True), nullable=True)  # Última vez que el usuario abrió el protocolo
    
    # Relaciones
    protocol = relationship("Protocol", back_populates="user_accesses", foreign_keys=[protocol_id])
    user = relationship("User", foreign_keys=[user_id])
    order = relationship("Order", foreign_keys=[order_id])
    order_item = relationship("OrderItem", foreign_keys=[order_item_id])
    
    def __repr__(self):
        return f"<ProtocolAccess(user_id={self.user_id}, protocol_id={self.protocol_id}, is_active={self.is_active})>"
