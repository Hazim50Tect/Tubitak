import requests
import json
import re
import os

# AnythingLLM API ayarları
API_KEY = os.getenv("ANYTHINGLLM_API_KEY", "R212Y2R-Z494M7R-J8Q01DP-JY4DV4N")
BASE_URL = "http://localhost:3001/api/v1"

headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

FINAL_MEAN_FILE = "FINAL_ai_results_mean.json"


def extract_text(text: str) -> str:
    """<document_metadata> bloklarını temizler ve satır sonlarını düzleştirir."""
    if not text:
        return ""
    cleaned = re.sub(r"<document_metadata>.*?</document_metadata>", "", text, flags=re.DOTALL)
    cleaned = re.sub(r"\s*\n\s*", " ", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return cleaned.strip()


def clean_response(raw, import_sources=False):
    """AnythingLLM yanıtını temizler ve sources varsa ekler."""
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


def extract_score_from_response(response_text: str) -> float:
    """AI yanıtından uygunluk skorunu çıkarır."""
    if not response_text:
        return None

    # "Uygunluk Skoru" veya "Skor" kelimelerini ara
    score_patterns = [
        r"Uygunluk Skoru[:\s]*(\d+(?:\.\d+)?)",
        r"Skor[:\s]*(\d+(?:\.\d+)?)",
        r"(\d+(?:\.\d+)?)\s*\/\s*1",  # X/1 formatı
        r"(\d+(?:\.\d+)?)\s*\/\s*10",  # X/10 formatı
        r"(\d+(?:\.\d+)?)\s*\/\s*100",  # X/100 formatı
    ]

    for pattern in score_patterns:
        match = re.search(pattern, response_text, re.IGNORECASE)
        if match:
            score = float(match.group(1))
            # Eğer skor 1'den büyükse, 1'e normalize et
            if score > 1:
                if score <= 10:
                    score = score / 10
                elif score <= 100:
                    score = score / 100
                else:
                    score = 1.0
            return score

    return None


def update_final_mean_file(program_name: str, score: float):
    """FINAL_ai_results_mean.json dosyasını günceller."""
    # Mevcut dosyayı oku
    if os.path.exists(FINAL_MEAN_FILE):
        try:
            with open(FINAL_MEAN_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            data = {}
    else:
        data = {}

    # Program için skor listesini güncelle
    if program_name not in data:
        data[program_name] = {"scores": [], "mean": 0.0}

    # Yeni skoru ekle
    data[program_name]["scores"].append(score)

    # Ortalamayı hesapla
    scores = data[program_name]["scores"]
    mean_score = sum(scores) / len(scores)
    data[program_name]["mean"] = round(mean_score, 3)

    # Dosyayı kaydet
    try:
        with open(FINAL_MEAN_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Ortalama güncellendi: {program_name} - Yeni skor: {score}, Ortalama: {mean_score}")
    except Exception as e:
        print(f"Ortalama dosyası kaydedilemedi: {str(e)}")


def send_program_to_anythingllm(program_name, applicant_requirements, program_index, workspace_slug):
    """Tek bir programı AnythingLLM'e gönderir ve yanıtı döndürür."""
    message = f"""
Program Adı: {program_name}

Başvuru Koşulları: {applicant_requirements}

Bu program büyük ölçekli kurumsal bir Ar-Ge Merkezi için uygun mu?
"""
    data = {"message": message, "reset": False, "mode": "chat"}

    try:
        print(f"[{program_index}] Gönderiliyor: {program_name}")
        response = requests.post(f"{BASE_URL}/workspace/{workspace_slug}/chat", headers=headers, json=data, timeout=60)

        if response.status_code == 200:
            raw = response.json()
            cleaned = clean_response(raw, import_sources=True)

            print(f"[{program_index}] Başarılı: {program_name}")
            print(f"Yanıt: {cleaned['response'][:100]}...")  # sadece özet
            print("-" * 80)
            return cleaned
        else:
            print(f"[{program_index}] Hata: {program_name} - Status Code: {response.status_code}")
            print(f"Hata mesajı: {response.text}")
            return None

    except Exception as e:
        print(f"[{program_index}] Exception: {program_name} - {str(e)}")
        return None
