import requests
from bs4 import BeautifulSoup
import time
import re
import json
import os
from datetime import datetime

BASE_URL = "https://tubitak.gov.tr"
ACTIVE_CALLS_URL = f"{BASE_URL}/tr/destekler/sanayi/ulusal-destek-programlari"

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def clean_text(text):
    """Gereksiz boşlukları ve satır sonlarını temizler"""
    text = re.sub(r"\s+", " ", text).strip()
    return text


def get_active_calls():
    """Aktif çağrıları çeker ve döndürür."""
    print("🔍 Aktif çağrılar kontrol ediliyor...")

    try:
        r = requests.get(ACTIVE_CALLS_URL, headers=headers)
        soup = BeautifulSoup(r.text, "html.parser")

        # Aktif çağrılar container'ını bul
        active_calls_container = soup.select_one("#block-feza-gursey-views-block-cagrilar-block-2")

        if not active_calls_container:
            print("⚠️ Aktif çağrılar container'ı bulunamadı.")
            return []

        # Çağrı linklerini bul
        call_links = active_calls_container.select(".views-row a[href]")

        active_calls = []
        for link in call_links:
            name = clean_text(link.get_text())
            href = link.get("href")

            if not href.startswith("http"):
                href = BASE_URL + href

            active_calls.append({"name": name, "url": href, "found_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})

        print(f"✅ {len(active_calls)} aktif çağrı bulundu.")
        return active_calls

    except Exception as e:
        print(f"❌ Aktif çağrılar çekilirken hata: {str(e)}")
        return []


def get_call_details(url):
    """Çağrı detay sayfasından 'Kimler Başvurabilir' bilgisini çeker."""
    try:
        r = requests.get(url, headers=headers)
        soup = BeautifulSoup(r.text, "html.parser")

        # "Kimler Başvurabilir" başlığını bul
        basliklar = soup.select(".field--name-field-baslik.field__item")

        for baslik in basliklar:
            if "Kimler Başvurabilir" in baslik.get_text(strip=True):
                # Parent paragraph'ı bul
                parent_paragraph = baslik.find_parent("div", class_="paragraph")
                if parent_paragraph:
                    # İçerik alanını bul
                    icerik = parent_paragraph.select_one(".field--name-field-icerik.field__item")
                    if not icerik:
                        return None

                    # Tüm içeriği birleştir
                    full_text_parts = []

                    # Önce paragrafları al
                    for p in icerik.find_all("p"):
                        text = clean_text(p.get_text())
                        if text:
                            full_text_parts.append(text)

                    # Sonra liste elemanlarını al
                    for li in icerik.find_all("li"):
                        text = clean_text(li.get_text())
                        if text:
                            full_text_parts.append(text)

                    # Eğer hiçbir şey bulunamadıysa, tüm içeriği al
                    if not full_text_parts:
                        full_text = clean_text(icerik.get_text())
                        if full_text:
                            full_text_parts = [full_text]

                    # Tüm parçaları birleştir
                    if full_text_parts:
                        return " ".join(full_text_parts)

                    return None
        return None

    except Exception as e:
        print(f"❌ Çağrı detayları çekilirken hata: {str(e)}")
        return None


def scrape_active_calls():
    """Aktif çağrıları çeker (sadece isimler)."""
    print("🚀 Aktif çağrılar işleniyor...")

    # Aktif çağrıları çek
    active_calls = get_active_calls()

    if not active_calls:
        print("⚠️ Aktif çağrı bulunamadı.")
        return None

    # RAG için uygun JSON formatında veri toplama
    rag_data = {"source": "TÜBİTAK Aktif Çağrılar", "url": ACTIVE_CALLS_URL, "extraction_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "programs": []}

    for i, call in enumerate(active_calls, 1):
        print(f"[{i}/{len(active_calls)}] {call['name']}")

        program_data = {
            "program_name": call["name"],
            "program_url": call["url"],
            "applicant_requirements": "Aktif çağrı - detay çekilmedi",
            "status": "active_call",
            "found_date": call["found_date"],
        }

        rag_data["programs"].append(program_data)

    from change_tracker import backup_before_active_update, get_current_changes

    # Mevcut veriyi bir önceki çalıştırma olarak yedekle
    backup_before_active_update()

    # JSON dosyasına kaydet
    with open("active_calls_data.json", "w", encoding="utf-8") as f:
        json.dump(rag_data, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Aktif çağrılar 'active_calls_data.json' dosyasına kaydedildi.")
    print(f"✅ Toplam {len(rag_data['programs'])} çağrı işlendi.")

    # Değişiklik raporunu güncelle
    try:
        get_current_changes()
    except Exception as e:
        print(f"Aktif çağrı değişiklik raporu güncellenemedi: {e}")

    return rag_data


def check_active_calls_file():
    """active_calls_data.json dosyasının varlığını kontrol eder."""
    return os.path.exists("active_calls_data.json")


def get_active_calls_data():
    """active_calls_data.json dosyasını okur."""
    try:
        with open("active_calls_data.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None
