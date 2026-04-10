from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from pathlib import Path

class Settings(BaseSettings):
    """
    Sistemin tüm ortam değişkenlerini ve sabitlerini yönetir.
    Parametreler:
        Yok (Değerleri arka planda .env 'den doldurur)
    Döndürdüğü Değer:
        Uygulama ayarlarını tutan class objesi
    """
    gemini_api_key: str = ""
    input_dir: str = "data/input"
    output_dir: str = "data/output"
    model_name: str = "gemini-2.5-flash"
    
    # SaaS Veritabanı Yapılandırması (SQLite veya PostgreSQL)
    database_url: str = Field(default="sqlite+aiosqlite:///data/saas_db.sqlite", alias="DATABASE_URL")
    
    # Mail Bot Yapılandırması (IMAP — Gmail, Outlook vb.)
    mail_imap_server: str = Field(default="imap.gmail.com", alias="MAIL_IMAP_SERVER")
    mail_imap_port: int   = Field(default=993, alias="MAIL_IMAP_PORT")
    mail_address: str     = Field(default="", alias="MAIL_ADDRESS")
    mail_password: str    = Field(default="", alias="MAIL_PASSWORD")
    mail_check_interval: int = Field(default=60, alias="MAIL_CHECK_INTERVAL")  # saniye
    
    # '.env' dosyasından gizli keyleri ve yolları yükleyerek
    # 'Global değişken yasağı'nı uyguluyoruz.
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def get_input_path(self) -> Path:
        """
        Giriş dizinini Path objesi olarak getirir.
        Parametreler:
            Yok
        Döndürdüğü Değer:
            Path: Giriş klasör yolu objesi
        """
        # Kullanımlarda işletim sistemi bağımsız dosya yolunu (Pathlib) garanti ediyoruz.
        return Path(self.input_dir)

    def get_output_path(self) -> Path:
        """
        Çıkış dizinini Path objesi olarak getirir.
        Parametreler:
            Yok
        Döndürdüğü Değer:
            Path: Çıkış klasör yolu objesi
        """
        return Path(self.output_dir)

# Singleton pattern benzeri bir yapı için tek bir instance yaratılıp diğer yerlere dağıtılacak.
settings = Settings()
