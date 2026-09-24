# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  main.py — FastAPI Application                                              ║
# ║  Aksesibilitas Spasial Bangunan Publik sebagai TES Banjir (SDWFCM)          ║
# ║  Kabupaten Kulon Progo                                                      ║
# ║                                                                             ║
# ║  • Geometri grid statis dimuat SATU KALI oleh frontend (GeoJSON)            ║
# ║  • API mengembalikan atribut ringan per id_grid untuk setiap level          ║
# ║    intensitas banjir (Baseline, Rendah, Sedang, Tinggi)                     ║
# ║  • Hasil Bab IV dihitung offline (scripts/thesis_analysis.py)               ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
import asyncio
import json
import logging
import math
import os
import pickle
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import geopandas as gpd
import networkx as nx
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from scipy.sparse.csgraph import dijkstra as csgraph_dijkstra
from scipy.spatial import cKDTree
from shapely.geometry import Point

from . import thesis as T
from .config import (BASE_DIR, DATA_DIR, cfg, k_utama_default, utm_to_wgs84 as _utm_to_wgs84,
                     wgs84_to_utm as _wgs84_to_utm)
from .engine import (apply_road_cuts_to_graph, build_road_graph, filter_tes, load_data, load_road_network,
                     road_closed_mask, simulate_hazard)
from .schemas import RoadRequest, RouteAllTesRequest, SimulateRequest
from .state import state

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

RESULTS_FILE = "thesis_results.json"
GRID_FILE = "thesis_grid_results.csv.gz"
GRAPH_CACHE_MAX_ITEMS = 12
NAME_COLS = ["Nama_Objek", "nama", "Nama", "NAMA", "Name", "NAME", "REMARK", "Fasilitas", "KETERANGAN", "NAMA_UNSUR"]


# ══════════════════════════════════════════════════════════════════════════════
# 1. CACHE GRAPH JALAN PER LEVEL
# ══════════════════════════════════════════════════════════════════════════════
def _compute_roads_signature() -> str:
    try:
        stat = os.stat(cfg.roads_file)
        return f"{stat.st_size}_{int(stat.st_mtime)}"
    except OSError:
        return "missing"


def _graph_cache_root() -> Path:
    return BASE_DIR / "scratch" / "graph_cache"


def _graph_cache_path(intensity: float) -> Path:
    tag = str(round(float(intensity), 4)).replace(".", "p")
    return _graph_cache_root() / f"{state.roads_signature}_{T.SKENARIO}_{tag}.pkl"


def _prune_graph_cache_dir() -> None:
    root = _graph_cache_root()
    if not root.exists():
        return
    for path in root.glob("*.pkl"):
        if not path.name.startswith(f"{state.roads_signature}_{T.SKENARIO}_"):
            try:
                path.unlink()
                state.graph_cache_stats["stale_disk_pruned"] += 1
            except OSError:
                logger.warning(f"[graph-cache] Gagal menghapus cache usang: {path.name}")


def _remember_graph_cache(key: tuple, pack) -> None:
    state.graph_cache[key] = pack
    while len(state.graph_cache) > GRAPH_CACHE_MAX_ITEMS:
        state.graph_cache.pop(next(iter(state.graph_cache)), None)
        state.graph_cache_stats["evictions"] += 1


def _get_or_build_graph(intensity: float):
    key = ("road_graph", round(float(intensity), 4))
    cached = state.graph_cache.get(key)
    if cached is not None:
        state.graph_cache_stats["memory_hits"] += 1
        return cached
    if state.roads_raw is None:
        return None, None, None

    path = _graph_cache_path(intensity)
    if path.exists():
        try:
            with path.open("rb") as fh:
                G, nl = pickle.load(fh)
            pack = (G, nl, cKDTree(nl) if len(nl) else None)
            state.graph_cache_stats["disk_hits"] += 1
            _remember_graph_cache(key, pack)
            return pack
        except Exception as e:
            logger.warning(f"[graph-cache] Gagal membaca {path.name}: {e}")

    state.graph_cache_stats["misses"] += 1
    pack = build_road_graph(state.roads_raw, T.SKENARIO, intensity, cfg)
    _remember_graph_cache(key, pack)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as fh:
            pickle.dump((pack[0], pack[1]), fh, protocol=pickle.HIGHEST_PROTOCOL)
        state.graph_cache_stats["writes"] += 1
    except Exception as e:
        logger.warning(f"[graph-cache] Gagal menulis {path.name}: {e}")
    return pack


# ══════════════════════════════════════════════════════════════════════════════
# 2. FASTAPI APP
# ══════════════════════════════════════════════════════════════════════════════
app = FastAPI(
    title="Aksesibilitas TES Banjir Kulon Progo API",
    description=(
        "REST API dashboard skripsi: pemetaan tingkat aksesibilitas spasial bangunan "
        "publik sebagai Tempat Evakuasi Sementara (TES) banjir menggunakan SDWFCM "
        "berbasis grid mikro 100 × 100 m."
    ),
    version="3.0.0",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])
app.add_middleware(GZipMiddleware, minimum_size=2048)


