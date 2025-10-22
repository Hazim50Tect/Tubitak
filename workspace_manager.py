import requests
import json
import os

# AnythingLLM API ayarları
API_KEY = os.getenv("ANYTHINGLLM_API_KEY", "R212Y2R-Z494M7R-J8Q01DP-JY4DV4N")
BASE_URL = "http://localhost:3001/api/v1"

headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}


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
