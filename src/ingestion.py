import asyncio
from pathlib import Path
from src.config import settings

async def get_files_to_process() -> list[Path]:
    """
    Giriş klasörünü okur ve desteklenen (Örn: .pdf, .txt) dosyaları bir Path listesi olarak döndürür.
    
    Parametreler:
        Yok (.env içerisindeki giriş dizini okunur)
        
    Döndürdüğü Değer:
        list[Path]: İşlenecek dosya yollarının (Path objelerinin) listesi
    """
    try:
        input_directory = settings.get_input_path()
        # Sistemde 'data/input' klasörü yoksa anında hata vermek yerine o klasörü oluşturur, kullanıcı deneyimini artırır.
        input_directory.mkdir(parents=True, exist_ok=True)
        
        # Gelecekte asenkron I/O beklemeleri eklenirse (örneğin FTP'den indirmek gibi), altyapıyı non-blocking bırakmak için.
        await asyncio.sleep(0) 
        
        # Sadece izin verilen güvenli uzantılar seçilir (Artık görseller de dahil)
        allowed_extensions = {".pdf", ".txt", ".png", ".jpg", ".jpeg"}
        files = [f for f in input_directory.iterdir() if f.is_file() and f.suffix.lower() in allowed_extensions]
        
        return files
    except Exception as e:
        print(f"[HATA] Dosya giriş katmanında (Ingestion) dizin okunurken kritik bir hata meydana geldi -> {e}")
        return []
