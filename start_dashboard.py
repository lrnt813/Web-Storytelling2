import json
import os
import subprocess
import sys
import time
import urllib.request
import webbrowser


def start_dashboard():
    print("=" * 60)
    print("MEMULAI DASHBOARD EVAKUASI BENCANA KULON PROGO")
    print("=" * 60)

    # 0. Jalankan analisis skripsi (Bab IV) jika hasilnya belum ada.
    print("\n[0/3] Memeriksa hasil analisis skripsi...")
    try:
        from scripts.thesis_analysis import GRID_FILE, RESULTS_FILE, run_thesis_analysis

        base_path = os.path.dirname(os.path.abspath(__file__))
        data_path = os.path.join(base_path, "data")
        missing = [f for f in (RESULTS_FILE, GRID_FILE) if not os.path.exists(os.path.join(data_path, f))]
        if missing:
            print(f"[WARN] Hasil analisis belum ada ({', '.join(missing)}).")
            print("   Menjalankan analisis lengkap: 4 level banjir, pemilihan K, perbandingan")
            print("   algoritma, transisi, dan Titik Aman Semu (~10-15 menit)...")
            run_thesis_analysis(data_dir=data_path)
            print("[OK] Analisis selesai.")
        else:
            print("[OK] Hasil analisis tersedia.")
    except Exception as e:
        print(f"[WARN] Peringatan saat menjalankan analisis: {e}")
        print("   Backend akan mencoba menjalankan analisis ringkas saat startup...")

    # 1. Jalankan Backend (Uvicorn).
    print("\n[1/3] Menjalankan server backend (FastAPI)...")
    backend_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8000"],
        creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == "nt" else 0,
    )

    # 2. Tunggu backend siap (polling health check).
    print("[2/3] Menunggu backend siap (warm-up sedang berjalan)...")
    health_url = "http://127.0.0.1:8000/api/health"
    max_retries = 150
    ready = False

    for i in range(max_retries):
        try:
            with urllib.request.urlopen(health_url, timeout=2) as response:
                data = json.loads(response.read().decode())
                if data.get("is_ready"):
                    ready = True
                    break
        except Exception:
            pass

        if i % 5 == 0 and i > 0:
            print(f"      Masih memuat data... ({i * 2} detik)")
        time.sleep(2)

    if not ready:
        print("[WARN] Backend memakan waktu terlalu lama untuk siap. Mencoba membuka dashboard saja...")
    else:
        print("[OK] Backend SIAP!")

    # 3. Buka Frontend di browser via backend port.
    dashboard_url = "http://127.0.0.1:8000/"
    print(f"[3/3] Membuka dashboard: {dashboard_url}")

    try:
        opened = webbrowser.open(dashboard_url)
        if not opened:
            print("[WARN] Gagal membuka browser otomatis. Silakan buka URL di atas secara manual.")
    except Exception as e:
        print(f"[WARN] Terjadi kesalahan saat membuka browser: {e}")
        print(f"Silakan buka secara manual: {dashboard_url}")

    print("\n[OK] Dashboard siap digunakan!")
    print("Backend berjalan di jendela konsol baru. JANGAN TUTUP jendela tersebut.")
    print("Tekan Ctrl+C di jendela ini untuk menghentikan launcher (backend akan tetap berjalan).")

    try:
        backend_process.wait()
    except KeyboardInterrupt:
        print("\nMenutup launcher...")


if __name__ == "__main__":
    start_dashboard()
