import asyncio
import hashlib
from pathlib import Path
import time

from src.ingestion import get_files_to_process
from src.preprocessing import process_file_content
from src.intelligence import perform_analysis
from src.export import export_data, export_db_report
from sqlalchemy import select

from src.database.session import init_db, AsyncSessionLocal
from src.database.models import InvoiceRecord, ContractRecord

class Engine:
    """
    Sistemin uçtan uca asenkron (paralel) çalışmasını sağlayan birleştirici çekirdek (Core Engine).
    Tüm modüller bu sınıf içerisinde bir araya getirilerek izole (oop) bir yapı sunulur.
    """
    def __init__(self):
        # API 503/429 hatalarına karşı asenkron işlemciyi 1 eşzamanlı işlemle sınırlar (sıralı mod).
        self.semaphore = asyncio.Semaphore(1)
        # Sistem hafızasında (runtime memory) faturaların tekrar edip etmediğini kontrol edecek izleyici.
        self.seen_invoices = set()

    async def _process_single_file(self, file_path: Path, progress_callback=None):
        """
        Gelen her bir dosya için Okuma, Temizleme, Doğrulama ve LLM Analizi akışını yönetir.
        """
        print(f"[İŞLEM BAŞLIYOR] -> {file_path.name}")
        
        # 1. Okuma & Temizleme
        cleaned_text = process_file_content(str(file_path))
        
        if not cleaned_text:
            print(f"[ATLANDI] {file_path.name} belgesinden metin alınamadı veya belge boş.")
            return None
            
        # 2. LLM Analizi (Semaphore ile sıralı güvenli blok)
        async with self.semaphore:
            ai_result = await perform_analysis(cleaned_text)
            # Her istek sonrası API'ye nefes aldır (503/429 önleyici)
            await asyncio.sleep(3)
        
        if ai_result:
            print(f"[BAŞARILI] {file_path.name} LLM tarafından ayrıştırıldı. İç denetimler başlatılıyor...")
            
            # Kaynak dosya izine sahip çık
            ai_result.source_file_path = str(file_path.absolute())
            
            # 3. Zırhlı Kontroller Katmanı (LLM sonrası Validasyon İşlemleri)
            if ai_result.fatura_detaylari:
                inv = ai_result.fatura_detaylari
                
                # A: Güven Skoru Denetimi
                if inv.confidence_score is not None and inv.confidence_score < 0.70:
                    ai_result.low_confidence = True
                    
                # B: Matematiksel Sağlama (Ara Toplam + KDV = Toplam Tutar)
                if inv.ara_toplam is not None and inv.kdv_tutari is not None and inv.toplam_tutar is not None:
                    # Küsürat yuvarlamalarından oluşabilecek ufak float hataları tolere edilir (>0.1)
                    if abs((inv.ara_toplam + inv.kdv_tutari) - inv.toplam_tutar) > 0.1:
                        ai_result.math_error = True
                        
                # C: Mükerrer (Duplicate) Kayıt Kontrolü
                if inv.fatura_no and inv.satici_unvan and inv.toplam_tutar is not None:
                    unique_code = f"{inv.fatura_no}_{inv.satici_unvan}_{inv.toplam_tutar}"
                    if unique_code in self.seen_invoices:
                        ai_result.is_duplicate = True
                        print(f"[UYARI] {file_path.name} MÜKERRER KAYIT OLARAK TESPİT EDİLDİ!")
                    else:
                        self.seen_invoices.add(unique_code)

            elif ai_result.sozlesme_detaylari:
                ctr = ai_result.sozlesme_detaylari
                if ctr.confidence_score is not None and ctr.confidence_score < 0.70:
                    ai_result.low_confidence = True
                    
        else:
            print(f"[HATA] {file_path.name} metninin AI tarafında yapılandırılmış JSON'a dökülmesi başarısız oldu.")
            
        # UI tetikleyicisini çalıştır
        if progress_callback:
            progress_callback()
            
        return ai_result

    async def save_to_db(self, valid_results):
        """
        İşlenen ve doğrulanan verileri asenkron olarak SQLite / PostgreSQL veritabanına kaydeder.
        """
        print("\n[BİLGİ] Veritabanına asenkron kayıt / validasyon işlemi başlatılıyor...")
        DEFAULT_TENANT = "local_tenant_01"  # SaaS Multi-Tenancy için izole müşteri kimliği
        
        async with AsyncSessionLocal() as session:
            for item in valid_results:
                # Benzersiz Hash (Duplicate check veritabanı yansıması)
                try:
                    with open(item.source_file_path, "rb") as f:
                        file_hash = hashlib.sha256(f.read()).hexdigest()
                except:
                    # Dosya yoksa veya okunamadıysa geçici hash uydur
                    file_hash = str(time.time())
                
                # Sadece Mükerrer Olmayanları veya Yeni Olanları Ekle!
                if getattr(item, 'is_duplicate', False):
                    continue

                record = None
                if item.fatura_detaylari:
                    inv = item.fatura_detaylari
                    record = InvoiceRecord(
                        tenant_id=DEFAULT_TENANT,
                        file_hash=file_hash,
                        fatura_no=inv.fatura_no,
                        tarih=inv.tarih,
                        satici_unvan=inv.satici_unvan,
                        alici_unvan=inv.alici_unvan,
                        ara_toplam=inv.ara_toplam,
                        kdv_tutari=inv.kdv_tutari,
                        toplam_tutar=inv.toplam_tutar,
                        para_birimi=inv.para_birimi,
                        kalemler=", ".join(inv.kalemler) if getattr(inv, 'kalemler', None) else None,
                        confidence_score=inv.confidence_score,
                        math_error=getattr(item, 'math_error', False),
                        low_confidence=getattr(item, 'low_confidence', False),
                        source_file=item.source_file_path
                    )
                    session.add(record)
                    
                elif item.sozlesme_detaylari:
                    ctr = item.sozlesme_detaylari
                    record = ContractRecord(
                        tenant_id=DEFAULT_TENANT,
                        file_hash=file_hash,
                        sozlesme_konusu=ctr.sozlesme_konusu,
                        sozlesme_tarihi=ctr.sozlesme_tarihi,
                        taraflar=", ".join(ctr.taraflar) if getattr(ctr, 'taraflar', None) else None,
                        gecerlilik_suresi=ctr.gecerlilik_suresi,
                        fesih_sartlari_var_mi=ctr.fesih_sartlari_var_mi,
                        confidence_score=ctr.confidence_score,
                        low_confidence=getattr(item, 'low_confidence', False),
                        source_file=item.source_file_path
                    )
                    session.add(record)
                
                if record:
                    try:
                        await session.commit()
                        print(f"[VERİTABANI] {Path(item.source_file_path).name} başarıyla SaaS veritabanına yazıldı.")
                    except Exception as e:
                        await session.rollback()
                        print(f"[UYARI] {Path(item.source_file_path).name} veritabanına eklenemedi (Dosya zaten var veya hash çakışması).")


    async def process_files(self, file_paths: list[Path], progress_callback=None):
        """
        Web (Streamlit) arayüzünden yüklenen listeyi asenkron olarak kabul edip çalıştıran yeni modüler tetikleyici.
        Mevcut Semaphore(2) zırhı geçerlidir. API yasaklarından korunur.
        """
        if not file_paths:
            return []
            
        print(f"\n[BİLGİ] Toplam {len(file_paths)} belge analiz hattına alındı.")
        
        # Görevleri listeleyip (İsteğe bağlı progress trigger atayarak) tetikleyelim
        tasks = [self._process_single_file(f, progress_callback) for f in file_paths]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        valid_results = [res for res in results if res is not None and not isinstance(res, Exception)]
        
        if valid_results:
            # Veritabanına Yazma
            await self.save_to_db(valid_results)
            
            # Veritabanından okuyarak Tam Senkron Excel Raporunu oluştur
            print("\n[BİLGİ] İşlemler tamamlandı, Tüm Veritabanı okunarak Tam Senkron Excel Raporu oluşturuluyor...")
            async with AsyncSessionLocal() as session:
                stmt_inv = select(InvoiceRecord)
                res_inv = await session.execute(stmt_inv)
                all_invoices = res_inv.scalars().all()
                
                stmt_ctr = select(ContractRecord)
                res_ctr = await session.execute(stmt_ctr)
                all_contracts = res_ctr.scalars().all()
                
                export_db_report(all_invoices, all_contracts, output_filename="otonom_sistem_sonuclari.xlsx")
        else:
            print("\n[BİLGİ] Kaydedilebilir herhangi bir sonuç üretilemedi.")
            
        return valid_results


    async def run(self):
        """
        Geleneksel terminal/komut İstemi üzerinden çalıştırıldığında tetiklenen otonom sistem başlangıcı.
        """
        start_time = time.time()
        print("\n=======================================================")
        print(" OTONOM VERİ İŞLEME SİSTEMİ MOTORU BAŞLATILIYOR... ")
        print("=======================================================\n")
        
        # [SaaS ALTYAPISI OLUŞTURUCU]
        print("[MİMARİ] Asenkron Veritabanı motoru uyandırılıyor...")
        await init_db()
        
        files = await get_files_to_process()
        if not files:
            print("[BİLGİ] Girdi dizininde uygun formatta belge bulunamadı.")
            return
            
        print("[MİMARİ BİLGİ] Sistem Semaphore(1) bariyeri ile güçlendirilmiştir (Belgeler sırayla, birer birer işlenir).\n")
        
        # Ana işlemi merkezi fonksiyona pasla ve sonuçları döndür
        results = await self.process_files(files)
        
        elapsed = time.time() - start_time
        print(f"\n[SİSTEM KAPANDI] İşlem başarıyla tamamlandı. Toplam Süre: {elapsed:.2f} saniye")
        return results