@app.middleware("http")
async def no_cache_frontend(request, call_next):
    """Browser selalu memvalidasi ulang berkas dashboard agar tampilan lama
    (mis. pilihan tipe ancaman versi sebelumnya) tidak tertahan di cache."""
    response = await call_next(request)
    path = request.url.path
    if path == "/" or path.startswith("/frontend") or path.startswith("/api"):
        response.headers["Cache-Control"] = "no-cache, must-revalidate"
    return response

FRONTEND_DIR = BASE_DIR / "frontend"
STATIC_DIR = BASE_DIR / "static"
if FRONTEND_DIR.exists():
    app.mount("/frontend", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend")
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
async def root_redirect():
    return RedirectResponse(url="/frontend/index.html")


# ══════════════════════════════════════════════════════════════════════════════
# 3. HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def _check_ready():
    if not state.is_ready:
        msg = state.startup_error or "Server sedang memuat data, coba lagi sebentar."
        raise HTTPException(status_code=503, detail=f"Service tidak tersedia: {msg}")


def _sanitize(val: Any) -> Any:
    """Konversi numpy types & NaN/Inf ke tipe Python / None secara rekursif."""
    if val is None or isinstance(val, str):
        return val
    if isinstance(val, dict):
        return {k: _sanitize(v) for k, v in val.items()}
    if isinstance(val, (list, tuple, np.ndarray)):
        return [_sanitize(x) for x in val]
    if isinstance(val, (bool, np.bool_)):
        return bool(val)
    if isinstance(val, (int, np.integer)):
        return int(val)
    if isinstance(val, (float, np.floating)):
        v = float(val)
        return None if (math.isnan(v) or math.isinf(v)) else v
    return val


def _resolve_level(level: Optional[str], intensity: Optional[float]) -> dict:
    if level and level not in T.LEVEL_BY_KEY:
        raise HTTPException(status_code=422,
                            detail=f"Level '{level}' tidak valid. Pilihan: {T.LEVEL_KEYS}")
    return T.resolve_level(level, intensity)


def _latlon_to_projected(lat: float, lng: float):
    return _wgs84_to_utm.transform(lng, lat)


def _snap(G, tn, nl, xy, max_snap: float = 300):
    if G is None or tn is None or nl is None:
        return None
    try:
        dist, idx = tn.query(xy)
        if dist > max_snap:
            return None
        node = nl[idx]
        return (round(float(node[0]), 2), round(float(node[1]), 2))
    except Exception:
        return None


def _prepare_cut_roads(cut_roads) -> List[dict]:
    result = []
    for item in cut_roads:
        d = item.dict(exclude_none=True) if hasattr(item, "dict") else dict(item)
        if "lat" in d and "lng" in d and "x" not in d:
            d["x"], d["y"] = _latlon_to_projected(d["lat"], d["lng"])
        result.append(d)
    return result


def _tes_name(row) -> str:
    for c in NAME_COLS:
        if c in row.index and pd.notna(row[c]):
            v = str(row[c]).strip()
            if v:
                return v
    return "Fasilitas TES"


def _k_list() -> List[int]:
    return [int(k) for k in state.thesis_results.get("k_keluaran", [])]


def _resolve_k(k: Optional[int]) -> int:
    ks = _k_list()
    if k is None:
        k = k_utama_default()
        return k if k in ks else (ks[0] if ks else k)
    if int(k) not in ks:
        raise HTTPException(status_code=422, detail=f"K = {k} tidak tersedia. Pilihan: {ks}")
    return int(k)


def _model(k: int) -> dict:
    return state.thesis_results["model"][str(k)]


def _level_payload(level: dict, summary: dict, records: List[dict], k: int, distribusi: List[dict],
                   simulated: bool = False, n_cut: int = 0, elapsed: float = 0.0) -> dict:
    return {
        "status": "ok",
        "skenario": T.SKENARIO,
        "level": level["key"],
        "level_label": level["label"],
        "intensity": level["intensity"],
        "sk_key": level["key"] + ("_sim" if simulated else ""),
        "simulated": simulated,
        "n_cut_roads": n_cut,
        "elapsed_sec": round(elapsed, 2),
        "level_label_lengkap": level["label_lengkap"],
        "kelas_ditutup": level["kelas_ditutup"],
        "k_optimal": int(k),
        "k_utama": k_utama_default(),
        "k_keluaran": _k_list(),
        "cluster_names": _model(k).get("cluster_names", {}),
        "cluster_profile": _model(k).get("cluster_profile", []),
        "distribusi_tipologi": distribusi,
        "tas": summary.get("tas", {}),
        "n_titik_semu": int(summary.get("tas", {}).get("jumlah_tas", 0) or 0),
        "n_grid_tergenang": summary.get("n_grid_tergenang"),
        "mean_waktu_min": summary.get("mean_waktu_min"),
        "n_grid": len(records),
        "data_klaster": records,
    }


def _load_thesis_results() -> bool:
    res_path = Path(DATA_DIR) / RESULTS_FILE
    grid_path = Path(DATA_DIR) / GRID_FILE
    if not (res_path.exists() and grid_path.exists()):
        return False
    state.thesis_results = json.loads(res_path.read_text(encoding="utf-8"))
    state.thesis_grid = pd.read_csv(grid_path)
    state.t_pen = state.thesis_results.get("t_pen")
    return True


def _build_level_cache():
    for k in _k_list():
        for lv in T.LEVELS:
            summary = state.thesis_results.get("levels", {}).get(lv["key"], {})
            records = T.records_from_grid(state.thesis_grid, lv["key"], cfg, k)
            dist = _model(k)["distribusi"][lv["key"]]
            state.level_cache[(lv["key"], k)] = _sanitize(_level_payload(lv, summary, records, k, dist))


# ══════════════════════════════════════════════════════════════════════════════
# 4. STARTUP
# ══════════════════════════════════════════════════════════════════════════════
@app.on_event("startup")
async def startup_event():
    t0 = time.time()
    state.compute_lock = asyncio.Lock()
    try:
        logger.info("[startup] Memuat grid, jalan, dan TES...")
        state.gdf_base = load_data(cfg)
        state.roads_raw, state.tes_raw = load_road_network(cfg)
        state.roads_signature = _compute_roads_signature()
        _prune_graph_cache_dir()

        if not _load_thesis_results():
            from scripts.thesis_analysis import restore_locked
            if restore_locked(DATA_DIR) and _load_thesis_results():
                logger.info("[startup] Hasil terkunci dipulihkan dari data/locked/")
        if not state.thesis_results:
            logger.warning("[startup] Hasil analisis skripsi belum ada -> menjalankan analisis "
                           "(tanpa perbandingan algoritma, ±3 menit)...")
            from scripts.thesis_analysis import run_thesis_analysis
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: run_thesis_analysis(data_dir=DATA_DIR, skip_comparison=True))
            _load_thesis_results()

        _build_level_cache()
        # graph baseline disiapkan untuk routing klik grid
        def _warm():
            G, _, _ = _get_or_build_graph(0.0)
            _level_tes_cache(T.LEVEL_BY_KEY["baseline"])
            _graph_csr(G)
        await asyncio.get_event_loop().run_in_executor(None, _warm)
        state.is_ready = True
        logger.info(f"[startup] SELESAI dalam {time.time() - t0:.1f} detik "
                    f"(K keluaran={_k_list()}, K utama={k_utama_default()}, t_pen={state.t_pen:.2f} menit)")
    except Exception as e:
        state.startup_error = str(e)
        logger.error(f"STARTUP GAGAL: {e}", exc_info=True)


