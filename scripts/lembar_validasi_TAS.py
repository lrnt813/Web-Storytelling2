"""Lembar validasi manual Titik Aman Semu (TAS, aturan utama) untuk keempat level.

    python -m scripts.lembar_validasi_TAS

Keluaran (output_bab4/validasi/):
  validasi_TAS.xlsx   satu baris per grid TAS per level: identitas grid, koordinat centroid (WGS84),
                      TES terdekat secara Euclidean (nama, kategori, koordinat), T_ideal, T_aktual,
                      DI_t, tautan Google Maps (centroid dan TES), tautan peta, serta kolom kosong untuk
                      peneliti: "Penyebab" (pilihan), "Catatan", "Valid (Y/T)".
  peta/<level>_<id_grid>.png   peta kecil per TAS: grid, TES terdekat, garis lurus, dan rute jaringan.

Status TAS, T_ideal, T_aktual, dan DI_t diambil dari hasil TERKUNCI (data/locked/). Rute jaringan
dihitung ulang dengan aturan yang sama (graf jalan level tersebut, snapping ≤ 300 m, ruas snapping,
batas minimum 50 m); T_aktual hasil hitung ulang dibandingkan dengan nilai terkunci (kolom
"Cek T_aktual"). Setelah diisi, lembar direkap dengan `python -m scripts.rekap_validasi_TAS`.
"""
import json
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend import thesis as T
from backend.engine import (Cfg, graph_csr, load_data, load_road_network, road_closed_mask)
from scripts.rekap_validasi_TAS import LEMBAR, PENYEBAB, SHEET, VALIDASI_DIR

LOCKED = PROJECT_ROOT / "data" / "locked"
NAME_COLS = ["Nama_Objek", "nama", "Nama", "NAMA", "Name", "NAME", "REMARK", "Fasilitas", "KETERANGAN", "NAMA_UNSUR"]
KAT_LABEL = {"pendidikan": "Pendidikan", "kesehatan": "Kesehatan", "pemerintahan": "Pemerintahan",
             "ibadah": "Tempat Ibadah", "gor": "GOR/Gedung Serbaguna"}


def tes_name(row) -> str:
    for c in NAME_COLS:
        if c in row.index and pd.notna(row[c]) and str(row[c]).strip():
            return str(row[c]).strip()
    return "(tanpa nama)"


def gmaps(lat, lon) -> str:
    return f"https://www.google.com/maps/search/?api=1&query={lat:.6f},{lon:.6f}"


def _route(csr, pred_cache, src, dst):
    """Simpul-simpul jalur terpendek dari simpul src (TES) ke dst (grid)."""
    from scipy.sparse.csgraph import dijkstra
    if src not in pred_cache:
        dist, pred = dijkstra(csr, directed=False, indices=src, return_predecessors=True)
        pred_cache[src] = (dist, pred)
    dist, pred = pred_cache[src]
    if not np.isfinite(dist[dst]):
        return None, np.inf
    path = [dst]
    while path[-1] != src:
        path.append(int(pred[path[-1]]))
    return path, float(dist[dst])


