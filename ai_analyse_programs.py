import requests
import json
import time

# AnythingLLM API ayarları
API_KEY = "R212Y2R-Z494M7R-J8Q01DP-JY4DV4N"
BASE_URL = "http://localhost:3001/api/v1"

headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}


def extract_text(text: str) -> str:
    """
    <document_metadata>...</document_metadata> bloklarını atıp
    kalan metni temizler ve satır sonlarını düzleştirir.
    """
    if not text:
        return ""
    # metadata kısmını sil
    cleaned = re.sub(r"<document_metadata>.*?</document_metadata>", "", text, flags=re.DOTALL)
    # tüm \n ve fazla boşlukları temizle
    cleaned = re.sub(r"\s*\n\s*", " ", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)  # art arda boşlukları tek boşluk yap
    return cleaned.strip()


def clean_response(raw, import_sources=False):
    result = {"response": raw.get("textResponse"), "metrics": raw.get("metrics"), "reasoning": raw.get("reasoning")}
    if import_sources:
        result["sources"] = [
            {
                "title": s.get("title"),
                "description": s.get("description"),
                "published": s.get("published"),
                "wordCount": s.get("wordCount"),
                "token_count_estimate": s.get("token_count_estimate"),
                "text": extract_text(s.get("text")),
            }
            for s in raw.get("sources", [])
        ]
    return result


def send_program_to_anythingllm(program_name, applicant_requirements, program_index):
    """
    Tek bir programı AnythingLLM'e gönderir
    """
    # Program bilgilerini içeren mesaj oluştur
    message = f"""
        Program Adı: {program_name}

        Başvuru Koşulları: {applicant_requirements}

        Bu program büyük ölçekli kurumsal bir Ar-Ge Merkezi için uygun mu?
        """

    data = {"message": message, "reset": False, "mode": "chat"}

    try:
        print(f"[{program_index}] Gönderiliyor: {program_name}")

        print(f"[{program_index}] Gönderilen mesaj: {message}")
        response = requests.post(f"{BASE_URL}/workspace/deneme/chat", headers=headers, json=data)

        if response.status_code == 200:
            raw = response.json()
            cleaned = clean_response(raw, import_sources=True)

            print(f"[{program_index}] Başarılı: {program_name}")
            print(f"Yanıt: {cleaned['response']}")
            print("-" * 80)

            return cleaned
        else:
            print(f"[{program_index}] Hata: {program_name} - Status Code: {response.status_code}")
            print(f"Hata mesajı: {response.text}")
            return None

    except Exception as e:
        print(f"[{program_index}] Exception: {program_name} - {str(e)}")
        return None


def main():
    # JSON dosyasını oku
    try:
        with open("tubitak_rag_data.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print("tubitak_rag_data.json dosyası bulunamadı!")
        return
    except json.JSONDecodeError:
        print("JSON dosyası geçersiz format!")
        return

    programs = data.get("programs", [])
    print(f"Toplam {len(programs)} program bulundu.")
    print("=" * 80)

    # Sonuçları saklamak için liste
    results = []

    # Tüm programları sırayla gönder
    for index, program in enumerate(programs, 1):
        program_name = program.get("program_name", "Bilinmeyen Program")
        applicant_requirements = program.get("applicant_requirements", "Veri bulunamadı")
        status = program.get("status", "unknown")

        # Sadece başarılı olan programları gönder
        if status == "success" and applicant_requirements != "Veri bulunamadı":
            result = send_program_to_anythingllm(program_name, applicant_requirements, index)

            # Sonucu kaydet
            if result:
                # \n karakterlerini gerçek satır sonlarına çevir
                analysis_text = result.get("response", "").replace("\\n", "\n")

                results.append(
                    {
                        "program_name": program_name,
                        "applicant_requirements": applicant_requirements,
                        "analysis": analysis_text,
                    }
                )
            else:
                results.append({"program_name": program_name, "applicant_requirements": applicant_requirements, "analysis": "Hata: Analiz yapılamadı"})

            # API'ye çok hızlı istek atmamak için kısa bir bekleme
            time.sleep(1)
        else:
            print(f"[{index}] Atlanıyor: {program_name} - Status: {status}")
            print("-" * 80)

    # Sonuçları JSON dosyasına kaydet
    with open("ai_analyse_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("Tüm programlar işlendi!")
    print(f"Sonuçlar 'ai_analyse_results.json' dosyasına kaydedildi.")


if __name__ == "__main__":
    import re  # extract_text fonksiyonu için gerekli

    main()
