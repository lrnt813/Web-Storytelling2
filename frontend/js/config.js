const API_BASE = "/api";
const backendOriginOverride = window.__EVAC_API_ORIGIN || localStorage.getItem('evac_api_origin');
const backendOrigin = backendOriginOverride || ((window.location.hostname === '127.0.0.1' || window.location.hostname === 'localhost') && window.location.port !== '8000'
    ? `${window.location.protocol}//${window.location.hostname}:8000`
    : window.location.origin);
const RESOLVED_API_BASE = `${backendOrigin}/api`;
// Warna klaster: palet kategorikal tab10 (urutan tetap per nomor klaster)
const clusterColors = { 0: "#1f77b4", 1: "#2ca02c", 2: "#9467bd", 3: "#e377c2", 4: "#bcbd22", 5: "#17becf",
                        6: "#8c564b", 7: "#d62728", 8: "#7f7f7f", 9: "#ff7f0e", "-1": "#475569" };
const TERPUTUS_COLOR = "#0f172a";
const TERGENANG_COLOR = "#38bdf8";   // grid tergenang (terdampak simulasi) — dikeluarkan dari klasterisasi & TAS
const TAS_COLOR = "#a855f7";
const TERDAMPAK_COLOR = "#ff7f0e";
const NEUTRAL_FILL = "#475569";

// Level banjir = kelas bahaya InaRisk yang ditutup (intensity hanya detail implementasi API)
const LEVELS = [
    { key: 'baseline', label: 'Baseline', kelas: 'tidak ada kelas ditutup', full: 'Baseline (tidak ada kelas ditutup)', intensity: 0.00 },
    { key: 'rendah',   label: 'Rendah',   kelas: 'kelas 3 ditutup',   full: 'Level Rendah (kelas 3 ditutup)',   intensity: 0.25 },
    { key: 'sedang',   label: 'Sedang',   kelas: 'kelas ≥ 2 ditutup', full: 'Level Sedang (kelas ≥ 2 ditutup)', intensity: 0.50 },
    { key: 'tinggi',   label: 'Tinggi',   kelas: 'kelas ≥ 1 ditutup', full: 'Level Tinggi (kelas ≥ 1 ditutup)', intensity: 0.75 }
];

const viewModes = {
    klaster:   'Tipologi Klaster SDWFCM',
    tas:       'Titik Aman Semu (TAS)',
    terdampak: 'Grid Tergenang',
    waktu:     'Waktu Tempuh Minimum ke TES',
    bahaya:    'Indeks Bahaya Banjir'
};

// Kelas waktu tempuh (menit) — ramp sekuensial satu hue (oranye), terang → gelap
const waktuBins = [
    { max: 5,        color: '#fdd9b5', label: '≤ 5 menit' },
    { max: 10,       color: '#fdb97d', label: '5 – 10 menit' },
    { max: 15,       color: '#fd8d3c', label: '10 – 15 menit' },
    { max: 30,       color: '#e6550d', label: '15 – 30 menit' },
    { max: 60,       color: '#b33c06', label: '30 – 60 menit' },
    { max: Infinity, color: '#7f2704', label: '> 60 menit / terisolasi' }
];
// Indeks bahaya banjir (InaRISK) — ramp sekuensial biru
const bahayaColors = { 0: '#c6dbef', 1: '#6baed6', 2: '#2171b5', 3: '#08306b' };
const bahayaLabels = { 0: 'Tidak Ada / Sangat Rendah', 1: 'Rendah', 2: 'Sedang', 3: 'Tinggi' };

function waktuColor(v) {
    if (v === null || v === undefined || !Number.isFinite(Number(v))) return NEUTRAL_FILL;
    return waktuBins.find(b => Number(v) <= b.max).color;
}
const routeColors = { 'pendidikan': '#3b82f6', 'kesehatan': '#ef4444', 'pemerintahan': '#f59e0b', 'ibadah': '#8b5cf6', 'gor': '#10b981' };
const mapTypeOptions = {
    'analitik': { label: 'Analitik', icon: 'fa-moon', requiresAdmin: false, requiresLandCover: false },
    'jalan':    { label: 'Jalan', icon: 'fa-road', requiresAdmin: false, requiresLandCover: false },
    'terrain':  { label: 'Terrain', icon: 'fa-mountain', requiresAdmin: false, requiresLandCover: false },
    'satelit':  { label: 'Satelit', icon: 'fa-satellite', requiresAdmin: false, requiresLandCover: false }
};
const tesCategories = {
    'pendidikan':   { label: 'Pendidikan', icon: 'fa-graduation-cap' },
    'kesehatan':    { label: 'Kesehatan', icon: 'fa-hospital' },
    'pemerintahan': { label: 'Pemerintahan', icon: 'fa-building' },
    'ibadah':       { label: 'Ibadah', icon: 'fa-place-of-worship' },
    'gor':          { label: 'GOR', icon: 'fa-volleyball-ball' }
};

