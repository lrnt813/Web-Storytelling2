"""EKSPLORASI (tidak diregistrasi sebelum melihat hasil): celah lokal antara jaringan sisi grid dan
sisi TES untuk setiap TAS unik, dalam penyangga 200 m di sekitar garis grid–TES.

    python -m scripts.eksplorasi_celah_lokal
"""
import sys, logging
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
logging.disable(logging.WARNING)
import numpy as np, pandas as pd, networkx as nx, shapely
from pyproj import Transformer
from scipy.spatial import cKDTree
from backend.engine import Cfg, load_data, load_road_network
from scripts import topologi as TP

cfg = Cfg(base_dir=str(ROOT / "data"))
gdf = load_data(cfg); roads, tes = load_road_network(cfg)
print("fclass:", roads["fclass"].value_counts().to_dict())
e = TP.edges_from_roads(roads)
G, nl, tn = TP.graph_from_edges(e)
val = pd.read_excel(ROOT / "output_bab4" / "validasi" / "validasi_TAS.xlsx", sheet_name="Validasi TAS")
to_utm = Transformer.from_crs("EPSG:4326", cfg.target_crs, always_xy=True)
rows = []
for gid, grp in val.groupby("id_grid"):
    r0 = grp.iloc[0]
    gxy = np.array([gdf["cx"].iloc[gid], gdf["cy"].iloc[gid]])
    txy = np.array(to_utm.transform(r0["Lon TES"], r0["Lat TES"]))
    gd, gn = tn.query(gxy); td, tnn = tn.query(txy)
    line = shapely.linestrings([gxy, txy])
    near = tn.query_ball_point((gxy + txy) / 2, r=np.linalg.norm(gxy - txy) / 2 + 200)
    near = [i for i in near if shapely.distance(shapely.points(nl[i]), line) <= 200]
    sub = G.subgraph([tuple(nl[i]) for i in near])
    cg = nx.node_connected_component(sub, tuple(nl[gn])) if tuple(nl[gn]) in sub else set()
    ct = nx.node_connected_component(sub, tuple(nl[tnn])) if tuple(nl[tnn]) in sub else set()
    if cg and ct and cg is not ct and not (cg & ct):
        A, B = np.array(list(cg)), np.array(list(ct))
        gap = float(cKDTree(B).query(A)[0].min())
    else:
        gap = 0.0 if (cg & ct) else np.nan
    rows.append({"id_grid": gid, "snap_grid_m": gd, "snap_tes_m": td, "euclid_m": np.linalg.norm(gxy - txy),
                 "terhubung_lokal_200m": bool(cg & ct), "celah_lokal_m": gap})
d = pd.DataFrame(rows)
print(d.describe().round(1).to_string())
print("terhubung lokal:", d["terhubung_lokal_200m"].sum(), "dari", len(d))
print("celah lokal (tidak terhubung lokal):", d.loc[~d["terhubung_lokal_200m"], "celah_lokal_m"].describe().round(1).to_dict())
print(pd.cut(d.loc[~d["terhubung_lokal_200m"], "celah_lokal_m"], [0, 5, 10, 20, 50, 100, 1000]).value_counts().sort_index())
d.to_csv(ROOT / "output_bab4" / "diagnostik_topologi" / "celah_lokal_TAS.csv", index=False)
