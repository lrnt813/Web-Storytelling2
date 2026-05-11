import subprocess
import time
import webbrowser
import os
import sys

def start_dashboard():
    print("="*60)
    print("🚀 MEMULAI DASHBOARD EVAKUASI BENCANA KULON PROGO 🚀")
    print("="*60)
    
    # 1. Jalankan Backend (Uvicorn)
    print("\n[1/3] Menjalankan server backend (FastAPI)...")
    backend_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"],
        creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
    )
    
    # 2. Tunggu backend siap (Polling Health Check)
    print("[2/3] Menunggu backend siap (Warm-up sedang berjalan)...")
    health_url = "http://127.0.0.1:8000/api/health"
    max_retries = 30  # Tunggu maksimal 60 detik
    ready = False
    
    import urllib.request
    import json
    
    for i in range(max_retries):
        try:
            with urllib.request.urlopen(health_url) as response:
                data = json.loads(response.read().decode())
                if data.get("is_ready"):
                    ready = True
                    break
        except:
            pass
        
        if i % 5 == 0 and i > 0:
            print(f"      Masih memuat data... ({i*2} detik)")
        time.sleep(2)
    
    if not ready:
        print("⚠️ Backend memakan waktu terlalu lama untuk siap. Mencoba membuka dashboard saja...")
    else:
        print("✅ Backend SIAP!")
    
    # 3. Buka Frontend di Browser via Backend Port
    dashboard_url = "http://127.0.0.1:8000/"
    print(f"[3/3] Membuka dashboard: {dashboard_url}")
    
    try:
        opened = webbrowser.open(dashboard_url)
        if not opened:
            print("⚠️ Gagal membuka browser otomatis. Silakan buka URL di atas secara manual.")
    except Exception as e:
        print(f"⚠️ Terjadi kesalahan saat membuka browser: {e}")
        print(f"Silakan buka secara manual: {dashboard_url}")
    
    print("\n✅ Dashboard siap digunakan!")
    print("Backend berjalan di jendela konsol baru. JANGAN TUTUP jendela tersebut.")
    print("Tekan Ctrl+C di jendela ini untuk menghentikan launcher (backend akan tetap berjalan).")
    
    try:
        backend_process.wait()
    except KeyboardInterrupt:
        print("\nMenutup launcher...")

if __name__ == "__main__":
    start_dashboard()