def _map(png, grid_geom, tes_pt, path_xy, gxy, roads_lv, closed_lv):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    xs = [gxy[0], tes_pt[0]] + ([p[0] for p in path_xy] if path_xy else [])
    ys = [gxy[1], tes_pt[1]] + ([p[1] for p in path_xy] if path_xy else [])
    pad = 150.0
    x0, x1, y0, y1 = min(xs) - pad, max(xs) + pad, min(ys) - pad, max(ys) + pad
    fig, ax = plt.subplots(figsize=(4.2, 4.2), dpi=110)
    sub = roads_lv.cx[x0:x1, y0:y1]
    sc = closed_lv[sub.index.values]
    if (~sc).any():
        sub[~sc].plot(ax=ax, color="#9ca3af", linewidth=0.6)
    if sc.any():
        sub[sc].plot(ax=ax, color="#dc2626", linewidth=0.8, linestyle="--")
    for poly in getattr(grid_geom, "geoms", [grid_geom]):
        ax.fill(*poly.exterior.xy, facecolor="#a855f7", alpha=0.35, edgecolor="#6b21a8", linewidth=1)
    ax.plot([gxy[0], tes_pt[0]], [gxy[1], tes_pt[1]], color="#111827", linestyle=":", linewidth=1.2)
    if path_xy:
        net = path_xy[1:-1]
        ax.plot([p[0] for p in net], [p[1] for p in net], color="#2563eb", linewidth=1.8)
        for a_, b_ in ((path_xy[0], path_xy[1]), (path_xy[-2], path_xy[-1])):     # ruas snapping
            ax.plot([a_[0], b_[0]], [a_[1], b_[1]], color="#f97316", linewidth=1.4, linestyle="--")
    ax.plot(*tes_pt, marker="*", markersize=12, color="#16a34a")
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title("ungu = grid TAS; bintang = TES terdekat; ··· garis lurus\n"
                 "biru = rute jaringan; oranye putus = ruas snapping; merah = ruas ditutup",
                 fontsize=6.5)
    fig.tight_layout()
    fig.savefig(png)
    plt.close(fig)


def build(out_dir: Path = VALIDASI_DIR) -> pd.DataFrame:
    from pyproj import Transformer
    logging.basicConfig(level=logging.WARNING)
    R = json.loads((LOCKED / "thesis_results.json").read_text(encoding="utf-8"))
    grid = pd.read_csv(LOCKED / "thesis_grid_results.csv.gz")
    t_pen = float(R["t_pen"])
    cfg = Cfg(base_dir=str(PROJECT_ROOT / "data"))
    gdf = load_data(cfg)
    roads, tes = load_road_network(cfg)
    to_wgs = Transformer.from_crs(cfg.target_crs, "EPSG:4326", always_xy=True)
    speed = cfg.walking_speed_m_per_min
    peta_dir = out_dir / "peta"
    peta_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for lv in T.LEVELS:
        key = lv["key"]
        sel = np.where(grid[f"tas_status_{key}"].values == 1)[0]
        if not len(sel):
            continue
        acc = T.compute_level_accessibility(gdf, roads, tes, lv["intensity"], cfg, t_pen=t_pen)
        tes_v = acc["tes_v"].reset_index(drop=True)
        G, nl, tn = acc["graph"]
        csr = graph_csr(G, nl)
        closed = road_closed_mask(roads, T.SKENARIO, lv["intensity"], cfg)
        tes_xy = np.column_stack([tes_v.geometry.x.values, tes_v.geometry.y.values])
        from scipy.spatial import cKDTree
        gxy_all = np.column_stack([gdf["cx"].values, gdf["cy"].values])
        _, tes_idx = cKDTree(tes_xy).query(gxy_all[sel], k=1)
        pred_cache = {}
        for gi, ti in zip(sel, tes_idx):
            gxy, txy = gxy_all[gi], tes_xy[ti]
            g_d, g_node = tn.query(gxy, k=1)
            t_d, t_node = tn.query(txy, k=1)
            path, net = _route(csr, pred_cache, int(t_node), int(g_node))
            path_xy = [tuple(txy)] + [tuple(nl[i]) for i in (path or [])] + [tuple(gxy)]
            t_akt_ulang = min(max(g_d + net + t_d, T.TAS_MIN_EUCLID_M) / speed, t_pen)
            lon_g, lat_g = to_wgs.transform(*gxy)
            lon_t, lat_t = to_wgs.transform(*txy)
            t_akt = float(grid.at[gi, f"t_aktual_{key}"])
            png = peta_dir / f"{key}_{int(grid.at[gi, 'id_grid'])}.png"
            _map(png, gdf.geometry.iloc[gi], tuple(txy), path_xy[::-1] if path else None, gxy, roads, closed)
            trow = tes_v.iloc[int(ti)]
            rows.append({
                "id_grid": int(grid.at[gi, "id_grid"]), "id_grid_asli": str(grid.at[gi, "id_grid_asli"]),
                "level": lv["label"],
                "Lat centroid": round(lat_g, 6), "Lon centroid": round(lon_g, 6),
                "TES terdekat": tes_name(trow), "Kategori TES": KAT_LABEL.get(trow["kategori"], trow["kategori"]),
                "Lat TES": round(lat_t, 6), "Lon TES": round(lon_t, 6),
                "T_ideal (menit)": float(grid.at[gi, f"t_ideal_{key}"]), "T_aktual (menit)": t_akt,
                "DI_t": float(grid.at[gi, f"di_{key}"]),
                "Cek T_aktual (hitung ulang)": "sama" if abs(t_akt_ulang - t_akt) < 1e-2 else f"beda ({t_akt_ulang:.2f})",
                "Google Maps centroid": gmaps(lat_g, lon_g), "Google Maps TES": gmaps(lat_t, lon_t),
                "Peta": f"peta/{png.name}",
                "Penyebab": None, "Catatan": None, "Valid (Y/T)": None,
            })
    df = pd.DataFrame(rows)
    write_xlsx(df, out_dir / LEMBAR.name)
    return df


