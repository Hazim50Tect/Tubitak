#!/usr/bin/env python3
"""
TÜBİTAK Analiz GUI Arayüzü
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import time
from datetime import datetime
import queue
import json
import os
from scheduler import analyze_active_calls, start_scheduler
from main import main as run_full_analysis


class TubitakAnalyzerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("TÜBİTAK Analiz Sistemi")
        self.root.geometry("1000x700")
        self.root.configure(bg="#f0f0f0")

        # Thread kontrolü
        self.scheduler_thread = None
        self.analysis_thread = None
        self.is_scheduler_running = False

        # Queue for thread communication
        self.log_queue = queue.Queue()

        # GUI bileşenlerini oluştur
        self.create_widgets()

        # Log queue'yu kontrol et
        self.check_log_queue()

    def create_widgets(self):
        """GUI bileşenlerini oluşturur."""
        # Ana başlık
        title_frame = tk.Frame(self.root, bg="#f0f0f0")
        title_frame.pack(fill="x", padx=10, pady=5)

        title_label = tk.Label(title_frame, text="TÜBİTAK Analiz Sistemi", font=("Arial", 16, "bold"), bg="#f0f0f0", fg="#2c3e50")
        title_label.pack()

        # Kontrol paneli
        control_frame = tk.LabelFrame(self.root, text="Kontrol Paneli", font=("Arial", 12, "bold"), bg="#f0f0f0", fg="#2c3e50")
        control_frame.pack(fill="x", padx=10, pady=5)

        # Butonlar
        button_frame = tk.Frame(control_frame, bg="#f0f0f0")
        button_frame.pack(fill="x", padx=10, pady=10)

        # Tüm çağrıları analiz et butonu
        self.analyze_button = tk.Button(
            button_frame,
            text="🔍 Tüm Çağrıları Analiz Et",
            command=self.start_full_analysis,
            font=("Arial", 12, "bold"),
            bg="#3498db",
            fg="white",
            padx=20,
            pady=10,
            relief="raised",
            bd=3,
        )
        self.analyze_button.pack(side="left", padx=5)

        # Zamanlayıcı başlat/durdur butonu
        self.scheduler_button = tk.Button(
            button_frame,
            text="⏰ Zamanlayıcıyı Başlat",
            command=self.toggle_scheduler,
            font=("Arial", 12, "bold"),
            bg="#27ae60",
            fg="white",
            padx=20,
            pady=10,
            relief="raised",
            bd=3,
        )
        self.scheduler_button.pack(side="left", padx=5)

        # Aktif çağrıları analiz et butonu
        self.active_analyze_button = tk.Button(
            button_frame,
            text="📊 Aktif Çağrıları Analiz Et",
            command=self.start_active_analysis,
            font=("Arial", 12, "bold"),
            bg="#e67e22",
            fg="white",
            padx=20,
            pady=10,
            relief="raised",
            bd=3,
        )
        self.active_analyze_button.pack(side="left", padx=5)

        # Durum paneli
        status_frame = tk.LabelFrame(self.root, text="Sistem Durumu", font=("Arial", 12, "bold"), bg="#f0f0f0", fg="#2c3e50")
        status_frame.pack(fill="x", padx=10, pady=5)

        # Durum göstergeleri
        status_info_frame = tk.Frame(status_frame, bg="#f0f0f0")
        status_info_frame.pack(fill="x", padx=10, pady=5)

        self.scheduler_status = tk.Label(status_info_frame, text="Zamanlayıcı: Durduruldu", font=("Arial", 10), bg="#f0f0f0", fg="#e74c3c")
        self.scheduler_status.pack(side="left", padx=10)

        self.analysis_status = tk.Label(status_info_frame, text="Analiz: Hazır", font=("Arial", 10), bg="#f0f0f0", fg="#27ae60")
        self.analysis_status.pack(side="left", padx=10)

        # Zamanlayıcı bilgisi
        self.scheduler_info = tk.Label(status_info_frame, text="Zamanlanmış: 08:00, 12:00, 17:00, 00:00", font=("Arial", 9), bg="#f0f0f0", fg="#7f8c8d")
        self.scheduler_info.pack(side="right", padx=10)

        # Log paneli
        log_frame = tk.LabelFrame(self.root, text="Sistem Logları", font=("Arial", 12, "bold"), bg="#f0f0f0", fg="#2c3e50")
        log_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Log text widget
        self.log_text = scrolledtext.ScrolledText(log_frame, height=20, font=("Consolas", 9), bg="#2c3e50", fg="#ecf0f1", insertbackground="white")
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)

        # İlk log mesajı
        self.log_message("🚀 TÜBİTAK Analiz Sistemi başlatıldı")
        self.log_message("📋 Hazır durumda - işlem seçin")

    def log_message(self, message):
        """Log mesajı ekler."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def check_log_queue(self):
        """Log queue'yu kontrol eder."""
        try:
            while True:
                message = self.log_queue.get_nowait()
                self.log_message(message)
        except queue.Empty:
            pass
        finally:
            # 100ms sonra tekrar kontrol et
            self.root.after(100, self.check_log_queue)

    def start_full_analysis(self):
        """Tüm çağrıları analiz et işlemini başlatır."""
        if self.analysis_thread and self.analysis_thread.is_alive():
            messagebox.showwarning("Uyarı", "Analiz işlemi zaten devam ediyor!")
            return

        self.analyze_button.config(state="disabled", text="⏳ Analiz Ediliyor...")
        self.analysis_status.config(text="Analiz: Çalışıyor", fg="#e67e22")

        self.analysis_thread = threading.Thread(target=self.run_full_analysis_thread)
        self.analysis_thread.daemon = True
        self.analysis_thread.start()

    def run_full_analysis_thread(self):
        """Tam analiz işlemini thread'de çalıştırır."""
        try:
            self.log_queue.put("🔍 Tüm çağrılar analiz ediliyor...")
            self.log_queue.put("📊 Workspace oluşturuluyor...")
            self.log_queue.put("🤖 AI analizleri başlatılıyor...")

            # main.py'deki fonksiyonu çalıştır
            run_full_analysis()

            self.log_queue.put("✅ Tüm analiz işlemi tamamlandı!")
            self.log_queue.put("📁 Sonuçlar HTML ve JSON dosyalarına kaydedildi")

        except Exception as e:
            self.log_queue.put(f"❌ Analiz hatası: {str(e)}")
        finally:
            # UI'yi güncelle
            self.root.after(0, self.reset_analysis_button)

    def reset_analysis_button(self):
        """Analiz butonunu sıfırlar."""
        self.analyze_button.config(state="normal", text="🔍 Tüm Çağrıları Analiz Et")
        self.analysis_status.config(text="Analiz: Hazır", fg="#27ae60")

    def start_active_analysis(self):
        """Aktif çağrıları analiz et işlemini başlatır."""
        if self.analysis_thread and self.analysis_thread.is_alive():
            messagebox.showwarning("Uyarı", "Analiz işlemi zaten devam ediyor!")
            return

        self.active_analyze_button.config(state="disabled", text="⏳ Analiz Ediliyor...")
        self.analysis_status.config(text="Analiz: Çalışıyor", fg="#e67e22")

        self.analysis_thread = threading.Thread(target=self.run_active_analysis_thread)
        self.analysis_thread.daemon = True
        self.analysis_thread.start()

    def run_active_analysis_thread(self):
        """Aktif analiz işlemini thread'de çalıştırır."""
        try:
            self.log_queue.put("📊 Aktif çağrılar analiz ediliyor...")
            self.log_queue.put("🔍 TÜBİTAK sayfasından aktif çağrılar çekiliyor...")
            self.log_queue.put("📈 Ortalama değerler hesaplanıyor...")

            # Scheduler'daki analiz fonksiyonunu çalıştır
            analyze_active_calls()

            self.log_queue.put("✅ Aktif çağrı analizi tamamlandı!")
            self.log_queue.put("📁 Sonuçlar active_calls_analysis_output klasörüne kaydedildi")

        except Exception as e:
            self.log_queue.put(f"❌ Analiz hatası: {str(e)}")
        finally:
            # UI'yi güncelle
            self.root.after(0, self.reset_active_analysis_button)

    def reset_active_analysis_button(self):
        """Aktif analiz butonunu sıfırlar."""
        self.active_analyze_button.config(state="normal", text="📊 Aktif Çağrıları Analiz Et")
        self.analysis_status.config(text="Analiz: Hazır", fg="#27ae60")

    def toggle_scheduler(self):
        """Zamanlayıcıyı başlatır/durdurur."""
        if not self.is_scheduler_running:
            self.start_scheduler()
        else:
            self.stop_scheduler()

    def start_scheduler(self):
        """Zamanlayıcıyı başlatır."""
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            return

        self.is_scheduler_running = True
        self.scheduler_button.config(text="⏹️ Zamanlayıcıyı Durdur", bg="#e74c3c")
        self.scheduler_status.config(text="Zamanlayıcı: Çalışıyor", fg="#27ae60")

        self.scheduler_thread = threading.Thread(target=self.run_scheduler_thread)
        self.scheduler_thread.daemon = True
        self.scheduler_thread.start()

        self.log_message("⏰ Zamanlayıcı başlatıldı")
        self.log_message("📅 Zamanlanmış saatler: 08:00, 12:00, 17:00, 00:00")

    def run_scheduler_thread(self):
        """Zamanlayıcı thread'ini çalıştırır."""
        try:
            import schedule

            # Zamanlanmış görevleri tanımla
            schedule.every().day.at("08:00").do(self.run_scheduled_analysis)
            schedule.every().day.at("12:00").do(self.run_scheduled_analysis)
            schedule.every().day.at("17:00").do(self.run_scheduled_analysis)
            schedule.every().day.at("00:00").do(self.run_scheduled_analysis)
            schedule.every().day.at("17:11").do(self.run_scheduled_analysis)

            self.log_queue.put("✅ Zamanlanmış görevler tanımlandı")

            # Ana döngü
            while self.is_scheduler_running:
                schedule.run_pending()
                time.sleep(60)  # Her dakika kontrol et

        except Exception as e:
            self.log_queue.put(f"❌ Zamanlayıcı hatası: {str(e)}")

    def run_scheduled_analysis(self):
        """Zamanlanmış analiz işlemini çalıştırır."""
        try:
            self.log_queue.put("🕐 Zamanlanmış analiz başlatıldı")
            self.log_queue.put("📊 Aktif çağrılar çekiliyor...")

            # Scheduler'daki analiz fonksiyonunu çalıştır
            analyze_active_calls()

            self.log_queue.put("✅ Zamanlanmış analiz tamamlandı")

        except Exception as e:
            self.log_queue.put(f"❌ Zamanlanmış analiz hatası: {str(e)}")

    def stop_scheduler(self):
        """Zamanlayıcıyı durdurur."""
        self.is_scheduler_running = False
        self.scheduler_button.config(text="⏰ Zamanlayıcıyı Başlat", bg="#27ae60")
        self.scheduler_status.config(text="Zamanlayıcı: Durduruldu", fg="#e74c3c")

        self.log_message("⏹️ Zamanlayıcı durduruldu")

    def on_closing(self):
        """Uygulama kapatılırken çalışır."""
        if self.is_scheduler_running:
            self.stop_scheduler()
        self.root.destroy()


def main():
    """Ana GUI uygulamasını başlatır."""
    root = tk.Tk()
    app = TubitakAnalyzerGUI(root)

    # Kapatma olayını yakala
    root.protocol("WM_DELETE_WINDOW", app.on_closing)

    # GUI'yi başlat
    root.mainloop()


if __name__ == "__main__":
    main()
