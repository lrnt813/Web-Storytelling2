"""Cek reproduksi: jalankan ulang analisis ke folder sementara lalu bandingkan dengan LOCK.json.

    python -m scripts.cek_reproduksi            # jalankan ulang penuh (± 2,1 jam)
    python -m scripts.cek_reproduksi --simpan   # sama, folder sementara tidak dihapus

Yang dibandingkan:
  * fingerprint thesis_results.json tanpa field waktu dan meta.git;
  * SHA-256 isi CSV grid dan CSV data gabungan (setelah dekompresi).
Data masukan (*.gpkg) disalin dari data/; folder data/ dan data/locked/ tidak disentuh.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.kunci_hasil import grid_content_sha256
from scripts.thesis_analysis import GRID_FILE, LOCK_DIR, LOCK_FILE, POOLED_FILE, RESULTS_FILE, results_fingerprint


def main(keep: bool = False) -> int:
    data = PROJECT_ROOT / "data"
    lock = json.loads((data / LOCK_DIR / LOCK_FILE).read_text(encoding="utf-8"))
    tmp = Path(tempfile.mkdtemp(prefix="cek_reproduksi_"))
    try:
        for f in list(data.glob("*.gpkg")) + list(data.glob("*.tif")):
            shutil.copy2(f, tmp / f.name)
        env = dict(os.environ, SDWFCM_DATA_DIR=str(tmp))
        print(f"Menjalankan ulang analisis di {tmp} ...", flush=True)
        subprocess.run([sys.executable, "-m", "scripts.thesis_analysis", "--force"],
                       cwd=PROJECT_ROOT, env=env, check=True)
        fp = results_fingerprint(tmp / RESULTS_FILE)
        grid = grid_content_sha256(tmp / GRID_FILE)
        pooled = grid_content_sha256(tmp / POOLED_FILE)
    finally:
        if not keep:
            shutil.rmtree(tmp, ignore_errors=True)

    checks = [("fingerprint thesis_results.json", lock["fingerprint_hasil_tanpa_waktu"], fp),
              ("isi CSV grid", lock.get("sha256_isi_grid_csv"), grid),
              ("isi CSV data gabungan", lock.get("sha256_isi_pooled_csv"), pooled)]
    ok = True
    for name, expected, got in checks:
        same = expected == got
        ok &= same
        print(f"{'SAMA ' if same else 'BEDA '} {name}\n      terkunci : {expected}\n      ulang    : {got}")
    print("REPRODUKSI BERHASIL" if ok else "REPRODUKSI GAGAL — periksa versi Python/pustaka terhadap LOCK.json")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(keep="--simpan" in sys.argv))
