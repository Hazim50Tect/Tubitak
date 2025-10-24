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
        system_state.is_scheduler_running = True
        system_state.scheduler_status = "Çalışıyor"

        def run_scheduler():
            import schedule

            schedule.every().day.at("08:00").do(analyze_active_calls)
            schedule.every().day.at("12:00").do(analyze_active_calls)
            schedule.every().day.at("17:00").do(analyze_active_calls)
            schedule.every().day.at("00:00").do(analyze_active_calls)

            while system_state.is_scheduler_running:
                schedule.run_pending()
                time.sleep(60)

        system_state.scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        system_state.scheduler_thread.start()

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
