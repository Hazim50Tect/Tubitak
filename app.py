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
    return """
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>TÜBİTAK Analiz Sistemi</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                border-radius: 15px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                overflow: hidden;
            }
            
            .header {
                background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
                color: white;
                padding: 30px;
                text-align: center;
            }
            
            .header h1 {
                font-size: 2.5rem;
                margin-bottom: 10px;
            }
            
            .header p {
                font-size: 1.1rem;
                opacity: 0.9;
            }
            
            .main-content {
                padding: 40px;
            }
            
            .control-panel {
                background: #f8f9fa;
                border-radius: 10px;
                padding: 30px;
                margin-bottom: 30px;
            }
            
            .control-panel h2 {
                color: #2c3e50;
                margin-bottom: 20px;
                font-size: 1.5rem;
            }
            
            .button-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            
            .btn {
                background: linear-gradient(135deg, #3498db 0%, #2980b9 100%);
                color: white;
                border: none;
                padding: 15px 25px;
                border-radius: 8px;
                font-size: 1.1rem;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
                text-decoration: none;
                display: inline-block;
                text-align: center;
            }
            
            .btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 10px 20px rgba(52, 152, 219, 0.3);
            }
            
            .btn:disabled {
                background: #bdc3c7;
                cursor: not-allowed;
                transform: none;
                box-shadow: none;
            }
            
            .btn-success {
                background: linear-gradient(135deg, #27ae60 0%, #229954 100%);
            }
            
            .btn-warning {
                background: linear-gradient(135deg, #e67e22 0%, #d35400 100%);
            }
            
            .btn-danger {
                background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
            }
            
            .status-panel {
                background: #ecf0f1;
                border-radius: 10px;
                padding: 25px;
                margin-bottom: 30px;
            }
            
            .status-panel h3 {
                color: #2c3e50;
                margin-bottom: 15px;
                font-size: 1.3rem;
            }
            
            .status-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
            }
            
            .status-item {
                background: white;
                padding: 15px;
                border-radius: 8px;
                border-left: 4px solid #3498db;
            }
            
            .status-item h4 {
                color: #2c3e50;
                margin-bottom: 5px;
            }
            
            .status-item p {
                color: #7f8c8d;
                font-size: 0.9rem;
            }
            
            .status-running {
                border-left-color: #27ae60;
            }
            
            .status-stopped {
                border-left-color: #e74c3c;
            }
            
            .results-panel {
                background: #f8f9fa;
                border-radius: 10px;
                padding: 25px;
                margin-top: 20px;
            }
            
            .results-panel h3 {
                color: #2c3e50;
                margin-bottom: 15px;
            }
            
            .result-item {
                background: white;
                padding: 15px;
                border-radius: 8px;
                margin-bottom: 10px;
                border-left: 4px solid #3498db;
            }
            
            .loading {
                display: none;
                text-align: center;
                padding: 20px;
            }
            
            .spinner {
                border: 4px solid #f3f3f3;
                border-top: 4px solid #3498db;
                border-radius: 50%;
                width: 40px;
                height: 40px;
                animation: spin 1s linear infinite;
                margin: 0 auto 10px;
            }
            
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            
            .alert {
                padding: 15px;
                border-radius: 8px;
                margin-bottom: 20px;
                display: none;
            }
            
            .alert-success {
                background: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
            }
            
            .alert-error {
                background: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚀 TÜBİTAK Analiz Sistemi</h1>
                <p>Program analizi ve aktif çağrı takibi</p>
            </div>
            
            <div class="main-content">
                <div class="control-panel">
                    <h2>🎛️ Kontrol Paneli</h2>
                    <div class="button-grid">
                        <button class="btn" onclick="startFullAnalysis()" id="fullAnalysisBtn">
                            🔍 Tüm Çağrıları Analiz Et
                        </button>
                        <button class="btn btn-warning" onclick="startActiveAnalysis()" id="activeAnalysisBtn">
                            📊 Aktif Çağrıları Analiz Et
                        </button>
                        <button class="btn btn-success" onclick="toggleScheduler()" id="schedulerBtn">
                            ⏰ Zamanlayıcıyı Başlat
                        </button>
                        <button class="btn btn-danger" onclick="stopAll()" id="stopBtn">
                            ⏹️ Tüm İşlemleri Durdur
                        </button>
                    </div>
                </div>
                
                <div class="status-panel">
                    <h3>📊 Sistem Durumu</h3>
                    <div class="status-grid">
                        <div class="status-item" id="analysisStatus">
                            <h4>Analiz Durumu</h4>
                            <p id="analysisStatusText">Hazır</p>
                        </div>
                        <div class="status-item" id="schedulerStatus">
                            <h4>Zamanlayıcı Durumu</h4>
                            <p id="schedulerStatusText">Durduruldu</p>
                        </div>
                        <div class="status-item">
                            <h4>Son Analiz</h4>
                            <p id="lastAnalysisTime">Henüz analiz yapılmadı</p>
                        </div>
                        <div class="status-item">
                            <h4>Zamanlanmış Saatler</h4>
                            <p>08:00, 12:00, 17:00, 00:00</p>
                        </div>
                    </div>
                </div>
                
                <div class="loading" id="loading">
                    <div class="spinner"></div>
                    <p>İşlem devam ediyor...</p>
                </div>
                
                <div class="alert" id="alert"></div>
                
                <div class="results-panel" id="resultsPanel" style="display: none;">
                    <h3>📈 Sonuçlar</h3>
                    <div id="resultsContent"></div>
                </div>
            </div>
        </div>
        
        <script>
            let isSchedulerRunning = false;
            
            // Sayfa yüklendiğinde durumu kontrol et
            window.onload = function() {
                updateStatus();
                setInterval(updateStatus, 5000); // Her 5 saniyede durumu güncelle
            };
            
            async function updateStatus() {
                try {
                    const response = await fetch('/api/status');
                    const data = await response.json();
                    
                    document.getElementById('analysisStatusText').textContent = data.analysis_status;
                    document.getElementById('schedulerStatusText').textContent = data.scheduler_status;
                    document.getElementById('lastAnalysisTime').textContent = data.last_analysis_time || 'Henüz analiz yapılmadı';
                    
                    // Buton durumlarını güncelle
                    const fullBtn = document.getElementById('fullAnalysisBtn');
                    const activeBtn = document.getElementById('activeAnalysisBtn');
                    const schedulerBtn = document.getElementById('schedulerBtn');
                    
                    fullBtn.disabled = data.is_analysis_running;
                    activeBtn.disabled = data.is_analysis_running;
                    
                    if (data.is_analysis_running) {
                        fullBtn.textContent = '⏳ Analiz Ediliyor...';
                        activeBtn.textContent = '⏳ Analiz Ediliyor...';
                    } else {
                        fullBtn.textContent = '🔍 Tüm Çağrıları Analiz Et';
                        activeBtn.textContent = '📊 Aktif Çağrıları Analiz Et';
                    }
                    
                    if (data.is_scheduler_running) {
                        schedulerBtn.textContent = '⏹️ Zamanlayıcıyı Durdur';
                        schedulerBtn.className = 'btn btn-danger';
                    } else {
                        schedulerBtn.textContent = '⏰ Zamanlayıcıyı Başlat';
                        schedulerBtn.className = 'btn btn-success';
                    }
                    
                } catch (error) {
                    console.error('Durum güncellenirken hata:', error);
                }
            }
            
            async function startFullAnalysis() {
                showLoading();
                try {
                    const response = await fetch('/api/start-full-analysis', { method: 'POST' });
                    const data = await response.json();
                    
                    if (response.ok) {
                        showAlert('Analiz başlatıldı!', 'success');
                    } else {
                        showAlert('Hata: ' + data.detail, 'error');
                    }
                } catch (error) {
                    showAlert('Hata: ' + error.message, 'error');
                } finally {
                    hideLoading();
                }
            }
            
            async function startActiveAnalysis() {
                showLoading();
                try {
                    const response = await fetch('/api/start-active-analysis', { method: 'POST' });
                    const data = await response.json();
                    
                    if (response.ok) {
                        showAlert('Aktif çağrı analizi başlatıldı!', 'success');
                    } else {
                        showAlert('Hata: ' + data.detail, 'error');
                    }
                } catch (error) {
                    showAlert('Hata: ' + error.message, 'error');
                } finally {
                    hideLoading();
                }
            }
            
            async function toggleScheduler() {
                try {
                    const response = await fetch('/api/toggle-scheduler', { method: 'POST' });
                    const data = await response.json();
                    
                    if (response.ok) {
                        showAlert(data.message, 'success');
                    } else {
                        showAlert('Hata: ' + data.detail, 'error');
                    }
                } catch (error) {
                    showAlert('Hata: ' + error.message, 'error');
                }
            }
            
            async function stopAll() {
                try {
                    const response = await fetch('/api/stop-all', { method: 'POST' });
                    const data = await response.json();
                    
                    if (response.ok) {
                        showAlert(data.message, 'success');
                    } else {
                        showAlert('Hata: ' + data.detail, 'error');
                    }
                } catch (error) {
                    showAlert('Hata: ' + error.message, 'error');
                }
            }
            
            function showLoading() {
                document.getElementById('loading').style.display = 'block';
            }
            
            function hideLoading() {
                document.getElementById('loading').style.display = 'none';
            }
            
            function showAlert(message, type) {
                const alert = document.getElementById('alert');
                alert.textContent = message;
                alert.className = `alert alert-${type}`;
                alert.style.display = 'block';
                
                setTimeout(() => {
                    alert.style.display = 'none';
                }, 5000);
            }
        </script>
    </body>
    </html>
    """


@app.get("/api/status")
async def get_status():
    """Sistem durumunu döndürür."""
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
