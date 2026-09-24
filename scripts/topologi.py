"""Fungsi diagnostik dan perapian topologi jaringan jalan (analisis sensitivitas; tidak dipakai
pipeline utama). Definisi dan toleransi: docs/CATATAN_TEMUAN.md (bagian diagnostik topologi).

Graf dibangun seperti backend.engine.build_road_graph: simpul = ujung segmen dibulatkan 0,01 m, sisi =
segmen, bobot = panjang (terpendek bila ganda). Setiap sisi membawa indeks segmen sumber (`src`) agar
penutupan ruas per level dapat diterapkan pada jaringan yang dirapikan.
"""
from dataclasses import dataclass
from typing import Optional

import networkx as nx
import numpy as np
import pandas as pd
import shapely
from scipy.spatial import cKDTree

NET_EXCLUDE_M = 20.0          # near-miss: ujung sisi sasaran tidak boleh terjangkau ≤ 20 m lewat jaringan
MIN_CONNECTOR_M = 0.01        # panjang minimum sambungan (bobot 0 diabaikan csgraph)
NM_COLS = ["x", "y", "dist", "edge", "px", "py", "src_ujung"]


@dataclass
class Edges:
    """Sisi graf: koordinat ujung (dibulatkan 0,01 m), panjang, segmen sumber, segmen sumber kedua
    (untuk sambungan; −1 bila bukan sambungan), dan penanda segmen khusus (jembatan/terowongan/layer)."""
    u: np.ndarray
    v: np.ndarray
    w: np.ndarray
    src: np.ndarray
    src2: np.ndarray
    special: np.ndarray

    def __len__(self):
        return len(self.w)

    def subset(self, keep: np.ndarray) -> "Edges":
        return Edges(self.u[keep], self.v[keep], self.w[keep], self.src[keep], self.src2[keep], self.special[keep])


def special_mask(roads: pd.DataFrame) -> np.ndarray:
    b = roads["bridge"].astype(str).str.upper().eq("T") if "bridge" in roads else False
    t = roads["tunnel"].astype(str).str.upper().eq("T") if "tunnel" in roads else False
    lay = roads["layer"].fillna(0).astype(int).ne(0) if "layer" in roads else False
    return np.asarray(b | t | lay, dtype=bool)


def edges_from_roads(roads) -> Edges:
    """Satu sisi per pasangan titik berurutan pada setiap segmen (semua segmen data berupa garis 2 titik)."""
    us, vs, ws, src = [], [], [], []
    for i, g in enumerate(roads.geometry.values):
        if g is None or g.is_empty:
            continue
        for line in ([g] if g.geom_type == "LineString" else list(g.geoms)):
            c = np.asarray(line.coords)[:, :2]
            for a, b in zip(c[:-1], c[1:]):
                us.append(a)
                vs.append(b)
                ws.append(float(np.hypot(*(b - a))))
                src.append(i)
    sp = special_mask(roads)
    src = np.asarray(src)
    return Edges(np.round(np.asarray(us), 2), np.round(np.asarray(vs), 2), np.asarray(ws), src,
                 np.full(len(src), -1), sp[src])


def graph_from_edges(e: Edges):
    """nx.Graph (bobot terpendek bila ganda; loop diabaikan), array simpul, dan KD-tree simpul."""
    best = {}
    for (ux, uy), (vx, vy), w in zip(e.u, e.v, e.w):
        a, b = (ux, uy), (vx, vy)
        if a == b:
            continue
        key = (a, b) if a <= b else (b, a)
        if key not in best or w < best[key]:
            best[key] = w
    G = nx.Graph()
    G.add_weighted_edges_from((a, b, w) for (a, b), w in best.items())
    nl = np.array(list(G.nodes())) if G.number_of_nodes() else np.empty((0, 2))
    return G, nl, (cKDTree(nl) if len(nl) else None)


def edge_lines(e: Edges):
    return shapely.linestrings(np.stack([e.u, e.v], axis=1))


