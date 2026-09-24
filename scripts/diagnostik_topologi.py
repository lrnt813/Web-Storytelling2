"""Diagnostik topologi jaringan jalan dan analisis sensitivitas jaringan yang dirapikan.

    python -m scripts.diagnostik_topologi

Hasil terkunci v5 tidak diubah. Definisi dan toleransi (ditetapkan sebelum melihat hasil):
docs/CATATAN_TEMUAN.md, bagian "Diagnostik topologi jaringan". Keluaran:
  output_bab4/diagnostik_topologi/   JSON, CSV, peta sebaran, dan peta sebelum/sesudah
(ringkasan dan penilaian ditulis di docs/DIAGNOSTIK_TOPOLOGI.md dari keluaran ini)
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

import shapely
from backend import thesis as T
from backend.engine import Cfg, build_road_graph, graph_csr, load_data, load_road_network, road_closed_mask
from scripts import topologi as TP

LOCKED = PROJECT_ROOT / "data" / "locked"
OUT = PROJECT_ROOT / "output_bab4" / "diagnostik_topologi"
TOLS_DIAG = (0.5, 1.0, 2.0, 5.0)
TOL_UTAMA, TOL_SENS = 1.0, 2.0
TAS_TOL_NM = 2.0
TAS_BUFFER_M = 100.0
THRS = tuple(sorted((T.EVAC_TIME_MIN,) + tuple(T.EVAC_TIME_SENS)))
LEVEL_LABEL = {lv["key"]: lv["label"] for lv in T.LEVELS}


def level_results(gdf, roads, tes, cfg, t_pen, edges):
    """Aksesibilitas + TAS per level pada jaringan `edges` (penutupan ruas per level diterapkan)."""
    out = {}
    for lv in T.LEVELS:
        closed = road_closed_mask(roads, T.SKENARIO, lv["intensity"], cfg)
        G, nl, tn = TP.graph_from_edges(TP.edges_for_level(edges, closed))
        prep = T.prepare_level(gdf, roads, tes, lv["intensity"], cfg, t_pen=t_pen, graph_pack=(G, nl, tn))
        df = prep["df"]
        out[lv["key"]] = {
            "df": df, "tas": prep["tas"], "graph": (G, nl, tn), "tes_v": prep["tes_v"],
            "akses": {thr: T.access_category(df["waktu_tes_min"].values, df["tergenang"].values, t_pen, thr)
                      for thr in (T.EVAC_TIME_MIN,) + tuple(T.EVAC_TIME_SENS)},
        }
    return out


def summarize(res, t_pen):
    rows = {}
    for key, r in res.items():
        df = r["df"]
        non = df["tergenang"].values == 0
        w = df.loc[non, "waktu_tes_min"].values
        reach = w < t_pen - 1e-9
        s = {"tas": int((r["tas"]["status"] == 1).sum()),
             "median_waktu_min": float(np.median(w)), "p90_waktu_min": float(np.percentile(w, 90)),
             "median_waktu_min_terjangkau": float(np.median(w[reach])),
             "p90_waktu_min_terjangkau": float(np.percentile(w[reach], 90))}
        for thr, cat in r["akses"].items():
            s[f"terputus_{thr:g}"] = int((cat == 2).sum())
            s[f"jauh_{thr:g}"] = int((cat == 1).sum())
            s[f"terjangkau_{thr:g}"] = int((cat == 0).sum())
        rows[key] = s
    return rows


def route_xy(graph, gxy, txy):
    from scipy.sparse.csgraph import dijkstra
    G, nl, tn = graph
    csr = graph_csr(G, nl)
    _, g_node = tn.query(gxy, k=1)
    _, t_node = tn.query(txy, k=1)
    dist, pred = dijkstra(csr, directed=False, indices=int(t_node), return_predecessors=True)
    if not np.isfinite(dist[g_node]):
        return None
    path = [int(g_node)]
    while path[-1] != int(t_node):
        path.append(int(pred[path[-1]]))
    return [tuple(gxy)] + [tuple(nl[i]) for i in path] + [tuple(txy)]


def main():
    logging.basicConfig(level=logging.WARNING)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from pyproj import Transformer

    OUT.mkdir(parents=True, exist_ok=True)
    R = json.loads((LOCKED / "thesis_results.json").read_text(encoding="utf-8"))
    grid5 = pd.read_csv(LOCKED / "thesis_grid_results.csv.gz")
    pool5 = pd.read_csv(LOCKED / "thesis_pooled_results.csv.gz", usecols=["id_grid", "level", "klaster_k4"])
    t_pen = float(R["t_pen"])
    cfg = Cfg(base_dir=str(PROJECT_ROOT / "data"))
    gdf = load_data(cfg)
    roads, tes = load_road_network(cfg)
    gxy_all = np.column_stack([gdf["cx"].values, gdf["cy"].values])

    # ── 1. topologi Baseline ────────────────────────────────────────────────
    e = TP.edges_from_roads(roads)
    G0, nl0, tn0 = TP.graph_from_edges(e)
    Ge, _, _ = build_road_graph(roads, T.SKENARIO, 0.0, cfg)
    sama_engine = (G0.number_of_nodes() == Ge.number_of_nodes() and G0.number_of_edges() == Ge.number_of_edges())
    stats = TP.component_stats(G0)
    cross = TP.crossings(e)
    nm = TP.near_misses(e, G0, tol_max=max(TOLS_DIAG))
    diag = {
        "graf_sama_dengan_engine": bool(sama_engine),
        **stats,
        "near_miss": {f"{t:g}": int((nm["dist"] <= t).sum()) for t in TOLS_DIAG},
        "perpotongan_tanpa_simpul": {"total": int(len(cross)), "non_khusus": int((~cross["khusus"]).sum()),
                                     "melibatkan_jembatan_terowongan_layer": int(cross["khusus"].sum())},
        "segmen_khusus": int(TP.special_mask(roads).sum()),
    }
    nm.to_csv(OUT / "near_miss.csv", index=False)
    cross.to_csv(OUT / "perpotongan_tanpa_simpul.csv", index=False)

    fig, ax = plt.subplots(figsize=(8, 10), dpi=120)
    roads.plot(ax=ax, color="#d1d5db", linewidth=0.15)
    c0 = cross[~cross["khusus"]]
    ax.scatter(c0["x"], c0["y"], s=4, color="#dc2626", label=f"perpotongan tanpa simpul (non-khusus, {len(c0):,})".replace(",", "."))
    for tol, col in ((1.0, "#2563eb"), (2.0, "#16a34a"), (5.0, "#f59e0b")):
        lo = {1.0: -1, 2.0: 1.0, 5.0: 2.0}[tol]
        sel = (nm["dist"] > lo) & (nm["dist"] <= tol)
        ax.scatter(nm.loc[sel, "x"], nm.loc[sel, "y"], s=4, color=col,
                   label=f"near-miss {'≤' if lo < 0 else f'{lo:g}–'}{tol:g} m ({int(sel.sum()):,})".replace(",", "."))
    ax.set_axis_off()
    ax.legend(loc="lower left", fontsize=7, markerscale=3)
    ax.set_title("Near-miss ujung buntu dan perpotongan tanpa simpul (graf Baseline)", fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "peta_near_miss_perpotongan.png")
    plt.close(fig)

    # ── 2. per TAS ──────────────────────────────────────────────────────────
    val = pd.read_excel(PROJECT_ROOT / "output_bab4" / "validasi" / "validasi_TAS.xlsx", sheet_name="Validasi TAS")
    to_utm = Transformer.from_crs("EPSG:4326", cfg.target_crs, always_xy=True)
    comp = TP.node_component(G0)
    nm2 = nm[nm["dist"] <= TAS_TOL_NM]
    art_pts = np.concatenate([np.column_stack([nm2["x"], nm2["y"]]), np.column_stack([c0["x"], c0["y"]])])
    art_kind = np.array(["near-miss"] * len(nm2) + ["perpotongan"] * len(c0))
    tree = shapely.STRtree(shapely.points(art_pts))
    rows = []
    for gid, grp in val.groupby("id_grid", sort=True):
        r0 = grp.iloc[0]
        gxy = gxy_all[int(gid)]
        txy = np.array(to_utm.transform(r0["Lon TES"], r0["Lat TES"]))
        _, gn = tn0.query(gxy, k=1)
        _, tnn = tn0.query(txy, k=1)
        buf = shapely.buffer(shapely.linestrings([gxy, txy]), TAS_BUFFER_M)
        hit = tree.query(buf, predicate="intersects")
        kinds = art_kind[hit]
        n_nm, n_cr = int((kinds == "near-miss").sum()), int((kinds == "perpotongan").sum())
        rows.append({"id_grid": int(gid), "level_TAS": ", ".join(grp["level"]), "TES terdekat": r0["TES terdekat"],
                     "komponen_grid": comp.get(tuple(nl0[gn])), "komponen_TES": comp.get(tuple(nl0[tnn])),
                     "komponen_sama": comp.get(tuple(nl0[gn])) == comp.get(tuple(nl0[tnn])),
                     "near_miss_2m_dalam_100m": n_nm, "perpotongan_dalam_100m": n_cr,
                     "klasifikasi": "kemungkinan artefak topologi" if (n_nm + n_cr) > 0 else "tidak terdeteksi artefak"})
    per_tas = pd.DataFrame(rows)
    per_tas.to_csv(OUT / "per_TAS.csv", index=False, encoding="utf-8-sig")

    # ── 3. jaringan dirapikan: hitung ulang per level ───────────────────────
    res = {"mentah": level_results(gdf, roads, tes, cfg, t_pen, e)}
    for tol in (TOL_UTAMA, TOL_SENS):
        ce = TP.cleaned_edges(e, cross, nm, tol)
        Gc, _, _ = TP.graph_from_edges(ce)
        diag[f"dirapikan_{tol:g}m"] = {**TP.component_stats(Gc), "sambungan": int((nm["dist"] <= tol).sum()),
                                      "perpotongan_disambung": int(len(c0))}
        res[f"dirapikan_{tol:g}m"] = level_results(gdf, roads, tes, cfg, t_pen, ce)
    summ = {k: summarize(v, t_pen) for k, v in res.items()}

    # reproduksi v5 dengan graf mentah
    repro = {}
    for key in T.LEVEL_KEYS:
        repro[key] = {
            "tas_sama": bool(np.array_equal(res["mentah"][key]["tas"]["status"], grid5[f"tas_status_{key}"].values)),
            "waktu_min_sama": bool(np.allclose(res["mentah"][key]["df"]["waktu_tes_min"].values,
                                               grid5[f"waktu_min_{key}"].values, atol=1e-3)),
        }
    diag["reproduksi_v5_graf_mentah"] = repro

    comp_rows, lost = [], {}
    for name in ("dirapikan_1m", "dirapikan_2m"):
        for key in T.LEVEL_KEYS:
            v5 = grid5[f"tas_status_{key}"].values == 1
            new = res[name][key]["tas"]["status"] == 1
            k4 = pool5[(pool5["level"] == key) & (pool5["klaster_k4"] == 3)]["id_grid"].values
            w_new = res[name][key]["df"]["waktu_tes_min"].values
            w_v5 = res["mentah"][key]["df"]["waktu_tes_min"].values   # tak dibulatkan (CSV terkunci dibulatkan 3 desimal)
            s5, sc = summ["mentah"][key], summ[name][key]
            comp_rows.append({
                "jaringan": name, "level": LEVEL_LABEL[key],
                "TAS v5": int(v5.sum()), "TAS dirapikan": int(new.sum()),
                "TAS v5 hilang": int((v5 & ~new).sum()), "TAS baru": int((~v5 & new).sum()),
                **{f"Terputus {t:g} v5": s5[f"terputus_{t:g}"] for t in (T.EVAC_TIME_MIN,)},
                **{f"Terputus {t:g} dirapikan": sc[f"terputus_{t:g}"] for t in (T.EVAC_TIME_MIN,)},
                **{f"Jauh {t:g} v5": s5[f"jauh_{t:g}"] for t in THRS},
                **{f"Jauh {t:g} dirapikan": sc[f"jauh_{t:g}"] for t in THRS},
                "Median waktu min v5": s5["median_waktu_min"], "Median waktu min dirapikan": sc["median_waktu_min"],
                "P90 waktu min v5": s5["p90_waktu_min"], "P90 waktu min dirapikan": sc["p90_waktu_min"],
                "Median waktu min terjangkau v5": s5["median_waktu_min_terjangkau"],
                "Median waktu min terjangkau dirapikan": sc["median_waktu_min_terjangkau"],
                "P90 waktu min terjangkau v5": s5["p90_waktu_min_terjangkau"],
                "P90 waktu min terjangkau dirapikan": sc["p90_waktu_min_terjangkau"],
                "Baris Tipologi 4 (K=4) v5": int(len(k4)),
                "Tipologi 4 tak terjangkau di v5": int((w_v5[k4] >= t_pen - 1e-9).sum()),
                "Tipologi 4 menjadi terjangkau": int(((w_v5[k4] >= t_pen - 1e-9) & (w_new[k4] < t_pen - 1e-9)).sum()),
            })
            lost[(name, key)] = np.where(v5 & ~new)[0]
    comp_df = pd.DataFrame(comp_rows)
    comp_df.to_csv(OUT / "perbandingan_v5_vs_dirapikan.csv", index=False, encoding="utf-8-sig")

    # ── 4. peta sebelum/sesudah: 10 TAS v5 dengan DI tertinggi ──────────────
    pdir = OUT / "peta_sebelum_sesudah"
    pdir.mkdir(exist_ok=True)
    top = val.sort_values("DI_t", ascending=False).head(10)
    key_of = {lv["label"]: lv["key"] for lv in T.LEVELS}
    top_rows = []
    for _, r0 in top.iterrows():
        key = key_of[r0["level"]]
        gid = int(r0["id_grid"])
        gxy = gxy_all[gid]
        txy = np.array(to_utm.transform(r0["Lon TES"], r0["Lat TES"]))
        fig, axes = plt.subplots(1, 2, figsize=(8.4, 4.4), dpi=110)
        info = []
        for ax, name, title in ((axes[0], "mentah", "v5 (jaringan asli)"), (axes[1], "dirapikan_1m", "dirapikan 1 m")):
            path = route_xy(res[name][key]["graph"], gxy, txy)
            st = int(res[name][key]["tas"]["status"][gid])
            ta = float(res[name][key]["tas"]["t_aktual"][gid])
            di = float(res[name][key]["tas"]["detour_index"][gid])
            info.append((ta, di, st))
            xs = [gxy[0], txy[0]] + ([p[0] for p in path] if path else [])
            ys = [gxy[1], txy[1]] + ([p[1] for p in path] if path else [])
            x0, x1, y0, y1 = min(xs) - 150, max(xs) + 150, min(ys) - 150, max(ys) + 150
            sub = roads.cx[x0:x1, y0:y1]
            sub.plot(ax=ax, color="#9ca3af", linewidth=0.6)
            for poly in getattr(gdf.geometry.iloc[gid], "geoms", [gdf.geometry.iloc[gid]]):
                ax.fill(*poly.exterior.xy, facecolor="#a855f7", alpha=0.35, edgecolor="#6b21a8")
            ax.plot([gxy[0], txy[0]], [gxy[1], txy[1]], ":", color="#111827")
            if path:
                ax.plot([p[0] for p in path], [p[1] for p in path], color="#2563eb", linewidth=1.8)
            ax.plot(*txy, marker="*", markersize=12, color="#16a34a")
            if name != "mentah":
                nn = nm[(nm["dist"] <= TOL_UTAMA) & nm["x"].between(x0, x1) & nm["y"].between(y0, y1)]
                cc = c0[c0["x"].between(x0, x1) & c0["y"].between(y0, y1)]
                ax.scatter(nn["x"], nn["y"], s=14, color="#f97316", zorder=5)
                ax.scatter(cc["x"], cc["y"], s=14, color="#dc2626", marker="x", zorder=5)
            ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
            ax.set_title(f"{title}: T_aktual {ta:.1f} mnt, DI {di:.1f}, {T.TAS_STATUS[st]}", fontsize=7)
        fig.suptitle(f"Grid {gid} — {r0['level']} — TES: {r0['TES terdekat']}\n"
                     "biru = rute; oranye = near-miss ≤ 1 m yang disambung; x merah = perpotongan yang disambung",
                     fontsize=7.5)
        fig.tight_layout()
        fig.savefig(pdir / f"{key}_{gid}.png")
        plt.close(fig)
        top_rows.append({"id_grid": gid, "level": r0["level"], "DI v5": info[0][1], "T_aktual v5": info[0][0],
                         "DI dirapikan 1 m": info[1][1], "T_aktual dirapikan 1 m": info[1][0],
                         "status dirapikan 1 m": T.TAS_STATUS[info[1][2]]})
    top_df = pd.DataFrame(top_rows)
    top_df.to_csv(OUT / "top10_DI_sebelum_sesudah.csv", index=False, encoding="utf-8-sig")

    json.dump({"diagnostik": diag, "ringkasan": summ,
               "per_TAS_klasifikasi": per_tas["klasifikasi"].value_counts().to_dict(),
               "per_TAS_komponen_sama": int(per_tas["komponen_sama"].sum())},
              open(OUT / "diagnostik_topologi.json", "w", encoding="utf-8"), indent=1, default=float)
    return diag, per_tas, comp_df, top_df


if __name__ == "__main__":
    diag, per_tas, comp_df, top_df = main()
    print(json.dumps(diag, indent=1, default=float))
    print(per_tas["klasifikasi"].value_counts())
    pd.set_option("display.width", 250)
    print(comp_df.to_string())
    print(top_df.to_string())
