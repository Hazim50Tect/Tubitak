import json
import time
from pathlib import Path
from core.anythingllm_client import create_new_workspace
from utils.file_manager import get_next_html_filename, get_next_json_filename
from core.ai_analyzer import send_program_to_anythingllm, extract_score_from_response, update_final_mean_file
from utils.output_manager import init_html, close_html, append_to_html, init_json, append_to_json, close_json
from scrapers.tubitak_programs_scraper import check_data_file, scrape_tubitak_data

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RAG_FILE = str(DATA_DIR / "tubitak_rag_data.json")


def main():
    # 1. TÜBİTAK sayfasındaki güncel program listesini çek ve JSON'ı güncelle
    print("🔄 TÜBİTAK web sitesindeki güncel programlar çekiliyor ve 'tubitak_rag_data.json' güncelleniyor...")
    try:
        data = scrape_tubitak_data()
        print("=" * 80)
    except Exception as e:
        print(f"⚠️ TÜBİTAK verileri çekilirken hata oluştu: {str(e)}")
        print(f"📁 Mevcut '{RAG_FILE}' dosyasından devam edilmeye çalışılıyor...")
        data = None

    # Eğer canlı çekimden data dönmediyse dosyadan oku
    if not data:
        try:
            with open(RAG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            print("❌ tubitak_rag_data.json dosyası bulunamadı!")
            return
        except json.JSONDecodeError:
            print("❌ JSON dosyası geçersiz format!")
            return

    # 2. Yeni workspace oluştur
    workspace_slug = create_new_workspace()
    if not workspace_slug:
        print("Workspace oluşturulamadı! İşlem sonlandırılıyor.")
        return

    print(f"Kullanılacak workspace: {workspace_slug}")
    print("=" * 80)

    # 3. HTML ve JSON dosya adlarını belirle
    html_file = get_next_html_filename()
    json_file = get_next_json_filename()

    programs = data.get("programs", [])
    print(f"Toplam {len(programs)} program bulundu.")
    print(f"Toplam {len(programs)} program analiz edilecek.")
    print("=" * 80)

    results = []

    # HTML dosyasını başlat
    init_html(html_file)

    # JSON dosyasını başlat
    init_json(json_file)

    for index, program in enumerate(programs, 1):
        program_name = program.get("program_name", "Bilinmeyen Program")
        applicant_requirements = program.get("applicant_requirements", "Veri bulunamadı")
        status = program.get("status", "unknown")

        if status == "success" and applicant_requirements != "Veri bulunamadı":
            result = send_program_to_anythingllm(program_name, applicant_requirements, index, workspace_slug)

            if result:
                analysis_text = result.get("response", "").replace("\\n", "\n")

                # AI yanıtından skoru çıkar ve kaydet
                score = extract_score_from_response(analysis_text)
                if score is not None:
                    update_final_mean_file(program_name, score)
                else:
                    print(f"[{index}] Skor bulunamadı: {program_name}")

                item = {
                    "program_name": program_name,
                    "applicant_requirements": applicant_requirements,
                    "analysis": analysis_text,
                }

                results.append(item)
                append_to_html(item, html_file)
                append_to_json(item, json_file)

            else:
                error_item = {
                    "program_name": program_name,
                    "applicant_requirements": applicant_requirements,
                    "analysis": "Hata: Analiz yapılamadı",
                }
                results.append(error_item)
                append_to_html(error_item, html_file)
                append_to_json(error_item, json_file)

            print("-" * 80)
            time.sleep(1)
        else:
            print(f"[{index}] Atlanıyor: {program_name} - Status: {status}")
            print("-" * 80)

    # HTML dosyasını kapat
    close_html(html_file)

    # JSON dosyasını kapat
    close_json(json_file)

    print("Tüm programlar işlendi!")
    print(f"Sonuçlar '{html_file}' ve '{json_file}' dosyalarına kaydedildi.")


if __name__ == "__main__":
    main()
