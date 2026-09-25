"""Laporan dampak koreksi snapping (Putaran 6): v5 (snapping ke verteks) vs v6 (snapping ke ruas).

    python -m scripts.dampak_koreksi_snapping

Membaca hasil terkunci v5 (data/locked/arsip_v5/), hasil terkunci v6 (data/locked/), dan lembar validasi v5
yang sudah diisi (output_bab4/validasi/validasi_TAS_v5_terisi.xlsx). Keluaran:
  docs/DAMPAK_KOREKSI_SNAPPING.md
  output_bab4/dampak_koreksi_snapping/   CSV pendukung dan peta sebelum/sesudah (10 grid)

TAS v5 "ditandai kesalahan snapping" = baris lembar v5 terisi yang teks Penyebab/Catatan-nya memuat kata
"snapping" (aturan kata kunci kode F). Peta sebelum/sesudah: 10 grid Baseline dengan |ΔT_aktual| terbesar di
antara grid yang terjangkau di kedua versi (T_aktual < T_pen). Rute v5 direkonstruksi dengan snapping ke
verteks (metode v5), rute v6 dengan snapping ke ruas (backend.thesis.tas_routes).
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

LOCKED = PROJECT_ROOT / "data" / "locked"
ARSIP_V5 = LOCKED / "arsip_v5"
LEMBAR_V5 = PROJECT_ROOT / "output_bab4" / "validasi" / "validasi_TAS_v5_terisi.xlsx"
OUT = PROJECT_ROOT / "output_bab4" / "dampak_koreksi_snapping"
DOC = PROJECT_ROOT / "docs" / "DAMPAK_KOREKSI_SNAPPING.md"
LEVELS = [("baseline", "Baseline"), ("rendah", "Rendah"), ("sedang", "Sedang"), ("tinggi", "Tinggi")]
LABEL_KEY = {lab: key for key, lab in LEVELS}
STATUS = {0: "Non-TAS", 1: "TAS", 2: "TES terdekat tidak terjangkau", 3: "Tergenang"}
GRID_KHUSUS = (8895, 9632)
N_PETA = 10


def fmt(v, d=2):
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return "–"
    s = f"{v:,.{d}f}"
    return s.replace(",", "·").replace(".", ",").replace("·", ".")


def md_table(df: pd.DataFrame) -> list:
    L = ["| " + " | ".join(map(str, df.columns)) + " |", "|" + "---|" * len(df.columns)]
    for r in df.itertuples(index=False):
        L.append("| " + " | ".join("" if (isinstance(v, float) and np.isnan(v)) else str(v) for v in r) + " |")
    return L


def route_vertex(graph_pack, gxy, txy, max_snap=300.0):
    """Rute metode v5: snapping ke VERTEKS terdekat (≤ 300 m)."""
    from scipy.sparse.csgraph import dijkstra
    from backend.engine import graph_csr
    G, nl, tn = graph_pack
    gd, gn = tn.query(gxy)
    td, tnode = tn.query(txy)
    if gd > max_snap or td > max_snap:
        return None
    dist, pred = dijkstra(graph_csr(G, nl), directed=False, indices=int(tnode), return_predecessors=True)
    if not np.isfinite(dist[gn]):
        return None
    path = [int(gn)]
    while path[-1] != int(tnode):
        path.append(int(pred[path[-1]]))
    return {"xy": [tuple(gxy)] + [tuple(nl[i]) for i in path] + [tuple(txy)], "jarak_m": float(gd + dist[gn] + td)}


def maps(rows, gdf, roads, pack, tes_xy_by_id):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from backend import thesis as T
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("peta_*.png"):
        old.unlink()
    files = []
    for r in rows:
        gi = int(r["id_grid"])
        gxy = np.array([gdf["cx"].iloc[gi], gdf["cy"].iloc[gi]])
        txy = np.array(tes_xy_by_id[r["id_tes"]])
        old = route_vertex(pack, gxy, txy)
        new = T.tas_routes(pack, gxy[None], txy[None])[0]
        pts = [gxy, txy] + (old["xy"] if old else []) + (new["xy"] if new else [])
        x0, x1 = min(p[0] for p in pts) - 150, max(p[0] for p in pts) + 150
        y0, y1 = min(p[1] for p in pts) - 150, max(p[1] for p in pts) + 150
        fig, axes = plt.subplots(1, 2, figsize=(9, 4.6), dpi=110)
        for ax, rt, lab, t_akt in ((axes[0], old, "v5 (snapping ke verteks)", r["T_aktual v5"]),
                                   (axes[1], new, "v6 (snapping ke ruas)", r["T_aktual v6"])):
            roads.cx[x0:x1, y0:y1].plot(ax=ax, color="#9ca3af", linewidth=0.6)
            geom = gdf.geometry.iloc[gi]
            for poly in getattr(geom, "geoms", [geom]):
                ax.fill(*poly.exterior.xy, facecolor="#a855f7", alpha=0.35, edgecolor="#6b21a8", linewidth=1)
            ax.plot([gxy[0], txy[0]], [gxy[1], txy[1]], color="#111827", linestyle=":", linewidth=1.2)
            if rt:
                p = rt["xy"]
                ax.plot([q[0] for q in p[1:-1]], [q[1] for q in p[1:-1]], color="#2563eb", linewidth=1.6)
                for a_, b_ in ((p[0], p[1]), (p[-2], p[-1])):
                    ax.plot([a_[0], b_[0]], [a_[1], b_[1]], color="#f97316", linewidth=1.4, linestyle="--")
            ax.plot(*txy, marker="*", markersize=12, color="#16a34a")
            ax.set_xlim(x0, x1)
            ax.set_ylim(y0, y1)
            ax.set_aspect("equal")
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_title(f"{lab}\nT_aktual {fmt(t_akt)} menit", fontsize=8)
        fig.suptitle(f"Grid {gi} (Baseline) — biru = rute jaringan; oranye putus = ruas snapping; ··· garis lurus",
                     fontsize=8)
        fig.tight_layout()
        png = OUT / f"peta_{gi}.png"
        fig.savefig(png)
        plt.close(fig)
        files.append(png)
    return files


def main():
    from backend import thesis as T
    from backend.engine import (Cfg, build_road_graph, filter_tes, graph_edge_arrays, load_data, load_road_network,
                                simulate_hazard, snap_points, snap_to_segments)
    logging.basicConfig(level=logging.WARNING)
    R5 = json.loads((ARSIP_V5 / "thesis_results.json").read_text(encoding="utf-8"))
    R6 = json.loads((LOCKED / "thesis_results.json").read_text(encoding="utf-8"))
    g5 = pd.read_csv(ARSIP_V5 / "thesis_grid_results.csv.gz")
    g6 = pd.read_csv(LOCKED / "thesis_grid_results.csv.gz")
    v5 = pd.read_excel(LEMBAR_V5, sheet_name="Validasi TAS")
    OUT.mkdir(parents=True, exist_ok=True)
    tp5, tp6 = float(R5["t_pen"]), float(R6["t_pen"])
    L = ["# Dampak koreksi snapping (v5 → v6)", "",
         "v5 = `data/locked/arsip_v5/` (snapping ke **verteks** jalan terdekat); v6 = `data/locked/` (snapping ke "
         "**ruas** terdekat dengan simpul virtual; METODOLOGI §4, CATATAN P6-1). Semua aturan lain sama. Dibuat oleh "
         "`python -m scripts.dampak_koreksi_snapping`; angka dari hasil terkunci.",
         f"T_pen v5 = {fmt(tp5)} menit; T_pen v6 = {fmt(tp6)} menit (aturan sama: 3 × waktu maksimum valid di Baseline).", ""]

    # 1. TAS v5 yang ditandai kesalahan snapping
    teks = (v5["Penyebab"].fillna("").astype(str) + " " + v5["Catatan"].fillna("").astype(str)).str.lower()
    fl = v5[teks.str.contains("snapping")].copy()
    rows = []
    for _, r in fl.iterrows():
        key, gi = LABEL_KEY[r["level"]], int(r["id_grid"])
        st6 = int(g6.at[gi, f"tas_status_{key}"])
        rows.append({"id_grid": gi, "Level": r["level"], "T_aktual v5": fmt(g5.at[gi, f"t_aktual_{key}"]),
                     "DI v5": fmt(g5.at[gi, f"di_{key}"]), "Status v6": STATUS[st6],
                     "T_aktual v6": fmt(g6.at[gi, f"t_aktual_{key}"]), "DI v6": fmt(g6.at[gi, f"di_{key}"])})
    urut = {lab: i for i, (_, lab) in enumerate(LEVELS)}
    t1 = pd.DataFrame(rows)
    t1 = t1.iloc[np.lexsort((t1["id_grid"].values, t1["Level"].map(urut).values))].reset_index(drop=True)
    t1.to_csv(OUT / "tas_v5_ditandai_snapping.csv", index=False, encoding="utf-8-sig")
    still = (t1["Status v6"] == "TAS")
    L += ["## 1. Nasib TAS v5 yang ditandai kesalahan snapping", "",
          f"Baris lembar v5 terisi yang teks Penyebab/Catatan-nya memuat \"snapping\": **{len(t1)}** "
          f"({', '.join(f'{lab} {int((t1.Level == lab).sum())}' for _, lab in LEVELS if (t1.Level == lab).any())}). "
          f"Di v6: masih TAS **{int(still.sum())}**, tidak lagi TAS **{int((~still).sum())}** "
          f"({'; '.join(f'{k} {v}' for k, v in t1.loc[~still, 'Status v6'].value_counts().items())}).", ""]
    L += md_table(t1) + [""]

    # 2. grid 8895 dan 9632
    rows = []
    for gi in GRID_KHUSUS:
        for key, lab in LEVELS:
            rows.append({"id_grid": gi, "Level": lab, "Status v5": STATUS[int(g5.at[gi, f"tas_status_{key}"])],
                         "T_aktual v5": fmt(g5.at[gi, f"t_aktual_{key}"]), "DI v5": fmt(g5.at[gi, f"di_{key}"]),
                         "Status v6": STATUS[int(g6.at[gi, f"tas_status_{key}"])],
                         "T_aktual v6": fmt(g6.at[gi, f"t_aktual_{key}"]), "DI v6": fmt(g6.at[gi, f"di_{key}"]),
                         "T_ideal": fmt(g6.at[gi, f"t_ideal_{key}"])})
    L += ["## 2. Grid 8895 dan 9632 (kasus \"belum terjelaskan\" di v5)", ""] + md_table(pd.DataFrame(rows)) + [""]

    # 3. jarak snapping verteks vs ruas
    cfg = Cfg(base_dir=str(PROJECT_ROOT / "data"))
    gdf = load_data(cfg)
    roads, tes = load_road_network(cfg)
    gxy = np.column_stack([gdf["cx"].values, gdf["cy"].values])
    rows, pack_b = [], None
    for key, lab in LEVELS:
        lv = T.LEVEL_BY_KEY[key]
        pack = build_road_graph(roads, T.SKENARIO, lv["intensity"], cfg)
        if key == "baseline":
            pack_b = pack
        _, _, tes_sim, _ = simulate_hazard(gdf, roads, tes, T.SKENARIO, lv["intensity"], cfg)
        tes_v, _ = filter_tes(tes_sim, T.SKENARIO, cfg)
        txy = np.column_stack([tes_v.geometry.x.values, tes_v.geometry.y.values])
        ea, eb, _ = graph_edge_arrays(pack[0], pack[1])
        for nama, pts in (("grid", gxy), ("TES valid", txy)):
            dv, _, okv = snap_points(pts, pack[2])
            dr, _, _, okr = snap_to_segments(pts, pack[1], ea, eb)
            rows.append({"Level": lab, "Titik": nama, "n": len(pts),
                         "Median verteks (m)": fmt(np.median(dv)), "P90 verteks (m)": fmt(np.percentile(dv, 90)),
                         "Median ruas (m)": fmt(np.median(dr[okr])), "P90 ruas (m)": fmt(np.percentile(dr[okr], 90)),
                         "Ter-snap ≤ 300 m verteks": int(okv.sum()), "Ter-snap ≤ 300 m ruas": int(okr.sum())})
    t3 = pd.DataFrame(rows)
    t3.to_csv(OUT / "jarak_snapping.csv", index=False, encoding="utf-8-sig")
    L += ["## 3. Jarak snapping (centroid grid dan TES valid ke jaringan terbuka)", "",
          "Median/P90 verteks dihitung atas semua titik (seperti v5); median/P90 ruas atas titik yang ter-snap "
          "≤ 300 m.", ""] + md_table(t3) + [""]

    # 4. TAS, Terputus, Jauh; 5. median/P90 waktu minimum
    rows4, rows5 = [], []
    for key, lab in LEVELS:
        a5, a6 = R5["levels"][key], R6["levels"][key]
        k5, k6 = a5["kategori_akses"]["30"], a6["kategori_akses"]["30"]
        rows4.append({"Level": lab, "TAS v5": a5["tas"]["jumlah_tas"], "TAS v6": a6["tas"]["jumlah_tas"],
                      "TES terdekat tidak terjangkau v5": a5["tas"]["jumlah_tes_terdekat_tidak_terjangkau"],
                      "TES terdekat tidak terjangkau v6": a6["tas"]["jumlah_tes_terdekat_tidak_terjangkau"],
                      "Terputus v5": k5["Terputus"]["jumlah_grid"], "Terputus v6": k6["Terputus"]["jumlah_grid"],
                      "Jauh (30) v5": k5["Jauh"]["jumlah_grid"], "Jauh (30) v6": k6["Jauh"]["jumlah_grid"]})
        dry = g6[f"tergenang_{key}"].values == 0
        w5, w6 = g5.loc[dry, f"waktu_min_{key}"].values, g6.loc[dry, f"waktu_min_{key}"].values
        rows5.append({"Level": lab, "Median v5": fmt(np.median(w5)), "Median v6": fmt(np.median(w6)),
                      "P90 v5": fmt(np.percentile(w5, 90)), "P90 v6": fmt(np.percentile(w6, 90)),
                      "Median terjangkau v5": fmt(np.median(w5[w5 < tp5 - 1e-3])),
                      "Median terjangkau v6": fmt(np.median(w6[w6 < tp6 - 1e-3])),
                      "P90 terjangkau v5": fmt(np.percentile(w5[w5 < tp5 - 1e-3], 90)),
                      "P90 terjangkau v6": fmt(np.percentile(w6[w6 < tp6 - 1e-3], 90))})
    L += ["## 4. Jumlah TAS, Terputus, dan Jauh per level", "",
          "TAS = aturan utama; Terputus dan Jauh = kategori akses dengan batas 30 menit.", ""]
    L += md_table(pd.DataFrame(rows4)) + [""]
    L += ["## 5. Waktu tempuh minimum per level (grid non-Tergenang, menit)", "",
          "\"Terjangkau\" = waktu < T_pen versi masing-masing. Dari kolom `waktu_min_<level>` CSV grid terkunci "
          "(dibulatkan 3 desimal).", ""] + md_table(pd.DataFrame(rows5)) + [""]

    # 6. peta 10 grid dengan perubahan T_aktual terbesar (Baseline, terjangkau di kedua versi)
    ta5, ta6 = g5["t_aktual_baseline"].values, g6["t_aktual_baseline"].values
    ok = (ta5 < tp5 - 1e-3) & (ta6 < tp6 - 1e-3)
    d = np.where(ok, ta6 - ta5, np.nan)
    top = np.argsort(-np.nan_to_num(np.abs(d), nan=-1))[:N_PETA]
    rows6 = [{"id_grid": int(i), "id_tes": g6.at[i, "id_tes_terdekat_baseline"], "T_aktual v5": ta5[i],
              "T_aktual v6": ta6[i], "Selisih (menit)": d[i], "DI v5": g5.at[i, "di_baseline"],
              "DI v6": g6.at[i, "di_baseline"], "Status v5": STATUS[int(g5.at[i, "tas_status_baseline"])],
              "Status v6": STATUS[int(g6.at[i, "tas_status_baseline"])]} for i in top]
    tes_b, _ = filter_tes(tes, T.SKENARIO, cfg)
    tes_xy = dict(zip(tes_b["id_tes"], zip(tes_b.geometry.x, tes_b.geometry.y)))
    files = maps(rows6, gdf, roads, pack_b, tes_xy)
    t6 = pd.DataFrame(rows6)
    t6.to_csv(OUT / "top10_perubahan_t_aktual.csv", index=False, encoding="utf-8-sig")
    t6f = t6.assign(**{c: t6[c].map(fmt) for c in ("T_aktual v5", "T_aktual v6", "Selisih (menit)", "DI v5", "DI v6")})
    L += ["## 6. Peta sebelum/sesudah: 10 grid dengan perubahan T_aktual terbesar", "",
          "Baseline; grid yang terjangkau di kedua versi; diurutkan menurut |T_aktual v6 − T_aktual v5|. Peta: "
          "`output_bab4/dampak_koreksi_snapping/peta_<id_grid>.png` (kiri v5, kanan v6).", ""]
    L += md_table(t6f.drop(columns=["id_tes"])) + [""]
    L += [f"- `output_bab4/dampak_koreksi_snapping/{f.name}`" for f in files] + [""]
    DOC.write_text("\n".join(L), encoding="utf-8")
    print(f"ditulis: {DOC}")


if __name__ == "__main__":
    sys.exit(main())
