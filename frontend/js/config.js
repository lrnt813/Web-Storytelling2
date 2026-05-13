const API_BASE = "/api";
const backendOriginOverride = window.__EVAC_API_ORIGIN || localStorage.getItem('evac_api_origin');
const backendOrigin = backendOriginOverride || ((window.location.hostname === '127.0.0.1' || window.location.hostname === 'localhost') && window.location.port !== '8000'
    ? `${window.location.protocol}//${window.location.hostname}:8000`
    : window.location.origin);
const RESOLVED_API_BASE = `${backendOrigin}/api`;
const clusterColors = { 0: "#3b82f6", 1: "#ef4444", 2: "#10b981", 3: "#f59e0b", 4: "#8b5cf6", "-1": "#475569" };
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
let roadCuts = [], cutMarkers = [], routeLayers, originMarker = null, gridPopup = null;
let routingAbortController = null, isCalculating = false, markerPopupOpen = false;
let searchMarker = null, activeCluster = null, clustersHidden = false, searchBoundaryLayer = null;
let isolatedOrigin = null; // Store { latlng, routes, gridAttr, recommendations }
let lastK = 5; // Global store for cluster count

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
    return foundId ? gridLayer.lookup[foundId] : null;
}

function isGridIsolated(gridAttr) {
    return gridAttr?.is_isolated === true || gridAttr?.is_isolated === 1;
}

function renderAlrValue(gridAttr, hasRouteAccess = false) {
    if (!gridAttr || gridAttr.alr_val === undefined) return '';
    const isolated = isGridIsolated(gridAttr) && !hasRouteAccess;
    const alr = Number(gridAttr.alr_val);
    const hasValidAlr = gridAttr.alr_val !== null && Number.isFinite(alr);
    const color = isolated || (hasValidAlr && alr >= 0.75) ? 'var(--danger)' : 'var(--accent-primary)';
    const label = isolated ? 'ISOLATED' : (hasValidAlr ? `${(alr * 100).toFixed(0)}%` : 'N/A');
    return `<div style="display:flex; justify-content:space-between; margin-top:4px;"><span style="color:var(--text-dim); font-size:10px;">ALR (Loss Ratio)</span><span style="font-weight:700; color:${color}">${label}</span></div>`;
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