# ══════════════════════════════════════════════════════════════════════════════
# 5. ENDPOINTS — SISTEM & HASIL SKRIPSI
# ══════════════════════════════════════════════════════════════════════════════
@app.get("/api/health", tags=["System"])
async def health_check():
    return {
        "status": "ok" if state.is_ready else "loading",
        "is_ready": state.is_ready,
        "startup_error": state.startup_error,
        "data": {
            "n_grid": len(state.gdf_base) if state.gdf_base is not None else 0,
            "n_roads": len(state.roads_raw) if state.roads_raw is not None else 0,
            "tes_counts": {k: len(v) for k, v in state.tes_raw.items()},
            "k_keluaran": _k_list(),
            "k_utama": k_utama_default(),
            "t_pen": state.t_pen,
        },
        "config": {"skenario": T.SKENARIO, "levels": T.LEVELS, "target_crs": cfg.target_crs},
    }


@app.get("/api/levels", tags=["System"], summary="Daftar level intensitas banjir")
async def get_levels():
    return {"status": "ok", "skenario": T.SKENARIO, "levels": T.LEVELS, "k": _resolve_k(None),
            "k_utama": k_utama_default(), "k_keluaran": _k_list(),
            "tas_status": T.TAS_STATUS}


@app.get("/api/thesis-results", tags=["Hasil"], summary="Ringkasan seluruh hasil Bab IV")
async def get_thesis_results():
    _check_ready()
    return JSONResponse(content=_sanitize(state.thesis_results))


@app.get("/api/baseline", tags=["Clustering"],
         summary="Tipologi SDWFCM per level (atribut ringan per id_grid, tanpa geometri)")
async def get_level(
    level: Optional[str] = Query(None, description="baseline | rendah | sedang | tinggi"),
    intensity: Optional[float] = Query(None, ge=0.0, le=1.0, description="Alternatif numerik untuk level"),
    skenario: Optional[str] = Query(None, description="Diabaikan — penelitian hanya banjir"),
    k: Optional[int] = Query(None, description="K model (2 atau 3); bawaan = K utama"),
):
    _check_ready()
    lv = _resolve_level(level, intensity)
    return JSONResponse(content=state.level_cache[(lv["key"], _resolve_k(k))])


@app.post("/api/simulate", tags=["Clustering"],
          summary="Simulasi blokir jalan pada suatu level (keanggotaan terhadap pusat klaster final)")
