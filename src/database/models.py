from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Float, Boolean, Text, Integer, DateTime
from datetime import datetime, timezone

class Base(DeclarativeBase):
    """
    SQLAlchemy 2.0 ORM base sınıfı (Tüm modeller bundan türetilir)
    """
    pass

class InvoiceRecord(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # SaaS Multi-Tenancy Sütunları
    tenant_id: Mapped[str] = mapped_column(String(50), index=True)
    file_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    
    # Fatura Özel Alanları
    fatura_no: Mapped[str] = mapped_column(String(100), nullable=True)
    tarih: Mapped[str] = mapped_column(String(50), nullable=True)
    satici_unvan: Mapped[str] = mapped_column(String(200), nullable=True)
    alici_unvan: Mapped[str] = mapped_column(String(200), nullable=True)
    
    ara_toplam: Mapped[float] = mapped_column(Float, nullable=True)
    kdv_tutari: Mapped[float] = mapped_column(Float, nullable=True)
    toplam_tutar: Mapped[float] = mapped_column(Float, nullable=True)
    para_birimi: Mapped[str] = mapped_column(String(10), nullable=True)
    
    kalemler: Mapped[str] = mapped_column(Text, nullable=True) # Liste -> Virgül ayrılmış Metin
    
    # Programatik ve AI Mantık Sütunları
    confidence_score: Mapped[float] = mapped_column(Float, nullable=True)
    math_error: Mapped[bool] = mapped_column(Boolean, default=False)
    low_confidence: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Kaynak dosya izi
    source_file: Mapped[str] = mapped_column(String(500), nullable=True)
    
    # Kayıt Zamanı
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

class ContractRecord(Base):
    __tablename__ = "contracts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # SaaS Multi-Tenancy Sütunları
    tenant_id: Mapped[str] = mapped_column(String(50), index=True)
    file_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    
    # Sözleşme Özel Alanları
    sozlesme_konusu: Mapped[str] = mapped_column(String(300), nullable=True)
    sozlesme_tarihi: Mapped[str] = mapped_column(String(50), nullable=True)
    taraflar: Mapped[str] = mapped_column(Text, nullable=True)
    gecerlilik_suresi: Mapped[str] = mapped_column(String(100), nullable=True)
    fesih_sartlari_var_mi: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Programatik ve AI Mantık Sütunları
    confidence_score: Mapped[float] = mapped_column(Float, nullable=True)
    low_confidence: Mapped[bool] = mapped_column(Boolean, default=False)
    
    source_file: Mapped[str] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
