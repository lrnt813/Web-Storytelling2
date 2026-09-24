"""Kelas bahaya banjir dari satu sumber raster InaRisk (`data/Kulonprogo_Banjir.tif`).

Nilai piksel: 1 = rendah, 2 = sedang, 3 = tinggi; nodata (15) = 0 (tidak berbahaya).
Metode (keputusan peneliti, Putaran 3):
  * grid  : kelas MAYORITAS piksel yang pusatnya berada di dalam grid (termasuk kelas 0);
            seri → kelas terendah; grid tanpa pusat piksel → nilai piksel di centroid;
  * ruas  : kelas MAKSIMUM piksel yang dilalui segmen (sampel titik tiap ≤ RUAS_STEP_M
            sepanjang segmen, termasuk kedua ujung);
  * TES   : nilai piksel di titik TES.
"""
from typing import Optional

import numpy as np

RUAS_STEP_M = 5.0    # jarak sampel sepanjang ruas (≈ 1/6 lebar piksel 29,7 m)


class HazardRaster:
    def __init__(self, path: str):
        import rasterio
        with rasterio.open(path) as src:
            a = src.read(1).astype(np.int16)
            nodata = src.nodata
            self.transform = src.transform
            self.crs = src.crs
            self.res = src.res
        if nodata is not None:
            a[a == nodata] = 0
        a[(a < 0) | (a > 3)] = 0
        self.a = a.astype(np.int8)

    def values_at(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        """Nilai piksel pada koordinat (x, y); di luar raster = 0."""
        inv = ~self.transform
        col, row = inv @ (np.asarray(x, float), np.asarray(y, float))
        col = np.floor(col).astype(np.int64)
        row = np.floor(row).astype(np.int64)
        ok = (row >= 0) & (row < self.a.shape[0]) & (col >= 0) & (col < self.a.shape[1])
        out = np.zeros(len(col), dtype=np.int8)
        out[ok] = self.a[row[ok], col[ok]]
        return out

    def grid_majority(self, gdf) -> np.ndarray:
        """Kelas mayoritas piksel (pusat piksel di dalam poligon grid); seri → kelas terendah."""
        from rasterio import features
        lab = features.rasterize(((g, i + 1) for i, g in enumerate(gdf.geometry)), out_shape=self.a.shape,
                                 transform=self.transform, fill=0, dtype="int32")
        m = lab > 0
        n = len(gdf)
        counts = np.zeros((n, 4), dtype=np.int64)
        np.add.at(counts, (lab[m] - 1, self.a[m]), 1)
        cls = counts.argmax(axis=1).astype(np.int8)          # argmax → indeks terendah bila seri
        empty = counts.sum(axis=1) == 0
        if empty.any():
            c = gdf.geometry.centroid
            cls[empty] = self.values_at(c.x.values[empty], c.y.values[empty])
        return cls

    def line_max(self, geoms, step: float = RUAS_STEP_M) -> np.ndarray:
        """Kelas maksimum piksel sepanjang tiap garis (sampel tiap ≤ step meter)."""
        import shapely
        geoms = np.asarray(geoms, dtype=object)
        out = np.zeros(len(geoms), dtype=np.int8)
        valid = np.array([g is not None and not g.is_empty for g in geoms])
        idx = np.where(valid)[0]
        if len(idx) == 0:
            return out
        L = shapely.length(geoms[idx])
        k = np.maximum(1, np.ceil(L / step).astype(np.int64))       # jumlah interval per garis
        owner = np.repeat(idx, k + 1)
        frac = np.concatenate([np.linspace(0.0, 1.0, kk + 1) for kk in k])
        pts = shapely.line_interpolate_point(geoms[owner], frac, normalized=True)
        v = self.values_at(shapely.get_x(pts), shapely.get_y(pts))
        np.maximum.at(out, owner, v)
        return out

    def points(self, geoms) -> np.ndarray:
        return self.values_at(np.array([g.x for g in geoms]), np.array([g.y for g in geoms]))


_CACHE = {}


def load_hazard_raster(path: str) -> HazardRaster:
    if path not in _CACHE:
        _CACHE[path] = HazardRaster(path)
    return _CACHE[path]


def apply_raster_classes(gdf=None, roads=None, tes: Optional[dict] = None, raster: Optional[HazardRaster] = None,
                         col: str = "banjir") -> None:
    """Ganti kolom kelas bahaya (in-place) dengan turunan raster; nilai lama disimpan di
    `{col}_atribut_lama` untuk diagnostik."""
    if gdf is not None:
        gdf[f"{col}_atribut_lama"] = gdf[col].values if col in gdf.columns else np.nan
        gdf[col] = raster.grid_majority(gdf).astype(int)
    if roads is not None:
        roads[f"{col}_atribut_lama"] = roads[col].values if col in roads.columns else np.nan
        roads[col] = raster.line_max(roads.geometry.values).astype(int)
    if tes:
        for k, t in tes.items():
            t[f"{col}_atribut_lama"] = t[col].values if col in t.columns else np.nan
            t[col] = raster.points(t.geometry.values).astype(int)
