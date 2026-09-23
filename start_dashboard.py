"""Peluncur dashboard.

    python start_dashboard.py            # lokal: http://127.0.0.1:8000
    python start_dashboard.py --publik   # lokal + alamat publik https://….trycloudflare.com
                                         # (Cloudflare Tunnel; aktif selama jendela ini terbuka)
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_PATH, "data")
PORT = 8000
LOCAL_URL = f"http://127.0.0.1:{PORT}/"
CLOUDFLARED = os.path.join(BASE_PATH, "tools", "cloudflared.exe" if os.name == "nt" else "cloudflared")
PUBLIC_URL_FILE = os.path.join(BASE_PATH, "scratch", "alamat_publik.txt")


def ensure_results():
    print("\n[1] Memeriksa hasil analisis skripsi...")
    try:
        from scripts.thesis_analysis import GRID_FILE, RESULTS_FILE, run_thesis_analysis
        missing = [f for f in (RESULTS_FILE, GRID_FILE) if not os.path.exists(os.path.join(DATA_PATH, f))]
        if missing:
            print(f"    Hasil analisis belum ada ({', '.join(missing)}) -> memulihkan/menjalankan analisis...")
            run_thesis_analysis(data_dir=DATA_PATH)
        print("    [OK] Hasil analisis tersedia.")
    except Exception as e:
        print(f"    [PERINGATAN] {e}")


def start_backend(new_console: bool):
    print(f"\n[2] Menjalankan server dashboard (port {PORT})...")
    flags = subprocess.CREATE_NEW_CONSOLE if (os.name == "nt" and new_console) else 0
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", str(PORT)],
        cwd=BASE_PATH, creationflags=flags,
    )
    for i in range(150):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/health", timeout=2) as r:
                if json.loads(r.read().decode()).get("is_ready"):
                    print("    [OK] Server siap.")
                    return proc
        except Exception:
            pass
        if proc.poll() is not None:
            raise SystemExit("    [GAGAL] Server berhenti saat memuat. Periksa pesan error di atas.")
        if i and i % 5 == 0:
            print(f"    Masih memuat data... ({i * 2} detik)")
        time.sleep(2)
    print("    [PERINGATAN] Server lama merespons; melanjutkan.")
    return proc


def ensure_cloudflared():
    """Unduh cloudflared resmi (Windows 64-bit / Linux) dan verifikasi checksum SHA-256."""
    if os.path.exists(CLOUDFLARED):
        return CLOUDFLARED
    asset_name = "cloudflared-windows-amd64.exe" if os.name == "nt" else "cloudflared-linux-amd64"
    print(f"    cloudflared belum ada -> mengunduh {asset_name} dari rilis resmi Cloudflare...")
    req = urllib.request.Request("https://api.github.com/repos/cloudflare/cloudflared/releases/latest",
                                 headers={"User-Agent": "dashboard-tes-banjir"})
    api = json.load(urllib.request.urlopen(req, timeout=30))
    asset = next(a for a in api["assets"] if a["name"] == asset_name)
    m = re.search(re.escape(asset_name) + r":\s*([0-9a-f]{64})", api.get("body", ""))
    expected = m.group(1) if m else (asset.get("digest") or "").replace("sha256:", "")
    data = urllib.request.urlopen(asset["browser_download_url"], timeout=600).read()
    if not expected or hashlib.sha256(data).hexdigest() != expected:
        raise SystemExit("    [GAGAL] Checksum cloudflared tidak cocok; unduhan dibatalkan demi keamanan.")
    os.makedirs(os.path.dirname(CLOUDFLARED), exist_ok=True)
    with open(CLOUDFLARED, "wb") as fh:
        fh.write(data)
    if os.name != "nt":
        os.chmod(CLOUDFLARED, 0o755)
    print(f"    [OK] cloudflared {api['tag_name']} terpasang (checksum terverifikasi).")
    return CLOUDFLARED


def start_tunnel():
    print("\n[3] Membuka alamat publik (Cloudflare Tunnel)...")
    exe = ensure_cloudflared()
    proc = subprocess.Popen(
        [exe, "tunnel", "--url", f"http://127.0.0.1:{PORT}", "--no-autoupdate"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
    )
    found = {}
    pattern = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")

    def reader():
        for line in proc.stdout:
            if "url" not in found:
                m = pattern.search(line)
                if m:
                    found["url"] = m.group(0)
            if "ERR" in line and "url" in found:
                print("    [tunnel]", line.strip()[:160])

    threading.Thread(target=reader, daemon=True).start()
    for _ in range(90):
        if "url" in found or proc.poll() is not None:
            break
        time.sleep(1)
    if "url" not in found:
        raise SystemExit("    [GAGAL] Alamat publik tidak diperoleh. Periksa koneksi internet lalu coba lagi.")
    # tunggu sampai alamat benar-benar dapat diakses dari internet
    for _ in range(30):
        try:
            with urllib.request.urlopen(found["url"] + "/api/health", timeout=5) as r:
                if r.status == 200:
                    break
        except Exception:
            time.sleep(2)
    return proc, found["url"]


def main():
    publik = "--publik" in sys.argv or "--public" in sys.argv
    print("=" * 64)
    print("  DASHBOARD AKSESIBILITAS TES BANJIR - KULON PROGO" + ("  [MODE PUBLIK]" if publik else ""))
    print("=" * 64)
    ensure_results()
    backend = start_backend(new_console=not publik)
    tunnel, url = None, LOCAL_URL
    try:
        if publik:
            tunnel, url = start_tunnel()
            os.makedirs(os.path.dirname(PUBLIC_URL_FILE), exist_ok=True)
            with open(PUBLIC_URL_FILE, "w", encoding="utf-8") as fh:
                fh.write(url + "\n")
            print("\n" + "=" * 64)
            print("  ALAMAT PUBLIK (bagikan tautan ini):")
            print(f"\n      {url}\n")
            print(f"  Lokal : {LOCAL_URL}")
            print("  Alamat publik berubah setiap kali dijalankan ulang.")
            print("  Dashboard hanya dapat diakses selama jendela ini terbuka")
            print("  dan laptop tidak dalam mode tidur (sleep).")
            print("  Tekan Ctrl+C untuk menghentikan server & alamat publik.")
            print("=" * 64)
        else:
            print(f"\n[OK] Dashboard: {url}")
            print("Server berjalan di jendela konsol baru. JANGAN TUTUP jendela tersebut.")
        if not os.environ.get("DASHBOARD_NO_BROWSER"):
            webbrowser.open(url)
        (tunnel or backend).wait()
    except KeyboardInterrupt:
        print("\nMenghentikan...")
    finally:
        if publik:
            for p in (tunnel, backend):
                if p and p.poll() is None:
                    p.terminate()
            print("Server dan alamat publik dihentikan.")


if __name__ == "__main__":
    main()
