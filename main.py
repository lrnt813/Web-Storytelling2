# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  main.py — FastAPI Application  (v2 — Payload-Optimized)                   ║
# ║  Tipologi Kerawanan Evakuasi & Deteksi Titik Aman Semu, Kulon Progo        ║
# ║                                                                             ║
# ║  ARSITEKTUR v2 ("Aturan Emas Web GIS"):                                     ║
# ║  * Geometri statis dimuat SATU KALI oleh frontend dari GeoJSON file         ║
# ║  * API hanya mengembalikan array JSON ringan (id_grid + atribut)            ║
# ║  * Frontend JOIN: geom[id_grid] <-> atribut[id_grid]                       ║
# ║                                                                             ║
# ║  PERUBAHAN dari v1:                                                         ║
# ║  x  _gdf_to_geojson()  DIHAPUS — tidak ada lagi GeoJSON multi-MB           ║
# ║  v  _gdf_to_data_klaster() BARU — array JSON ringan tanpa geometri         ║
# ║  v  /api/baseline  -> field "data_klaster" (bukan "geojson")               ║
# ║  v  /api/simulate  -> field "data_klaster" (bukan "geojson")               ║
# ║  v  Startup WARNING sangat mencolok jika Pandana tidak aktif               ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

# ══════════════════════════════════════════════════════════════════════════════
# 1. IMPORTS
# ══════════════════════════════════════════════════════════════════════════════
import asyncio
import math
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import geopandas as gpd
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from pyproj import Transformer

from engine import (
    Cfg, PANDANA_OK,
    apply_road_cuts_to_graph, build_road_graph,
    build_weights, compute_distances, calc_t_max,
    detect_titik_aman_semu, filter_tes, load_data, load_road_network,
    preprocess, route_to_nearest_tes, run_all_clustering, run_pipeline,
    simulate_hazard, SpatialDistanceWeightedFCM,
)

# ══════════════════════════════════════════════════════════════════════════════
# 2. LOGGING SETUP
# ══════════════════════════════════════════════════════════════════════════════
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════════
# 3. KONFIGURASI
# ══════════════════════════════════════════════════════════════════════════════
# Tentukan direktori dasar (lokasi file main.py ini berada)
BASE_DIR = Path(__file__).parent.resolve()

DATA_DIR = os.environ.get("SDWFCM_DATA_DIR", str(BASE_DIR / "data"))
cfg = Cfg(base_dir=DATA_DIR)

# ══════════════════════════════════════════════════════════════════════════════
# 4. GLOBAL APP STATE
# ══════════════════════════════════════════════════════════════════════════════
class AppState:
    gdf_base:   Optional[gpd.GeoDataFrame] = None
    roads_raw:  Optional[gpd.GeoDataFrame] = None
    tes_raw:    Dict[str, gpd.GeoDataFrame] = {}
    w_baseline     = None
    nx_graph_base  = None
    nx_node_list   = None
    nx_kdtree      = None
    is_ready:      bool = False
    startup_error: Optional[str] = None
    
    # Caching Graph untuk responsivitas routing
    # {(skenario, intensity, frozenset(cut_roads)): (G, tn, nl)}
    graph_cache: Dict[tuple, tuple] = {}
    
    # Ranks cluster berdasarkan kualitas (0=terburuk, 1=terbaik)
    # {skenario: {cluster_id: score}}
    cluster_ranks: Dict[str, Dict[int, float]] = {}
    
    # Caching untuk akselerasi
    baseline_params: Dict[str, dict] = {}
    baseline_cache:  Dict[str, dict] = {} # Menyimpan {skenario: {data_klaster, k, t_pen, eval}}
    
    # NEW: Baseline Accessibility Cache (Waktu tempuh 0% intensitas)
    # {skenario: array_of_times_min_per_grid}
    baseline_times:  Dict[str, np.ndarray] = {}

    # Kunci antrian komputasi
    compute_lock: Optional[asyncio.Lock] = None

state = AppState()


def _has_offline_cluster_cache(gdf: gpd.GeoDataFrame) -> bool:
    """True jika GPKG sudah berisi cache SDWFCM untuk semua skenario/intensitas UI."""
    required = []
    for skenario in cfg.skenario_list:
        required.append(f"PSI_{skenario}")
        for pct in range(0, 101, 10):
            required.extend([
                f"cl_sdwfcm_{skenario}_{pct}pct",
                f"mem_sdwfcm_{skenario}_{pct}pct",
                f"waktu_min_{skenario}_{pct}pct",
            ])
    missing = [c for c in required if c not in gdf.columns]
    if missing:
        logger.info(f"[startup] Offline cache belum lengkap. Contoh kolom hilang: {missing[:6]}")
        return False
    return True

