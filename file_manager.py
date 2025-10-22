import glob
import os


def ensure_directories():
    """Gerekli klasörleri oluşturur."""
    os.makedirs("ai_analyse_results_html", exist_ok=True)
    os.makedirs("ai_analyse_results_json", exist_ok=True)


def get_next_html_filename():
    """Mevcut HTML dosyalarını kontrol edip bir sonraki numarayı döndürür."""
    ensure_directories()

    # Mevcut HTML dosyalarını bul
    pattern = "ai_analyse_results_html/ai_analyse_results*.html"
    existing_files = glob.glob(pattern)

    existing_numbers = []
    for filepath in existing_files:
        filename = os.path.basename(filepath)
        # "ai_analyse_results" sonrasındaki sayıyı çıkar
        if filename == "ai_analyse_results.html":
            # Eğer numarasız dosya varsa, onu 1 olarak say
            existing_numbers.append(1)
        else:
            # "ai_analyse_results" + sayı + ".html" formatından sayıyı çıkar
            try:
                # "ai_analyse_results" = 18 karakter
                num_part = filename[18:-5]  # ".html" = 5 karakter
                if num_part.isdigit():
                    existing_numbers.append(int(num_part))
            except (ValueError, IndexError):
                continue

    if existing_numbers:
        next_num = max(existing_numbers) + 1
    else:
        next_num = 1

    return f"ai_analyse_results_html/ai_analyse_results{next_num}.html"


def get_next_json_filename():
    """Mevcut JSON dosyalarını kontrol edip bir sonraki numarayı döndürür."""
    ensure_directories()

    # Mevcut JSON dosyalarını bul
    pattern = "ai_analyse_results_json/ai_analyse_results*.json"
    existing_files = glob.glob(pattern)

    existing_numbers = []
    for filepath in existing_files:
        filename = os.path.basename(filepath)
        # "ai_analyse_results" sonrasındaki sayıyı çıkar
        if filename == "ai_analyse_results.json":
            # Eğer numarasız dosya varsa, onu 1 olarak say
            existing_numbers.append(1)
        else:
            # "ai_analyse_results" + sayı + ".json" formatından sayıyı çıkar
            try:
                # "ai_analyse_results" = 18 karakter
                num_part = filename[18:-5]  # ".json" = 5 karakter
                if num_part.isdigit():
                    existing_numbers.append(int(num_part))
            except (ValueError, IndexError):
                continue

    if existing_numbers:
        next_num = max(existing_numbers) + 1
    else:
        next_num = 1

    return f"ai_analyse_results_json/ai_analyse_results{next_num}.json"
