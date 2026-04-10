import streamlit as st
import asyncio
import pandas as pd
from sqlalchemy import select

from src.database.session import AsyncSessionLocal, init_db
from src.database.models import InvoiceRecord, ContractRecord

st.set_page_config(
    page_title="IDP SaaS Dashboard", 
    layout="wide", 
    page_icon="🤖"
)

async def fetch_data():
    """
    Asenkron SQLite/PostgreSQL modülünden onaylanmış evrakları güvende çeker.
    """
    await init_db()  # Veritabanı yoksa oluştur
    async with AsyncSessionLocal() as session:
        # Faturalar
        stmt_inv = select(InvoiceRecord).limit(100)
        result_inv = await session.execute(stmt_inv)
        invoices = result_inv.scalars().all()
        
        # Sözleşmeler
        stmt_ctr = select(ContractRecord).limit(100)
        result_ctr = await session.execute(stmt_ctr)
        contracts = result_ctr.scalars().all()
        
        return invoices, contracts

# Streamlit sayfayı senkron ilerlettiği için asenkron fonksiyonu TTL (Önbellek) ile yakalıyoruz
@st.cache_data(ttl=5) # 5 Saniyede bir kendini tazeler
def load_db_data():
    return asyncio.run(fetch_data())

def main():
    st.title("SaaS Akıllı Belge Karar Destek Sistemi (IDP)")
    st.markdown("Yapay zekanın doğruladığı sisteme düşen Mükerrer Kontrollü şirket evraklarınız tek merkezde.")
    
    # 1. DOSYA YÜKLEME ALANI
    st.sidebar.header("📁 Buluta Belge Yükle")
    uploaded_files = st.sidebar.file_uploader(
        "Faturalarınızı Buraya Sürükleyin (PNG, JPG, PDF, TXT)", 
        accept_multiple_files=True
    )
    
    if uploaded_files:
        st.sidebar.success(f"✓ {len(uploaded_files)} Adet Belge Hedefe Alındı.")
        
        if st.sidebar.button("🚀 Karar Motorunu Tetikle", type="primary", width="stretch"):
            # 1. Bellekteki (Webstream) dosyaları fiziksel Input dizinine yazdır
            from src.config import settings
            input_dir = settings.get_input_path()
            input_dir.mkdir(parents=True, exist_ok=True)
            
            saved_paths = []
            for u_file in uploaded_files:
                file_path = input_dir / u_file.name
                with open(file_path, "wb") as f:
                    f.write(u_file.getbuffer())
                saved_paths.append(file_path)
            
            # 2. Görsel Progress Bar Entegrasyonu
            progress_bar = st.sidebar.progress(0, text="Motor Uyandırılıyor (Semaphore Aktif)...")
            
            # Asenkron dünyadan gelen callback ile senkron state takibi:
            class ProgressState:
                completed = 0
                total = len(saved_paths)
                
            def on_file_processed():
                ProgressState.completed += 1
                progress_bar.progress(ProgressState.completed / ProgressState.total, text=f"{ProgressState.completed} / {ProgressState.total} Belge AI'dan Geçirildi.")
            
            # 3. İzole Çekirdek (Engine) Motorunu Ateşle
            from engine import Engine
            bot = Engine()
            
            with st.spinner("Yapay Zeka Devrede: Analiz yapılıyor (Yaklaşık Tane Başına 3-5 saniye sürebilir)..."):
                # Senkron Streamlit evreninde Asenkron Motoru koşutuyoruz:
                asyncio.run(bot.process_files(saved_paths, progress_callback=on_file_processed))
                
            st.sidebar.success("🎉 Tüm Belgeler Başarıyla Veritabanına Kodlandı!")
            
            # Sistemi tazeleyip tabloları anlık göstermek için Hard Rerun
            st.rerun()
    
    # 2. VERİTABANI GÖSTERGE PANELİ (TABLOLAR)
    st.subheader("📊 Merkezi Raporlama & İzleme")
    
    # EXCEL İNDİRME BUTONU (SİDEBAR)
    from src.config import settings
    report_path = settings.get_output_path() / "otonom_sistem_sonuclari.xlsx"
    if report_path.exists():
        st.sidebar.markdown("---")
        st.sidebar.header("📊 Raporları İndir")
        with open(report_path, "rb") as f:
            st.sidebar.download_button(
                label="📥 Tam Senkron Excel'i İndir",
                data=f.read(),
                file_name="Tam_Senkronize_DB_Raporu.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
    
    try:
        invoices, contracts = load_db_data()
    except Exception as e:
        st.error(f"Veritabanına bağlanılamadı. Muhtemelen henüz 'py main.py' çalışıp DB'yi kurmadı: {e}")
        return

    # Fatura ve Sözleşmeleri iki sekme (TABS) halinde düzenleme
    tab1, tab2 = st.tabs(["Fatura Havuzu", "Sözleşme Havuzu"])
    
    with tab1:
        if invoices:
            # SQL objelerini temiz görünümlü Pandas formatına dökelim
            inv_data = [{
                "Sistem ID": i.id,
                "Durum": "🚨 KDV İhtilaflı" if i.math_error else ("⚠️ Riskli Skoru" if i.low_confidence else "✅ Kusursuz"),
                "Müşteri Kimliği": i.tenant_id,
                "Fatura No": i.fatura_no,
                "Kesim Tarihi": i.tarih,
                "Satıcı Unvanı": i.satici_unvan,
                "Ara Toplam": i.ara_toplam,
                "KDV Tutarı": i.kdv_tutari,
                "Toplam Ödenecek": f"{i.toplam_tutar} {i.para_birimi}",
                "Yapay Zeka Güveni": f"%{int((i.confidence_score or 0)*100)}"
            } for i in invoices]
            
            st.dataframe(pd.DataFrame(inv_data), use_container_width=True)
        else:
            st.info("Henüz veritabanında onaylanmış bir Fatura kaydı bulunmuyor.")
            
    with tab2:
        if contracts:
            ctr_data = [{
                "Sistem ID": c.id,
                "Durum": "⚠️ Riskli Skor" if c.low_confidence else "✅ Kusursuz",
                "Müşteri Kimliği": c.tenant_id,
                "Sözleşme Türü": c.sozlesme_konusu,
                "Tarih": c.sozlesme_tarihi,
                "Geçerlilik Uzunluğu": c.gecerlilik_suresi,
                "Fesih Hakkı": "Var" if c.fesih_sartlari_var_mi else "Yok",
                "Yapay Zeka Güveni": f"%{int((c.confidence_score or 0)*100)}"
            } for c in contracts]
            
            st.dataframe(pd.DataFrame(ctr_data), use_container_width=True)
        else:
            st.info("Henüz veritabanında onaylanmış bir Sözleşme kaydı bulunmuyor.")

if __name__ == "__main__":
    main()