const categoryIcons = {
    'pendidikan':   L.divIcon({ html: '<div class="tes-marker-container" style="color:#3b82f6"><i class="fa fa-graduation-cap"></i></div>', className: '', iconSize:[38,38], iconAnchor:[19,19] }),
    'kesehatan':    L.divIcon({ html: '<div class="tes-marker-container" style="color:#ef4444"><i class="fa fa-hospital"></i></div>', className: '', iconSize:[38,38], iconAnchor:[19,19] }),
    'pemerintahan': L.divIcon({ html: '<div class="tes-marker-container" style="color:#f59e0b"><i class="fa fa-building"></i></div>', className: '', iconSize:[38,38], iconAnchor:[19,19] }),
    'ibadah':       L.divIcon({ html: '<div class="tes-marker-container" style="color:#8b5cf6"><i class="fa fa-place-of-worship"></i></div>', className: '', iconSize:[38,38], iconAnchor:[19,19] }),
    'gor':          L.divIcon({ html: '<div class="tes-marker-container" style="color:#10b981"><i class="fa fa-volleyball-ball"></i></div>', className: '', iconSize:[38,38], iconAnchor:[19,19] })
};

let map, gridLayer, roadsLayer, roadsGeoJSON = null, legendControl = null, mode = 'visualize';
let tesLayer, tesGeoJSON = null, activeTesCategories = new Set();
let baseMapLayer = null, adminBoundaryLayer = null, landCoverLayer = null, adminGeoJSON = null;
let activeMapType = localStorage.getItem('evac_map_type') || 'analitik';
let activeAdminLayers = new Set(['kecamatan', 'desa']);
let landCoverOpacity = Number(localStorage.getItem('evac_land_cover_opacity') || '0.72');
let mapRuntimeState = { basemap: 'ready', overlay: 'idle', message: '' };
let landCoverRuntimeState = { tileErrors: 0, hasSuccessfulTile: false };
let roadCuts = [], cutMarkers = [], routeLayers, contextRouteLayers, originMarker = null, gridPopup = null;
let routingAbortController = null, isCalculating = false, markerPopupOpen = false;
let searchMarker = null, activeCluster = null, clustersHidden = false, searchBoundaryLayer = null;
let isolatedOrigin = null; // Store { latlng, routes, gridAttr, recommendations }
let lastK = 4; // diperbarui dari hasil API (k_optimal)
let activeLevel = localStorage.getItem('evac_level') || 'baseline';
let activeView = 'klaster';
let lastLevelResult = null;
let activePopupSnapshot = null;
let suppressRecommendationRestore = false;
let clusterNames = {};
let clusterNamesBySkKey = {};

function ensureGridPopup() {
    if (!gridPopup) {
        const narrow = window.innerWidth <= 760;
        gridPopup = L.popup({
            maxWidth: narrow ? 260 : 300, minWidth: narrow ? 220 : 260, maxHeight: narrow ? 240 : 420,
            autoClose: false, closeOnClick: false, autoPan: true,
            // ruang untuk panel kiri/kanan (desktop) atau header & panel rute bawah (ponsel)
            autoPanPaddingTopLeft: narrow ? L.point(10, 70) : L.point(380, 90),
            autoPanPaddingBottomRight: narrow ? L.point(10, Math.round(window.innerHeight * 0.45)) : L.point(300, 30),
            className: 'grid-popup'
        });
    }
    return gridPopup;
}

function toggleClusters(hide) {
    clustersHidden = hide;
    if (gridLayer) applyGridStyle();
}

function getGridAttrAt(latlng) {
    if (!gridLayer || !gridLayer.lookup) return null;
    let foundId = null;
    // Simple bound check (grid is regular)
    gridLayer.eachLayer(layer => {
        if (layer.getBounds().contains(latlng)) {
            foundId = layer.feature.properties.id_grid;
        }
    });
    return foundId !== null && foundId !== undefined ? gridLayer.lookup[foundId] : null;
}

function getGridCenterById(idGrid) {
    if (!gridLayer || idGrid === null || idGrid === undefined) return null;
    let center = null;
    gridLayer.eachLayer(layer => {
        if (layer.feature?.properties?.id_grid === idGrid) {
            center = layer.getBounds().getCenter();
        }
    });
    return center;
}

function clonePopupLatLng(latlng) {
    if (!latlng) return null;
    const cloned = L.latLng(latlng.lat, latlng.lng);
    if (latlng.gridAttr) cloned.gridAttr = latlng.gridAttr;
    if (latlng.id_grid !== undefined) cloned.id_grid = latlng.id_grid;
    if (latlng.isRecommendation) cloned.isRecommendation = true;
    return cloned;
}

function captureActivePopupState() {
    if (!map) return null;
    if (gridPopup && map.hasLayer(gridPopup) && gridPopup._gridRouteState) {
        const state = gridPopup._gridRouteState;
        activePopupSnapshot = {
            kind: 'grid',
            latlng: clonePopupLatLng(state.latlng),
            isGridClick: true
        };
        return activePopupSnapshot;
    }

    const popup = map._popup;
    if (popup && map.hasLayer(popup)) {
        const content = popup.getContent();
        activePopupSnapshot = {
            kind: 'generic',
            latlng: clonePopupLatLng(popup.getLatLng()),
            content: typeof content === 'string' ? content : popup._contentNode?.innerHTML || ''
        };
        return activePopupSnapshot;
    }
    activePopupSnapshot = null;
    return null;
}

