"""
src/mail_bot.py — Asenkron Mail Botu

Gelen kutusundaki (INBOX) okunmamış maillerin eklerini (PDF, PNG, JPG, TXT)
data/input/ dizinine indirir ve Engine motoruna otomatik olarak paslar.

Bağımsız çalışma (Streamlit'ten bağımsız background task):
    python -m src.mail_bot

.env dosyasında aşağıdaki değişkenlerin tanımlı olması gerekir:
    MAIL_IMAP_SERVER   → IMAP sunucusu (varsayılan: imap.gmail.com)
    MAIL_IMAP_PORT     → IMAP portu (varsayılan: 993)
    MAIL_ADDRESS       → E-posta adresi
    MAIL_PASSWORD      → Uygulama şifresi (Gmail için: Hesap → Güvenlik → Uygulama Şifresi)
    MAIL_CHECK_INTERVAL → Kaç saniyede bir kontrol edilsin (varsayılan: 60)
"""

import asyncio
import imaplib
import email
import sys
import re
from pathlib import Path
from email.header import decode_header
from email.message import Message

# Proje kök dizinini Python path'ine ekle (doğrudan modül olarak çalıştırılabilmek için)
sys.path.append(str(Path(__file__).parent.parent))

from src.config import settings
from engine import Engine

# ─── Desteklenen ek uzantıları ────────────────────────────────────────────────
DESTEKLENEN_UZANTILAR = {".pdf", ".png", ".jpg", ".jpeg", ".txt"}


def _dosya_adini_temizle(ham_ad: str) -> str:
    """
    IMAP başlıklarından gelen encoded dosya adlarını çözümler ve
    dosya sisteminde sorun çıkarabilecek özel karakterleri temizler.
    """
    # RFC 2047 encoded-word formatını çöz (örn: =?utf-8?b?...?=)
    parcalar = decode_header(ham_ad)
    ad = ""
    for parca, kodlama in parcalar:
        if isinstance(parca, bytes):
            ad += parca.decode(kodlama or "utf-8", errors="replace")
        else:
            ad += parca
    # Dosya adında yasak karakterleri alt çizgiyle değiştir
    return re.sub(r'[\\/:*?"<>|]', "_", ad).strip()


def _ekleri_indir(mail_mesaji: Message, hedef_dizin: Path) -> list[Path]:
    """
    Tek bir e-posta mesajındaki desteklenen formattaki ekleri indirir.

    Parametreler:
        mail_mesaji (Message): Python email kütüphanesinin ayrıştırdığı mesaj objesi
        hedef_dizin (Path)   : Eklerin kaydedileceği klasör (data/input/)

    Döndürdüğü Değer:
        list[Path]: Başarıyla indirilen dosyaların yol listesi
    """
    indirilenler = []
    
    for parca in mail_mesaji.walk():
        # İçerik tipi multipart ise alt parçalara geç (gerçek içerik değil)
        if parca.get_content_maintype() == "multipart":
            continue
        
        # Disposition başlığı yoksa bu parça bir ek değil, gövde metnidir
        if parca.get("Content-Disposition") is None:
            continue
        
        ham_dosya_adi = parca.get_filename()
        if not ham_dosya_adi:
            continue
        
        dosya_adi = _dosya_adini_temizle(ham_dosya_adi)
        uzanti = Path(dosya_adi).suffix.lower()
        
        # Sadece desteklenen uzantılardaki ekleri işle
        if uzanti not in DESTEKLENEN_UZANTILAR:
            print(f"[MAIL BOT] Atlandı → '{dosya_adi}' (desteklenmeyen uzantı: {uzanti})")
            continue
        
        kayit_yolu = hedef_dizin / dosya_adi
        
        # Aynı adlı dosya varsa üzerine yazma: sonuna sayaç ekle
        sayac = 1
        while kayit_yolu.exists():
            kayit_yolu = hedef_dizin / f"{Path(dosya_adi).stem}_{sayac}{uzanti}"
            sayac += 1
        
        # Dosya içeriğini diske yaz
        with open(kayit_yolu, "wb") as f:
            f.write(parca.get_payload(decode=True))
        
        print(f"[MAIL BOT] ✅ İndirildi → {kayit_yolu.name}")
        indirilenler.append(kayit_yolu)
    
    return indirilenler