async def post_simulate(body: SimulateRequest):
    _check_ready()
    lv = _resolve_level(body.level, body.intensity)
    k = _resolve_k(body.k)
    if not body.cut_roads:
        return JSONResponse(content=state.level_cache[(lv["key"], k)])

    t0 = time.time()
    cuts = _prepare_cut_roads(body.cut_roads)
    async with state.compute_lock:
        try:
            def _run():
                G, nl, tn = _get_or_build_graph(lv["intensity"])
                G_cut = apply_road_cuts_to_graph(G, nl, tn, cuts, cfg)
                prep = T.prepare_level(state.gdf_base, state.roads_raw, state.tes_raw,
                                       lv["intensity"], cfg, t_pen=state.t_pen,
                                       graph_pack=(G_cut, nl, tn))
                # Keanggotaan terhadap pusat klaster final yang TETAP (bukan klasterisasi ulang)
                sim = T.simulate_level(prep, T.Preprocessor.from_dict(state.thesis_results["preprocessing"]),
                                       np.asarray(_model(k)["model_final"]["pusat_klaster_pca"]),
                                       state.gdf_base, cfg)
                grid = pd.concat([
                    state.thesis_grid[["id_grid", "id_grid_asli", "Road_Density_mean", T.SKENARIO]],
                    T.level_grid_frame(lv["key"], prep["df"], prep["tas"], cfg),
                    T.model_grid_frame(lv["key"], k, sim["labels"], sim["membership"], sim["states"]),
                ], axis=1)
                return (T.level_summary(lv["key"], prep, cfg), T.records_from_grid(grid, lv["key"], cfg, k),
                        T.level_distribution(sim["states"], k))

            summary, records, dist = await asyncio.get_event_loop().run_in_executor(None, _run)
        except Exception as e:
            logger.error(f"[POST /api/simulate] error: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Simulasi gagal: {e}")

    payload = _level_payload(lv, summary, records, k, dist, simulated=True,
                             n_cut=len(body.cut_roads), elapsed=time.time() - t0)
    return JSONResponse(content=_sanitize(payload))


@app.get("/api/tes-layers", tags=["System"], summary="Titik TES per kategori (status aktif per level)")
async def get_tes_layers(
    level: Optional[str] = Query(None),
    intensity: Optional[float] = Query(None, ge=0.0, le=1.0),
    skenario: Optional[str] = Query(None),
):
    _check_ready()
    lv = _resolve_level(level, intensity)
    tes_source = state.tes_raw
    if lv["intensity"] > 0:
        _, _, tes_source, _ = simulate_hazard(state.gdf_base, state.roads_raw, state.tes_raw,
                                              T.SKENARIO, lv["intensity"], cfg)
    features = []
    counts = {}
    for kat in cfg.kategori_fac:
        tes_gdf = tes_source.get(kat)
        if tes_gdf is None or tes_gdf.empty:
            counts[kat] = 0
            continue
        counts[kat] = int(len(tes_gdf))
        for idx, row in tes_gdf.to_crs("EPSG:4326").iterrows():
            hazard = row.get(T.SKENARIO)
            is_valid = int(hazard) < cfg.tes_hazard_threshold if pd.notna(hazard) else True
            features.append({
                "type": "Feature",
                "geometry": row.geometry.__geo_interface__,
                "properties": {"id_tes": f"{kat}-{idx}", "kategori": kat, "name": _tes_name(row),
                               "hazard": _sanitize(hazard), "is_valid": bool(is_valid)},
            })
    return JSONResponse(content=_sanitize({
        "status": "ok", "level": lv["key"], "counts": counts,
        "geojson": {"type": "FeatureCollection", "features": features},
    }))


_LEVEL_TES_CACHE: Dict[str, tuple] = {}
_CSR_CACHE: Dict[int, tuple] = {}


def _level_tes_cache(lv: dict):
    """TES valid + simpul jaringan terdekatnya per level (dihitung sekali per level)."""
    key = lv["key"]
    if key not in _LEVEL_TES_CACHE:
        _, _, tes_sim, _ = simulate_hazard(state.gdf_base, state.roads_raw, state.tes_raw,
                                           T.SKENARIO, lv["intensity"], cfg)
        tes_v_all, tes_stats = filter_tes(tes_sim, T.SKENARIO, cfg)
        G, nl, tn = _get_or_build_graph(lv["intensity"])
        entries = []
        if tes_v_all is not None:
            for _, row in tes_v_all.iterrows():
                nd = _snap(G, tn, nl, [row.geometry.x, row.geometry.y], max_snap=1000)
                if nd:
                    entries.append({"kat": row["kategori"], "node": nd, "name": _tes_name(row),
                                    "xy": (float(row.geometry.x), float(row.geometry.y))})
        _LEVEL_TES_CACHE[key] = (tes_v_all, tes_stats, entries)
    return _LEVEL_TES_CACHE[key]


def _graph_csr(G):
    """Matriks CSR + indeks simpul untuk graf jalan (di-cache per objek graf)."""
    hit = _CSR_CACHE.get(id(G))
    if hit is not None and hit[0] is G:
        return hit[1:]
    nodes = list(G.nodes())
    csr = nx.to_scipy_sparse_array(G, nodelist=nodes, weight="weight", format="csr")
    index = {n: i for i, n in enumerate(nodes)}
    _CSR_CACHE[id(G)] = (G, csr, nodes, index)
    while len(_CSR_CACHE) > 8:
        _CSR_CACHE.pop(next(iter(_CSR_CACHE)))
    return csr, nodes, index


# ══════════════════════════════════════════════════════════════════════════════
# 6. ROUTING — rute ke TES terdekat per kategori
# ══════════════════════════════════════════════════════════════════════════════
@app.post("/api/route-all-tes", tags=["Routing"],
          summary="Rute ke TES terdekat per 5 kategori pada level terpilih (+ blokir jalan)")
