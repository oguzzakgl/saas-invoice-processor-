from pydantic import BaseModel, Field
from typing import List, Optional

class InvoiceModel(BaseModel):
    """
    Fatura türündeki belgeler için özel veri çıkarım şeması.
    """
    fatura_no: Optional[str] = Field(None, description="Faturanın numarası (Örn: INV-2023-01)")
    tarih: Optional[str] = Field(None, description="Faturanın kesildiği tarih")
    ara_toplam: Optional[float] = Field(None, description="Vergiler HARİÇ (KDV Hariç) fatura tutarı")
    kdv_tutari: Optional[float] = Field(None, description="Faturadaki sadece KDV veya Vergi olan tutar")
    toplam_tutar: Optional[float] = Field(None, description="Vergiler dahil faturadaki toplam ödenecek tutar")
    para_birimi: Optional[str] = Field(None, description="Tutarın para birimi (TRY, USD, EUR vb.)")
    satici_unvan: Optional[str] = Field(None, description="Faturayı kesen kurumun/kişinin adı")
    alici_unvan: Optional[str] = Field(None, description="Faturanın kesildiği kurumun/kişinin adı")
    kalemler: List[str] = Field(default_factory=list, description="Fatura içerisindeki alınan hizmet/ürün kalemleri")
    confidence_score: Optional[float] = Field(None, description="Tüm bu fatura verilerinin doğruluğuna dair AI güven skoru (0.00 ile 1.00 arası)")

class ContractModel(BaseModel):
    """
    Sözleşme türündeki belgeler için özel veri çıkarım şeması.
    """
    sozlesme_tarihi: Optional[str] = Field(None, description="Sözleşmenin imzalandığı veya geçerli olduğu tarih")
    taraflar: List[str] = Field(default_factory=list, description="Sözleşmeye dahil olan şirketlerin veya kişilerin isimleri")
    sozlesme_konusu: Optional[str] = Field(None, description="Sözleşmenin ana teması (Örn: Gizlilik, Hizmet Alımı, Satış)")
    gecerlilik_suresi: Optional[str] = Field(None, description="Sözleşmenin ne kadar süreyle geçerli olacağı")
    fesih_sartlari_var_mi: bool = Field(False, description="Sözleşmede bir fesih/iptal maddesi bulunup bulunmadığı")
    confidence_score: Optional[float] = Field(None, description="Bu sözleşme verilerinin doğruluğuna dair AI güven skoru (0.00 ile 1.00 arası)")

class ExtractedData(BaseModel):
    """
    LLM'den dönecek zorunlu JSON şemasını temsil eder.
    Ayrıca belge tipine göre ilgili alt modelleri barındıran Esnek/Kapsayıcı yapıdadır.
    """
    document_summary: str = Field(..., description="Belgenin net ve açıklayıcı özeti")
    keywords: List[str] = Field(default_factory=list, description="Belgede geçen ve bağlamı nitelendiren en kritik anahtar kelimeler")
    document_type: str = Field(..., description="Belgenin türü (örn. Fatura, Sözleşme, Makale, Rapor vb.)")
    
    # Özelleştirilmiş Yapılar: LLM belgenin türünü anladığında uygun olanı doldurur.
    fatura_detaylari: Optional[InvoiceModel] = Field(None, description="Eğer belge kesinlikle bir FATURA ise detayları buraya doldurulur.")
    sozlesme_detaylari: Optional[ContractModel] = Field(None, description="Eğer belge kesinlikle bir SÖZLEŞME ise detayları buraya doldurulur.")

    # Programatik Flag'ler (AI doldurmaz, Python kod ortamında Engine veya Export içerisinde enjekte edilir)
    source_file_path: Optional[str] = Field(None, description="Arkaplan: Belgenin ait olduğu orijinal dosya yolu")
    low_confidence: Optional[bool] = Field(False, description="Arkaplan: Eğer güven skoru 0.70 altındaysa kilitlenir")
    math_error: Optional[bool] = Field(False, description="Arkaplan: Faturadaki Ara Toplam + KDV = Toplam uyuşmuyorsa kilitlenir")
    is_duplicate: Optional[bool] = Field(False, description="Arkaplan: Sistemde aynı Fatura No + Satıcı + Tutar varsa kilitlenir")