# ══════════════════════════════════════════════════════════════════════════════
# 5. FASTAPI APP
# ══════════════════════════════════════════════════════════════════════════════
app = FastAPI(
    title="Tipologi Kerawanan Evakuasi API",
    description=(
        "REST API untuk Web Storytelling Interaktif: Tipologi Kerawanan Evakuasi "
        "& Deteksi Titik Aman Semu, Kulon Progo. "
        "v2: Arsitektur 'Aturan Emas Web GIS' — API hanya kirim id_grid + atribut."
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ══════════════════════════════════════════════════════════════════════════════
# 5.5 STATIC FILES & REDIRECT
# ══════════════════════════════════════════════════════════════════════════════
# Gunakan path absolut untuk mounting agar terhindar dari 404 jika CWD berbeda
FRONTEND_DIR = BASE_DIR / "frontend"
STATIC_DIR   = BASE_DIR / "static"

if FRONTEND_DIR.exists():
    app.mount("/frontend", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend")
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/", include_in_schema=False)
async def root_redirect():
    """Otomatis arahkan user ke halaman dashboard."""
    # Selalu arahkan ke path absolut relatif terhadap domain
    return RedirectResponse(url="/frontend/index.html")

# ══════════════════════════════════════════════════════════════════════════════
# 6. STARTUP EVENT
# ══════════════════════════════════════════════════════════════════════════════
@app.on_event("startup")
async def startup_event():
    t0 = time.time()
    logger.info("=" * 70)
    logger.info("STARTUP v2 — Memuat data, membangun network...")
    logger.info(f"DATA_DIR = {DATA_DIR}")
    logger.info("Arsitektur v2: endpoint kirim data_klaster (tanpa geometri).")
    logger.info("=" * 70)

    state.compute_lock = asyncio.Lock()

    try:
        # Step 1: Load grid
        logger.info("[startup] Step 1/4: Load grid Kulon Progo...")
        state.gdf_base = load_data(cfg)
        logger.info(f"[startup] OK Grid: {len(state.gdf_base)} baris | id_grid: 0..{len(state.gdf_base)-1}")
        offline_cache_ready = _has_offline_cluster_cache(state.gdf_base)
        if offline_cache_ready:
            logger.info("[startup] Offline SDWFCM cache lengkap -> mode startup cepat aktif.")

        # Step 2: Load jalan & TES
        logger.info("[startup] Step 2/4: Load jalan & TES...")
        state.roads_raw, state.tes_raw = load_road_network(cfg)
        logger.info(
            f"[startup] OK Jalan: {len(state.roads_raw) if state.roads_raw is not None else 0} segmen | "
            f"TES: {sum(len(v) for v in state.tes_raw.values())} titik"
        )

        if offline_cache_ready:
            logger.info("[startup] Step 3/4: Lewati Spatial Weight Matrix (pakai offline cache).")
        else:
            # Step 3: Spatial weights
            logger.info("[startup] Step 3/4: Bangun Spatial Weight Matrix baseline...")
            state.w_baseline = build_weights(state.gdf_base)
            logger.info(f"[startup] OK Spatial weight: N={state.w_baseline.n} | avg_nb={state.w_baseline.mean_neighbors:.2f}")

        # Step 4: Routing network
        if offline_cache_ready:
            logger.info("[startup] Step 4/4: Lewati Routing Network awal (lazy-build saat routing).")
        elif state.roads_raw is not None:
            logger.info("[startup] Step 4/4: Bangun Routing Network (Optimized NetworkX)...")
            (state.nx_graph_base,
             state.nx_node_list,
             state.nx_kdtree) = build_road_graph(state.roads_raw, "banjir", 0.0, cfg)
            logger.info(
                f"[startup] OK NetworkX Optimized: "
                f"{len(state.nx_graph_base.nodes())} node | "
                f"{len(state.nx_graph_base.edges())} edge"
            )
        else:
            logger.warning("[startup] Tidak ada data jalan → routing tidak tersedia")

        # Step 5: Warm-up Baseline (Parallelized)
        logger.info("[startup] Step 5/5: Warm-up Baseline (Parallelized)...")
        
        async def _warmup(sk):
            # OPTIMASI: Cek apakah baseline (0%) sudah ada di cache GPKG
            col_cache = f"waktu_min_{sk}_0pct"
            if col_cache in state.gdf_base.columns:
                logger.info(f"[startup] Baseline {sk} ditemukan di GPKG Cache. Memuat...")
                state.baseline_times[sk] = state.gdf_base[col_cache].values
                # Kita tetap jalankan run_pipeline sekali untuk populate baseline_cache (t_pen, k, dll)
                # Tapi ini akan cepat karena CACHE HIT di engine.run_pipeline
            
            logger.info(f"[startup] Warm-up Baseline {sk}...")
            res = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: run_pipeline(
                    gdf_base=state.gdf_base,
                    roads_raw=state.roads_raw,
                    tes_raw=state.tes_raw,
                    skenario=sk,
                    intensity=0.0,
                    cfg=cfg,
                    k_opt_override=None,
                    t_pen_override=None,
                    cut_roads=None,
                    G_override=state.nx_graph_base,
                    nl_override=state.nx_node_list,
                    tn_override=state.nx_kdtree,
                    w_override=state.w_baseline,
                    baseline_times_override=None, # Baseline tidak butuh baseline_override
                    psi_array_override=state.gdf_base[f"PSI_{sk}"].values if f"PSI_{sk}" in state.gdf_base.columns else None
                )
            )
            gdf_res, cl_res, eval_res, metadata = res
            
            # Simpan baseline times jika belum ada (jika tadi tidak hit GPKG cache secara eksplisit di sini)
            if sk not in state.baseline_times:
                col_time = f"waktu_tes_min_{sk}"
                if col_time in gdf_res.columns:
                    state.baseline_times[sk] = gdf_res[col_time].values

            data_klaster = _gdf_to_data_klaster(gdf_res, sk, "banjir")
            
            state.baseline_params[sk] = metadata
            state.baseline_cache[sk] = {
                "status": "ok",
                "arsitektur": "v2",
                "skenario": sk,
                "intensity": 0.0,
                "elapsed_sec": 0.0,
                "evaluation": _eval_df_to_list(eval_res),
                "n_grid": len(gdf_res),
                "n_titik_semu": int(gdf_res["titik_aman_semu"].sum()) if "titik_aman_semu" in gdf_res.columns else 0,
                "data_klaster": data_klaster,
                "k_optimal": _sanitize(metadata.get("k", 3)),
                "t_pen": _sanitize(metadata.get("t_pen", 200.0)),
            }
            # Hitung rank cluster untuk rekomendasi
            # Cluster dengan rata-rata waktu_tes_min rendah = rank tinggi
            df_klaster = pd.DataFrame(data_klaster)
            t_col = f"waktu_tes_min_{sk}" # sk di sini adalah sk_key dari loop gather
            if "cluster_sdwfcm" in df_klaster.columns and t_col in df_klaster.columns:
                avg_t = df_klaster.groupby("cluster_sdwfcm")[t_col].mean()
                # Score 0..1 (1 = paling cepat/aman)
                if not avg_t.empty:
                    t_min, t_max = avg_t.min(), avg_t.max()
                    denom = (t_max - t_min) if t_max > t_min else 1.0
                    ranks = {int(c): float(1.0 - (v - t_min) / denom) for c, v in avg_t.items()}
                    state.cluster_ranks[sk.split("_")[0]] = ranks
            
            logger.info(f"[startup] Baseline {sk} tersimpan: k={metadata.get('k', '?')}")

        await asyncio.gather(*[_warmup(sk) for sk in ["banjir", "banjir_bandang", "tanah_longsor"]])

        elapsed = time.time() - t0
        state.is_ready = True
        logger.info("=" * 70)
        logger.info(f"STARTUP SELESAI dalam {elapsed:.1f} detik")
        logger.info("Arsitektur v2: /api/baseline & /api/simulate -> data_klaster (bukan geojson)")
        logger.info("=" * 70)

    except Exception as e:
        state.startup_error = str(e)
        logger.error(f"STARTUP GAGAL: {e}", exc_info=True)


# ══════════════════════════════════════════════════════════════════════════════
# 7. PYDANTIC MODELS
# ══════════════════════════════════════════════════════════════════════════════
class RoadCutItem(BaseModel):
    lat:       Optional[float]       = Field(None, description="Latitude WGS84")
    lng:       Optional[float]       = Field(None, description="Longitude WGS84")
    x:         Optional[float]       = Field(None, description="Koordinat X EPSG:32749")
    y:         Optional[float]       = Field(None, description="Koordinat Y EPSG:32749")
    edge_from: Optional[List[float]] = Field(None, description="[x,y] node asal edge")
    edge_to:   Optional[List[float]] = Field(None, description="[x,y] node tujuan edge")


class SimulateRequest(BaseModel):
    skenario:  str               = Field(..., description="banjir | banjir_bandang | tanah_longsor")
    intensity: float             = Field(..., ge=0.0, le=1.0)
    cut_roads: List[RoadCutItem] = Field(default_factory=list)


class RouteRequest(BaseModel):
    lat:       float = Field(..., description="Latitude asal (WGS84)")
    lng:       float = Field(..., description="Longitude asal (WGS84)")
    skenario:  str   = Field("banjir")
    intensity: float = Field(0.0, ge=0.0, le=1.0)


class RouteAllTesRequest(BaseModel):
    lat:       float             = Field(..., description="Latitude asal (WGS84)")
    lng:       float             = Field(..., description="Longitude asal (WGS84)")
    skenario:  str               = Field("banjir")
    intensity: float             = Field(0.0, ge=0.0, le=1.0)
    cut_roads: List[RoadCutItem] = Field(
        default_factory=list,
        description="Daftar titik jalan yang diputus oleh user (opsional)"
    )


# ══════════════════════════════════════════════════════════════════════════════
# 8. HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def _check_ready():
    if not state.is_ready:
        msg = state.startup_error or "Server sedang memuat data, coba lagi sebentar."
        raise HTTPException(status_code=503, detail=f"Service tidak tersedia: {msg}")


def _validate_skenario(skenario: str):
    if skenario not in cfg.skenario_list:
        raise HTTPException(
            status_code=422,
            detail=f"Skenario '{skenario}' tidak valid. Pilihan: {cfg.skenario_list}",
        )


def _sanitize(val: Any) -> Any:
    """Konversi numpy types & NaN/Inf ke Python native / None secara rekursif."""
    if val is None:
        return None
    
    # Handle numpy scalars / arrays
    if hasattr(val, "item") and not isinstance(val, (np.ndarray, list, dict, str)):
        try:
            val = val.item()
        except:
            pass

    if isinstance(val, (np.integer, int)):
        return int(val)
    if isinstance(val, (np.floating, float)):
        v = float(val)
        return None if (math.isnan(v) or math.isinf(v)) else round(v, 6)
    if isinstance(val, (np.bool_, bool)):
        return bool(val)
    
    # Rekursi untuk list/dict agar semua level tersanitasi
    if isinstance(val, dict):
        return {k: _sanitize(v) for k, v in val.items()}
    if isinstance(val, (list, tuple, np.ndarray)):
        return [_sanitize(x) for x in val]
    
    return val


_wgs84_to_utm = Transformer.from_crs("EPSG:4326", cfg.target_crs, always_xy=True)
_utm_to_wgs84 = Transformer.from_crs(cfg.target_crs, "EPSG:4326", always_xy=True)


def _latlon_to_projected(lat: float, lng: float):
    x, y = _wgs84_to_utm.transform(lng, lat)
    return x, y


def _snap(G, tn, nl, xy, max_snap: float = 300):
    """
    Snap titik [x, y] ke node terdekat di graph G menggunakan KDTree tn.
    - G: NetworkX graph
    - tn: scipy.spatial.KDTree dari koordinat node
    - nl: List of node IDs sesuai urutan KDTree
    - xy: [x, y] yang akan di-snap
    - max_snap: Jarak maksimum (meter) untuk snapping
    """
    if G is None or tn is None or nl is None:
        return None
    try:
        dist, idx = tn.query(xy)
        if dist > max_snap:
            return None
        # WAJIB: Konversi ke tuple agar hashable (NetworkX requirement)
        # Sesuai format di build_road_graph: (round(x, 2), round(y, 2))
        node = nl[idx]
        return (round(float(node[0]), 2), round(float(node[1]), 2))
    except:
        return None


# ── TUGAS 3: _gdf_to_geojson() DIHAPUS TOTAL ─────────────────────────────────
# Endpoint TIDAK BOLEH lagi mengkonversi GDF → GeoJSON feature collection.
# Gunakan _gdf_to_data_klaster() di bawah.


def _gdf_to_data_klaster(
    gdf: gpd.GeoDataFrame,
    skenario: str,
    sk: str,
) -> List[dict]:
    """
    Konversi GeoDataFrame hasil pipeline ke array JSON ringan TANPA geometri.

    Reduksi payload: ~50 MB GeoJSON (22.000 polygon) → ~2-4 MB array atribut.

    Kolom yang dikembalikan (sesuai TUGAS 3):
        id_grid              : PRIMARY KEY untuk JOIN geometri statis di frontend
        cluster_sdwfcm       : label klaster SDWFCM
        membership_max       : derajat keanggotaan tertinggi [0-1]
        cluster_sfcm         : label klaster SFCM
        cluster_redcap       : label klaster REDCAP
        cluster_skater       : label klaster SKATER
        waktu_tes_min_{sk}   : waktu ke TES terdekat (menit)
        aksesibilitas_{sk}   : 1=Tinggi / 2=Sedang / 3=Rendah
        titik_aman_semu      : 1 jika terdeteksi Titik Aman Semu
        alr_val              : Accessibility Loss Ratio; null jika isolated
        is_isolated          : true jika grid kehilangan seluruh akses TES
        sim_dampak_{skenario}: dampak simulasi bencana
        waktu_tes_{kat}_{sk} : waktu ke TES per kategori fasilitas

    Nilai float NaN / Infinity → None (JSON null, tidak menyebabkan error 500).
    Tipe numpy integer/float → Python native (JSON-serializable).
    """
    wanted: List[str] = [
        "id_grid",              # WAJIB — primary key JOIN
        "cluster_sdwfcm",
        "membership_max",
        "cluster_sfcm",
        "cluster_redcap",
        "cluster_skater",
        f"waktu_tes_min_{sk}",
        f"aksesibilitas_{sk}",
        "titik_aman_semu",
        "psi_val",
        "alr_val",
        "is_isolated",
        f"sim_dampak_{skenario}",
        cfg.indeks_bahaya.get(skenario, skenario), # Indeks bahaya mentah (0,1,2,3)
    ]
    for kat in cfg.kategori_fac:
        wanted.append(f"waktu_tes_{kat}_{sk}")

    existing = [c for c in wanted if c in gdf.columns]
    missing  = [c for c in wanted if c not in gdf.columns]
    if missing:
        logger.debug(f"[_gdf_to_data_klaster] Kolom tidak ada (dilewati): {missing}")

    # Failsafe: jika id_grid tidak ada, engine.py belum diupdate
    if "id_grid" not in existing:
        logger.error(
            "[_gdf_to_data_klaster] 'id_grid' TIDAK ADA! "
            "Pastikan load_data() di engine.py sudah diupdate (Tugas 2). "
            "Membuat id_grid darurat dari RangeIndex..."
        )
        gdf = gdf.copy()
        gdf["id_grid"] = range(len(gdf))
        existing = ["id_grid"] + [c for c in existing if c != "id_grid"]

    # Ambil subset (DataFrame biasa, tanpa kolom geometry)
    df_out = pd.DataFrame(gdf[existing])

    records: List[dict] = []
    for row_tuple in df_out.itertuples(index=False, name=None):
        records.append({col: _sanitize(val) for col, val in zip(existing, row_tuple)})

    return records


def _eval_df_to_list(eval_df: pd.DataFrame) -> List[dict]:
    """Konversi DataFrame evaluasi ke list of dict, NaN/Inf → null."""
    if eval_df is None or len(eval_df) == 0:
        return []
    records = eval_df.to_dict(orient="records")
    for row in records:
        for key, val in row.items():
            row[key] = _sanitize(val)
    return records


def _prepare_cut_roads(cut_roads: List[RoadCutItem]) -> List[dict]:
    result = []
    for item in cut_roads:
        d = item.dict(exclude_none=True)
        if "lat" in d and "lng" in d and "x" not in d:
            x, y = _latlon_to_projected(d["lat"], d["lng"])
            d["x"] = x
            d["y"] = y
        result.append(d)
    return result


# ══════════════════════════════════════════════════════════════════════════════
# 9. ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

# ── 9.0 Health Check ─────────────────────────────────────────────────────────
def _tes_to_geojson(tes_by_category: Dict[str, gpd.GeoDataFrame], skenario: str) -> Dict[str, Any]:
    name_cols = ["Nama_Objek", "nama", "Nama", "NAMA", "Name", "NAME", "REMARK", "Fasilitas", "KETERANGAN", "NAMA_UNSUR"]
    hazard_col = cfg.hazard_col_map.get(skenario, skenario)
    features = []

    for kategori in cfg.kategori_fac:
        tes_gdf = tes_by_category.get(kategori)
        if tes_gdf is None or tes_gdf.empty:
            continue

        tes_wgs = tes_gdf.to_crs("EPSG:4326")

        for idx, row in tes_wgs.iterrows():
            name = "Fasilitas TES"
            for col in name_cols:
                if col in tes_wgs.columns and pd.notna(row.get(col)):
                    value = str(row.get(col)).strip()
                    if value:
                        name = value
                        break

            hazard_value = None
            if hazard_col in tes_wgs.columns and pd.notna(row.get(hazard_col)):
                hazard_value = _sanitize(row.get(hazard_col))
            is_valid = (
                int(row.get(hazard_col, 0)) < cfg.tes_hazard_threshold
                if hazard_col in tes_wgs.columns and pd.notna(row.get(hazard_col))
                else True
            )

            features.append({
                "type": "Feature",
                "geometry": row.geometry.__geo_interface__,
                "properties": {
                    "id_tes": f"{kategori}-{idx}",
                    "kategori": kategori,
                    "name": name,
                    "hazard": hazard_value,
                    "is_valid": bool(is_valid),
                },
            })

    return {
        "type": "FeatureCollection",
        "features": features,
    }


@app.get("/api/health", tags=["System"])
async def health_check():
    return {
        "status":          "ok" if state.is_ready else "loading",
        "is_ready":        state.is_ready,
        "startup_error":   state.startup_error,
        "arsitektur":      "v2 — Geometri-Atribut dipisah (payload ringan)",
        "routing_engine":  "Optimized NetworkX (Multi-Source Dijkstra)",
        "data": {
            "n_grid":      len(state.gdf_base) if state.gdf_base is not None else 0,
            "n_roads":     len(state.roads_raw) if state.roads_raw is not None else 0,
            "tes_counts":  {k: len(v) for k, v in state.tes_raw.items()},
            "nx_graph_ok": state.nx_graph_base is not None,
            "baseline_params": state.baseline_params,
        },
        "config": {
            "skenario_list":    cfg.skenario_list,
            "intensity_levels": cfg.intensity_levels,
            "target_crs":       cfg.target_crs,
        },
    }


# ── 9.1 GET /api/baseline ────────────────────────────────────────────────────
@app.get("/api/tes-layers", tags=["System"], summary="Ambil titik TES per kategori untuk layer peta")
async def get_tes_layers(
    skenario: str = Query("banjir", description="banjir | banjir_bandang | tanah_longsor"),
    intensity: float = Query(0.0, ge=0.0, le=1.0),
):
    _check_ready()
    _validate_skenario(skenario)

    tes_source = state.tes_raw
    if intensity > 0:
        _, _, tes_source, _ = simulate_hazard(
            state.gdf_base.copy(),
            state.roads_raw.copy() if state.roads_raw is not None else None,
            state.tes_raw,
            skenario,
            intensity,
            cfg,
        )

    tes_geojson = _tes_to_geojson(tes_source, skenario)
    counts = {
        kategori: len(tes_source.get(kategori, []))
        for kategori in cfg.kategori_fac
    }

    return JSONResponse(content=_sanitize({
        "status": "ok",
        "skenario": skenario,
        "intensity": intensity,
        "categories": cfg.kategori_fac,
        "counts": counts,
        "geojson": tes_geojson,
    }))


@app.get(
    "/api/baseline",
    tags=["Clustering"],
    summary="Klaster SDWFCM baseline — respons ringan (id_grid + atribut, TANPA geometri)",
    response_class=JSONResponse,
)
async def get_baseline(
    skenario:  str   = Query(..., description="banjir | banjir_bandang | tanah_longsor"),
    intensity: float = Query(0.0, ge=0.0, le=1.0),
    algo:      str   = Query("SDWFCM", description="SDWFCM | SFCM | REDCAP | SKATER | all"),
):
    """
    Jalankan pipeline SDWFCM baseline dan kembalikan **array atribut ringan**.

    ### Perubahan dari v1
    - Field `geojson` **DIHAPUS** (penyebab crash browser ~50 MB).
    - Field `data_klaster` **BARU** — array JSON ringan ~2-4 MB.

    ### Cara JOIN di Frontend
```javascript
    // Init SATU KALI
    const geom = await fetch('/static/static_grid_kulonprogo.geojson').then(r=>r.json());
    const layer = L.geoJSON(geom).addTo(map);

    // Saat update skenario (tanpa reload geometri)
    const resp  = await fetch('/api/baseline?skenario=banjir&intensity=0').then(r=>r.json());
    const lut   = Object.fromEntries(resp.data_klaster.map(d => [d.id_grid, d]));
    layer.setStyle(feat => {
        const d = lut[feat.properties.id_grid];
        return { fillColor: clusterColor(d?.cluster_sdwfcm), fillOpacity: d?.membership_max ?? 0.6 };
    });
```
    """
    _check_ready()
    _validate_skenario(skenario)

    logger.info(f"[GET /api/baseline] skenario={skenario} intensity={intensity} algo={algo}")
    t_req = time.time()

    # 1. Cek Cache
    if skenario in state.baseline_cache:
        logger.info(f"[baseline] HIT Cache: {skenario}")
        return state.baseline_cache[skenario]

    async with state.compute_lock:
        try:
            params = state.baseline_params.get(skenario, {})
            k_opt_ov = params.get("k")
            t_pen_ov = params.get("t_pen")

            gdf_result, cl_results, eval_df, _ = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: run_pipeline(
                    gdf_base     = state.gdf_base,
                    roads_raw    = state.roads_raw,
                    tes_raw      = state.tes_raw,
                    skenario     = skenario,
                    intensity    = intensity,
                    cfg          = cfg,
                    k_opt_override=k_opt_ov,
                    t_pen_override=t_pen_ov,
                    cut_roads    = None,
                    G_override   = None,
                    w_override   = state.w_baseline,
                    baseline_times_override=state.baseline_times.get(skenario),
                    psi_array_override=state.gdf_base[f"PSI_{skenario}"].values if f"PSI_{skenario}" in state.gdf_base.columns else None
                )
            )
        except Exception as e:
            logger.error(f"[GET /api/baseline] Pipeline error: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Pipeline error: {e}")

    sk = cfg.sk_key(skenario, intensity)
    data_klaster = _gdf_to_data_klaster(gdf_result, skenario, sk)

    elapsed = round(time.time() - t_req, 2)
    est_kb  = len(json.dumps(data_klaster[:1])) * len(data_klaster) // 1024 if data_klaster else 0
    logger.info(f"[GET /api/baseline] selesai {elapsed}s | n={len(data_klaster)} | ~{est_kb} KB")

    return JSONResponse(content=_sanitize({
        "status":       "ok",
        "arsitektur":   "v2",
        "skenario":     skenario,
        "intensity":    intensity,
        "sk_key":       sk,
        "k_optimal":    state.baseline_params.get(skenario, {}).get("k", None),
        "elapsed_sec":  elapsed,
        "evaluation":   _eval_df_to_list(eval_df),
        "n_grid":       len(gdf_result),
        "n_titik_semu": int(gdf_result["titik_aman_semu"].sum())
                        if "titik_aman_semu" in gdf_result.columns else 0,
        "data_klaster": data_klaster,   # ← BARU (ringan, tanpa geometri)
        # "geojson": ...               # ← DIHAPUS (penyebab crash)
    }))


# ── 9.2 POST /api/simulate ───────────────────────────────────────────────────
@app.post(
    "/api/simulate",
    tags=["Clustering"],
    summary="Simulasi penutupan jalan + re-clustering — respons ringan (tanpa geometri)",
    response_class=JSONResponse,
)
async def post_simulate(body: SimulateRequest):
    """
    Terima perintah penutupan jalan, hitung ulang SDWFCM, kembalikan `data_klaster` ringan.

    Frontend cukup UPDATE warna layer via lookup id_grid — geometri TIDAK dimuat ulang.

    **Body JSON:**
```json
    { "skenario": "banjir", "intensity": 0.5,
      "cut_roads": [{"lat": -7.8, "lng": 110.1}] }
```
    """
    _check_ready()
    _validate_skenario(body.skenario)

    logger.info(f"[POST /api/simulate] skenario={body.skenario} intensity={body.intensity} n_cut={len(body.cut_roads)}")
    t_req = time.time()

    cut_roads_converted = _prepare_cut_roads(body.cut_roads)

    async with state.compute_lock:
        try:
            G_sim = nl_sim = tn_sim = None

            if state.nx_graph_base is not None and cut_roads_converted:
                G_sim  = apply_road_cuts_to_graph(
                    state.nx_graph_base, state.nx_node_list, state.nx_kdtree,
                    cut_roads_converted, cfg,
                )
                nl_sim = state.nx_node_list
                tn_sim = state.nx_kdtree
            elif cut_roads_converted and state.roads_raw is not None:
                G_sim, nl_sim, tn_sim = build_road_graph(
                    state.roads_raw, body.skenario, body.intensity, cfg
                )
                G_sim = apply_road_cuts_to_graph(G_sim, nl_sim, tn_sim, cut_roads_converted, cfg)

            params = state.baseline_params.get(body.skenario, {})
            k_opt_ov = params.get("k")
            t_pen_ov = params.get("t_pen")

            gdf_result, cl_results, eval_df, _ = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: run_pipeline(
                    gdf_base     = state.gdf_base,
                    roads_raw    = state.roads_raw,
                    tes_raw      = state.tes_raw,
                    skenario     = body.skenario,
                    intensity    = body.intensity,
                    cfg          = cfg,
                    k_opt_override=k_opt_ov,
                    t_pen_override=t_pen_ov,
                    cut_roads    = cut_roads_converted,
                    G_override   = G_sim,
                    nl_override  = nl_sim,
                    tn_override  = tn_sim,
                    w_override   = state.w_baseline,
                    baseline_times_override=state.baseline_times.get(body.skenario),
                    psi_array_override=state.gdf_base[f"PSI_{body.skenario}"].values if f"PSI_{body.skenario}" in state.gdf_base.columns else None
                )
            )
        except Exception as e:
            logger.error(f"[POST /api/simulate] Pipeline error: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Pipeline error: {e}")

    sk = cfg.sk_key(body.skenario, body.intensity)
    data_klaster = _gdf_to_data_klaster(gdf_result, body.skenario, sk)

    elapsed = round(time.time() - t_req, 2)
    logger.info(f"[POST /api/simulate] selesai {elapsed}s | n={len(data_klaster)}")

    return JSONResponse(content=_sanitize({
        "status":       "ok",
        "arsitektur":   "v2",
        "skenario":     body.skenario,
        "intensity":    body.intensity,
        "sk_key":       sk,
        "n_cut_roads":  len(body.cut_roads),
        "k_optimal":    state.baseline_params.get(body.skenario, {}).get("k", None),
        "elapsed_sec":  elapsed,
        "evaluation":   _eval_df_to_list(eval_df),
        "n_grid":       len(gdf_result),
        "n_titik_semu": int(gdf_result["titik_aman_semu"].sum())
                        if "titik_aman_semu" in gdf_result.columns else 0,
        "data_klaster": data_klaster,   # ← BARU (ringan, tanpa geometri)
        # "geojson": ...               # ← DIHAPUS
    }))


