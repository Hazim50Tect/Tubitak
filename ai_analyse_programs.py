import requests
import json
import time
import re
import os

# AnythingLLM API ayarları
API_KEY = os.getenv("ANYTHINGLLM_API_KEY", "R212Y2R-Z494M7R-J8Q01DP-JY4DV4N")
BASE_URL = "http://localhost:3001/api/v1"

headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

HTML_FILE = "ai_analyse_results.html"


def get_next_workspace_name():
    """Mevcut workspace'leri kontrol edip bir sonraki tubitak numarasını döndürür."""
    try:
        response = requests.get(f"{BASE_URL}/workspaces", headers=headers)
        if response.status_code == 200:
            workspaces = response.json()
            existing_names = []

            for workspace in workspaces.get("workspaces", []):
                name = workspace.get("name", "")
                if name.startswith("tubitak"):
                    try:
                        # "tubitak" sonrasındaki sayıyı çıkar
                        num = int(name[7:])  # "tubitak" = 7 karakter
                        existing_names.append(num)
                    except ValueError:
                        continue

            if existing_names:
                next_num = max(existing_names) + 1
            else:
                next_num = 1

            return f"tubitak{next_num}"
        else:
            print(f"Workspace listesi alınamadı: {response.status_code}")
            return "tubitak1"
    except Exception as e:
        print(f"Workspace kontrolü sırasında hata: {str(e)}")
        return "tubitak1"


def create_new_workspace():
    """Yeni workspace oluşturur ve workspace slug'ını döndürür."""
    workspace_name = get_next_workspace_name()

    workspace_data = {
        "name": workspace_name,
        "similarityThreshold": 0.4,
        "openAiTemp": 0.4,
        "openAiHistory": 20,
        "openAiPrompt": "Sen TÜBİTAK destek programlarının şirkete uygunluğunu değerlendiren bir uzmansın.\nSana bir TÜBİTAK programı ve şirket bilgisi verilecek.\nGörevin, verilen bilgilere göre uygunluk değerlendirmesi yapmaktır.\n\nKurallar:\n\nAsla uydurma bilgi verme.\n\nBilgi eksikse, o şart sağlanmıyor varsayılır.\n\nSonuçta aşağıdaki formatta kısa bir analiz üret:\n\nUygunluk Skoru (0–1 arası)\n\nSonuç (Uygun / Uygun Değil / Şartlı Uygun)\n\nKısa açıklama (en fazla 2–3 cümle)\n\nGereksiz genel bilgiler, tablo, HTML veya formatlama kullanma.",
        "queryRefusalResponse": "Yanıt bulunamadı!",
        "chatMode": "chat",
        "topN": 4,
    }

    try:
        print(f"Yeni workspace oluşturuluyor: {workspace_name}")
        response = requests.post(f"{BASE_URL}/workspace/new", headers=headers, json=workspace_data, timeout=30)

        if response.status_code == 200:
            result = response.json()
            workspace_slug = result.get("workspace").get("slug")
            print(f"Workspace başarıyla oluşturuldu: {workspace_name} (slug: {workspace_slug})")
            return workspace_slug
        else:
            print(f"Workspace oluşturma hatası: {response.status_code}")
            print(f"Hata mesajı: {response.text}")
            return None

    except Exception as e:
        print(f"Workspace oluşturma sırasında hata: {str(e)}")
        return None


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


def append_to_html(item, html_file=HTML_FILE):
    """
    HTML dosyasına eklerken:
    - Markdown işaretlerini temizler (#, *, **)
    - | ve --- ile yazılmış tablo varsa gerçek HTML <table> yapar
    - Satır sonlarını <br> ile korur
    """
    text = item["analysis"]

    # Tablo var mı kontrol et
    table_blocks = []
    lines = text.split("\n")
    non_table_lines = []
    current_table = []

    for line in lines:
        if "|" in line:
            current_table.append(line)
        else:
            if current_table:
                table_blocks.append(current_table)
                current_table = []
            non_table_lines.append(line)
    if current_table:
        table_blocks.append(current_table)

    # Tabloyu HTML yap
    html_tables = []
    for table in table_blocks:
        html_table = ["<table border='1' cellspacing='0' cellpadding='5'>"]
        for i, row in enumerate(table):
            cells = [c.strip() for c in row.split("|") if c.strip()]
            if i == 0 or all(re.match(r"^-+$", c) for c in cells):
                html_table.append("<tr>" + "".join(f"<th>{c}</th>" for c in cells) + "</tr>")
            else:
                html_table.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
        html_table.append("</table>")
        html_tables.append("\n".join(html_table))

    # Markdown işaretlerini temizle
    clean_text = re.sub(r"[*#]+", "", "\n".join(non_table_lines)).strip()
    clean_text = clean_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    clean_text = clean_text.replace("\n", "<br>")

    # HTML yaz
    with open(html_file, "a", encoding="utf-8") as f:
        f.write(f"<h2>{item['program_name']}</h2>\n")
        f.write(f"<p><strong>Başvuru Koşulları:</strong> {item['applicant_requirements']}</p>\n")
        f.write(f"<p>{clean_text}</p>\n")
        for table_html in html_tables:
            f.write(f"{table_html}\n")
        f.write("<hr>\n\n")


def init_html(html_file=HTML_FILE):
    """HTML dosyasını başlatır."""
    with open(html_file, "w", encoding="utf-8") as f:
        f.write("<!DOCTYPE html>\n<html lang='tr'>\n<head>\n<meta charset='utf-8'>\n")
        f.write("<title>Ar-Ge Program Analizleri</title>\n</head>\n<body>\n")
        f.write("<h1>TÜBİTAK Ar-Ge Program Analizleri</h1>\n")


def close_html(html_file=HTML_FILE):
    """HTML dosyasını kapatır."""
    with open(html_file, "a", encoding="utf-8") as f:
        f.write("</body>\n</html>")


def main():
    # Yeni workspace oluştur
    workspace_slug = create_new_workspace()
    if not workspace_slug:
        print("Workspace oluşturulamadı! İşlem sonlandırılıyor.")
        return

    print(f"Kullanılacak workspace: {workspace_slug}")
    print("=" * 80)

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

    results = []

    # HTML dosyasını başlat
    init_html()

    for index, program in enumerate(programs, 1):
        program_name = program.get("program_name", "Bilinmeyen Program")
        applicant_requirements = program.get("applicant_requirements", "Veri bulunamadı")
        status = program.get("status", "unknown")

        if status == "success" and applicant_requirements != "Veri bulunamadı":
            result = send_program_to_anythingllm(program_name, applicant_requirements, index, workspace_slug)

            if result:
                analysis_text = result.get("response", "").replace("\\n", "\n")
                item = {
                    "program_name": program_name,
                    "applicant_requirements": applicant_requirements,
                    "analysis": analysis_text,
                }

                results.append(item)
                append_to_html(item)

            else:
                error_item = {
                    "program_name": program_name,
                    "applicant_requirements": applicant_requirements,
                    "analysis": "Hata: Analiz yapılamadı",
                }
                results.append(error_item)
                append_to_html(error_item)

            time.sleep(1)
        else:
            print(f"[{index}] Atlanıyor: {program_name} - Status: {status}")
            print("-" * 80)

    # HTML dosyasını kapat
    close_html()

    # JSON dosyasına kaydet
    with open("ai_analyse_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("Tüm programlar işlendi!")
    print(f"Sonuçlar '{HTML_FILE}' ve 'ai_analyse_results.json' dosyalarına kaydedildi.")


if __name__ == "__main__":
    main()
