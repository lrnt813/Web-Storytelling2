"""DESC-N dan PESC-N: modifikasi ternormalisasi indeks DESC/PESC Guo dkk. (2015).

Rujukan: Guo, Y., Liu, K., Wu, Q., Hong, Q., & Zhang, H. (2015). A new spatial fuzzy c-means for spatial
clustering. WSEAS Transactions on Computers, 14, 369–381 (DESC dan PESC: hlm. 374, pers. 11–14).
Catatan: artikel menetapkan d̄ = 1 untuk blok satu sampel dan D_ij = jarak pasangan sampel terdekat antarblok.

DESC dan PESC asli (thesis.desc_pesc) tidak dapat dibandingkan antar-K: pembagi d̄ (DESC) dan D·d (PESC)
mendekati nol pada blok beratribut identik, tidak ada normalisasi terhadap K, dan satuannya bergantung skala.
Modifikasi (ditetapkan peneliti pada Finalisasi v6, sebelum dihitung):

  s      = rata-rata jarak Euclidean semua baris ke pusat global di ruang fitur (satu konstanta per data)
  g(x)   = 1 / (1 + x²)                          (terbatas di (0, 1]; g(0) = 1, tidak meledak bila d̄ = 0)
  blok   = komponen terhubung baris ber-label sama (label tegas) pada ketetanggaan ROOK `A` (untuk data
           gabungan: rook di dalam level yang sama, lalu digabung); N = jumlah baris
  V_i    = v_i / Cn_k   (v_i = ukuran blok i, Cn_k = ukuran klaster k)
  d̃_i    = d̄_i / s      (d̄_i = rata-rata jarak atribut anggota blok ke pusat blok); d̃_i = 1 untuk blok satu sampel
  DESC-N = Σ_k (Cn_k/N) Σ_{i∈k} V_i² g(d̃_i)
           = gabungan Kontiguitas = Σ_k (Cn_k/N) Σ V_i²  dan  Homogenitas = Σ_k (Cn_k/N) Σ_{i∈k} v_i g(d̃_i) / Cn_k
  PESC-N = Σ_k (Cn_k/N) P_k,  P_k = Σ_{i<j} V_i V_j (1/D̃_ij) g(d̃_ij) / Σ_{i<j} V_i V_j  (Bn_k ≥ 2),  P_k = 1 (Bn_k = 1)
  D̃_ij   = jarak terdekat antara sel-sel blok i dan j (koordinat centroid, m) / 100 m, minimal 1
  d̃_ij   = jarak atribut antarpusat blok / s

Keduanya bernilai (0, 1]; makin besar makin baik. PESC-N dihitung eksak bila jumlah pasangan blok per klaster
≤ MAX_PAIRS; bila lebih: pasangan antarblok berukuran ≥ 2 dihitung eksak (bila jumlahnya ≤ MAX_PAIRS) dan sisanya
diperkirakan dari N_SAMPLE pasangan acak berbobot V_iV_j (seed 42). Aproksimasi dicatat di keluaran.
Catatan pada data gabungan: pasangan blok lintas level ikut dihitung dan jaraknya diukur pada koordinat grid, sehingga
blok di level berbeda yang menempati lokasi berdekatan/sama mendapat D̃ = 1.
"""
from typing import Optional

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

MAX_PAIRS = 2_000_000
N_SAMPLE = 200_000
SEED = 42
CELL_M = 100.0


def g(x):
    """g(x) = 1 / (1 + x²)."""
    return 1.0 / (1.0 + np.asarray(x, float) ** 2)


def scale_s(X: np.ndarray) -> float:
    """s = rata-rata jarak Euclidean baris ke pusat global."""
    X = np.asarray(X, float)
    return float(np.linalg.norm(X - X.mean(axis=0), axis=1).mean())


def blocks(labels: np.ndarray, A: csr_matrix) -> np.ndarray:
    """Nomor blok per baris: komponen terhubung baris ber-label sama pada ketetanggaan A."""
    coo = A.tocoo()
    same = labels[coo.row] == labels[coo.col]
    B = csr_matrix((np.ones(int(same.sum())), (coo.row[same], coo.col[same])), shape=A.shape)
    return connected_components(B, directed=False)[1]