# ── 9.3 POST /api/route ──────────────────────────────────────────────────────
@app.post("/api/route", tags=["Routing"],
          summary="Rute terpendek ke TES terdekat",
          response_class=JSONResponse)
async def post_route(body: RouteRequest):
    """
    Kembalikan GeoJSON LineString rute ke TES terdekat.
    Endpoint ini TETAP mengembalikan GeoJSON — ukurannya kecil (satu garis, bukan 22.000 polygon).
    """
    _check_ready()
    _validate_skenario(body.skenario)

    logger.info(f"[POST /api/route] lat={body.lat} lng={body.lng} skenario={body.skenario}")
    t_req = time.time()

    origin_x, origin_y = _latlon_to_projected(body.lat, body.lng)

    _, _, tes_sim, _ = simulate_hazard(
        state.gdf_base.copy(),
        state.roads_raw.copy() if state.roads_raw is not None else None,
        state.tes_raw, body.skenario, body.intensity, cfg,
    )
    tes_v, tes_stats = filter_tes(tes_sim, body.skenario, cfg)

    try:
        route_result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: route_to_nearest_tes(
                origin_x=origin_x, origin_y=origin_y, tes_v=tes_v, cfg=cfg,
                G=state.nx_graph_base, nl=state.nx_node_list, tn=state.nx_kdtree,
                net=None, edge_df=None,
                skenario=body.skenario, intensity=body.intensity, t_pen=None,
            )
        )
    except Exception as e:
        logger.error(f"[POST /api/route] Routing error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Routing error: {e}")

    geojson_wgs84 = None
    tes_coords_wgs84 = None

    if route_result.get("path_coords"):
        path_wgs84 = [list(_utm_to_wgs84.transform(xy[0], xy[1])) for xy in route_result["path_coords"]]
        if len(path_wgs84) >= 2:
            geojson_wgs84 = {
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": path_wgs84},
                "properties": {
                    "travel_time_min": route_result["travel_time_min"],
                    "distance_m":      route_result["distance_m"],
                    "tes_kategori":    route_result["tes_kategori"],
                    "skenario":        body.skenario,
                    "intensity":       body.intensity,
                },
            }

    if route_result.get("tes_coords"):
        lon, lat = _utm_to_wgs84.transform(route_result["tes_coords"][0], route_result["tes_coords"][1])
        tes_coords_wgs84 = [lon, lat]

    elapsed = round(time.time() - t_req, 2)
    if not route_result["found"]:
        raise HTTPException(status_code=404,
            detail=f"Tidak ada rute dari ({body.lat:.4f},{body.lng:.4f}) ke TES manapun.")

    return JSONResponse(content=_sanitize({
        "status": "ok", "found": route_result["found"],
        "travel_time_min": route_result["travel_time_min"],
        "distance_m":      route_result["distance_m"],
        "tes_kategori":    route_result["tes_kategori"],
        "tes_coords_wgs84": tes_coords_wgs84,
        "tes_stats":       tes_stats,
        "elapsed_sec":     elapsed,
        "geojson":         geojson_wgs84,
    }))