def _okunmamis_mailleri_isle(imap_baglantisi: imaplib.IMAP4_SSL, hedef_dizin: Path) -> list[Path]:
    """
    IMAP bağlantısı üzerinden INBOX'taki okunmamış (UNSEEN) mailleri tarar,
    her maildeki desteklenen ekleri indirir ve mail'i okundu olarak işaretler.

    Parametreler:
        imap_baglantisi (IMAP4_SSL): Aktif IMAP SSL bağlantısı
        hedef_dizin     (Path)      : Eklerin indirileceği klasör

    Döndürdüğü Değer:
        list[Path]: Tüm maillerden indirilen dosyaların birleşik listesi
    """
    tum_indirilenler = []
    
    # Gelen kutusu seçimi
    imap_baglantisi.select("INBOX")
    
    # Okunmamış mesajların ID'lerini al
    durum, mesaj_idleri = imap_baglantisi.search(None, "UNSEEN")
    if durum != "OK" or not mesaj_idleri[0]:
        print("[MAIL BOT] Gelen kutusunda yeni (okunmamış) mesaj bulunamadı.")
        return []
    
    id_listesi = mesaj_idleri[0].split()
    print(f"[MAIL BOT] {len(id_listesi)} yeni mesaj tespit edildi.")
    
    for mail_id in id_listesi:
        # Mesajı raw (ham) formatıyla çek
        _, mesaj_verisi = imap_baglantisi.fetch(mail_id, "(RFC822)")
        ham_mesaj = mesaj_verisi[0][1]
        
        # Python'un email kütüphanesiyle ayrıştır
        mesaj = email.message_from_bytes(ham_mesaj)
        
        gonderen = mesaj.get("From", "Bilinmeyen Gönderici")
        konu     = mesaj.get("Subject", "(Konu Yok)")
        print(f"[MAIL BOT] 📧 İşleniyor → Gönderen: {gonderen} | Konu: {konu}")
        
        # Ekleri indir
        indirilenler = _ekleri_indir(mesaj, hedef_dizin)
        tum_indirilenler.extend(indirilenler)
        
        # Maili "Okundu" olarak işaretle (bir dahaki taramada tekrar işlenmemesi için)
        imap_baglantisi.store(mail_id, "+FLAGS", "\\Seen")
    
    return tum_indirilenler


async def _tek_tarama_dongusu() -> list[Path]:
    """
    IMAP'a bağlan → Okunmamış ekleri indir → Bağlantıyı kapat.
    Senkron IMAP işlemlerini asyncio'nun blocking event loop'unu
    kilitlememesi için ayrı bir thread'de koşturur.

    Döndürdüğü Değer:
        list[Path]: Bu taramada indirilen tüm dosyaların listesi
    """
    def _senkron_tarama():
        # Ayarlar .env'den okunur; eksikse erken çık
        if not settings.mail_address or not settings.mail_password:
            print("[MAIL BOT] ❌ MAIL_ADDRESS veya MAIL_PASSWORD .env'de tanımlı değil.")
            return []
        
        hedef_dizin = settings.get_input_path()
        hedef_dizin.mkdir(parents=True, exist_ok=True)
        
        try:
            # SSL üzerinden IMAP sunucusuna bağlan
            print(f"[MAIL BOT] 🔌 {settings.mail_imap_server}:{settings.mail_imap_port} bağlantısı kuruluyor...")
            baglanti = imaplib.IMAP4_SSL(settings.mail_imap_server, settings.mail_imap_port)
            baglanti.login(settings.mail_address, settings.mail_password)
            print("[MAIL BOT] 🔓 IMAP girişi başarılı.")
            
            indirilenler = _okunmamis_mailleri_isle(baglanti, hedef_dizin)
            
            baglanti.logout()
            return indirilenler
        
        except imaplib.IMAP4.error as e:
            # Kimlik doğrulama veya sunucu hatası
            print(f"[MAIL BOT] ❌ IMAP Hatası: {e}")
            return []
        except Exception as e:
            print(f"[MAIL BOT] ❌ Beklenmedik hata: {e}")
            return []
    
    # Senkron IMAP çağrısını ayrı thread'de koştur (Event loop'u bloke etmeden)
    return await asyncio.to_thread(_senkron_tarama)


async def mail_bot_calistir():
    """
    Sürekli çalışan asenkron mail botu döngüsü.
    
    Her MAIL_CHECK_INTERVAL saniyede bir IMAP'ı tarar:
      1. Okunmamış maillerin eklerini data/input/'a indirir
      2. İndirilen dosyaları Engine motoruna paslar (otomatik analiz)
      3. Bir sonraki taramaya kadar bekler
    
    Kullanım:
        python -m src.mail_bot
    """
    print("=" * 55)
    print(" MAIL BOT ARKA PLAN GÖREVİ BAŞLATILDI")
    print(f" Her {settings.mail_check_interval} saniyede bir inbox taranacak.")
    print("=" * 55)
    
    engine = Engine()
    
    while True:
        print(f"\n[MAIL BOT] 🔍 Yeni tarama başlıyor...")
        
        # 1. IMAP'ı tara ve ekleri indir
        indirilen_dosyalar = await _tek_tarama_dongusu()
        
        # 2. İndirilen dosya varsa Engine'e pasla
        if indirilen_dosyalar:
            print(f"[MAIL BOT] 🚀 {len(indirilen_dosyalar)} dosya Engine'e gönderiliyor...")
            await engine.process_files(indirilen_dosyalar)
            print("[MAIL BOT] ✅ Analiz tamamlandı, veritabanı güncellendi.")
        else:
            print("[MAIL BOT] 💤 Yeni ek bulunamadı, beklemeye geçiliyor.")
        
        # 3. Bir sonraki taramaya kadar bekle
        print(f"[MAIL BOT] ⏱️  Sonraki tarama {settings.mail_check_interval} saniye sonra...")
        await asyncio.sleep(settings.mail_check_interval)


# Modül doğrudan çalıştırıldığında (python -m src.mail_bot)
if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    try:
        asyncio.run(mail_bot_calistir())
    except KeyboardInterrupt:
        print("\n[MAIL BOT] 🛑 Bot kullanıcı tarafından durduruldu.")