async def post_route_all_tes(body: RouteAllTesRequest):
    _check_ready()
    lv = _resolve_level(body.level, body.intensity)
    t_req = time.time()

    origin_x, origin_y = _latlon_to_projected(body.lat, body.lng)
    if body.id_grid is not None:
        match = state.gdf_base[state.gdf_base["id_grid"] == int(body.id_grid)]
        if not match.empty:
            origin_x, origin_y = float(match.iloc[0]["cx"]), float(match.iloc[0]["cy"])

    cuts = _prepare_cut_roads(body.cut_roads)
    fingerprint = frozenset(
        tuple(sorted((k, tuple(v) if isinstance(v, list) else v) for k, v in c.dict(exclude_none=True).items()))
        for c in body.cut_roads
    )
    key = ("route_graph", lv["intensity"], fingerprint)
    if key in state.graph_cache:
        G_use, nl_use, tn_use = state.graph_cache[key]
    else:
        G_use, nl_use, tn_use = _get_or_build_graph(lv["intensity"])
        if cuts:
            G_use = apply_road_cuts_to_graph(G_use, nl_use, tn_use, cuts, cfg)
            _remember_graph_cache(key, (G_use, nl_use, tn_use))

    tes_v_all, tes_stats, tes_entries = _level_tes_cache(lv)
    origin_node = _snap(G_use, tn_use, nl_use, [origin_x, origin_y], max_snap=1000)
    speed = cfg.walking_speed_m_per_min

    def _route_all():
        """Dijkstra satu sumber (scipy, CSR ter-cache) lalu rekonstruksi jalur
        hanya ke TES terdekat per kategori — jauh lebih cepat daripada
        menyimpan jalur ke seluruh simpul jaringan."""
        if origin_node is None or tes_v_all is None:
            return {kat: {"found": False} for kat in cfg.kategori_fac}
        csr, nodes, index = _graph_csr(G_use)
        src = index.get(origin_node)
        if src is None:
            return {kat: {"found": False} for kat in cfg.kategori_fac}
        dist, pred = csgraph_dijkstra(csr, directed=False, indices=src, return_predecessors=True)
        routes = {}
        for kat in cfg.kategori_fac:
            best_d, best = float("inf"), None
            for e in tes_entries:
                if e["kat"] != kat:
                    continue
                j = index.get(e["node"])
                if j is not None and dist[j] < best_d:
                    best_d, best = float(dist[j]), (j, e)
            if best is None or not np.isfinite(best_d):
                routes[kat] = {"found": False}
                continue
            j, e = best
            chain = [j]
            while chain[-1] != src and pred[chain[-1]] >= 0:
                chain.append(int(pred[chain[-1]]))
            coords = [[float(nodes[i][0]), float(nodes[i][1])] for i in reversed(chain)]
            if len(coords) < 2:
                coords = [[origin_x, origin_y], list(e["xy"])]
            else:
                coords[0] = [origin_x, origin_y]
                coords[-1] = list(e["xy"])
            path_wgs = [list(_utm_to_wgs84.transform(x, y)) for x, y in coords]
            lon, lat = _utm_to_wgs84.transform(*e["xy"])
            t_min = round(best_d / speed, 2)
            routes[kat] = {
                "found": True, "travel_time_min": t_min, "distance_m": round(best_d, 1),
                "tes_kategori": kat, "tes_name": e["name"], "tes_coords_wgs84": [lon, lat],
                "geojson": {"type": "Feature", "geometry": {"type": "LineString", "coordinates": path_wgs},
                            "properties": {"kategori": kat, "travel_time_min": t_min}},
            }
        return routes

    try:
        routes = await asyncio.get_event_loop().run_in_executor(None, _route_all)
    except Exception as e:
        logger.error(f"[route-all-tes] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Routing error: {e}")

    # ── Rekomendasi bila grid terisolasi total ────────────────────────────────
    recommendations = []
    found_count = sum(1 for r in routes.values() if r["found"])
    if found_count == 0 and tes_v_all is not None and G_use is not None:
        tes_nodes = [e["node"] for e in tes_entries if e["node"] in G_use]
        if tes_nodes:
            try:
                reach = nx.multi_source_dijkstra_path_length(G_use, tes_nodes, weight="weight")
                r_nodes = list(reach.keys())
                r_xy = np.array(r_nodes)
                euc = np.hypot(r_xy[:, 0] - origin_x, r_xy[:, 1] - origin_y)
                cands = []
                origin_geom = None
                if body.id_grid is not None:
                    m = state.gdf_base[state.gdf_base["id_grid"] == int(body.id_grid)]
                    origin_geom = m.iloc[0].geometry if not m.empty else None
                for idx in np.argsort(euc)[:100]:
                    node = r_nodes[idx]
                    if origin_geom is not None and origin_geom.covers(Point(node)):
                        continue
                    t_tes = reach[node] / speed
                    cands.append({"node": node, "dist_euc": float(euc[idx]),
                                  "score": round(max(0.0, 100 * (1 - t_tes / 60)), 1)})
                if cands:
                    c1 = cands[0]
                    lon1, lat1 = _utm_to_wgs84.transform(*c1["node"])
                    recommendations.append({"level": "Sub-Optimal", "lat": lat1, "lng": lon1,
                                            "dist_m": round(c1["dist_euc"], 1), "score": c1["score"],
                                            "desc": "Akses Terdekat", "color_type": "pekat"})
                    cb = max(cands, key=lambda c: c["score"])
                    if cb["score"] > c1["score"] + 2 or cb["dist_euc"] > c1["dist_euc"] + 20:
                        lon2, lat2 = _utm_to_wgs84.transform(*cb["node"])
                        recommendations.append({"level": "Optimal", "lat": lat2, "lng": lon2,
                                                "dist_m": round(cb["dist_euc"], 1), "score": cb["score"],
                                                "desc": "Area Terhubung", "color_type": "gradient"})
            except Exception as e:
                logger.error(f"[recommendation] Gagal: {e}")

    return JSONResponse(content=_sanitize({
        "status": "ok", "level": lv["key"], "n_cut_roads": len(body.cut_roads),
        "tes_stats": tes_stats, "found_count": found_count,
        "elapsed_sec": round(time.time() - t_req, 2),
        "routes": routes, "recommendations": recommendations,
    }))