# ── 9.4 POST /api/route-all-tes ──────────────────────────────────────────────
@app.post("/api/route-all-tes", tags=["Routing"],
          summary="Rute ke TES terdekat per 5 kategori, dengan simulasi jalan terputus",
          response_class=JSONResponse)
async def post_route_all_tes(body: RouteAllTesRequest):
    """
    Hitung rute terpendek dari satu titik asal ke TES terdekat di **setiap kategori**
    (pendidikan, kesehatan, pemerintahan, ibadah, gor).

    User dapat mensimulasikan pemutusan jalan dengan mengirimkan `cut_roads` —
    daftar titik yang dipilih sendiri di peta.

    **Body JSON:**
    ```json
    {
      "lat": -7.85, "lng": 110.20,
      "skenario": "banjir", "intensity": 0.5,
      "cut_roads": [{"lat": -7.84, "lng": 110.19}, ...]
    }
    ```

    **Response:** dict `routes` berisi hasil per kategori:
    ```json
    {
      "pendidikan": { "found": true, "travel_time_min": 12.3, "geojson": {...} },
      "kesehatan":  { "found": false }
    }
    ```
    """
    _check_ready()
    _validate_skenario(body.skenario)

    logger.info(
        f"[POST /api/route-all-tes] lat={body.lat} lng={body.lng} "
        f"skenario={body.skenario} intensity={body.intensity} "
        f"n_cut={len(body.cut_roads)}"
    )
    t_req = time.time()

    origin_x, origin_y = _latlon_to_projected(body.lat, body.lng)
    cut_roads_converted = _prepare_cut_roads(body.cut_roads)

    # ── Gunakan Cache Graph jika memungkinkan ──────────────────────────────
    # Konversi cut_roads ke format yang bisa di-hash (tuple of sorted items)
    # Gunakan frozenset agar urutan pemutusan jalan tidak mempengaruhi cache
    cut_roads_tuple = []
    for c in body.cut_roads:
        d = c.dict(exclude_none=True)
        # Konversi nested list (seperti edge_from) ke tuple agar hashable
        hashable_item = tuple(sorted((k, tuple(v) if isinstance(v, list) else v) for k, v in d.items()))
        cut_roads_tuple.append(hashable_item)

    cache_key = (body.skenario, body.intensity, frozenset(cut_roads_tuple))
    if cache_key in state.graph_cache:
        G_use, tn_use, nl_use = state.graph_cache[cache_key]
        logger.info("[route-all-tes] Menggunakan Graph dari cache")
    else:
        # ── Bangun graph sesuai skenario & intensitas saat ini ─────────────────────
        G_use = nl_use = tn_use = None
        
        # Optimasi: Gunakan graph baseline jika intensity=0 dan tidak ada cut_roads
        if body.intensity == 0.0 and not cut_roads_converted and body.skenario == "banjir" and state.nx_graph_base is not None:
            G_use, nl_use, tn_use = state.nx_graph_base, state.nx_node_list, state.nx_kdtree
        elif state.roads_raw is not None:
            # Bangun graph sesuai kondisi (intensity/skenario mempengaruhi jalan yang putus)
            G_use, nl_use, tn_use = build_road_graph(state.roads_raw, body.skenario, body.intensity, cfg)
            # Terapkan pemutusan jalan user jika ada
            if cut_roads_converted:
                G_use = apply_road_cuts_to_graph(G_use, nl_use, tn_use, cut_roads_converted, cfg)
        
        if G_use is None:
            G_use, nl_use, tn_use = state.nx_graph_base, state.nx_node_list, state.nx_kdtree

        # Simpan ke cache (batasi ukuran cache)
        if len(state.graph_cache) > 10: state.graph_cache.clear()
        state.graph_cache[cache_key] = (G_use, tn_use, nl_use)
        logger.info("[route-all-tes] Graph baru dibuat dan disimpan ke cache")
    _, _, tes_sim, _ = simulate_hazard(
        state.gdf_base.copy(),
        state.roads_raw.copy() if state.roads_raw is not None else None,
        state.tes_raw, body.skenario, body.intensity, cfg,
    )
    tes_v_all, tes_stats = filter_tes(tes_sim, body.skenario, cfg)

    # ── Snap origin ke jalan terdekat (1000m) ──────────────────────────────────
    origin_node = _snap(G_use, tn_use, nl_use, [origin_x, origin_y], max_snap=1000)
    
    t_pen = state.baseline_params.get(body.skenario, {}).get("t_pen")

    # ── Jalankan routing (Optimized: Dijkstra 1x untuk semua kategori) ────────
    def _route_all_optimized():
        import networkx as nx
        routes = {}
        
        # 1. Dijkstra 1x dari origin ke semua node
        try:
            lengths, paths = nx.single_source_dijkstra(G_use, origin_node, weight="weight")
        except Exception as e:
            logger.error(f"[route-all-tes] Dijkstra gagal: {e}")
            return {kat: {"found": False} for kat in cfg.kategori_fac}

        # 2. Cari TES terdekat per kategori
        name_cols = ["Nama_Objek", "nama", "Nama", "NAMA", "Name", "NAME", "REMARK", "Fasilitas", "KETERANGAN", "NAMA_UNSUR"]

        for kat in cfg.kategori_fac:
            # Filter TES kategori ini
            tes_v_kat = tes_v_all[tes_v_all["kategori"] == kat]
            if tes_v_kat.empty:
                routes[kat] = {"found": False}
                continue

            # Snap & Cari minimum distance
            best_d = float('inf')
            best_node = None
            tes_geom_map = {}
            tes_name_map = {}

            for _, row in tes_v_kat.iterrows():
                # Gunakan radius 1000m untuk TES agar tidak gagal di area rural
                nd = _snap(G_use, tn_use, nl_use, [row.geometry.x, row.geometry.y], max_snap=1000)
                if nd:
                    tes_geom_map[nd] = (row.geometry.x, row.geometry.y)
                    # Cari nama
                    name = "Fasilitas TES"
                    for c in name_cols:
                        if c in row.index and pd.notna(row[c]):
                            name = str(row[c])
                            break
                    tes_name_map[nd] = name
                    
                    d = lengths.get(nd, float('inf'))
                    if d < best_d:
                        best_d = d
                        best_node = nd

            if best_node is None or best_d == float('inf'):
                routes[kat] = {"found": False}
                continue

            # Rekonstruksi rute
            path_nodes = paths.get(best_node, [])
            path_coords = [[float(n[0]), float(n[1])] for n in path_nodes]
            
            # Failsafe: Pastikan rute memiliki minimal 2 titik agar bisa dirender sebagai LineString
            if not path_coords:
                path_coords = [[origin_x, origin_y], [tes_geom_map[best_node][0], tes_geom_map[best_node][1]]]
            elif len(path_coords) == 1:
                path_coords = [[origin_x, origin_y]] + path_coords
            else:
                path_coords[0] = [origin_x, origin_y]
                path_coords[-1] = list(tes_geom_map[best_node])

            # Konversi rute ke WGS84
            path_wgs84 = [list(_utm_to_wgs84.transform(xy[0], xy[1])) for xy in path_coords]
            geojson_wgs84 = {
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": path_wgs84},
                "properties": {
                    "kategori": kat,
                    "travel_time_min": round(best_d / cfg.walking_speed_m_per_min, 2),
                    "tes_name": tes_name_map.get(best_node, "Fasilitas TES")
                },
            }

            lon, lat = _utm_to_wgs84.transform(tes_geom_map[best_node][0], tes_geom_map[best_node][1])
            routes[kat] = {
                "found": True,
                "travel_time_min": round(best_d / cfg.walking_speed_m_per_min, 2),
                "distance_m": round(best_d, 1),
                "tes_kategori": kat,
                "tes_name": tes_name_map.get(best_node, "Fasilitas TES"),
                "tes_coords_wgs84": [lon, lat],
                "geojson": geojson_wgs84,
            }
        return routes

    try:
        routes = await asyncio.get_event_loop().run_in_executor(None, _route_all_optimized)
    except Exception as e:
        logger.error(f"[POST /api/route-all-tes] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Routing error: {e}")

    elapsed = round(time.time() - t_req, 2)
    logger.info(f"[POST /api/route-all-tes] selesai {elapsed}s | n_cut={len(body.cut_roads)}")

    # ── Deteksi Isolasi & Rekomendasi ──────────────────────────────────────────
    recommendations = []
    found_count = sum(1 for r in routes.values() if r["found"])
    
    if found_count == 0:
        logger.info("[route-all-tes] Deteksi isolasi total. Mencari rekomendasi...")
        # 1. Temukan semua node yang bisa mencapai TES manapun di G_use
        all_tes_nodes = []
        for kat in cfg.kategori_fac:
            tes_v_kat = tes_v_all[tes_v_all["kategori"] == kat]
            for _, row in tes_v_kat.iterrows():
                nd = _snap(G_use, tn_use, nl_use, [row.geometry.x, row.geometry.y], max_snap=1000)
                if nd: all_tes_nodes.append(nd)
        
        if all_tes_nodes:
            # Dijkstra terbalik: Dari semua TES ke seluruh node
            try:
                # lengths[node] = jarak ke TES terdekat
                import networkx as nx
                reachable_lengths = nx.multi_source_dijkstra_path_length(G_use, all_tes_nodes, weight="weight")
                
                # 2. Cari kandidat node terdekat dari origin_x, origin_y (Euclidean)
                # Kita ambil subset node yang reachable dan hitung jarak Euclidean-nya
                candidates = []
                r_nodes = list(reachable_lengths.keys())
                r_coords = np.array(r_nodes) # [[x, y], ...]
                
                # Jarak Euclidean ke origin
                euc_dists = np.hypot(r_coords[:, 0] - origin_x, r_coords[:, 1] - origin_y)
                
                # Ambil misal 100 node terdekat secara Euclidean untuk dievaluasi kualitasnya
                top_idx = np.argsort(euc_dists)[:100]
                
                for idx in top_idx:
                    node = r_nodes[idx]
                    dist_euc = euc_dists[idx]
                    dist_to_tes = reachable_lengths[node]
                    
                    # 3. Hitung skor kualitas (0-100)
                    # Faktor A: Kedekatan ke TES (waktu tempuh)
                    time_to_tes = dist_to_tes / cfg.walking_speed_m_per_min
                    score_time = max(0, 100 * (1 - time_to_tes / 60)) # 60 menit sebagai penalti max
                    
                    # Faktor B: Cluster Rank (jika ada)
                    score_cluster = 50 # default
                    # Cari id_grid dari node ini (pencarian terdekat di state.gdf_base)
                    if state.nx_kdtree is not None:
                        # Ini node graph, kita cari grid terdekatnya
                        # Tapi lebih akurat kalau kita simpan mapping node -> grid di startup
                        # Untuk sekarang, kita gunakan Euclidean ke centroid grid
                        pass

                    total_score = round(score_time, 1)
                    
                    candidates.append({
                        "node": node,
                        "dist_euc": dist_euc,
                        "score": total_score,
                        "time_to_tes": round(time_to_tes, 1)
                    })
                
                # 4. Pilih level rekomendasi: Terdekat dan Terbaik
                candidates.sort(key=lambda x: x["dist_euc"])
                
                if candidates:
                    # Level 1: Terdekat - "Pekat"
                    c1 = candidates[0]
                    lon1, lat1 = _utm_to_wgs84.transform(c1["node"][0], c1["node"][1])
                    recommendations.append({
                        "level": "Sub-Optimal",
                        "lat": lat1, "lng": lon1,
                        "dist_m": round(c1["dist_euc"], 1),
                        "score": c1["score"],
                        "desc": "Akses Terdekat",
                        "color_type": "pekat"
                    })
                    
                    # Level 2: Cari yang skornya tertinggi (Akses Terbaik)
                    c_best = max(candidates, key=lambda x: x["score"])
                    
                    # Jika c_best jauh lebih baik atau lokasinya cukup berbeda dari c1
                    if c_best["score"] > c1["score"] + 2 or c_best["dist_euc"] > c1["dist_euc"] + 20:
                        lon2, lat2 = _utm_to_wgs84.transform(c_best["node"][0], c_best["node"][1])
                        recommendations.append({
                            "level": "Optimal",
                            "lat": lat2, "lng": lon2,
                            "dist_m": round(c_best["dist_euc"], 1),
                            "score": c_best["score"],
                            "desc": "Area Terhubung",
                            "color_type": "gradient" # Label khusus untuk frontend
                        })
            except Exception as e:
                logger.error(f"[recommendation] Gagal: {e}")

    return JSONResponse(content=_sanitize({
        "status": "ok",
        "origin_lat": body.lat, "origin_lng": body.lng,
        "skenario": body.skenario, "intensity": body.intensity,
        "n_cut_roads": len(body.cut_roads),
        "tes_stats": tes_stats,
        "found_count": found_count,
        "elapsed_sec": elapsed,
        "routes": routes,
        "recommendations": recommendations # ← BARU
    }))