def crossings(e: Edges) -> pd.DataFrame:
    """Pasangan sisi yang berpotongan di satu titik tanpa berbagi ujung."""
    lines = edge_lines(e)
    tree = shapely.STRtree(lines)
    i, j = tree.query(lines, predicate="intersects")
    keep = i < j
    i, j = i[keep], j[keep]
    share = ((e.u[i] == e.u[j]).all(1) | (e.u[i] == e.v[j]).all(1)
             | (e.v[i] == e.u[j]).all(1) | (e.v[i] == e.v[j]).all(1))
    i, j = i[~share], j[~share]
    pts = shapely.intersection(lines[i], lines[j])
    is_pt = shapely.get_type_id(pts) == 0
    i, j, pts = i[is_pt], j[is_pt], pts[is_pt]
    return pd.DataFrame({"i": i, "j": j, "x": shapely.get_x(pts), "y": shapely.get_y(pts),
                         "khusus": e.special[i] | e.special[j]})


def near_misses(e: Edges, G: nx.Graph, tol_max: float = 5.0, net_exclude: float = NET_EXCLUDE_M) -> pd.DataFrame:
    """Ujung buntu non-khusus dengan sisi non-khusus lain berjarak ≤ tol_max (tidak bersisian dan
    tidak terjangkau ≤ net_exclude lewat jaringan). Satu baris per ujung buntu (sisi sasaran terdekat)."""
    deg1 = np.array([n for n, d in G.degree() if d == 1])
    if not len(deg1):
        return pd.DataFrame(columns=NM_COLS)
    lines = edge_lines(e)
    tree = shapely.STRtree(lines)
    # sisi sumber tiap ujung buntu (untuk menentukan status khusus)
    key = {tuple(p): k for k, p in enumerate(map(tuple, deg1))}
    own = np.full(len(deg1), -1)
    for idx, (a, b) in enumerate(zip(map(tuple, e.u), map(tuple, e.v))):
        for p in (a, b):
            k = key.get(p)
            if k is not None and own[k] < 0:
                own[k] = idx
    ok = (own >= 0) & ~e.special[np.maximum(own, 0)]
    deg1, own = deg1[ok], own[ok]
    pts = shapely.points(deg1)
    qi, qe = tree.query(pts, predicate="dwithin", distance=tol_max)
    qe_ok = ~e.special[qe]
    qi, qe = qi[qe_ok], qe[qe_ok]
    d = shapely.distance(pts[qi], lines[qe])
    df = pd.DataFrame({"k": qi, "edge": qe, "dist": d}).sort_values(["k", "dist"])
    rows = []
    for k, grp in df.groupby("k", sort=True):
        node = tuple(deg1[k])
        reach = nx.single_source_dijkstra_path_length(G, node, cutoff=net_exclude, weight="weight")
        for edge, dist in zip(grp["edge"].values, grp["dist"].values):
            a, b = tuple(e.u[edge]), tuple(e.v[edge])
            if node in (a, b) or a in reach or b in reach:
                continue
            p = shapely.line_interpolate_point(lines[edge], shapely.line_locate_point(lines[edge], pts[k]))
            rows.append({"x": node[0], "y": node[1], "dist": float(dist), "edge": int(edge),
                         "px": shapely.get_x(p), "py": shapely.get_y(p), "src_ujung": int(e.src[own[k]])})
            break
    return pd.DataFrame(rows, columns=NM_COLS)


