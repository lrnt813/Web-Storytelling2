#!/usr/bin/env python3
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  export_geometry.py — Static Geometry Exporter (Jalankan SATU KALI)        ║
# ║  "Aturan Emas Web GIS": Pisahkan Geometri dari Atribut                      ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
import os, sys, logging, time, argparse
from pathlib import Path
import geopandas as gpd

logging.basicConfig(level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)

# ── Konfigurasi path ──────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_GPKG     = os.environ.get("SDWFCM_INPUT_GPKG", str(PROJECT_ROOT / "data" / "Kulonprogo_Ready4.gpkg"))
OUTPUT_GEOJSON = os.environ.get("SDWFCM_OUTPUT_GEOJSON", str(PROJECT_ROOT / "static" / "static_grid_kulonprogo.geojson"))

# HARUS sama dengan cfg.target_crs di engine.py — untuk urutan baris yang identik
ENGINE_CRS = "EPSG:32749"
OUTPUT_CRS = "EPSG:4326"   # WGS84 untuk Leaflet / Mapbox


def export_static_geometry(input_path=INPUT_GPKG, output_path=OUTPUT_GEOJSON):
    """
    Baca GPKG, tambahkan id_grid, buang semua atribut lain, simpan GeoJSON statis.

    Urutan operasi IDENTIK dengan load_data() di engine.py agar id_grid sinkron:
      1. read_file  → _read_gpkg (reproject ke ENGINE_CRS)
      2. filter: notna() & ~is_empty()
      3. reset_index(drop=True)
      4. id_grid = range(N)        ← PRIMARY KEY, 0-based
      5. to_crs(OUTPUT_CRS=4326)
      6. simpan hanya kolom id_grid + geometry
    """
    t0 = time.time()
    logger.info("=" * 70)
    logger.info("EXPORT GEOMETRI STATIS — 'Aturan Emas Web GIS'")
    logger.info(f"Input  : {input_path}")
    logger.info(f"Output : {output_path}")
    logger.info("=" * 70)

    if not os.path.exists(input_path):
        logger.error(f"File tidak ditemukan: {input_path}")
        sys.exit(1)

    # Step 1: Baca
    logger.info("[Step 1/5] Membaca GeoPackage...")
    gdf = gpd.read_file(input_path)
    logger.info(f"          {len(gdf)} baris | CRS={gdf.crs}")

    # Step 2: Set CRS default jika kosong
    if gdf.crs is None:
        logger.warning("          CRS tidak ada → set ke EPSG:4326")
        gdf = gdf.set_crs("EPSG:4326")

    # Step 3: Reproyek ke CRS engine (IDENTIK dengan load_data)
    logger.info(f"[Step 2/5] Reproyek ke {ENGINE_CRS} (sama dengan engine.py)...")
    if gdf.crs.to_epsg() != int(ENGINE_CRS.split(":")[1]):
        gdf = gdf.to_crs(ENGINE_CRS)

    # Step 4: Filter geometri invalid (IDENTIK dengan load_data)
    logger.info("[Step 3/5] Filter geometri null/empty...")
    n_before = len(gdf)
    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].reset_index(drop=True)
    if (dropped := n_before - len(gdf)) > 0:
        logger.warning(f"          {dropped} baris dibuang")
    logger.info(f"          Sisa: {len(gdf)} baris valid")

    # Step 5: Tambahkan id_grid (IDENTIK dengan load_data)
    logger.info("[Step 4/5] Menetapkan id_grid (integer urut 0..N-1)...")
    if "id_grid" in gdf.columns:
        logger.warning("          id_grid sudah ada → ditimpa ulang untuk menjamin konsistensi")
    gdf["id_grid"] = range(len(gdf))
    gdf["id_grid"] = gdf["id_grid"].astype("int32")

    # Step 6: Buang semua atribut, simpan hanya id_grid + geometry, reproyek ke WGS84
    logger.info("[Step 5/5] Membuang atribut, reproyek ke WGS84, simpan GeoJSON...")
    gdf_export = gdf[["id_grid", "geometry"]].copy().to_crs(OUTPUT_CRS)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    gdf_export.to_file(output_path, driver="GeoJSON")

    size_mb = os.path.getsize(output_path) / 1_048_576
    elapsed = time.time() - t0
    logger.info("=" * 70)
    logger.info("EXPORT SELESAI")
    logger.info(f"  File   : {output_path}")
    logger.info(f"  Ukuran : {size_mb:.2f} MB")
    logger.info(f"  Baris  : {len(gdf_export)} polygon")
    logger.info(f"  CRS    : {gdf_export.crs}")
    logger.info(f"  Waktu  : {elapsed:.1f} detik")
    logger.info("=" * 70)
    logger.info("LANGKAH SELANJUTNYA:")
    logger.info(f"  Salin '{output_path}' ke folder /static atau /public frontend.")
    logger.info("  Di Leaflet/JS:")
    logger.info("    const geom = await fetch('/static/static_grid_kulonprogo.geojson').then(r=>r.json());")
    logger.info("    const layer = L.geoJSON(geom).addTo(map);")
    logger.info("  Saat terima respons API:")
    logger.info("    const lut = Object.fromEntries(resp.data_klaster.map(d=>[d.id_grid, d]));")
    logger.info("    layer.setStyle(f => colorByCluster(lut[f.properties.id_grid]));")
    logger.info("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export geometri statis (jalankan SATU KALI)")
    parser.add_argument("--input",  "-i", default=INPUT_GPKG,     help="Path Kulonprogo_Ready4.gpkg")
    parser.add_argument("--output", "-o", default=OUTPUT_GEOJSON, help="Path output GeoJSON")
    args = parser.parse_args()
    export_static_geometry(input_path=args.input, output_path=args.output)
