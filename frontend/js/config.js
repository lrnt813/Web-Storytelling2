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
let roadCuts = [], cutMarkers = [], routeLayers, contextRouteLayers, originMarker = null, gridPopup = null;
let routingAbortController = null, isCalculating = false, markerPopupOpen = false;
let searchMarker = null, activeCluster = null, clustersHidden = false, searchBoundaryLayer = null;
let isolatedOrigin = null; // Store { latlng, routes, gridAttr, recommendations }
let lastK = 5; // Global store for cluster count
let pseudoSafetyThresholds = { psi: null, alr: null };
let activePopupSnapshot = null;
let suppressRecommendationRestore = false;
let clusterNames = {};
let clusterNamesBySkKey = {};

function ensureGridPopup() {
    if (!gridPopup) {
        gridPopup = L.popup({ maxWidth: 320, autoClose: false, closeOnClick: false, autoPan: false });
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

function setPseudoSafetyThresholds(thresholds) {
    pseudoSafetyThresholds = thresholds || { psi: null, alr: null };
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
    const key = String(clusterId);
    return clusterNames?.[key] || clusterNames?.[clusterId] || `Klaster ${clusterId}`;
}

function classifyByThreshold(metricKey, value) {
    const metric = pseudoSafetyThresholds?.[metricKey];
    const numericValue = Number(value);
    if (!metric || value === null || !Number.isFinite(numericValue)) return null;
    if (numericValue >= Number(metric.upper)) return 'high';
    if (numericValue >= Number(metric.lower)) return 'mid';
    return 'low';
}

function renderPsiValue(gridAttr) {
    if (!gridAttr || gridAttr.psi_val === undefined || gridAttr.psi_val === null) return '';
    const psi = Number(gridAttr.psi_val);
    if (!Number.isFinite(psi)) return '';
    const level = gridAttr.psi_class || classifyByThreshold('psi', psi);
    const color = level === 'critical' || level === 'high'
        ? 'var(--danger)'
        : (level === 'fragile' || level === 'mid' ? 'var(--warning)' : 'var(--accent-primary)');
    const label = gridAttr.psi_class ? `${psi.toFixed(2)} • ${String(gridAttr.psi_class).toUpperCase()}` : psi.toFixed(2);
    return `<div style="display:flex; justify-content:space-between; margin-top:4px;"><span style="color:var(--text-dim); font-size:10px;">PSI (Instability)</span><span style="font-weight:700; color:${color}">${label}</span></div>`;
}

function renderAlrValue(gridAttr, hasRouteAccess = false) {
    if (!gridAttr || gridAttr.alr_val === undefined) return '';
    const isolated = isGridIsolated(gridAttr) && !hasRouteAccess;
    const alr = Number(gridAttr.alr_val);
    const hasValidAlr = gridAttr.alr_val !== null && Number.isFinite(alr);
    const level = isolated ? 'isolated' : (gridAttr.alr_class || classifyByThreshold('alr', alr));
    const color = (level === 'isolated' || level === 'severe' || level === 'high')
        ? 'var(--danger)'
        : ((level === 'moderate' || level === 'mid') ? 'var(--warning)' : 'var(--accent-primary)');
    const label = isolated
        ? 'ISOLATED'
        : (hasValidAlr ? `${(alr * 100).toFixed(0)}%${gridAttr.alr_class ? ` • ${String(gridAttr.alr_class).toUpperCase()}` : ''}` : 'N/A');
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

