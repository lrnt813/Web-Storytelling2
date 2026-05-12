import os
import logging
import numpy as np
import geopandas as gpd
import pandas as pd
from pathlib import Path
from engine import (
    Cfg, load_data, load_road_network, build_weights, 
    run_pipeline
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger("OfflineAnalysis")

def run_offline_analysis(data_dir=None):
    logger.info("Memulai Offline Multi-Scenario Transition Analysis...")
    
    # 1. Inisialisasi Config & Data
    BASE_DIR = Path(__file__).parent.resolve()
    DATA_DIR = data_dir or os.environ.get("SDWFCM_DATA_DIR", str(BASE_DIR / "data"))
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
            logger.info(f"  K Optimal dikunci pada: {k_locked}")
        except Exception as e:
            logger.warning(f"  Gagal menentukan K baseline, menggunakan default 3: {e}")
            k_locked = 3

        for i in intensities:
            pct = int(i * 100)
            logger.info(f"  Menjalankan SDWFCM untuk Intensitas {pct}% (K={k_locked})...")
            try:
                gdf_sim, _, _, _ = run_pipeline(
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
                final_results[f"mem_sdwfcm_{sc}_{pct}pct"] = membership
                final_results[f"waktu_min_{sc}_{pct}pct"] = waktu_min
                final_results[f"iso_{sc}_{pct}pct"] = is_isolated.astype(int)
                
            except Exception as e:
                logger.error(f"  Gagal pada intensitas {i}: {e}")
                if history: history.append(history[-1])
                else: history.append(np.zeros(len(gdf_base)))

        # 3. Hitung Weighted Transition Severity (PSI)
        # Formula: Σ|C_t - C_(t-1)| / ((N_scenario-1)(K-1))
        # history_arr shape: (n_intensities, n_grid)
        history_arr = np.array(history)
        
        logger.info(f"  Menghitung Weighted Transition Severity untuk {sc}...")
        
        # Hitung selisih absolut antar step berurutan
        diffs = np.abs(np.diff(history_arr, axis=0)) # Shape: (10, n_grid)
        sum_diffs = np.sum(diffs, axis=0)
        
        # Tentukan K (jumlah klaster unik dalam skenario ini)
        unique_clusters = np.unique(history_arr)
        K = len(unique_clusters)
        if K < 2: K = 2 # Failsafe
        
        total_transitions = len(intensities) - 1
        denominator = total_transitions * (K - 1)
        psi_values = sum_diffs / denominator
        
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
    logger.info("Offline Analysis SELESAI. Dataset telah diperbarui dengan kolom PSI.")

if __name__ == "__main__":
    run_offline_analysis()
