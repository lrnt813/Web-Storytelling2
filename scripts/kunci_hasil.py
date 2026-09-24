"""Kunci hasil analisis ke data/locked/ dengan metadata lengkap.

Alur wajib: commit kode → python -m scripts.thesis_analysis --force → python -m scripts.kunci_hasil
→ commit hasil (data/locked/ + output_bab4/).

Penguncian DITOLAK bila:
  * `git status --porcelain` menunjukkan perubahan kode yang belum di-commit
    (di luar berkas hasil: data/thesis_*, data/locked/, output_bab4/, scratch/);
  * analisis dijalankan pada kode yang belum di-commit (meta.git di hasil);
  * berkas pipeline berubah antara commit analisis dan commit saat penguncian.
"""
import dataclasses
import datetime
import importlib.metadata as md
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.thesis_analysis import (GRID_FILE, LOCK_DIR, LOCK_FILE, RESULTS_FILE, file_sha256,
                                     results_fingerprint)

RESULT_PATHS = ("data/thesis_results.json", "data/thesis_grid_results.csv.gz", "data/locked/",
                "output_bab4/", "scratch/")
PIPELINE_FILES = ["backend/engine.py", "backend/thesis.py", "backend/config.py",
                  "scripts/thesis_analysis.py"]
LIBRARIES = ["numpy", "pandas", "scipy", "scikit-learn", "geopandas", "networkx", "libpysal",
             "esda", "shapely", "pyproj", "pyogrio", "spopt", "numba"]


def _git(*args) -> str:
    return subprocess.run(["git", *args], cwd=PROJECT_ROOT, capture_output=True, text=True,
                          check=True).stdout.strip()


def _uncommitted_code() -> list:
    out = []
    for line in _git("status", "--porcelain").splitlines():
        path = line[3:].strip().strip('"')
        if not path.startswith(RESULT_PATHS):
            out.append(line)
    return out


def _thesis_constants() -> dict:
    from backend import thesis as T
    names = ["SKENARIO", "LEVELS", "PCA_VARIANCE", "IQR_FACTOR", "CAPPED_COLUMNS", "VARIANCE_MIN",
             "IINDEX_P", "SDWFCM_N_INIT", "SDWFCM_SEED", "DUNN_SAMPLE", "MORAN_PERMUTATION_SEED",
             "TAS_MIN_EUCLID_M", "TAS_DI_ABSOLUTE", "K_SCORE_METRICS"]
    out = {n: getattr(T, n) for n in names}
    out["K_RANGE"] = list(T.K_RANGE)
    return out


def _cfg_params() -> dict:
    from backend.engine import Cfg
    cfg = Cfg(base_dir="./data")
    d = dataclasses.asdict(cfg)
    d["k_range"] = list(cfg.k_range)
    d["input_file"], d["roads_file"], d["tes_files"] = cfg.input_file, cfg.roads_file, cfg.tes_files
    return d


def lock(data_dir: Path = PROJECT_ROOT / "data") -> dict:
    dirty = _uncommitted_code()
    if dirty:
        raise SystemExit("DITOLAK: ada perubahan kode yang belum di-commit:\n  " + "\n  ".join(dirty))

    results_path = data_dir / RESULTS_FILE
    grid_path = data_dir / GRID_FILE
    results = json.loads(results_path.read_text(encoding="utf-8"))
    git_meta = results.get("meta", {}).get("git") or {}
    if not git_meta.get("commit"):
        raise SystemExit("DITOLAK: hasil tidak memuat commit analisis (meta.git). Jalankan ulang analisis.")
    if git_meta.get("kode_berubah_belum_commit"):
        raise SystemExit("DITOLAK: analisis dijalankan pada kode yang belum di-commit. Commit lalu jalankan ulang.")

    head = _git("rev-parse", "HEAD")
    changed = _git("diff", "--name-only", git_meta["commit"], head, "--", *PIPELINE_FILES)
    if changed:
        raise SystemExit("DITOLAK: berkas pipeline berubah sejak analisis dijalankan:\n  " + changed)

    lock_dir = data_dir / LOCK_DIR
    lock_dir.mkdir(parents=True, exist_ok=True)
    for src in (results_path, grid_path):
        shutil.copy2(src, lock_dir / src.name)

    meta = {
        "keterangan": "Hasil analisis terkunci. Jangan diedit manual. Semua angka skripsi berasal dari "
                      "output_bab4/ yang dibangun dari folder ini (python -m scripts.export_bab4).",
        "locked_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "git": {
            "commit_analisis": git_meta["commit"],
            "branch_analisis": git_meta.get("branch"),
            "commit_saat_kunci": head,
            "branch_saat_kunci": _git("rev-parse", "--abbrev-ref", "HEAD"),
            "berkas_pipeline_sama_dengan_commit_analisis": True,
        },
        "python": {"versi": platform.python_version(), "implementasi": platform.python_implementation(),
                   "platform": platform.platform()},
        "pustaka": {lib: (md.version(lib) if _installed(lib) else None) for lib in LIBRARIES},
        "parameter_cfg": _cfg_params(),
        "konstanta_thesis": _thesis_constants(),
        "seed": {"sdwfcm_seed_awal": _thesis_constants()["SDWFCM_SEED"],
                 "sdwfcm_n_init": _thesis_constants()["SDWFCM_N_INIT"],
                 "sdwfcm_seed_terbaik_per_level": {k: v.get("sdwfcm_seed") for k, v in results["levels"].items()},
                 "moran_permutation_seed": _thesis_constants()["MORAN_PERMUTATION_SEED"],
                 "dunn_sample_seed": 42},
        "k_terpilih": results.get("k"),
        "files": {f: file_sha256(lock_dir / f) for f in (RESULTS_FILE, GRID_FILE)},
        "fingerprint_hasil_tanpa_waktu": results_fingerprint(lock_dir / RESULTS_FILE),
        "catatan_fingerprint": "SHA-256 JSON kanonik thesis_results.json tanpa field waktu dan meta.git; "
                               "dipakai scripts/cek_reproduksi.py.",
    }
    (lock_dir / LOCK_FILE).write_text(json.dumps(meta, ensure_ascii=False, indent=1, default=str),
                                      encoding="utf-8")
    return meta


def _installed(lib: str) -> bool:
    try:
        md.version(lib)
        return True
    except md.PackageNotFoundError:
        return False


if __name__ == "__main__":
    m = lock()
    print("Hasil DIKUNCI:")
    print("  commit analisis :", m["git"]["commit_analisis"])
    print("  K terpilih      :", m["k_terpilih"])
    for f, h in m["files"].items():
        print(f"  {f:28s} {h}")
    print("  fingerprint     :", m["fingerprint_hasil_tanpa_waktu"])