class RoadRequest(BaseModel):
    skenario: str = "banjir"
    intensity: float = 0.0
    cut_roads: List[dict] = []
    full: bool = False # Jika true, kembalikan GeoJSON lengkap. Jika false, hanya ID yang putus.


# ── 9.5 POST /api/roads ──────────────────────────────────────────────────────
@app.post("/api/roads", tags=["System"], summary="Ambil data jalan dengan info keterputusan")
async def post_roads(body: RoadRequest):
    """
    Mengembalikan data jalan (GeoJSON) dengan atribut 'is_broken'.
    - is_broken = true jika terdampak bahaya (intensity)
    - is_broken = true jika dekat dengan titik cut_roads dari user.
    """
    _check_ready()
    if state.roads_raw is None:
        raise HTTPException(status_code=404, detail="Data jalan tidak tersedia")

    hc = cfg.hazard_col_map.get(body.skenario, body.skenario)
    roads_sim = state.roads_raw.copy()

    # 1. Tandai yang putus karena bahaya
    # Sesuai logika build_road_graph: intensity * norm_haz >= threshold
    roads_sim["is_broken"] = False
    if hc in roads_sim.columns:
        haz_vals = roads_sim[hc].apply(lambda x: cfg.norm_haz(int(x))).values
        impact = haz_vals * body.intensity
        roads_sim.loc[impact >= cfg.impact_closure_threshold, "is_broken"] = True

    # 2. Tandai yang putus karena user-cut
    if body.cut_roads:
        # Konversi cut_roads (WGS84) ke CRS target (UTM)
        from shapely.geometry import Point
        from pyproj import Transformer
        
        transformer = Transformer.from_crs("EPSG:4326", cfg.target_crs, always_xy=True)
        cut_points = []
        for c in body.cut_roads:
            tx, ty = transformer.transform(c["lng"], c["lat"])
            cut_points.append(Point(tx, ty))
        
        # Cari jalan yang dekat dengan titik cut (misal radius 10 meter)
        # Gunakan buffer + intersection atau sjoin_nearest
        if cut_points:
            cut_gdf = gpd.GeoDataFrame(geometry=cut_points, crs=cfg.target_crs)
            # Find roads within 50m of any cut point
            # sjoin_nearest with max_distance is good
            res = gpd.sjoin_nearest(roads_sim, cut_gdf, max_distance=50, how="inner")
            if not res.empty:
                roads_sim.loc[res.index, "is_broken"] = True

    # 3. Kembalikan hasil (Optimized)
    if not body.full:
        # Hanya kembalikan list index yang is_broken
        broken_indices = roads_sim.index[roads_sim["is_broken"]].tolist()
        return JSONResponse(content={
            "status": "ok",
            "broken_ids": broken_indices,
            "n_total": len(roads_sim)
        })

    # Jika full=true, export GeoJSON lengkap (hanya untuk loading awal)
    roads_sim["geometry"] = roads_sim.geometry.simplify(0.0001, preserve_topology=True)
    roads_wgs = roads_sim.to_crs("EPSG:4326")
    
    # Tambahkan index sebagai id_jalan agar sinkron dengan broken_ids
    roads_wgs["id_jalan"] = roads_wgs.index
    
    cols = ["geometry", "is_broken", "id_jalan"]
    if "name" in roads_wgs.columns: cols.append("name")
    
    return JSONResponse(content=json.loads(roads_wgs[cols].to_json()))


