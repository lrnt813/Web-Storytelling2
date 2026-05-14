import math
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans

JENKS_MAX_POINTS = 2048


def relabel_clusters_by_metric(
    labels: np.ndarray,
    metric_values: np.ndarray,
    ascending: bool = True,
) -> Tuple[np.ndarray, Dict[int, int], Dict[int, float]]:
    labels_arr = np.asarray(labels)
    metric_arr = np.asarray(metric_values, dtype=float)
    relabeled = labels_arr.copy()

    valid_clusters = sorted(int(c) for c in np.unique(labels_arr) if int(c) >= 0)
    if not valid_clusters:
        return relabeled.astype(int, copy=False), {}, {}

    cluster_scores: Dict[int, float] = {}
    for cluster_id in valid_clusters:
        mask = labels_arr == cluster_id
        vals = metric_arr[mask]
        vals = vals[np.isfinite(vals)]
        cluster_scores[cluster_id] = float(np.mean(vals)) if vals.size else math.inf

    ordered = sorted(
        cluster_scores.items(),
        key=lambda item: (item[1], item[0]) if ascending else (-item[1], item[0]),
    )
    mapping = {old_id: new_id for new_id, (old_id, _) in enumerate(ordered)}

    for old_id, new_id in mapping.items():
        relabeled[labels_arr == old_id] = new_id

    ordered_scores = {mapping[old_id]: score for old_id, score in cluster_scores.items()}
    return relabeled.astype(int, copy=False), mapping, ordered_scores


def relabel_clustering_result(result: dict, metric_values: np.ndarray) -> dict:
    if result is None or result.get("labels") is None:
        return result

    labels = np.asarray(result["labels"])
    relabeled, mapping, ordered_scores = relabel_clusters_by_metric(labels, metric_values, ascending=True)
    if not mapping:
        result["labels"] = relabeled
        return result

    order = [old_id for old_id, _ in sorted(mapping.items(), key=lambda item: item[1])]
    result["labels"] = relabeled
    result["label_mapping"] = {int(k): int(v) for k, v in mapping.items()}
    result["label_metric_mean"] = {int(k): float(v) for k, v in ordered_scores.items()}

    if isinstance(result.get("U"), np.ndarray) and result["U"].ndim == 2:
        result["U"] = result["U"][:, order]
    if isinstance(result.get("centers"), np.ndarray) and result["centers"].ndim >= 2:
        result["centers"] = result["centers"][order]
    return result


def compute_ordinal_psi(history_labels: List[np.ndarray], k_locked: Optional[int] = None) -> np.ndarray:
    if not history_labels:
        return np.array([], dtype=float)
    history_arr = np.asarray(history_labels, dtype=int)
    if history_arr.ndim != 2:
        raise ValueError("history_labels harus berbentuk [n_step, n_grid]")

    diffs = np.abs(np.diff(history_arr, axis=0))
    sum_diffs = np.sum(diffs, axis=0)

    if k_locked is None:
        unique_clusters = np.unique(history_arr[history_arr >= 0])
        k_locked = int(len(unique_clusters))
    k_eff = max(int(k_locked or 0), 2)
    n_transitions = max(history_arr.shape[0] - 1, 1)
    denominator = n_transitions * max(k_eff - 1, 1)
    return sum_diffs.astype(float) / float(denominator)


def _clean_values(values: np.ndarray) -> np.ndarray:
    arr = np.asarray(values, dtype=float).ravel()
    arr = arr[np.isfinite(arr)]
    return arr


def _downsample_sorted(values: np.ndarray, max_points: int) -> np.ndarray:
    data = np.sort(_clean_values(values))
    if data.size <= max_points:
        return data
    idx = np.linspace(0, data.size - 1, num=max_points, dtype=int)
    return data[idx]


def _jenks_breaks(values: np.ndarray, n_classes: int) -> Optional[List[float]]:
    data = _downsample_sorted(values, JENKS_MAX_POINTS)
    if data.size == 0:
        return None
    unique_n = len(np.unique(data))
    if unique_n < n_classes:
        return None

    n = data.size
    lower = np.zeros((n + 1, n_classes + 1), dtype=int)
    var = np.full((n + 1, n_classes + 1), np.inf, dtype=float)

    for i in range(1, n_classes + 1):
        lower[1, i] = 1
        var[1, i] = 0.0
        for j in range(2, n + 1):
            var[j, i] = np.inf

    for l in range(2, n + 1):
        s1 = s2 = w = 0.0
        for m in range(1, l + 1):
            idx = l - m + 1
            val = data[idx - 1]
            s1 += val
            s2 += val * val
            w += 1.0
            variance = s2 - (s1 * s1) / w
            if idx == 1:
                continue
            for j in range(2, n_classes + 1):
                candidate = variance + var[idx - 1, j - 1]
                if candidate < var[l, j]:
                    lower[l, j] = idx
                    var[l, j] = candidate
        lower[l, 1] = 1
        var[l, 1] = variance

    breaks = [0.0] * (n_classes + 1)
    breaks[n_classes] = float(data[-1])
    k = n
    for j in range(n_classes, 1, -1):
        idx = lower[k, j] - 1
        breaks[j - 1] = float(data[idx])
        k = lower[k, j] - 1
    breaks[0] = float(data[0])
    return breaks


