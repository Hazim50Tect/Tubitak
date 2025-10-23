#!/usr/bin/env python3
"""
TÜBİTAK Analiz Web Uygulaması Başlatıcı
"""

import subprocess
import sys
import os
import time


def start_server():
    """Web sunucusunu başlatır."""
    print("🚀 TÜBİTAK Analiz Web Uygulaması başlatılıyor...")
    print("=" * 60)
    print("📱 Web Arayüzü: http://localhost:8000")
    print("📊 API Dokümantasyonu: http://localhost:8000/docs")
    print("🔧 API Test: http://localhost:8000/redoc")
    print("=" * 60)
    print("⏹️  Durdurmak için Ctrl+C tuşlayın")
    print("=" * 60)

    try:
        # Uvicorn ile sunucuyu başlat
        subprocess.run([sys.executable, "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"])
    except KeyboardInterrupt:
        print("\n🛑 Sunucu durduruldu.")
    except Exception as e:
        print(f"❌ Hata: {e}")


def main():
    """Ana fonksiyon."""
    print("🎯 TÜBİTAK Analiz Web Sistemi")
    print("=" * 40)

    print("\n🌐 Web sunucusu başlatılıyor...")
    time.sleep(2)

    # Sunucuyu başlat
    start_server()


if __name__ == "__main__":
    main()
