"""Titik blokir jalan untuk simulasi dashboard: hanya boleh berada pada jaringan jalan.

Klik pengguna ditempelkan (snap) ke RUAS jalan terdekat bila jaraknya ≤ toleransi. Bila tidak ada ruas dalam
toleransi, titik ditolak (bukan jaringan jalan). Blokir diterapkan pada sisi graf yang mewakili ruas tersebut
(ujung ruas dibulatkan 0,01 m, sama dengan backend.engine.build_road_graph). Hanya dipakai simulasi dashboard;
tidak memengaruhi analisis skripsi maupun hasil terkunci.
"""
from typing import Optional

import numpy as np
import shapely

CUT_TOL_DEFAULT_M = 25.0     # toleransi bawaan jarak klik ke ruas jalan
CUT_TOL_MAX_M = 75.0         # batas atas toleransi yang boleh diminta klien


class RoadIndex:
    """STRtree atas ruas jalan (CRS terproyeksi, meter)."""

    def __init__(self, roads):
        self.roads = roads
        self.geoms = np.asarray(roads.geometry.values)
        self.tree = shapely.STRtree(self.geoms)

    def snap(self, x: float, y: float, tol_m: float = CUT_TOL_DEFAULT_M) -> Optional[dict]:
        """Ruas terdekat dari titik (x, y) dalam jarak ≤ tol_m, atau None bila titik bukan pada jaringan jalan.
        Returns: id_jalan (indeks baris), titik proyeksi pada ruas, jarak (m), dan ujung sisi graf ruas tersebut."""
        tol = float(min(max(tol_m, 0.0), CUT_TOL_MAX_M))
        pt = shapely.Point(x, y)
        idx = self.tree.query_nearest(pt, max_distance=tol, all_matches=False)
        if len(idx) == 0:
            return None
        i = int(idx[0])
        line = self.geoms[i]
        d = float(line.distance(pt))
        if d > tol:
            return None
        proj = line.interpolate(line.project(pt))
        coords = np.asarray(line.coords)[:, :2]
        # sisi graf terdekat (segmen data berupa garis dua titik; MultiLine/LineString panjang tetap ditangani)
        seg = min(range(len(coords) - 1),
                  key=lambda k: shapely.LineString(coords[k:k + 2]).distance(pt)) if len(coords) > 2 else 0
        a, b = coords[seg], coords[seg + 1]
        return {"id_jalan": int(self.roads.index[i]), "x": float(proj.x), "y": float(proj.y), "jarak_m": d,
                "edge_from": [round(float(a[0]), 2), round(float(a[1]), 2)],
                "edge_to": [round(float(b[0]), 2), round(float(b[1]), 2)]}