# ── 9.6 GET /api/skenario-info ───────────────────────────────────────────────

@app.get("/api/skenario-info", tags=["System"])
async def get_skenario_info():
    _check_ready()
    info = {}
    for skenario in cfg.skenario_list:
        tes_v, tes_stats = filter_tes(state.tes_raw, skenario, cfg)
        info[skenario] = {
            "tes_stats":        tes_stats,
            "k_optimal":        state.baseline_params.get(skenario, {}).get("k", None),
            "t_pen":            state.baseline_params.get(skenario, {}).get("t_pen", None),
            "intensity_levels": cfg.intensity_levels,
        }
    return {"status": "ok", "skenario_info": info}

@app.get("/api/boundary", tags=["Search"])
async def get_boundary(name: str, type: str):
    """
    Ambil boundary GeoJSON dari file GPKG lokal berdasarkan nama dan tipe (kapanewon/kalurahan).
    """
    try:
        file_path = Path(DATA_DIR) / ("KulonProgo_Kec.gpkg" if type == "kapanewon" else "KulonProgo_Desa.gpkg")
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"File GPKG tidak ditemukan: {file_path}")
            
        gdf = gpd.read_file(file_path)
        
        # Cari kolom nama yang sesuai (prioritaskan WADMKC/WADMKD sesuai permintaan user)
        if type == "kapanewon":
            target_col = "WADMKC" if "WADMKC" in gdf.columns else next((c for c in ["NAMOBJ", "KECAMATAN", "NAMA"] if c in gdf.columns), None)
        else:
            target_col = "WADMKD" if "WADMKD" in gdf.columns else next((c for c in ["NAMOBJ", "WADMKE", "DESA", "NAMA"] if c in gdf.columns), None)
        
        if not target_col:
            raise HTTPException(status_code=500, detail=f"Kolom nama tidak ditemukan di {file_path.name}. Columns: {list(gdf.columns)}")
            
        # Filter (exact match prioritized to avoid ambiguity between village/district with same name)
        search_name = name.replace("Kelurahan ", "").replace("Desa ", "").replace("Kecamatan ", "").strip()
        
        # Try exact match first to avoid pulling partial matches that might hide the intended result
        match = gdf[gdf[target_col].str.lower() == search_name.lower()]
        
        # If no exact match, try contains (fallback)
        if match.empty:
            match = gdf[gdf[target_col].str.contains(search_name, case=False, na=False)]
            
        if match.empty:
            raise HTTPException(status_code=404, detail=f"Wilayah '{search_name}' ({type}) tidak ditemukan di {file_path.name}")
            
        # Convert to GeoJSON (first match)
        res_gdf = match.iloc[[0]].to_crs("EPSG:4326")
        return JSONResponse(content=json.loads(res_gdf.to_json()))
        
    except Exception as e:
        logger.error(f"Error fetching boundary for {name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/search-list", tags=["Search"])