@app.post("/api/roads", tags=["System"], summary="Jaringan jalan dengan status terputus per level")
async def post_roads(body: RoadRequest):
    _check_ready()
    if state.roads_raw is None:
        raise HTTPException(status_code=404, detail="Data jalan tidak tersedia")
    lv = _resolve_level(body.level, body.intensity)
    roads_sim = state.roads_raw.copy()
    roads_sim["is_broken"] = False
    roads_sim.loc[road_closed_mask(roads_sim, T.SKENARIO, lv["intensity"], cfg), "is_broken"] = True

    if body.cut_roads:
        pts = [Point(*_latlon_to_projected(c["lat"], c["lng"])) for c in body.cut_roads
               if "lat" in c and "lng" in c]
        if pts:
            cut_gdf = gpd.GeoDataFrame(geometry=pts, crs=cfg.target_crs)
            res = gpd.sjoin_nearest(roads_sim, cut_gdf, max_distance=50, how="inner")
            if not res.empty:
                roads_sim.loc[res.index.unique(), "is_broken"] = True

    if not body.full:
        return JSONResponse(content={"status": "ok", "level": lv["key"],
                                     "broken_ids": roads_sim.index[roads_sim["is_broken"]].tolist(),
                                     "n_total": len(roads_sim)})
    roads_sim["geometry"] = roads_sim.geometry.simplify(0.0001, preserve_topology=True)
    roads_wgs = roads_sim.to_crs("EPSG:4326")
    roads_wgs["id_jalan"] = roads_wgs.index
    cols = ["geometry", "is_broken", "id_jalan"] + (["name"] if "name" in roads_wgs.columns else [])
    return JSONResponse(content=json.loads(roads_wgs[cols].to_json()))


# ══════════════════════════════════════════════════════════════════════════════
# 7. ADMINISTRASI & PENCARIAN
# ══════════════════════════════════════════════════════════════════════════════
def _admin_name_col(gdf: gpd.GeoDataFrame, kind: str) -> Optional[str]:
    if kind == "kapanewon":
        return "WADMKC" if "WADMKC" in gdf.columns else next(
            (c for c in ["NAMOBJ", "KECAMATAN", "NAMA"] if c in gdf.columns), None)
    return "WADMKD" if "WADMKD" in gdf.columns else next(
        (c for c in ["NAMOBJ", "WADMKE", "DESA", "NAMA"] if c in gdf.columns), None)


def _load_admin_gdf(file_name: str, kind: str) -> gpd.GeoDataFrame:
    path = Path(DATA_DIR) / file_name
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"File GPKG tidak ditemukan: {path}")
    gdf = gpd.read_file(path).to_crs("EPSG:4326")
    col = _admin_name_col(gdf, kind)
    if not col:
        raise HTTPException(status_code=500, detail=f"Kolom nama tidak ditemukan di {file_name}")
    out = gdf[[col, "geometry"]].rename(columns={col: "name"})
    out["geometry"] = out.geometry.simplify(0.0002, preserve_topology=True)
    return out


@app.get("/api/admin-layers", tags=["System"], summary="Layer administrasi Kulon Progo")
async def get_admin_layers():
    kec = _load_admin_gdf("KulonProgo_Kec.gpkg", "kapanewon")
    desa = _load_admin_gdf("KulonProgo_Desa.gpkg", "kalurahan")
    return JSONResponse(content={"status": "ok", "kecamatan": json.loads(kec.to_json()),
                                 "desa": json.loads(desa.to_json())})


@app.get("/api/boundary", tags=["Search"])
async def get_boundary(name: str, type: str):
    path = Path(DATA_DIR) / ("KulonProgo_Kec.gpkg" if type == "kapanewon" else "KulonProgo_Desa.gpkg")
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"File GPKG tidak ditemukan: {path}")
    gdf = gpd.read_file(path)
    col = _admin_name_col(gdf, type)
    if not col:
        raise HTTPException(status_code=500, detail=f"Kolom nama tidak ditemukan di {path.name}")
    search = name.replace("Kelurahan ", "").replace("Desa ", "").replace("Kecamatan ", "").strip()
    match = gdf[gdf[col].str.lower() == search.lower()]
    if match.empty:
        match = gdf[gdf[col].str.contains(search, case=False, na=False)]
    if match.empty:
        raise HTTPException(status_code=404, detail=f"Wilayah '{search}' ({type}) tidak ditemukan")
    return JSONResponse(content=json.loads(match.iloc[[0]].to_crs("EPSG:4326").to_json()))