function restoreActivePopupState(snapshot) {
    if (!snapshot || !map) return;
    if (snapshot.kind === 'grid' && snapshot.latlng) {
        const latlng = clonePopupLatLng(snapshot.latlng);
        latlng.gridAttr = getGridAttrAt(latlng) || latlng.gridAttr || null;
        calculateRoutes(latlng, true);
        return;
    }
    if (snapshot.kind === 'generic' && snapshot.latlng && snapshot.content) {
        L.popup({ maxWidth: 320, autoClose: false, closeOnClick: false })
            .setLatLng(snapshot.latlng)
            .setContent(snapshot.content)
            .openOn(map);
    }
}

function updateRouteResultsLayout() {
    const panel = document.getElementById('route-results');
    if (!panel) return;

    const layerControl = document.querySelector('.tes-layer-control');
    const attribution = document.querySelector('.leaflet-control-attribution');
    const viewportHeight = window.innerHeight || document.documentElement.clientHeight;

    const defaultTop = 100;
    const defaultBottom = 18;
    const gap = 12;

    const controlBottom = layerControl
        ? Math.min(viewportHeight - 120, Math.max(defaultTop, layerControl.getBoundingClientRect().bottom + gap))
        : defaultTop;

    const attributionTop = attribution
        ? Math.max(controlBottom + 180, attribution.getBoundingClientRect().top - gap)
        : (viewportHeight - 48);

    const availableHeight = Math.max(180, attributionTop - controlBottom);
    panel.style.top = `${Math.round(controlBottom)}px`;
    panel.style.maxHeight = `${Math.round(availableHeight)}px`;
    panel.style.bottom = 'auto';

    panel.classList.toggle('compact', availableHeight < 360);
    panel.classList.toggle('ultra-compact', availableHeight < 280);

    if (window.getComputedStyle(panel).display === 'none') {
        panel.style.height = 'auto';
        return;
    }

    panel.style.height = 'auto';
    const naturalHeight = panel.scrollHeight;
    panel.style.height = `${Math.min(Math.round(availableHeight), naturalHeight)}px`;
}

function isGridIsolated(gridAttr) {
    return gridAttr?.is_isolated === true || gridAttr?.is_isolated === 1;
}

function setClusterNames(names, skKey = null) {
    const hasNames = names && typeof names === 'object' && Object.keys(names).length > 0;
    if (hasNames) {
        clusterNames = names;
        if (skKey) clusterNamesBySkKey[skKey] = names;
        return;
    }
    if (skKey && clusterNamesBySkKey[skKey]) {
        clusterNames = clusterNamesBySkKey[skKey];
        return;
    }
    clusterNames = {};
}

function getClusterName(clusterId) {
    return clusterId === -1 ? 'Tergenang' : `Klaster ${clusterId}`;
}

function getClusterDesc(clusterId) {
    return clusterNames?.[String(clusterId)] || '';
}

function fmtNum(v, digits = 2) {
    const n = Number(v);
    return (v === null || v === undefined || !Number.isFinite(n)) ? '–' : n.toLocaleString('id-ID', { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

function fmtInt(v) {
    const n = Number(v);
    return (v === null || v === undefined || !Number.isFinite(n)) ? '–' : Math.round(n).toLocaleString('id-ID');
}

function levelLabel(key) {
    return (LEVELS.find(l => l.key === key) || LEVELS[0]).label;
}

function levelFullLabel(key) {
    return (LEVELS.find(l => l.key === key) || LEVELS[0]).full;
}

function popupRow(label, value, color = null) {
    return `<div class="popup-row"><span>${label}</span><b${color ? ` style="color:${color}"` : ''}>${value}</b></div>`;
}

function interpolateColor(color1, color2, color3, factor) {
    const hex = (c) => {
        const s = c.toString(16);
        return s.length == 1 ? '0' + s : s;
    };
    const decode = (h) => [parseInt(h.slice(1,3), 16), parseInt(h.slice(3,5), 16), parseInt(h.slice(5,7), 16)];
    let c1, c2, f;
    if (factor <= 0.5) {
        c1 = decode(color1); c2 = decode(color2); f = factor * 2;
    } else {
        c1 = decode(color2); c2 = decode(color3); f = (factor - 0.5) * 2;
    }
    const r = Math.round(c1[0] + (c2[0] - c1[0]) * f);
    const g = Math.round(c1[1] + (c2[1] - c1[1]) * f);
    const b = Math.round(c1[2] + (c2[2] - c1[2]) * f);
    return '#' + hex(r) + hex(g) + hex(b);
}

const searchIcon = L.divIcon({
    html: '<div class="tes-marker-container" style="color:#e74c3c; border-color:#e74c3c"><i class="fa fa-user-tag"></i></div>',
    className: '', iconSize:[40,40], iconAnchor:[20,20]
});

