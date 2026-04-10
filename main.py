import asyncio
import sys
from engine import Engine

# Windows'da asyncio'nun 'Could not contact DNS servers' veya SSL hataları vermesini
# önlemek için klasik Selector tipine (WindowsSelectorEventLoopPolicy) geçiriyoruz.
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

def main():
    """
    Sistemin dışarıdan tetiklendiği ilk çalıştırılabilir script.
    """
    app_engine = Engine()
    
    try:
        # Eski event loop yapısı yerine Python 3.7+ güvenli asenkron koşturucusu (asyncio.run) kullanılarak Engine tetiklenir.
        asyncio.run(app_engine.run())
    except KeyboardInterrupt:
        # Kullanıcı 'Ctrl+C' yaparak sistemi durdurduğunda ortaya çıkan kaba hatayı gizleyip insancıl bir metin yazarız (Hata Yönetimi prensibi)
        print("\n[BİLGİ] İşlem kullanıcı tarafından elle (manuel) durduruldu.")
    except Exception as e:
        print(f"\n[KRİTİK HATA] Ana akış rutini (main.py) çalıştırılamadı -> {e}")

if __name__ == "__main__":
    main()
