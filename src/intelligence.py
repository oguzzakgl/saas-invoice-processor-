from tenacity import retry, wait_exponential, stop_after_attempt
from google import genai
from google.genai import types
import json
import asyncio
from src.config import settings
from src.schemas import ExtractedData

# Asenkron Google GenAI istemcisi oluşturulur.
client = genai.Client(api_key=settings.gemini_api_key)

# API yoğunluğu veya 429 KOTA AŞIMI için "Otomatik Tekrar (Retry)" mekanizması.
# Eğer API limitlere takılırsa, kod çökmek yerine gitgide artan sürelerle (5sn, 10sn, 30sn, 60sn) bekleyip 5 kez dener.
@retry(wait=wait_exponential(multiplier=2, min=5, max=65), stop=stop_after_attempt(5), reraise=True)
def _sync_api_call_with_retry(contents):
    return client.models.generate_content(
        model=settings.model_name,
        contents=contents,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ExtractedData,
            temperature=0.1,
        )
    )

async def perform_analysis(text: str) -> ExtractedData | None:
    """
    LLM API'sine bağlanarak temizlenmiş metni veya görseli analiz eder ve JSON (Pydantic formatında) geri döner.
    Asenkron olarak çalışır ve verimliliği artırır.
    """
    try:
        is_image = text.startswith("[IMAGE]:")
        prompt = (
            "Sen yapılandırılmış veri çıkaran, uzman ve otonom bir AI asistanısın. Çıktın daima şemaya tam uyumlu bir JSON olmalıdır.\n"
            "ÖNEMLİ KURAL: Lütfen bulduğun verilere ne kadar güvendiğini (0.00 ile 1.00 arasında) 'confidence_score' alanına yaz! "
            "Eğer metin okunaksız veya çelişkili ise düşük bir skor (örn 0.40) ver. Eğer her şey netse yüksek skor (örn 0.95) ver."
        )
        
        if is_image:
             image_path = text.split(":", 1)[1]
             prompt += "\n\nLütfen sana verdiğim fatura/sözleşme görselini derinlemesine oku ve analiz et."
        else:
             prompt += f"\n\nAşağıdaki metni analiz et:\n{text}"

        print(f"[BİLGİ] AI Sunucusuna bağlantı kuruluyor... (Yoğunluk varsa otomatik beklenecek)")
        
        def _sync_api_call_wrapper():
             # İçeriği dinamik oluşturuyoruz
             contents_payload = [prompt]
             
             if is_image:
                  import mimetypes
                  mime_type, _ = mimetypes.guess_type(image_path)
                  # Resmi baytlara çevirip Gemini'nin anlayacağı formata (Part) sokuyoruz.
                  with open(image_path, "rb") as f:
                       contents_payload.append(types.Part.from_bytes(data=f.read(), mime_type=mime_type or "image/png"))
             
             return _sync_api_call_with_retry(contents_payload)

        # Threading ile senkron/retry çağrısını asenkrona (non-blocking) dönüştürüyoruz.
        response = await asyncio.to_thread(_sync_api_call_wrapper)
        
        # Dönen formatlanmış JSON metnini python sözlüğüne dönüştürüp Pydantic ile doğrulamasını yapıyoruz (Validasyon).
        raw_json = response.text
        if not raw_json:
            return None
            
        data_dict = json.loads(raw_json)
        return ExtractedData(**data_dict)
    
    except Exception as e:
        # Zırhlı kod kuralı gereğince hata metinleri açık Türkçe yazıldı ve çökme engellendi.
        print(f"[HATA] LLM (Intelligence) analiz sürecinde veya JSON çözümlemesinde arıza oluştu -> {e}")
        return None
