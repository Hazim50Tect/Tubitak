#!/usr/bin/env python3
"""
TÜBİTAK Analiz FastAPI Uygulaması
"""

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import threading
import time
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
import asyncio
from scheduler import analyze_active_calls
from main import main as run_full_analysis

# FastAPI uygulaması
app = FastAPI(title="TÜBİTAK Analiz Sistemi", description="TÜBİTAK program analizi ve aktif çağrı takibi", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global durum değişkenleri
class SystemState:
    def __init__(self):
        self.is_scheduler_running = False
        self.is_analysis_running = False
        self.scheduler_thread = None
        self.analysis_thread = None
        self.last_analysis_time = None
        self.last_active_analysis_time = None
        self.analysis_status = "Hazır"
        self.scheduler_status = "Durduruldu"


# Global sistem durumu
system_state = SystemState()

# Zamanlayıcı saatleri - dinamik liste
SCHEDULER_TIMES = ["08:00", "12:00", "17:00", "00:00"]


# Zamanlayıcı başlatma fonksiyonu
def start_scheduler():
    """Zamanlayıcıyı başlatır."""
    system_state.is_scheduler_running = True
    system_state.scheduler_status = "Çalışıyor"

    def run_scheduler():
        import schedule

        while system_state.is_scheduler_running:
            # Her döngüde zamanlayıcıları temizle ve yeniden oluştur
            schedule.clear()

            # Mevcut saatlerle zamanlayıcıları oluştur
            current_times = SCHEDULER_TIMES.copy()
            # print(f"Zamanlayıcı saatleri: {current_times}")

            for time_str in current_times:
                schedule.every().day.at(time_str).do(analyze_active_calls)
                # print(f"Zamanlayıcı eklendi: {time_str}")

            # 60 saniye boyunca zamanlayıcıları kontrol et
            for i in range(60):
                if not system_state.is_scheduler_running:
                    break
                schedule.run_pending()
                time.sleep(1)

    system_state.scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    system_state.scheduler_thread.start()
    print("🚀 Zamanlayıcı başlatıldı")


# Uygulama başladığında zamanlayıcıyı otomatik başlat
start_scheduler()


@app.get("/", response_class=HTMLResponse)
async def get_home():
    """Ana sayfa HTML'ini döndürür."""
    try:
        with open("templates/index.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return HTMLResponse("<h1>HTML dosyası bulunamadı!</h1>", status_code=404)


@app.get("/api/status")
async def get_status():
    """Sistem durumunu döndürür."""
    # Log'u sadece durum değiştiğinde göster
    return {
        "is_analysis_running": system_state.is_analysis_running,
        "is_scheduler_running": system_state.is_scheduler_running,
        "analysis_status": system_state.analysis_status,
        "scheduler_status": system_state.scheduler_status,
        "last_analysis_time": system_state.last_analysis_time,
        "last_active_analysis_time": system_state.last_active_analysis_time,
    }


@app.get("/api/scheduler-times")
async def get_scheduler_times():
    """Zamanlayıcı saatlerini döndürür."""
    return {"times": SCHEDULER_TIMES, "count": len(SCHEDULER_TIMES)}


@app.get("/api/scheduler-debug")
async def get_scheduler_debug():
    """Zamanlayıcı debug bilgilerini döndürür."""
    import schedule

    return {
        "current_times": SCHEDULER_TIMES,
        "is_scheduler_running": system_state.is_scheduler_running,
        "scheduled_jobs": len(schedule.jobs),
        "jobs": [str(job) for job in schedule.jobs],
    }


@app.post("/api/scheduler-times/add")
async def add_scheduler_time(time_str: str):
    """Yeni zamanlayıcı saati ekler."""
    global SCHEDULER_TIMES

    # Saat formatını kontrol et (HH:MM)
    import re

    if not re.match(r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$", time_str):
        raise HTTPException(status_code=400, detail="Geçersiz saat formatı! HH:MM formatında olmalı.")

    if time_str in SCHEDULER_TIMES:
        raise HTTPException(status_code=400, detail="Bu saat zaten mevcut!")

    SCHEDULER_TIMES.append(time_str)
    SCHEDULER_TIMES.sort()  # Saatleri sırala

    return {"message": f"Saat {time_str} eklendi", "times": SCHEDULER_TIMES}


@app.delete("/api/scheduler-times/remove")
async def remove_scheduler_time(time_str: str):
    """Zamanlayıcı saatini kaldırır."""
    global SCHEDULER_TIMES

    if time_str not in SCHEDULER_TIMES:
        raise HTTPException(status_code=404, detail="Bu saat bulunamadı!")

    SCHEDULER_TIMES.remove(time_str)

    return {"message": f"Saat {time_str} kaldırıldı", "times": SCHEDULER_TIMES}


@app.post("/api/start-full-analysis")
async def start_full_analysis(background_tasks: BackgroundTasks):
    """Tüm çağrıları analiz et işlemini başlatır."""
    if system_state.is_analysis_running:
        raise HTTPException(status_code=400, detail="Analiz işlemi zaten devam ediyor!")

    system_state.is_analysis_running = True
    system_state.analysis_status = "Çalışıyor"

    def run_analysis():
        try:
            run_full_analysis()
            system_state.last_analysis_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            print(f"Analiz hatası: {str(e)}")
        finally:
            system_state.is_analysis_running = False
            system_state.analysis_status = "Hazır"

    background_tasks.add_task(run_analysis)

    return {"message": "Tam analiz başlatıldı"}


@app.post("/api/start-active-analysis")
async def start_active_analysis(background_tasks: BackgroundTasks):
    """Aktif çağrıları analiz et işlemini başlatır."""
    if system_state.is_analysis_running:
        raise HTTPException(status_code=400, detail="Analiz işlemi zaten devam ediyor!")

    system_state.is_analysis_running = True
    system_state.analysis_status = "Çalışıyor"

    def run_active_analysis():
        try:
            analyze_active_calls()
            system_state.last_active_analysis_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            print(f"Aktif analiz hatası: {str(e)}")
        finally:
            system_state.is_analysis_running = False
            system_state.analysis_status = "Hazır"

    background_tasks.add_task(run_active_analysis)

    return {"message": "Aktif çağrı analizi başlatıldı"}


@app.post("/api/toggle-scheduler")
async def toggle_scheduler():
    """Zamanlayıcıyı başlatır/durdurur."""
    if system_state.is_scheduler_running:
        # Zamanlayıcıyı durdur
        system_state.is_scheduler_running = False
        system_state.scheduler_status = "Durduruldu"
        if system_state.scheduler_thread:
            system_state.scheduler_thread = None
        return {"message": "Zamanlayıcı durduruldu"}
    else:
        # Zamanlayıcıyı başlat
        start_scheduler()
        return {"message": "Zamanlayıcı başlatıldı"}


@app.post("/api/stop-all")
async def stop_all():
    """Tüm işlemleri durdurur."""
    system_state.is_analysis_running = False
    system_state.is_scheduler_running = False
    system_state.analysis_status = "Hazır"
    system_state.scheduler_status = "Durduruldu"

    if system_state.scheduler_thread:
        system_state.scheduler_thread = None

    return {"message": "Tüm işlemler durduruldu"}


@app.get("/api/results")
async def get_results():
    """Analiz sonuçlarını döndürür."""
    try:
        # Son analiz dosyalarını bul
        html_files = []
        json_files = []

        if os.path.exists("ai_analyse_results_html"):
            for file in os.listdir("ai_analyse_results_html"):
                if file.endswith(".html"):
                    html_files.append(file)

        if os.path.exists("ai_analyse_results_json"):
            for file in os.listdir("ai_analyse_results_json"):
                if file.endswith(".json"):
                    json_files.append(file)

        # Aktif çağrı analiz sonuçları
        active_analysis_files = []
        if os.path.exists("active_calls_analysis_output"):
            for file in os.listdir("active_calls_analysis_output"):
                if file.endswith(".json"):
                    active_analysis_files.append(file)

        return {
            "html_files": sorted(html_files, reverse=True)[:5],  # Son 5 dosya
            "json_files": sorted(json_files, reverse=True)[:5],
            "active_analysis_files": sorted(active_analysis_files, reverse=True)[:5],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sonuçlar alınırken hata: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