def cleaned_edges(e: Edges, cross: pd.DataFrame, nm: pd.DataFrame, tol: float) -> Edges:
    """(a) noding perpotongan non-khusus; (b) sambungan near-miss ≤ tol. Sisi pecahan mewarisi src;
    sambungan membawa src (ujung buntu) dan src2 (sasaran)."""
    splits = {}
    cr = cross[~cross["khusus"]]
    for i, j, x, y in cr[["i", "j", "x", "y"]].itertuples(index=False):
        for k in (int(i), int(j)):
            splits.setdefault(k, []).append((x, y))
    nm = nm[nm["dist"] <= tol]
    conn_u, conn_v, conn_w, conn_s, conn_s2 = [], [], [], [], []
    for x, y, dist, edge, px, py, s_ujung in nm[["x", "y", "dist", "edge", "px", "py", "src_ujung"]].itertuples(index=False):
        p = np.round([px, py], 2)
        if np.allclose(p, e.u[edge], atol=0.011):
            p = e.u[edge]
        elif np.allclose(p, e.v[edge], atol=0.011):
            p = e.v[edge]
        else:
            splits.setdefault(int(edge), []).append((px, py))
        conn_u.append([x, y])
        conn_v.append(p)
        conn_w.append(max(float(dist), MIN_CONNECTOR_M))
        conn_s.append(s_ujung)
        conn_s2.append(int(e.src[edge]))
    keep = np.ones(len(e), bool)
    nu, nv, nw, ns, ns2, nsp = [], [], [], [], [], []
    for k, plist in splits.items():
        keep[k] = False
        a, b = e.u[k], e.v[k]
        L = float(np.hypot(*(b - a)))
        # titik pecah = koordinat asli yang dibulatkan 0,01 m (sama persis dengan ujung sambungan dan
        # dengan titik pecah sisi lawan pada perpotongan), diurutkan menurut posisinya pada sisi
        inner = {}
        for p in plist:
            rp = tuple(np.round(p, 2))
            if rp != tuple(a) and rp != tuple(b):
                inner[rp] = float(np.dot(np.subtract(p, a), b - a) / (L * L))
        pts = [a] + [np.asarray(rp) for rp, _ in sorted(inner.items(), key=lambda kv: kv[1])] + [b]
        for p0, p1 in zip(pts[:-1], pts[1:]):
            w = float(np.hypot(*(p1 - p0)))
            if w <= 0:
                continue
            nu.append(p0); nv.append(p1); nw.append(w); ns.append(e.src[k]); ns2.append(-1); nsp.append(e.special[k])
    base = e.subset(keep)
    parts = [base]
    if nu:
        parts.append(Edges(np.asarray(nu), np.asarray(nv), np.asarray(nw), np.asarray(ns), np.asarray(ns2),
                           np.asarray(nsp, bool)))
    if conn_u:
        parts.append(Edges(np.round(np.asarray(conn_u, float), 2), np.round(np.asarray(conn_v, float), 2),
                           np.asarray(conn_w), np.asarray(conn_s), np.asarray(conn_s2), np.zeros(len(conn_u), bool)))
    return Edges(*(np.concatenate([getattr(p, f) for p in parts]) for f in ("u", "v", "w", "src", "src2", "special")))


def edges_for_level(e: Edges, closed_src: np.ndarray) -> Edges:
    """Hapus sisi (dan sambungan) yang segmen sumbernya ditutup pada level ini."""
    closed_src = np.asarray(closed_src, bool)
    drop = closed_src[e.src] | ((e.src2 >= 0) & closed_src[np.maximum(e.src2, 0)])
    return e.subset(~drop)


def component_stats(G: nx.Graph) -> dict:
    comps = sorted(nx.connected_components(G), key=len, reverse=True)
    n = G.number_of_nodes()
    total_km = G.size(weight="weight") / 1000
    big = comps[0]
    big_km = G.subgraph(big).size(weight="weight") / 1000
    return {"jumlah_komponen": len(comps), "simpul": n, "km_total": total_km,
            "komponen_terbesar_persen_simpul": len(big) / n * 100,
            "komponen_terbesar_persen_km": big_km / total_km * 100,
            "ujung_buntu": sum(1 for _, d in G.degree() if d == 1)}


def node_component(G: nx.Graph) -> dict:
    out = {}
    for c, comp in enumerate(sorted(nx.connected_components(G), key=len, reverse=True)):
        for nd in comp:
            out[nd] = c
    return out
