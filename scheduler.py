import schedule
import time
import json
import os
from datetime import datetime
from active_calls_manager import scrape_active_calls
from ai_analyzer import send_program_to_anythingllm, extract_score_from_response, update_final_mean_file
from workspace_manager import create_new_workspace
from file_manager import get_next_html_filename, get_next_json_filename
from output_manager import init_html, close_html, append_to_html


def load_final_ai_results():
    """FINAL_ai_results_mean.json dosyasını yükler."""
    try:
        with open("FINAL_ai_results_mean.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def extract_call_number(program_name):
    """Program adından çağrı numarasını çıkarır."""
    import re

    # "1707 - Sipariş Ar-Ge..." veya "1831 Yeşil İnovasyon..." formatından sayı çıkar
    # Önce "-" ile başlayan formatı dene
    match = re.match(r"^(\d+)\s*-", program_name)
    if match:
        return match.group(1)

    # Sonra sadece sayı ile başlayan formatı dene
    match = re.match(r"^(\d+)\s+", program_name)
    if match:
        return match.group(1)

    return None


def find_matching_program_in_rag_data(active_call_name, rag_data):
    """Aktif çağrı adını tubitak_rag_data.json'daki programlarla eşleştirir."""
    call_number = extract_call_number(active_call_name)

    if not call_number:
        return None

    # tubitak_rag_data.json'daki programları ara
    for program in rag_data.get("programs", []):
        program_name = program.get("program_name", "")
        if call_number in program_name:
            return program_name

    return None


def find_program_average(program_name, final_ai_data):
    """Program adına göre ortalama değeri bulur."""
    if program_name in final_ai_data:
        return final_ai_data[program_name].get("mean", None)
    return None


def analyze_active_calls():
    """Aktif çağrıları analiz eder ve ortalama değerlerini listeler."""
    print(f"\n🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Aktif çağrılar analiz ediliyor...")
    print("=" * 80)

    # 1. Aktif çağrıları çek (JSON dosyası oluşturmadan)
    print("📥 Aktif çağrılar çekiliyor...")
    from active_calls_manager import get_active_calls

    active_calls = get_active_calls()

    if not active_calls:
        print("❌ Aktif çağrı bulunamadı!")
        return

    # 2. tubitak_rag_data.json dosyasını yükle
    print("📊 TÜBİTAK veri dosyası yükleniyor...")
    try:
        with open("tubitak_rag_data.json", "r", encoding="utf-8") as f:
            rag_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print("❌ tubitak_rag_data.json dosyası bulunamadı!")
        print("📋 Sadece aktif çağrı listesi:")
        for call in active_calls:
            print(f"   - {call['name']}")
        return

    # 3. FINAL_ai_results_mean.json dosyasını yükle
    print("📊 Ortalama değerler yükleniyor...")
    final_ai_data = load_final_ai_results()

    if not final_ai_data:
        print("⚠️ FINAL_ai_results_mean.json dosyası bulunamadı veya boş!")
        print("📋 Sadece aktif çağrı listesi:")
        for call in active_calls:
            print(f"   - {call['name']}")
        return

    # 4. Her aktif çağrı için eşleştirme ve ortalama değeri bul
    print("🔍 Aktif çağrılar ve ortalama değerleri:")
    print("-" * 80)

    results = []

    for call in active_calls:
        active_call_name = call.get("name", "Bilinmeyen Program")

        # Aktif çağrıyı tubitak_rag_data.json'daki programlarla eşleştir
        matched_program_name = find_matching_program_in_rag_data(active_call_name, rag_data)

        if matched_program_name:
            # Eşleşen program için ortalama değeri bul
            average_score = find_program_average(matched_program_name, final_ai_data)
            match_status = "✅ Eşleşti"
        else:
            # Eşleşme bulunamadı
            average_score = None
            matched_program_name = None
            match_status = "❌ Eşleşmedi"

        result = {
            "active_call_name": active_call_name,
            "matched_program_name": matched_program_name,
            "average_score": average_score,
            "found_date": call.get("found_date", ""),
            "match_status": match_status,
        }
        results.append(result)

        # Konsol çıktısı
        print(f"📞 {active_call_name}")
        print(f"   {match_status}")

        if matched_program_name:
            print(f"   Eşleşen Program: {matched_program_name}")

            if average_score is None:
                score_emoji = "⚪"
                score_text = "Skor bulunamadı"
            else:
                score_emoji = "🟢" if average_score >= 0.7 else "🟡" if average_score >= 0.4 else "🔴"
                score_text = f"{average_score:.3f}"

            print(f"   {score_emoji} Ortalama Skor: {score_text}")
        else:
            print(f"   ⚪ Ortalama Skor: Eşleşme bulunamadı")

        print()

    # 4. Sonuçları JSON dosyasına kaydet
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Klasörü oluştur
    output_dir = "active_calls_analysis_output"
    os.makedirs(output_dir, exist_ok=True)

    output_file = os.path.join(output_dir, f"active_calls_analysis_{timestamp}.json")

    analysis_data = {"analysis_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "total_active_calls": len(active_calls), "results": results}

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(analysis_data, f, ensure_ascii=False, indent=2)

    print(f"💾 Analiz sonuçları '{output_file}' dosyasına kaydedildi.")

    # 5. Özet istatistikler
    matched_calls = [r for r in results if r["match_status"] == "✅ Eşleşti"]
    unmatched_calls = [r for r in results if r["match_status"] == "❌ Eşleşmedi"]

    high_score = [r for r in matched_calls if r["average_score"] is not None and r["average_score"] >= 0.7]
    medium_score = [r for r in matched_calls if r["average_score"] is not None and 0.4 <= r["average_score"] < 0.7]
    low_score = [r for r in matched_calls if r["average_score"] is not None and r["average_score"] < 0.4]
    no_score = [r for r in matched_calls if r["average_score"] is None]

    print("📈 Özet İstatistikler:")
    print(f"   ✅ Eşleşen Çağrılar: {len(matched_calls)}")
    print(f"   ❌ Eşleşmeyen Çağrılar: {len(unmatched_calls)}")
    print(f"   🟢 Yüksek Skor (≥0.7): {len(high_score)} çağrı")
    print(f"   🟡 Orta Skor (0.4-0.7): {len(medium_score)} çağrı")
    print(f"   🔴 Düşük Skor (<0.4): {len(low_score)} çağrı")
    print(f"   ⚪ Skor Bulunamadı: {len(no_score)} çağrı")

    if high_score:
        print("\n🎯 Yüksek Skorlu Aktif Çağrılar:")
        for result in high_score:
            print(f"   - {result['active_call_name']} → {result['matched_program_name']} (Skor: {result['average_score']:.3f})")

    if unmatched_calls:
        print("\n❌ Eşleşmeyen Aktif Çağrılar:")
        for result in unmatched_calls:
            print(f"   - {result['active_call_name']}")

    if no_score:
        print("\n⚪ Eşleşti Ama Skor Bulunamayan Çağrılar:")
        for result in no_score:
            print(f"   - {result['active_call_name']} → {result['matched_program_name']}")

    print("=" * 80)


def run_scheduled_analysis():
    """Zamanlanmış analiz işlemini çalıştırır."""
    try:
        analyze_active_calls()
    except Exception as e:
        print(f"❌ Analiz sırasında hata: {str(e)}")
        print(f"🕐 Hata zamanı: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def start_scheduler():
    """Zamanlayıcıyı başlatır."""
    print("🚀 TÜBİTAK Aktif Çağrı Analiz Zamanlayıcısı Başlatılıyor...")
    print("=" * 80)
    print("📅 Zamanlanmış Görevler:")
    print("   🌅 Sabah 08:00 - Aktif çağrılar analizi")
    print("   ☀️ Öğle 12:00 - Aktif çağrılar analizi")
    print("   🌆 Akşam 17:00 - Aktif çağrılar analizi")
    print("   🌙 Gece 00:00 - Aktif çağrılar analizi")
    print("=" * 80)
    print("⏰ Zamanlayıcı çalışıyor... (Ctrl+C ile durdurun)")

    # Zamanlanmış görevleri tanımla
    schedule.every().day.at("08:00").do(run_scheduled_analysis)
    schedule.every().day.at("12:00").do(run_scheduled_analysis)
    schedule.every().day.at("17:00").do(run_scheduled_analysis)
    schedule.every().day.at("00:00").do(run_scheduled_analysis)
    schedule.every().day.at("17:10").do(run_scheduled_analysis)

    # İlk analizi hemen çalıştır
    print("🔄 İlk analiz hemen çalıştırılıyor...")
    run_scheduled_analysis()

    # Ana döngü
    while True:
        schedule.run_pending()
        time.sleep(60)  # Her dakika kontrol et


if __name__ == "__main__":
    try:
        start_scheduler()
    except KeyboardInterrupt:
        print("\n⏹️ Zamanlayıcı durduruldu.")
    except Exception as e:
        print(f"❌ Zamanlayıcı hatası: {str(e)}")
