import requests
from bs4 import BeautifulSoup
import time
import re

BASE_URL = "https://tubitak.gov.tr"
LIST_URL = f"{BASE_URL}/tr/destekler/sanayi/ulusal-destek-programlari"

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def clean_text(text):
    """Gereksiz boşlukları ve satır sonlarını temizler"""
    text = re.sub(r"\s+", " ", text).strip()
    return text


def get_call_links_and_names():
    """Liste sayfasındaki çağrı adlarını ve linklerini döndürür"""
    r = requests.get(LIST_URL, headers=headers)
    soup = BeautifulSoup(r.text, "html.parser")

    container = soup.select_one("#paragraph-id--311 > div > div > div > div")
    if not container:
        print("⚠️ Çağrılar container'ı bulunamadı.")
        return []

    calls = []
    seen_urls = set()  # Tekrar eden URL'leri önlemek için

    for div in container.select("div > div > div > div > div"):
        a = div.find("a")
        if a and "href" in a.attrs:
            name = clean_text(a.get_text())
            link = a["href"]
            if not link.startswith("http"):
                link = BASE_URL + link

            # Aynı URL'yi tekrar ekleme
            if link not in seen_urls:
                seen_urls.add(link)
                calls.append({"name": name, "url": link})

    return calls


def get_applicant_info(url):
    """Çağrı detay sayfasından yalnızca 'Kimler Başvurabilir' kısmını döndürür"""
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

                # Tüm içeriği birleştir - hem p hem de ul/li elementlerini
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
                    return [" ".join(full_text_parts)]

                return None
    return None


def main():
    calls = get_call_links_and_names()
    print(f"🔗 {len(calls)} çağrı bulundu.\n")

    for i, call in enumerate(calls, 1):
        print(f"[{i}/{len(calls)}] {call['name']}")
        print("=" * 80)
        try:
            maddeler = get_applicant_info(call["url"])
            if maddeler:
                print("Kimler Başvurabilir:")
                for madde in maddeler:
                    print(f"  {madde}")
            else:
                print("(veri bulunamadı)")
        except Exception as e:
            print(f"⚠️ Hata: {e}")

        print("\n" + "-" * 80 + "\n")
        time.sleep(2)

    print("✅ Tüm çağrılar işlendi.")


if __name__ == "__main__":
    main()