async def get_search_list():
    """
    Kembalikan daftar lengkap wilayah dari GPKG untuk sinkronisasi KULON_PROGO_LIST.
    """
    try:
        kec_path = Path(DATA_DIR) / "KulonProgo_Kec.gpkg"
        desa_path = Path(DATA_DIR) / "KulonProgo_Desa.gpkg"
        
        results = []
        
        if kec_path.exists():
            gdf = gpd.read_file(kec_path)
            # Prioritaskan WADMKC
            col = "WADMKC" if "WADMKC" in gdf.columns else next((c for c in ["NAMOBJ", "KECAMATAN", "NAMA"] if c in gdf.columns), None)
            if col:
                names = sorted([str(n) for n in gdf[col].unique() if pd.notna(n)])
                for n in names:
                    results.append({"name": n, "type": "kapanewon", "desc": "Kecamatan di Kulon Progo"})
                    
        if desa_path.exists():
            gdf = gpd.read_file(desa_path)
            # Prioritaskan WADMKD
            col = "WADMKD" if "WADMKD" in gdf.columns else next((c for c in ["NAMOBJ", "WADMKE", "DESA", "NAMA"] if c in gdf.columns), None)
            # Kolom kecamatan (parent) untuk deskripsi
            kec_col = "WADMKC" if "WADMKC" in gdf.columns else next((c for c in ["KECAMATAN"] if c in gdf.columns), None)
            
            if col:
                # Gunakan data lengkap agar deskripsi kecamatan akurat
                for _, row in gdf.iterrows():
                    parent = row[kec_col] if kec_col in row and pd.notna(row[kec_col]) else "Kulon Progo"
                    results.append({
                        "name": str(row[col]),
                        "type": "kalurahan",
                        "desc": f"Kalurahan di {parent}"
                    })
                    
        return {"status": "ok", "results": results}
    except Exception as e:
        logger.error(f"Error building search list: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════════════════════
# 10. ENTRYPOINT
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000,
                reload=False, log_level="info", workers=1)
