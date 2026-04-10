import fitz  # PyMuPDF
import re

def clean_data(raw_text: str) -> str:
    """
    Ham metin içerisindeki gereksiz boşlukları ve karakterleri ayıklayarak Token sayısını optimize eder.
    
    Parametreler:
        raw_text (str): Temizlenecek ham makine metni
    
    Döndürdüğü Değer:
        str: Optimize edilmiş ve temizlenmiş metin
    """
    try:
        # LLM'in hem dikkatini dağıtabilecek hem de gereksiz token faturası çıkaracak
        # olan ardışık boşlukları (tab, newline) tek bir boşluğa indirgiyoruz. Token optimizasyonu sağlar.
        cleaned_text = re.sub(r'\s+', ' ', raw_text)
        
        # Kenarlardaki fazladan boşlukları temizleyip döner
        return cleaned_text.strip()
    except Exception as e:
        # Zırhlı kod kuralı: Hata anında uygulamanın çökmesini engellemek için try-except kullanıyoruz.
        print(f"[HATA] clean_data modülünde temizleme yapılırken bir arıza meydana geldi -> {e}")
        return ""

def extract_text_from_pdf(file_path: str) -> str:
    """
    PDF dokümanından metin okur ve temizlenmiş şekilde döndürür.
    
    Parametreler:
        file_path (str): Okunacak PDF belgesinin dosya yolu
        
    Döndürdüğü Değer:
        str: Belgeden elde edilmiş tüm metin
    """
    try:
        # Büyük belgeleri okurken sayfa sayfa ilerlemek, programın RAM'i (belleği) şişirmesini engeller.
        doc = fitz.open(file_path)
        full_text = ""
        for page in doc:
            full_text += page.get_text("text") + "\n"
        
        # Token kısıtlamalarına uymak için okuma biter bitmez temizliği uygular.
        return clean_data(full_text)
    except Exception as e:
        print(f"[HATA] {file_path} konumundaki PDF dosyasından metin çıkartılamadı -> {e}")
        return ""

def process_file_content(file_path: str) -> str:
    """
    Dosyanın uzantısını algılayıp ilgili metini dışarı çıkarır.
    
    Parametreler:
        file_path (str): Okunacak dosya yolu
        
    Döndürdüğü Değer:
        str: Çıkarılmış ham/temiz metin içeriği
    """
    try:
        if file_path.lower().endswith('.pdf'):
            return extract_text_from_pdf(file_path)
        elif file_path.lower().endswith('.txt'):
            with open(file_path, 'r', encoding='utf-8') as f:
                return clean_data(f.read())
        elif file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
            # Görüntü dosyalarının metnini burada çıkartmak yerine doğrudan Gemini Vision'a vereceğiz!
            # Bu yüzden AI katmanına anlasın diye "[IMAGE]" bayrağı takarak dosya yolunu gönderiyoruz.
            return f"[IMAGE]:{file_path}"
        else:
            # Okunamayan bir dosyaysa sadece okunamadı logu düşer, sistemi dondurmaz.
            print(f"[BİLGİ] Şimdilik bu format desteklenmiyor: {file_path}")
            return ""
    except Exception as e:
        print(f"[HATA] {file_path} dosyası işleme sürecinde çöktü -> {e}")
        return ""