def block_table(X: np.ndarray, labels: np.ndarray, A: csr_matrix) -> tuple:
    """(komponen per baris, tabel blok: klaster, v, pusat atribut, d̄)."""
    comp = blocks(labels, A)
    df = pd.DataFrame(X).groupby(comp)
    cen = df.mean()
    member = np.linalg.norm(X - cen.values[comp], axis=1)
    tab = pd.DataFrame({"klaster": pd.Series(labels).groupby(comp).first(),
                        "v": pd.Series(comp).value_counts().sort_index(),
                        "d_bar": pd.Series(member).groupby(comp).mean()})
    return comp, tab, cen.values


def _nearest_block_dist(pairs: np.ndarray, cells: dict) -> np.ndarray:
    """Jarak terdekat antarsel untuk pasangan blok (i, j); cells[b] = koordinat sel blok b."""
    out = np.empty(len(pairs))
    if len(pairs) == 0:
        return out
    size = np.array([len(cells[b]) for b in range(max(cells) + 1)]) if isinstance(next(iter(cells)), (int, np.integer))         else None
    pairs = np.array(pairs, copy=True)
    if size is not None:                           # KD-tree dibangun pada blok yang lebih besar
        swap = size[pairs[:, 1]] > size[pairs[:, 0]]
        pairs[swap] = pairs[swap][:, ::-1]
    order = np.argsort(pairs[:, 0], kind="stable")
    p = pairs[order]
    starts = np.r_[0, np.flatnonzero(np.diff(p[:, 0])) + 1, len(p)]
    res = np.empty(len(p))
    for a, b in zip(starts[:-1], starts[1:]):
        i = p[a, 0]
        js = p[a:b, 1]
        tree = cKDTree(cells[i])
        pts = np.concatenate([cells[j] for j in js])
        owner = np.repeat(np.arange(len(js)), [len(cells[j]) for j in js])
        d, _ = tree.query(pts, k=1)
        res[a:b] = pd.Series(d).groupby(owner).min().values
    out[order] = res
    return out


def _block_dist_matrix(ids: np.ndarray, cells: dict) -> np.ndarray:
    """Matriks jarak terdekat antarsel untuk semua pasangan blok `ids` (satu KD-tree per blok, dikueri dengan
    semua sel klaster; minimum per blok lewat reduceat)."""
    sizes = np.array([len(cells[b]) for b in ids])
    pts = np.concatenate([cells[b] for b in ids])
    starts = np.r_[0, np.cumsum(sizes)[:-1]]
    M = np.empty((len(ids), len(ids)))
    for a, b in enumerate(ids):
        d, _ = cKDTree(cells[b]).query(pts, k=1)
        M[a] = np.minimum.reduceat(d, starts)
    return M


