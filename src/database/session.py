from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from src.config import settings
from src.database.models import Base
from pathlib import Path

# Engine (Motor) oluşturulur. SQLite için echo false yapılıyor
engine = create_async_engine(settings.database_url, echo=False)

# Güvenli bağlantılar açıp/kapatmak için oturum fabrikası (Sessionmaker)
AsyncSessionLocal = async_sessionmaker(
    bind=engine, 
    expire_on_commit=False, 
    class_=AsyncSession
)

async def init_db():
    """
    Sistemin başlangıcında tanımlı Modellerin tablolarını veritabanında oluşturur.
    'CREATE TABLE IF NOT EXISTS' mantığıyla çalıştığı için data kaybına yol açmaz.
    """
    # SQLite kullanıyorsak dizini garanti altına alalım
    if settings.database_url.startswith("sqlite"):
        db_path = settings.database_url.replace("sqlite+aiosqlite:///", "")
        db_dir = Path(db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("\n[VERİTABANI] Asenkron ORM bağlantısı sağlandı ve tablolar doğrulandı.")

async def get_db_session():
    """
    FastAPI veya benzeri arayüzlerde Dependency Injection ile DB bağlantısını açıp kapatmak için jeneratör.
    """
    async with AsyncSessionLocal() as session:
        yield session
