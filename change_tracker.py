"""
TÜBİTAK Program ve Aktif Çağrı Değişiklik Takip Modülü (Change Tracker)
1. Yeni Eklenen Programlar
2. Yayından Kalkan / Silinen Programlar
3. Başvuru Şartları Değişen Programlar
4. Yeni Açılan Aktif Çağrılar
5. Süresi Dolup Kapanan Çağrılar
"""

import os
import json
import shutil
from datetime import datetime
import re


CHANGES_FILE = "changes_history.json"
RAG_FILE = "tubitak_rag_data.json"
PREV_RAG_FILE = "tubitak_rag_data_previous.json"
ACTIVE_FILE = "active_calls_data.json"
PREV_ACTIVE_FILE = "active_calls_previous.json"


def normalize_clean_text(text):
    """Metin karşılaştırması için boşlukları temizler."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", str(text)).strip()


def load_json(filepath):
    """Güvenli bir şekilde JSON dosyası okur."""
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None


def save_json(filepath, data):
    """JSON dosyasına kaydeder."""
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Hata ({filepath}): {str(e)}")
        return False


def compare_programs(old_programs, new_programs):
    """
    Eski ve yeni program listelerini karşılaştırır:
    - Yeni Eklenenler
    - Yayından Kalkanlar / Silinenler
    - Başvuru Şartları Değişenler
    """
    old_dict = {p.get("program_name"): p for p in (old_programs or []) if p.get("program_name")}
    new_dict = {p.get("program_name"): p for p in (new_programs or []) if p.get("program_name")}

    new_added = []
    removed = []
    modified = []

    # 1. Yeni eklenenler ve şartı değişenler
    for name, p in new_dict.items():
        if name not in old_dict:
            new_added.append({
                "program_name": name,
                "url": p.get("program_url", ""),
                "applicant_requirements": p.get("applicant_requirements", ""),
                "status": p.get("status", "success"),
                "detected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
        else:
            old_req = normalize_clean_text(old_dict[name].get("applicant_requirements", ""))
            new_req = normalize_clean_text(p.get("applicant_requirements", ""))

            # Şart metinleri var ve farklıysa
            if old_req and new_req and old_req != new_req and old_req != "Veri bulunamadı" and new_req != "Veri bulunamadı":
                modified.append({
                    "program_name": name,
                    "url": p.get("program_url", ""),
                    "old_requirements": old_req,
                    "new_requirements": new_req,
                    "detected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })

    # 2. Silinen / yayından kalkanlar
    for name, p in old_dict.items():
        if name not in new_dict:
            removed.append({
                "program_name": name,
                "url": p.get("program_url", ""),
                "last_requirements": p.get("applicant_requirements", ""),
                "detected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

    return new_added, removed, modified


def compare_active_calls(old_calls, new_calls):
    """
    Eski ve yeni aktif çağrıları karşılaştırır:
    - Yeni Açılan Aktif Çağrılar
    - Süresi Dolup Kapanan Aktif Çağrılar
    """
    def get_name(item):
        return item.get("name") or item.get("program_name") or ""

    old_dict = {get_name(c): c for c in (old_calls or []) if get_name(c)}
    new_dict = {get_name(c): c for c in (new_calls or []) if get_name(c)}

    new_opened = []
    closed = []

    for name, c in new_dict.items():
        if name not in old_dict:
            new_opened.append({
                "name": name,
                "url": c.get("url") or c.get("program_url", ""),
                "found_date": c.get("found_date", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                "detected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

    for name, c in old_dict.items():
        if name not in new_dict:
            closed.append({
                "name": name,
                "url": c.get("url") or c.get("program_url", ""),
                "closed_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "detected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

    return new_opened, closed


def save_changes_report(new_programs, removed_programs, modified_programs, new_active_calls, closed_active_calls):
    """Değişiklikleri dosyaya kaydeder."""
    total = (
        len(new_programs) +
        len(removed_programs) +
        len(modified_programs) +
        len(new_active_calls) +
        len(closed_active_calls)
    )

    report = {
        "last_check_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "new_programs_count": len(new_programs),
            "removed_programs_count": len(removed_programs),
            "modified_programs_count": len(modified_programs),
            "new_active_calls_count": len(new_active_calls),
            "closed_active_calls_count": len(closed_active_calls),
            "total_changes": total
        },
        "new_programs": new_programs,
        "removed_programs": removed_programs,
        "modified_programs": modified_programs,
        "new_active_calls": new_active_calls,
        "closed_active_calls": closed_active_calls
    }

    save_json(CHANGES_FILE, report)
    return report


def get_current_changes():
    """
    Kaydedilmiş veya hesaplanmış en güncel fark raporunu döndürür.
    """
    prev_rag = load_json(PREV_RAG_FILE)
    curr_rag = load_json(RAG_FILE)

    prev_active = load_json(PREV_ACTIVE_FILE)
    curr_active = load_json(ACTIVE_FILE)

    old_programs = prev_rag.get("programs", []) if prev_rag else []
    new_programs = curr_rag.get("programs", []) if curr_rag else []

    new_p, rem_p, mod_p = compare_programs(old_programs, new_programs)

    old_calls = prev_active.get("programs", []) if prev_active else []
    new_calls = curr_active.get("programs", []) if curr_active else []

    new_c, closed_c = compare_active_calls(old_calls, new_calls)

    report = save_changes_report(new_p, rem_p, mod_p, new_c, closed_c)
    return report


def backup_before_rag_update():
    """Yeni program verisi çekilmeden önce mevcut RAG dosyasını yedeğe alır."""
    if os.path.exists(RAG_FILE):
        try:
            shutil.copy2(RAG_FILE, PREV_RAG_FILE)
        except Exception as e:
            print(f"Yedekleme hatası ({RAG_FILE}): {e}")


def backup_before_active_update():
    """Yeni aktif çağrılar çekilmeden önce mevcut aktif çağrı dosyasını yedeğe alır."""
    if os.path.exists(ACTIVE_FILE):
        try:
            shutil.copy2(ACTIVE_FILE, PREV_ACTIVE_FILE)
        except Exception as e:
            print(f"Yedekleme hatası ({ACTIVE_FILE}): {e}")


def run_quick_diff_check():
    """
    Canlı sayfadan program isimlerini ve aktif çağrıları hızlıca çekip
    önceki çalıştırma verisi ile kıyaslar ve değişiklik raporunu günceller.
    """
    import requests
    from bs4 import BeautifulSoup

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    base_url = "https://tubitak.gov.tr"
    list_url = f"{base_url}/tr/destekler/sanayi/ulusal-destek-programlari"

    try:
        r = requests.get(list_url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")

        # 1. Sol taraftaki program isimlerini çek
        container = soup.select_one("#paragraph-id--311 > div > div > div > div")
        live_program_names = set()
        live_programs_quick = []
        if container:
            for div in container.select("div > div > div > div > div"):
                a = div.find("a")
                if a and "href" in a.attrs:
                    name = normalize_clean_text(a.get_text())
                    href = a["href"]
                    if not href.startswith("http"):
                        href = base_url + href
                    if name and name not in live_program_names:
                        live_program_names.add(name)
                        live_programs_quick.append({"program_name": name, "program_url": href})

        # 2. Sağ taraftaki aktif çağrıları çek
        active_container = soup.select_one("#block-feza-gursey-views-block-cagrilar-block-2")
        live_active_calls = []
        if active_container:
            for link in active_container.select(".views-row a[href]"):
                call_name = normalize_clean_text(link.get_text())
                href = link.get("href")
                if not href.startswith("http"):
                    href = base_url + href
                live_active_calls.append({"name": call_name, "url": href, "found_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})

        # 3. Önceki durumla karşılaştır
        prev_rag = load_json(PREV_RAG_FILE) or load_json(RAG_FILE) or {"programs": []}
        old_programs = prev_rag.get("programs", [])
        new_programs, removed_programs, modified_programs = compare_programs(old_programs, live_programs_quick)

        prev_active = load_json(PREV_ACTIVE_FILE) or load_json(ACTIVE_FILE) or {"programs": []}
        old_active = prev_active.get("programs", [])
        new_active, closed_active = compare_active_calls(old_active, live_active_calls)

        report = save_changes_report(new_programs, removed_programs, modified_programs, new_active, closed_active)
        return report

    except Exception as e:
        print(f"Canlı değişiklik kontrolünde hata: {str(e)}")
        return get_current_changes()