def write_xlsx(df: pd.DataFrame, path: Path):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.worksheet.datavalidation import DataValidation
    wb = Workbook()
    ws = wb.active
    ws.title = SHEET
    cols = list(df.columns)
    ws.append(cols)
    for r in df.itertuples(index=False):
        ws.append(list(r))
    head = Font(bold=True)
    fill_isi = PatternFill("solid", fgColor="FFF7CC")
    for j, c in enumerate(cols, start=1):
        cell = ws.cell(row=1, column=j)
        cell.font = head
        cell.alignment = Alignment(wrap_text=True, vertical="top")
        ws.column_dimensions[cell.column_letter].width = max(12, min(40, len(c) + 4))
    n = len(df) + 1
    link_cols = [cols.index(c) + 1 for c in ("Google Maps centroid", "Google Maps TES", "Peta")]
    for i in range(2, n + 1):
        for j in link_cols:
            cell = ws.cell(row=i, column=j)
            cell.hyperlink = cell.value
            cell.font = Font(color="1D4ED8", underline="single")
        for c in ("Penyebab", "Catatan", "Valid (Y/T)"):
            ws.cell(row=i, column=cols.index(c) + 1).fill = fill_isi
    col = lambda c: ws.cell(row=1, column=cols.index(c) + 1).column_letter
    dv1 = DataValidation(type="list", formula1='"' + ",".join(PENYEBAB) + '"', allow_blank=True)
    dv2 = DataValidation(type="list", formula1='"Y,T"', allow_blank=True)
    ws.add_data_validation(dv1)
    ws.add_data_validation(dv2)
    if n >= 2:
        dv1.add(f"{col('Penyebab')}2:{col('Penyebab')}{n}")
        dv2.add(f"{col('Valid (Y/T)')}2:{col('Valid (Y/T)')}{n}")
    ws.freeze_panes = "D2"
    info = wb.create_sheet("Petunjuk")
    for line in [
        "Lembar validasi manual Titik Aman Semu (aturan utama: DI ≥ 2, T_ideal ≤ 5 menit, T_aktual ≥ 30 menit).",
        "Satu baris = satu grid TAS pada satu level. Nilai diambil dari data/locked/ (hasil-skripsi-v5).",
        "Periksa grid dan TES terdekat di Google Maps dan peta (kolom Peta), lalu isi kolom berlatar kuning:",
        "  Penyebab: " + " / ".join(PENYEBAB),
        "  Catatan: bebas",
        "  Valid (Y/T): Y bila TAS nyata (TES dekat tetapi rute jaringan jauh memutar), T bila artefak data.",
        "Setelah diisi: python -m scripts.rekap_validasi_TAS",
    ]:
        info.append([line])
    info.column_dimensions["A"].width = 120
    wb.save(path)


if __name__ == "__main__":
    d = build()
    print(d.groupby("level").size().reindex(["Baseline", "Rendah", "Sedang", "Tinggi"]).fillna(0).astype(int))
    print("cek T_aktual:", d["Cek T_aktual (hitung ulang)"].value_counts().to_dict())
