import os
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, ForeignKey, Boolean
from sqlalchemy.orm import DeclarativeBase, sessionmaker, relationship
from datetime import datetime


class Base(DeclarativeBase):
    """Clase base para todos los modelos del ORM (SQLAlchemy 2.x)."""
    pass


class Section(Base):
    __tablename__ = 'sections'
    id = Column(Integer, primary_key=True)
    code = Column(String(10), unique=True, nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text)
    chapters = relationship("Chapter", back_populates="section", order_by="Chapter.code")

class Chapter(Base):
    __tablename__ = 'chapters'
    id = Column(Integer, primary_key=True)
    code = Column(String(10), unique=True, nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text)
    section_id = Column(Integer, ForeignKey('sections.id'))
    section = relationship("Section", back_populates="chapters")
    headings = relationship("Heading", back_populates="chapter", order_by="Heading.code")

class Heading(Base):
    __tablename__ = 'headings'
    id = Column(Integer, primary_key=True)
    code = Column(String(20), unique=True, nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text)
    chapter_id = Column(Integer, ForeignKey('chapters.id'))
    chapter = relationship("Chapter", back_populates="headings")
    subheadings = relationship("Subheading", back_populates="heading", order_by="Subheading.code")

class Subheading(Base):
    __tablename__ = 'subheadings'
    id = Column(Integer, primary_key=True)
    code = Column(String(20), unique=True, nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text)
    heading_id = Column(Integer, ForeignKey('headings.id'))
    heading = relationship("Heading", back_populates="subheadings")
    fractions = relationship("Fraction", back_populates="subheading", order_by="Fraction.code")

class Fraction(Base):
    __tablename__ = 'fractions'
    id = Column(Integer, primary_key=True)
    code = Column(String(20), unique=True, nullable=False)
    title = Column(String(500), nullable=True)
    description = Column(Text, nullable=False)
    subheading_id = Column(Integer, ForeignKey('subheadings.id'))
    subheading = relationship("Subheading", back_populates="fractions")

class Classification(Base):
    __tablename__ = 'classifications'
    id = Column(Integer, primary_key=True)
    product_description = Column(String(1000), nullable=False)
    hs_code = Column(String(20), nullable=False)
    confidence = Column(Float)
    method = Column(String(50))
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class RGIRule(Base):
    __tablename__ = 'rgi_rules'
    id = Column(Integer, primary_key=True)
    rule_number = Column(Integer, nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    examples = Column(Text)

class Client(Base):
    __tablename__ = 'crm_clients'
    id = Column(Integer, primary_key=True)
    rfc = Column(String(13), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    patent = Column(String(4), nullable=False)
    agent = Column(String(100))
    status = Column(String(20), default='Activo')
    created_at = Column(DateTime, default=datetime.utcnow)

class InventoryItem(Base):
    __tablename__ = 'erp_inventory'
    id = Column(Integer, primary_key=True)
    sku = Column(String(50), unique=True, nullable=False)
    description = Column(String(500), nullable=False)
    sat_code = Column(String(20), nullable=False)
    unit = Column(String(10), nullable=False)
    quantity = Column(Float, default=0.0)
    price = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id = Column(Integer, primary_key=True)
    username = Column(String(100), default='admin')
    action = Column(String(200), nullable=False)
    module = Column(String(50), nullable=False)
    details = Column(Text)
    ip_address = Column(String(50), default='127.0.0.1')
    created_at = Column(DateTime, default=datetime.utcnow)

class VucemAcuse(Base):
    __tablename__ = 'vucem_acuses'
    id = Column(Integer, primary_key=True)
    folio = Column(String(50), unique=True, nullable=False)
    type = Column(String(20), nullable=False) # 'COVE' o 'e-Document'
    rfc_importador = Column(String(13), nullable=False)
    status = Column(String(20), default='Pendiente') # 'Pendiente', 'Validado', 'Rechazado'
    error_details = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class CartaPorte(Base):
    __tablename__ = 'carta_porte'
    id = Column(Integer, primary_key=True)
    folio = Column(String(50), unique=True, nullable=False)
    origin = Column(String(200), nullable=False)
    destination = Column(String(200), nullable=False)
    goods_desc = Column(String(500), nullable=False)
    sat_code = Column(String(20), nullable=False)
    sat_unit = Column(String(10), nullable=False)
    vehicle_config = Column(String(50), nullable=False)
    status = Column(String(20), default='Borrador') # 'Borrador', 'Timbrado'
    created_at = Column(DateTime, default=datetime.utcnow)

class ManifestacionValor(Base):
    __tablename__ = 'manifestacion_valor'
    id = Column(Integer, primary_key=True)
    folio = Column(String(50), unique=True, nullable=False)
    rfc_importador = Column(String(20), nullable=False)
    razon_social = Column(String(200), nullable=False)
    metodo_valoracion = Column(String(100), nullable=False)
    valor_comercial = Column(Float, nullable=False)
    total_incrementables = Column(Float, nullable=False)
    valor_aduana_mxn = Column(Float, nullable=False)
    status = Column(String(20), default='Emitida') # 'Emitida', 'Anulada'

class SATProductKey(Base):
    __tablename__ = 'sat_product_keys'
    id = Column(Integer, primary_key=True)
    code = Column(String(8), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    default_hs_code = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)

class ChatThread(Base):
    __tablename__ = 'chat_threads'
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    finished = Column(Boolean, default=False)
    
    messages = relationship("ChatMessage", back_populates="thread", cascade="all, delete-orphan", order_by="ChatMessage.created_at")

class ChatMessage(Base):
    __tablename__ = 'chat_messages'
    id = Column(Integer, primary_key=True)
    thread_id = Column(Integer, ForeignKey('chat_threads.id'), nullable=False)
    sender = Column(String(10), nullable=False) # 'user' o 'bot'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    metadata_json = Column(Text, nullable=True)
    
    thread = relationship("ChatThread", back_populates="messages")

def init_db(db_path=None):
    if db_path is None:
        db_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance')
        os.makedirs(db_dir, exist_ok=True)
        db_path = os.path.join(db_dir, 'clasificador.db')
    engine = create_engine(f'sqlite:///{db_path}', echo=False)
    try:
        Base.metadata.create_all(engine)
    except Exception as e:
        print(f"Base.metadata.create_all bypass (race condition or table exists): {e}")
    return engine

def get_session(engine):
    Session = sessionmaker(bind=engine)
    return Session()
