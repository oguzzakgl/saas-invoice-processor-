# 🤖 SaaS Akıllı Belge Karar Destek Sistemi (IDP)

> Yapay zekanın doğruladığı, mükerrer kontrollü şirket evraklarınızı tek merkezde yöneten otonom belge işleme platformu.

---

## 📌 Özellikler

- 📄 **PDF, PNG, JPG, TXT** formatlarındaki fatura ve sözleşmeleri otomatik okur
- 🧠 **Google Gemini AI** ile belgeleri analiz eder ve yapılandırılmış veriye dönüştürür
- 🔁 **Mükerrer belge kontrolü** — aynı fatura iki kez kaydedilmez (SHA-256 hash ile)
- ✅ **KDV matematik doğrulaması** — Ara Toplam + KDV = Toplam doğruluğu otomatik kontrol edilir
- 🗄️ **SQLite veritabanı** (PostgreSQL'e geçiş desteği)
- 📊 **Senkronize Excel raporu** — Arayüzdeki verilerle birebir eşleşen kurumsal rapor
- 🌐 **Streamlit web arayüzü** — Canlı tablo görünümü, dosya yükleme ve raporları indirme

---

## 🚀 Kurulum

### 1. Projeyi Klonlayın
```bash
git clone https://github.com/KULLANICI_ADINIZ/REPO_ADINIZ.git
cd REPO_ADINIZ
```

### 2. Bağımlılıkları Yükleyin
```bash
pip install -r requirements.txt
```

### 3. API Key Ayarını Yapın

> [!IMPORTANT]
> Google Gemini API key'inizi [Google AI Studio](https://aistudio.google.com/apikey) adresinden ücretsiz alabilirsiniz.

`.env.example` dosyasını kopyalayıp `.env` adıyla kaydedin:
```bash
copy .env.example .env
```

Ardından `.env` dosyasını açıp kendi API key'inizi girin:
```
GEMINI_API_KEY=BURAYA_KENDI_API_KEYINIZI_GIRIN
```

### 4. Sistemi Başlatın
```bash
streamlit run app.py
```

Tarayıcınızda `http://localhost:8501` adresine gidin.

---

## 📁 Proje Yapısı

```
otomasyon/
├── app.py                  # Streamlit web arayüzü
├── engine.py               # Otonom işlem motoru
├── main.py                 # CLI başlatıcı (opsiyonel)
├── requirements.txt        # Python bağımlılıkları
├── .env.example            # Örnek ortam değişkenleri (API key girilmemiş)
├── data/
│   ├── input/              # Yüklenecek belgeler buraya düşer
│   └── output/             # Oluşturulan Excel raporları burada saklanır
└── src/
    ├── config.py           # Merkezi ayar yönetimi
    ├── intelligence.py     # Gemini AI entegrasyonu
    ├── export.py           # Excel rapor oluşturucu
    ├── schemas.py          # Pydantic veri modelleri
    └── database/
        ├── models.py       # SQLAlchemy ORM modelleri
        └── session.py      # Veritabanı bağlantı yöneticisi
```

---

## 🔑 Kullanım

1. Sol menüden **"Buluta Belge Yükle"** bölümüne fatura veya sözleşme dosyalarınızı yükleyin
2. **"🚀 Karar Motorunu Tetikle"** butonuna tıklayın
3. Yapay zeka tüm belgeleri sırayla analiz eder ve veritabanına yazar
4. **Fatura Havuzu** ve **Sözleşme Havuzu** sekmelerinde sonuçları görüntüleyin
5. **"📥 Tam Senkron Excel'i İndir"** butonu ile kurumsal raporunuzu indirin

---

## ⚙️ Yapılandırma (.env)

| Değişken | Açıklama | Varsayılan |
|---|---|---|
| `GEMINI_API_KEY` | **Zorunlu.** Google AI Studio API anahtarınız | — |
| `MODEL_NAME` | Kullanılacak Gemini modeli | `gemini-2.5-flash` |
| `INPUT_DIR` | Giriş dosya dizini | `data/input` |
| `OUTPUT_DIR` | Çıkış rapor dizini | `data/output` |
| `DATABASE_URL` | Veritabanı bağlantı URL'si | `sqlite+aiosqlite:///data/saas_db.sqlite` |

---

## 📦 Gereksinimler

- Python 3.10+
- Google AI Studio hesabı (ücretsiz API key)

Tüm Python bağımlılıkları `requirements.txt` içerisindedir:
```bash
pip install -r requirements.txt
```

---

## ⚠️ API Kota Bilgisi

Google Gemini ücretsiz katmanında şu limitleri uygular:
- **5 istek/dakika** (RPM)
- **gemini-2.5-flash için 20 istek/gün**

Üretim ortamı için Google Cloud üzerinde **Pay-as-you-go** planı aktif edilmesi önerilir.

---

## 📄 Lisans

MIT License — dilediğiniz gibi kullanabilir, değiştirebilir ve dağıtabilirsiniz.