@app.get("/api/search-list", tags=["Search"])
async def get_search_list():
    results = []
    kec_path = Path(DATA_DIR) / "KulonProgo_Kec.gpkg"
    desa_path = Path(DATA_DIR) / "KulonProgo_Desa.gpkg"
    if kec_path.exists():
        gdf = gpd.read_file(kec_path)
        col = _admin_name_col(gdf, "kapanewon")
        if col:
            for n in sorted(str(n) for n in gdf[col].unique() if pd.notna(n)):
                results.append({"name": n, "type": "kapanewon", "desc": "Kecamatan di Kulon Progo"})
    if desa_path.exists():
        gdf = gpd.read_file(desa_path)
        col = _admin_name_col(gdf, "kalurahan")
        kec_col = "WADMKC" if "WADMKC" in gdf.columns else ("KECAMATAN" if "KECAMATAN" in gdf.columns else None)
        if col:
            for _, row in gdf.iterrows():
                parent = row[kec_col] if kec_col and pd.notna(row[kec_col]) else "Kulon Progo"
                results.append({"name": str(row[col]), "type": "kalurahan", "desc": f"Kalurahan di {parent}"})
    return {"status": "ok", "results": results}


# ══════════════════════════════════════════════════════════════════════════════
# 8. BATAS WILAYAH & GEOCODING ALAMAT
# ══════════════════════════════════════════════════════════════════════════════
import threading
import urllib.parse
import urllib.request
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor

GEOCODE_UA = "KulonProgo-TES-Dashboard/1.0 (skripsi aksesibilitas TES banjir)"
# Kotak pencarian: Kulon Progo + sekitarnya (DIY/Purworejo) agar hasil relevan
GEOCODE_BBOX = (109.95, -8.05, 110.45, -7.55)          # lon_min, lat_min, lon_max, lat_max
_ADMIN_CACHE: Dict[str, Any] = {}
_GEOCODE_CACHE: "OrderedDict[tuple, list]" = OrderedDict()
_NOMINATIM_LOCK = threading.Lock()
_NOMINATIM_LAST = [0.0]


def _admin_frames():
    """Desa (88), kecamatan (12) dan kabupaten (hasil dissolve) dalam EPSG:4326."""
    if "frames" in _ADMIN_CACHE:
        return _ADMIN_CACHE["frames"]
    desa = gpd.read_file(Path(DATA_DIR) / "KulonProgo_Desa.gpkg").to_crs("EPSG:4326")
    desa = desa[["WADMKD", "WADMKC", "geometry"]].rename(columns={"WADMKD": "desa", "WADMKC": "kecamatan"})
    desa["geometry"] = desa.geometry.buffer(0)
    kec = desa.dissolve(by="kecamatan", as_index=False)[["kecamatan", "geometry"]]
    kab = gpd.GeoDataFrame({"kabupaten": ["Kulon Progo"]},
                           geometry=[desa.geometry.union_all().buffer(0)], crs="EPSG:4326")
    _ADMIN_CACHE["frames"] = (kab, kec, desa)
    return _ADMIN_CACHE["frames"]


def _boundary_fc(gdf: gpd.GeoDataFrame, name_col: str, tol: float, extra: Optional[List[str]] = None) -> dict:
    feats = []
    for _, row in gdf.iterrows():
        geom = row.geometry.simplify(tol, preserve_topology=True)
        lab = row.geometry.representative_point()
        props = {"name": str(row[name_col]), "label": [round(lab.x, 6), round(lab.y, 6)]}
        for c in extra or []:
            props[c] = str(row[c])
        feats.append({"type": "Feature", "properties": props, "geometry": geom.__geo_interface__})
    return {"type": "FeatureCollection", "features": feats}


@app.get("/api/admin-boundaries", tags=["Wilayah"], summary="Batas kabupaten, kecamatan (kapanewon), desa (kalurahan)")
async def get_admin_boundaries():
    if "boundaries" not in _ADMIN_CACHE:
        kab, kec, desa = _admin_frames()
        _ADMIN_CACHE["boundaries"] = _sanitize({
            "status": "ok",
            "kabupaten": _boundary_fc(kab, "kabupaten", 0.0002),
            "kecamatan": _boundary_fc(kec, "kecamatan", 0.0002),
            "desa": _boundary_fc(desa, "desa", 0.0001, extra=["kecamatan"]),
        })
    return JSONResponse(content=_ADMIN_CACHE["boundaries"])


