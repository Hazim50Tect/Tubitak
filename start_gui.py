#!/usr/bin/env python3
"""
TÜBİTAK Analiz Sistemi GUI Başlatıcı
"""

import sys
import os


def check_dependencies():
    """Gerekli kütüphaneleri kontrol eder."""
    required_packages = ["requests", "schedule"]
    missing_packages = []

    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)

    if missing_packages:
        print("❌ Eksik kütüphaneler bulundu:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\n📦 Kütüphaneleri yüklemek için:")
        print("   pip install -r requirements.txt")
        return False

    return True


def main():
    print("🚀 TÜBİTAK Analiz Sistemi Başlatılıyor...")
    print("=" * 50)

    # Bağımlılıkları kontrol et
    if not check_dependencies():
        input("\nEnter tuşuna basın...")
        return

    print("✅ Tüm kütüphaneler mevcut")
    print("🖥️ GUI arayüzü başlatılıyor...")
    print("=" * 50)

    try:
        # GUI uygulamasını başlat
        from gui_app import main as start_gui

        start_gui()
    except Exception as e:
        print(f"❌ GUI başlatma hatası: {str(e)}")
        input("\nEnter tuşuna basın...")


if __name__ == "__main__":
    main()