def desc_pesc_n(X: np.ndarray, labels: np.ndarray, A: csr_matrix, coords: np.ndarray,
                s: Optional[float] = None, max_pairs: int = MAX_PAIRS, n_sample: int = N_SAMPLE,
                seed: int = SEED) -> dict:
    """DESC-N, PESC-N, Kontiguitas, dan Homogenitas (lihat docstring modul)."""
    X = np.asarray(X, float)
    labels = np.asarray(labels)
    coords = np.asarray(coords, float)
    N = len(labels)
    s = scale_s(X) if s is None else float(s)
    comp, tab, cen = block_table(X, labels, A)
    d_t = np.where(tab["v"].values == 1, 1.0, (tab["d_bar"].values / s) if s > 0 else 0.0)
    tab["d_tilde"] = d_t
    cells = {b: coords[np.asarray(v)] for b, v in pd.Series(np.arange(N)).groupby(comp).groups.items()}
    rng = np.random.RandomState(seed)
    desc = kont = homo = pesc = 0.0
    info = {}
    for k, t in tab.groupby("klaster"):
        Cn = float(t["v"].sum())
        V = t["v"].values / Cn
        wk = Cn / N
        kont += wk * float((V ** 2).sum())
        homo += wk * float((t["v"].values * g(t["d_tilde"].values)).sum() / Cn)
        desc += wk * float((V ** 2 * g(t["d_tilde"].values)).sum())
        ids = t.index.values
        Bn = len(ids)
        if Bn < 2:
            pesc += wk * 1.0
            info[int(k)] = {"Bn": 1, "metode": "satu blok (P = 1)"}
            continue
        n_pairs = Bn * (Bn - 1) // 2

        def h_of(ii, jj):
            D = np.maximum(_nearest_block_dist(np.column_stack([ids[ii], ids[jj]]), cells) / CELL_M, 1.0)
            dd = np.linalg.norm(cen[ids[ii]] - cen[ids[jj]], axis=1) / s if s > 0 else np.zeros(len(ii))
            return g(dd) / D

        if n_pairs <= max_pairs:
            ii, jj = np.triu_indices(Bn, k=1)
            w = V[ii] * V[jj]
            D = np.maximum(_block_dist_matrix(ids, cells)[ii, jj] / CELL_M, 1.0)
            dd = np.linalg.norm(cen[ids[ii]] - cen[ids[jj]], axis=1) / s if s > 0 else np.zeros(len(ii))
            Pk = float((w * g(dd) / D).sum() / w.sum())
            info[int(k)] = {"Bn": Bn, "pasangan": int(n_pairs), "metode": "eksak"}
        else:
            big = np.flatnonzero(t["v"].values >= 2)
            W_tot = (V.sum() ** 2 - (V ** 2).sum()) / 2.0
            n_big = len(big) * (len(big) - 1) // 2
            num = 0.0
            if n_big <= max_pairs and len(big) >= 2:
                a, b = np.triu_indices(len(big), k=1)
                ii, jj = big[a], big[b]
                w = V[ii] * V[jj]
                D = np.maximum(_block_dist_matrix(ids[big], cells)[a, b] / CELL_M, 1.0)
                dd = np.linalg.norm(cen[ids[ii]] - cen[ids[jj]], axis=1) / s if s > 0 else np.zeros(len(ii))
                num += float((w * g(dd) / D).sum())
                W_S = float(w.sum())
                excl_big = True
            else:
                W_S, excl_big = 0.0, False
            W_R = W_tot - W_S
            p = V / V.sum()
            is_big = t["v"].values >= 2
            si, sj = [], []
            while len(si) < n_sample:
                a = rng.choice(Bn, size=n_sample, p=p)
                b = rng.choice(Bn, size=n_sample, p=p)
                keep = a != b
                if excl_big:
                    keep &= ~(is_big[a] & is_big[b])
                si.extend(a[keep].tolist())
                sj.extend(b[keep].tolist())
            si, sj = np.asarray(si[:n_sample]), np.asarray(sj[:n_sample])
            num += W_R * float(h_of(si, sj).mean())
            Pk = num / W_tot
            info[int(k)] = {"Bn": Bn, "pasangan": int(n_pairs), "pasangan_blok_besar_eksak": int(n_big) if excl_big else 0,
                            "sampel": int(n_sample), "metode": ("blok ≥ 2 eksak + sampel berbobot V_iV_j" if excl_big
                                                               else "sampel berbobot V_iV_j (semua pasangan)")}
        pesc += wk * Pk
        info[int(k)]["P_k"] = Pk
    return {"desc_n": desc, "pesc_n": pesc, "kontiguitas": kont, "homogenitas": homo, "s": s,
            "n_blok": int(len(tab)), "pesc_per_klaster": info,
            "aproksimasi": any(v.get("metode", "").startswith(("blok", "sampel")) for v in info.values())}


def desc_asli_per_blok(X: np.ndarray, labels: np.ndarray, A: csr_matrix) -> pd.DataFrame:
    """Kontribusi setiap blok terhadap DESC asli (thesis.desc_pesc): V_i² / d̄_i² untuk blok ≥ 2 dan d̄ > 1e-9."""
    comp, tab, _ = block_table(X, labels, A)
    Cn = tab.groupby("klaster")["v"].transform("sum")
    tab["V"] = tab["v"] / Cn
    ok = (tab["v"] >= 2) & (tab["d_bar"] > 1e-9)
    tab["kontribusi"] = np.where(ok, tab["V"] ** 2 / np.where(ok, tab["d_bar"], 1.0) ** 2, 0.0)
    return tab