@app.get("/api/grid-admin", tags=["Wilayah"], summary="Desa & kecamatan untuk setiap id_grid (ringkas)")
async def get_grid_admin():
    _check_ready()
    if "grid_admin" not in _ADMIN_CACHE:
        _, _, desa = _admin_frames()
        pts = gpd.GeoDataFrame({"id_grid": state.gdf_base["id_grid"].values},
                               geometry=gpd.points_from_xy(state.gdf_base["cx"], state.gdf_base["cy"]),
                               crs=cfg.target_crs)
        desa_utm = desa.reset_index(names="desa_idx").to_crs(cfg.target_crs)
        j = gpd.sjoin_nearest(pts, desa_utm[["desa_idx", "geometry"]], how="left", max_distance=500)
        j = j[~j.index.duplicated()]
        _ADMIN_CACHE["grid_admin"] = {
            "status": "ok",
            "desa": desa[["desa", "kecamatan"]].values.tolist(),   # [[desa, kecamatan], ...]
            "grid": {str(int(g)): (int(i) if pd.notna(i) else None) for g, i in zip(j["id_grid"], j["desa_idx"])},
        }
    return JSONResponse(content=_ADMIN_CACHE["grid_admin"])


def _locate_admin(lon: float, lat: float) -> dict:
    kab, _, desa = _admin_frames()
    pt = Point(lon, lat)
    hit = desa[desa.contains(pt)]
    return {
        "in_kulon_progo": bool(kab.geometry.iloc[0].contains(pt)),
        "desa": None if hit.empty else hit.iloc[0]["desa"],
        "kecamatan": None if hit.empty else hit.iloc[0]["kecamatan"],
    }


def _http_json(url: str, timeout: float = 6.0):
    req = urllib.request.Request(url, headers={"User-Agent": GEOCODE_UA, "Accept-Language": "id,en"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _photon(q: str, limit: int) -> List[dict]:
    lo1, la1, lo2, la2 = GEOCODE_BBOX
    url = "https://photon.komoot.io/api/?" + urllib.parse.urlencode(
        {"q": q, "limit": limit, "bbox": f"{lo1},{la1},{lo2},{la2}", "lat": -7.86, "lon": 110.16})
    out = []
    for f in _http_json(url).get("features", []):
        pr = f.get("properties", {})
        name = pr.get("name") or " ".join(str(x) for x in (pr.get("street"), pr.get("housenumber")) if x)
        if not name:
            continue
        addr_parts = [pr.get("street") if pr.get("name") else None, pr.get("district"),
                      pr.get("city") or pr.get("county"), pr.get("state")]
        out.append({"name": name, "address": ", ".join(str(x) for x in addr_parts if x),
                    "lon": f["geometry"]["coordinates"][0], "lat": f["geometry"]["coordinates"][1],
                    "type": pr.get("osm_value") or pr.get("type") or "place", "source": "photon"})
    return out


def _nominatim(q: str, limit: int) -> List[dict]:
    lo1, la1, lo2, la2 = GEOCODE_BBOX
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
        {"q": q, "format": "jsonv2", "limit": limit, "countrycodes": "id",
         "viewbox": f"{lo1},{la2},{lo2},{la1}", "bounded": 1})
    with _NOMINATIM_LOCK:                          # kebijakan Nominatim: maks. 1 permintaan/detik
        wait = 1.0 - (time.time() - _NOMINATIM_LAST[0])
        if wait > 0:
            time.sleep(wait)
        _NOMINATIM_LAST[0] = time.time()
        data = _http_json(url)
    out = []
    for x in data:
        parts = [p.strip() for p in x.get("display_name", "").split(",")]
        out.append({"name": parts[0] if parts else q, "address": ", ".join(parts[1:5]),
                    "lon": float(x["lon"]), "lat": float(x["lat"]), "type": x.get("type") or "place",
                    "source": "nominatim"})
    return out


@app.get("/api/geocode", tags=["Wilayah"], summary="Cari alamat/tempat (OpenStreetMap: Photon & Nominatim)")
async def get_geocode(q: str = Query(..., min_length=2, max_length=120),
                      full: bool = Query(False, description="True = sertakan Nominatim (pencarian alamat lengkap)")):
    key = (q.strip().lower(), full)
    if key in _GEOCODE_CACHE:
        _GEOCODE_CACHE.move_to_end(key)
        return {"status": "ok", "results": _GEOCODE_CACHE[key], "cached": True}

    def _run():
        results, errors = [], []
        jobs = [("photon", lambda: _photon(q, 8))]
        if full:
            jobs.append(("nominatim", lambda: _nominatim(q, 6)))
        with ThreadPoolExecutor(max_workers=2) as ex:
            futs = {name: ex.submit(fn) for name, fn in jobs}
            for name, fut in futs.items():
                try:
                    results.extend(fut.result())
                except Exception as e:
                    errors.append(f"{name}: {e}")
        seen, merged = set(), []
        for r in results:
            k = (r["name"].lower(), round(r["lat"], 3), round(r["lon"], 3))
            if k in seen:
                continue
            seen.add(k)
            r.update(_locate_admin(r["lon"], r["lat"]))
            merged.append(r)
        merged.sort(key=lambda r: not r["in_kulon_progo"])
        return merged[:10], errors

    merged, errors = await asyncio.get_event_loop().run_in_executor(None, _run)
    if merged or not errors:
        _GEOCODE_CACHE[key] = merged
        while len(_GEOCODE_CACHE) > 500:
            _GEOCODE_CACHE.popitem(last=False)
    return {"status": "ok" if (merged or not errors) else "error", "results": merged, "errors": errors}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=False, log_level="info", workers=1)