def _kmeans_1d_breaks(values: np.ndarray, n_classes: int) -> Optional[List[float]]:
    data = _clean_values(values)
    unique = np.unique(data)
    if unique.size < n_classes:
        return None

    km = KMeans(n_clusters=n_classes, random_state=42, n_init=10)
    km.fit(data.reshape(-1, 1))
    centers = np.sort(km.cluster_centers_.ravel())
    breaks = [float(np.min(data))]
    for i in range(len(centers) - 1):
        breaks.append(float((centers[i] + centers[i + 1]) / 2.0))
    breaks.append(float(np.max(data)))
    return breaks


def estimate_metric_thresholds(
    values: np.ndarray,
    metric_name: str,
    fallback_lower: float,
    fallback_upper: float,
    n_classes: int = 3,
) -> Dict[str, object]:
    data = _clean_values(values)
    meta: Dict[str, object] = {
        "metric": metric_name,
        "method": "fallback",
        "lower": float(fallback_lower),
        "upper": float(fallback_upper),
        "breaks": [float(np.min(data)) if data.size else 0.0, float(fallback_lower), float(fallback_upper), float(np.max(data)) if data.size else float(fallback_upper)],
        "n_samples": int(data.size),
        "n_unique": int(len(np.unique(data))) if data.size else 0,
    }
    if data.size < max(12, n_classes * 4):
        return meta

    method_chain = [("kmeans_1d", _kmeans_1d_breaks)]
    if data.size <= JENKS_MAX_POINTS * 4:
        method_chain.insert(0, ("jenks", _jenks_breaks))

    for method_name, fn in method_chain:
        try:
            breaks = fn(data, n_classes)
        except Exception:
            breaks = None
        if not breaks or len(breaks) < 4:
            continue
        lower = float(breaks[1])
        upper = float(breaks[2])
        if not np.isfinite(lower) or not np.isfinite(upper) or lower >= upper:
            continue
        meta.update({
            "method": method_name,
            "lower": lower,
            "upper": upper,
            "breaks": [float(b) for b in breaks],
        })
        return meta

    q_low, q_high = np.quantile(data, [1.0 / 3.0, 2.0 / 3.0])
    if np.isfinite(q_low) and np.isfinite(q_high) and q_low < q_high:
        meta.update({
            "method": "tertile_quantile",
            "lower": float(q_low),
            "upper": float(q_high),
            "breaks": [float(np.min(data)), float(q_low), float(q_high), float(np.max(data))],
        })
    return meta


def classify_metric_values(
    values: np.ndarray,
    thresholds: Dict[str, object],
    low_label: str,
    medium_label: str,
    high_label: str,
    null_label: str = "unknown",
) -> np.ndarray:
    lower = float(thresholds.get("lower", 0.0))
    upper = float(thresholds.get("upper", lower))
    arr = np.asarray(values, dtype=float)
    out = np.full(arr.shape, null_label, dtype=object)
    finite = np.isfinite(arr)
    out[finite & (arr < lower)] = low_label
    out[finite & (arr >= lower) & (arr < upper)] = medium_label
    out[finite & (arr >= upper)] = high_label
    return out


def generate_cluster_names(
    gdf: pd.DataFrame,
    labels: np.ndarray,
    hazard_col: str,
    road_density_col: str,
    tes_time_cols: List[str],
    z_threshold: float = 0.5,
) -> Dict[int, str]:
    labels_arr = np.asarray(labels, dtype=int)
    valid_clusters = sorted(int(c) for c in np.unique(labels_arr) if int(c) >= 0)
    if not valid_clusters:
        return {}
    if not tes_time_cols:
        raise KeyError("Kolom profiling klaster untuk waktu TES tidak ditemukan")

    feature_cols = [hazard_col, road_density_col, *tes_time_cols]
    missing = [col for col in feature_cols if col not in gdf.columns]
    if missing:
        raise KeyError(f"Kolom profiling klaster tidak ditemukan: {missing}")

    feature_df = gdf[feature_cols].apply(pd.to_numeric, errors="coerce")
    global_mean = feature_df.mean(axis=0, skipna=True)
    global_std = feature_df.std(axis=0, skipna=True, ddof=0).replace(0.0, np.nan)
    global_std = global_std.fillna(1.0)

    cluster_names: Dict[int, str] = {}
    for cluster_id in valid_clusters:
        cluster_mask = labels_arr == cluster_id
        cluster_mean = feature_df.loc[cluster_mask, :].mean(axis=0, skipna=True)
        z_scores = ((cluster_mean - global_mean) / global_std).replace([np.inf, -np.inf], np.nan).fillna(0.0)

        hazard_z = float(z_scores.get(hazard_col, 0.0))
        access_z = float(np.nanmean([z_scores.get(col, 0.0) for col in tes_time_cols]))
        infra_z = float(z_scores.get(road_density_col, 0.0))

        if hazard_z > z_threshold:
            hazard_label = "Bahaya Tinggi"
        elif hazard_z < -z_threshold:
            hazard_label = "Bahaya Rendah"
        else:
            hazard_label = "Bahaya Sedang"

        if access_z > z_threshold:
            access_label = "Akses Rendah"
        elif access_z < -z_threshold:
            access_label = "Akses Tinggi"
        else:
            access_label = "Akses Menengah"

        if infra_z > z_threshold:
            infra_label = "Jaringan Padat"
        elif infra_z < -z_threshold:
            infra_label = "Jaringan Jarang"
        else:
            infra_label = "Jaringan Sedang"

        cluster_names[cluster_id] = f"{hazard_label} - {access_label} - {infra_label}"

    return cluster_names
