import os
import logging
import json
import numpy as np
import geopandas as gpd
import pandas as pd
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.engine import (
    Cfg, load_data, load_road_network, build_weights, 
    run_pipeline
)
from backend.pseudo_safety import compute_ordinal_psi

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger("OfflineAnalysis")

OFFLINE_METADATA_FILE = "offline_cluster_metadata.json"

def run_offline_analysis(data_dir=None):
    logger.info("Memulai Offline Multi-Scenario Transition Analysis...")
    
    # 1. Inisialisasi Config & Data
    DATA_DIR = data_dir or os.environ.get("SDWFCM_DATA_DIR", str(PROJECT_ROOT / "data"))
    cfg = Cfg(base_dir=DATA_DIR)
    
    logger.info(f"Memuat data dari: {cfg.input_file}")
    gdf_base = load_data(cfg)
    roads_raw, tes_raw = load_road_network(cfg)
    
    # Build spatial weights sekali saja untuk efisiensi (asumsi geometri grid statis)
    logger.info("Membangun matriks bobot spasial...")
    w_base = build_weights(gdf_base)
    
    # 2. Definisikan Skenario Intensitas (0% - 100%, 11 steps -> 10 transisi)
    intensities = [round(x * 0.1, 1) for x in range(11)] 
    scenarios = ["banjir", "banjir_bandang", "tanah_longsor"]
    
    # Simpan hasil sementara
    final_results = gdf_base[['id_grid', 'geometry']].copy()
    offline_metadata = {
        "baseline_params": {},
        "cluster_names_by_sk": {},
    }
    
    for sc in scenarios:
        logger.info(f"=== Menganalisis Skenario: {sc.upper()} ===")
        history = []
        
        # 2a. Tentukan K Optimal dari kondisi baseline (0%) dan KUNCI untuk seluruh transisi
        # Hal ini penting agar label klaster (misal 0, 1, 2) memiliki makna yang konsisten antar skenario
        logger.info(f"  Menentukan K Optimal baseline untuk {sc}...")
        try:
            _, _, _, meta_bl = run_pipeline(
                gdf_base, roads_raw, tes_raw, sc, 0.0, cfg, 
                w_override=w_base
            )
            k_locked = meta_bl.get("k", 3)
            offline_metadata["baseline_params"][sc] = {
                "k": meta_bl.get("k"),
                "t_pen": meta_bl.get("t_pen"),
                "pseudo_safety_thresholds": meta_bl.get("pseudo_safety_thresholds", {}),
                "cluster_names": meta_bl.get("cluster_names", {}),
            }
            logger.info(f"  K Optimal dikunci pada: {k_locked}")
        except Exception as e:
            logger.warning(f"  Gagal menentukan K baseline, menggunakan default 3: {e}")
            k_locked = 3

        for i in intensities:
            pct = int(i * 100)
            logger.info(f"  Menjalankan SDWFCM untuk Intensitas {pct}% (K={k_locked})...")
            try:
                sk_key = cfg.sk_key(sc, i)
                gdf_sim, _, _, meta_sim = run_pipeline(
                    gdf_base, roads_raw, tes_raw, sc, i, cfg, 
                    w_override=w_base,
                    k_opt_override=k_locked
                )
                
                labels = gdf_sim['cluster_sdwfcm'].values
                membership = gdf_sim['membership_max'].values
                waktu_min = gdf_sim[f"waktu_tes_min_{sc}"].values
                is_isolated = (
                    gdf_sim["is_isolated"].astype(bool).values
                    if "is_isolated" in gdf_sim.columns
                    else np.zeros(len(gdf_sim), dtype=bool)
                )
                
                history.append(labels)
                
                # Simpan ke cache columns
                final_results[f"cl_sdwfcm_{sc}_{pct}pct"] = labels
                final_results[f"cl_ord_sdwfcm_{sc}_{pct}pct"] = labels
                final_results[f"mem_sdwfcm_{sc}_{pct}pct"] = membership
                final_results[f"waktu_min_{sc}_{pct}pct"] = waktu_min
                final_results[f"iso_{sc}_{pct}pct"] = is_isolated.astype(int)
                for kategori in cfg.kategori_fac:
                    col_time = f"waktu_tes_{kategori}_{sk_key}"
                    if col_time in gdf_sim.columns:
                        final_results[col_time] = gdf_sim[col_time].values
                offline_metadata["cluster_names_by_sk"][sk_key] = meta_sim.get("cluster_names", {})
                
            except Exception as e:
                logger.error(f"  Gagal pada intensitas {i}: {e}")
                if history: history.append(history[-1])
                else: history.append(np.zeros(len(gdf_base)))

        # 3. Hitung Weighted Transition Severity (PSI)
        # Formula: Σ|C_t - C_(t-1)| / ((N_scenario-1)(K-1))
        # history_arr shape: (n_intensities, n_grid)
        logger.info(f"  Menghitung Weighted Transition Severity untuk {sc}...")
        psi_values = compute_ordinal_psi(history, k_locked=k_locked)
        
        col_name = f"PSI_{sc}"
        final_results[col_name] = psi_values
        logger.info(f"  Selesai: {col_name} berhasil dihitung.")

    # 4. Simpan kembali ke GPKG
    logger.info(f"Menyimpan hasil PSI dan Cache ke: {cfg.input_file}")
    
    # Gabungkan semua kolom baru dari final_results ke dataset asli
    new_cols = [c for c in final_results.columns if c not in ["id_grid", "geometry"]]
    for col in new_cols:
        gdf_base[col] = final_results[col]
    
    # Simpan permanen
    gdf_base.to_file(cfg.input_file, driver="GPKG")
    metadata_path = Path(DATA_DIR) / OFFLINE_METADATA_FILE
    metadata_path.write_text(json.dumps(offline_metadata, ensure_ascii=True, indent=2), encoding="utf-8")
    logger.info(f"Metadata klaster offline tersimpan di: {metadata_path}")
    logger.info("Offline Analysis SELESAI. Dataset telah diperbarui dengan kolom PSI.")

if __name__ == "__main__":
    run_offline_analysis()
