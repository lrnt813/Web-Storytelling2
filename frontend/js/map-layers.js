function initMap() {
    map = L.map('map', { zoomControl: false }).setView([-7.83, 110.15], 11);
    map.createPane('base-overlay-pane');
    map.getPane('base-overlay-pane').style.zIndex = 240;
    map.createPane('admin-pane');
    map.getPane('admin-pane').style.zIndex = 420;
    map.getPane('admin-pane').style.pointerEvents = 'none';
    map.createPane('label-pane');
    map.getPane('label-pane').style.zIndex = 450;
    map.getPane('label-pane').style.pointerEvents = 'none';
    L.control.zoom({ position: 'topright' }).addTo(map);

    map.createPane('route-pane');
    map.getPane('route-pane').style.zIndex = 650;
    map.getPane('route-pane').style.pointerEvents = 'none';

    map.createPane('marker-pane');
    map.getPane('marker-pane').style.zIndex = 660;

    routeLayers = L.layerGroup().addTo(map);
    contextRouteLayers = L.layerGroup().addTo(map);
    tesLayer = L.layerGroup().addTo(map);
    searchBoundaryLayer = L.layerGroup().addTo(map);
    adminBoundaryLayer = L.layerGroup().addTo(map);
    roadsLayer = L.geoJSON(null, { renderer: L.canvas({ padding: 0.3 }), interactive: false, style: roadStyle(false) });
    initBoundaryPanes();
    addTesLayerHoverControl();
    initMapTypeControls();
    initBoundaryControls();
    renderBoundaries();
    applyMapType(activeMapType);

    map.on('click', onMapClick);
    map.on('popupopen', e => { if (e.popup !== gridPopup) markerPopupOpen = true; });
    map.on('popupclose', e => {
        if (e.popup === gridPopup) {
            const state = gridPopup?._gridRouteState;
            if (state?.isRecommendationView && !suppressRecommendationRestore && isolatedOrigin) {
                restoreIsolatedOriginView();
                return;
            }
            routeLayers.clearLayers();
            contextRouteLayers.clearLayers();
            document.getElementById('route-results').style.display = 'none';
            const legend = document.querySelector('.info.legend');
            if (legend) legend.classList.remove('legend-hidden');
        } else markerPopupOpen = false;
    });
    window.addEventListener('resize', updateRouteResultsLayout);
}

function roadStyle(isBroken) {
    return isBroken
        ? { color: '#ef4444', weight: 2.2, opacity: 0.95 }
        : { color: '#e2e8f0', weight: 1, opacity: 0.45 };
}

const MODE_HINTS = {
    visualize: 'Klik grid pada peta untuk melihat detail dan rute ke TES terdekat.',
    cut: 'Klik ruas jalan pada peta untuk menandai blokir (klik tanda merah untuk menghapus), lalu tekan <b>Terapkan Blokir</b>.'
};

function toggleMode(newMode) {
    mode = (mode === newMode) ? 'visualize' : newMode;
    document.querySelectorAll('.mode-container .btn-outline').forEach(b => b.classList.remove('active'));
    document.getElementById(`btn-mode-${mode}`).classList.add('active');
    const hint = document.getElementById('mode-hint');
    if (hint) hint.innerHTML = MODE_HINTS[mode];
    map.getContainer().classList.toggle('cut-mode', mode === 'cut');
    if (mode === 'cut' && gridPopup && map.hasLayer(gridPopup)) {
        suppressRecommendationRestore = true;
        map.closePopup(gridPopup);
        suppressRecommendationRestore = false;
    }
}

let appliedCutsSig = '[]';
function updateCutUI() {
    const count = document.getElementById('cut-count');
    const btn = document.getElementById('btn-apply-cuts');
    if (count) count.textContent = roadCuts.length;
    if (btn) btn.disabled = JSON.stringify(roadCuts) === appliedCutsSig;
}

function applyRoadCuts() {
    routeLayers.clearLayers(); contextRouteLayers.clearLayers();
    if (gridPopup && map.hasLayer(gridPopup)) map.closePopup(gridPopup);
    document.getElementById('route-results').style.display = 'none';
    fetchAndRenderData();
}

function togglePanel() {
    document.getElementById('control-panel').classList.toggle('collapsed');
}

function toggleRoads(show) {
    if (show) { loadRoads(); if (!map.hasLayer(roadsLayer)) roadsLayer.addTo(map); }
    else if (map.hasLayer(roadsLayer)) map.removeLayer(roadsLayer);
}

function addTesLayerHoverControl() {
    const layerControl = L.control({ position: 'topright' });
    layerControl.onAdd = () => {
        const div = L.DomUtil.create('div', 'tes-layer-control leaflet-control');
        div.innerHTML = `
            <div class="tes-layer-shell" title="Lapisan peta">
                <div class="tes-layer-head">
                    <i class="fa fa-layer-group"></i>
                    <span>Lapisan Peta</span>
                </div>
                <div class="tes-layer-body">
                    <div class="layer-section">
                        <div class="layer-section-title">Tipe Peta</div>
                        <div class="layer-list" id="map-type-controls"></div>
                    </div>
                    <div class="layer-section">
                        <div class="layer-section-title">Batas Wilayah</div>
                        <div class="layer-list" id="boundary-controls"></div>
                    </div>
                    <div class="layer-section">
                        <div class="layer-section-title">Kategori TES</div>
                        <div class="layer-list" id="tes-layer-controls"></div>
                    </div>
                </div>
            </div>
        `;
        L.DomEvent.disableClickPropagation(div);
        L.DomEvent.disableScrollPropagation(div);
        div.addEventListener('mouseenter', () => window.setTimeout(updateRouteResultsLayout, 30));
        div.addEventListener('mouseleave', () => window.setTimeout(updateRouteResultsLayout, 180));
        return div;
    };
    layerControl.addTo(map);
    window.setTimeout(updateRouteResultsLayout, 0);
}

function initMapTypeControls() {
    const container = document.getElementById('map-type-controls');
    if (!container) return;
    container.innerHTML = '';

    Object.entries(mapTypeOptions).forEach(([key, meta]) => {
        const id = `map-type-${key}`;
        const row = document.createElement('div');
        row.className = 'layer-option layer-option-map-type';
        row.innerHTML = `
            <input type="radio" name="map-type" id="${id}" value="${key}">
            <span class="layer-symbol"><i class="fa ${meta.icon}"></i></span>
            <label class="layer-label" for="${id}">${meta.label}</label>
            <span class="layer-status ${activeMapType === key ? 'on' : 'off'}" id="${id}-status">${activeMapType === key ? 'Aktif' : 'Siaga'}</span>
        `;
        container.appendChild(row);

        const input = row.querySelector('input');
        input.checked = activeMapType === key;
        input.addEventListener('change', e => {
            if (!e.target.checked) return;
            localStorage.setItem('evac_map_type', key);
            applyMapType(key);
        });
    });
}

function refreshMapTypeControls() {
    Object.keys(mapTypeOptions).forEach(key => {
        const input = document.getElementById(`map-type-${key}`);
        const status = document.getElementById(`map-type-${key}-status`);
        if (input) input.checked = activeMapType === key;
        if (status) {
            status.textContent = activeMapType === key ? 'Aktif' : 'Siaga';
            status.className = `layer-status ${activeMapType === key ? 'on' : 'off'}`;
        }
    });
}

function setMapRuntimeState(nextState = {}) {
    mapRuntimeState = {
        basemap: nextState.basemap ?? mapRuntimeState.basemap,
        overlay: nextState.overlay ?? mapRuntimeState.overlay,
        message: nextState.message ?? mapRuntimeState.message
    };
}

function resetMapRuntimeState(type) {
    setMapRuntimeState({
        basemap: 'ready',
        overlay: mapTypeOptions[type]?.requiresLandCover ? 'ready' : 'idle',
        message: ''
    });
}

function renderLayerRuntimeNote() {
    const note = document.getElementById('layer-runtime-note');
    if (!note) return;
    if (!mapRuntimeState.message) {
        note.style.display = 'none';
        note.textContent = '';
        note.className = 'layer-runtime-note';
        return;
    }
    const tone = mapRuntimeState.basemap === 'fallback' || mapRuntimeState.overlay === 'error' ? 'warn' : 'info';
    note.style.display = 'block';
    note.className = `layer-runtime-note ${tone}`;
    note.textContent = mapRuntimeState.message;
}

function updateLayerSourceInfo(type) {
    renderLayerRuntimeNote();
}

// Seluruh basemap memakai layanan tanpa API key (Esri ArcGIS Online & OSM).
// CARTO/Stadia kini mewajibkan API key sehingga tile-nya bertuliskan "API KEY REQUIRED".
const ESRI = 'https://server.arcgisonline.com/ArcGIS/rest/services';
const ESRI_ATTR = 'Tiles &copy; Esri';

function getBaseLayerConfig(type) {
    if (type === 'jalan') {
        return { url: `${ESRI}/World_Street_Map/MapServer/tile/{z}/{y}/{x}`,
                 options: { attribution: `${ESRI_ATTR} — Esri, HERE, OpenStreetMap contributors`, maxZoom: 19 } };
    }
    if (type === 'terrain') {
        return { url: `${ESRI}/World_Topo_Map/MapServer/tile/{z}/{y}/{x}`,
                 options: { attribution: `${ESRI_ATTR} — Esri, USGS, NOAA`, maxZoom: 19 } };
    }
    if (type === 'satelit') {
        return { url: `${ESRI}/World_Imagery/MapServer/tile/{z}/{y}/{x}`,
                 options: { attribution: `${ESRI_ATTR} — Esri, Maxar, Earthstar Geographics`, maxZoom: 19 },
                 labels: `${ESRI}/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}` };
    }
    return { url: `${ESRI}/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}`,
             options: { attribution: `${ESRI_ATTR} — Esri, HERE, OpenStreetMap contributors`, maxZoom: 19, maxNativeZoom: 16 },
             labels: `${ESRI}/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}` };
}

function getFallbackBaseLayerConfig() {
    return { url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
             options: { attribution: '&copy; OpenStreetMap contributors', maxZoom: 19 } };
}

function attachBaseLayerGuards(layer, type) {
    layer.once('loading', () => {
        setMapRuntimeState({ basemap: 'ready', message: '' });
        updateLayerSourceInfo(activeMapType);
    });
    let errors = 0;
    layer.on('tileerror', () => {
        errors += 1;
        if (layer._fallbackApplied || activeMapType !== type || errors < 6) return;
        layer._fallbackApplied = true;
        const fallback = getFallbackBaseLayerConfig();
        clearBaseLayers();
        baseMapLayer = L.tileLayer(fallback.url, fallback.options).addTo(map);
        setMapRuntimeState({
            basemap: 'fallback',
            message: `Basemap ${mapTypeOptions[type].label} sedang bermasalah. Sistem memakai OpenStreetMap agar peta tetap tampil.`
        });
        updateLayerSourceInfo(activeMapType);
    });
}

let baseLabelLayer = null;
function clearBaseLayers() {
    if (baseMapLayer && map.hasLayer(baseMapLayer)) map.removeLayer(baseMapLayer);
    if (baseLabelLayer && map.hasLayer(baseLabelLayer)) map.removeLayer(baseLabelLayer);
    baseLabelLayer = null;
}

function setBaseMap(type) {
    const cfg = getBaseLayerConfig(type);
    clearBaseLayers();
    baseMapLayer = L.tileLayer(cfg.url, cfg.options).addTo(map);
    if (cfg.labels) {
        baseLabelLayer = L.tileLayer(cfg.labels, { pane: 'label-pane', maxZoom: 19, maxNativeZoom: cfg.options.maxNativeZoom || 19 }).addTo(map);
    }
    attachBaseLayerGuards(baseMapLayer, type);
}

async function ensureAdminBoundariesLoaded() {
    if (adminGeoJSON) return adminGeoJSON;
    const candidates = [...new Set([`${RESOLVED_API_BASE}/admin-layers`, `${API_BASE}/admin-layers`])];
    let lastError = null;
    for (const url of candidates) {
        try {
            const resp = await fetch(url);
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            adminGeoJSON = await resp.json();
            return adminGeoJSON;
        } catch (err) {
            lastError = err;
        }
    }
    throw new Error(`Gagal memuat layer administrasi${lastError ? `: ${lastError.message}` : ''}`);
}

async function showAdminBoundaries(show) {
    adminBoundaryLayer.clearLayers();
    if (!show) return;
    const data = await ensureAdminBoundariesLoaded();
    if (activeAdminLayers.has('desa')) {
        L.geoJSON(data.desa, {
            pane: 'admin-pane',
            style: { color: '#94a3b8', weight: 1, opacity: 0.7, fillOpacity: 0 }
        }).addTo(adminBoundaryLayer);
    }

    if (activeAdminLayers.has('kecamatan')) {
        L.geoJSON(data.kecamatan, {
            pane: 'admin-pane',
            style: { color: '#f8fafc', weight: 2.2, opacity: 0.92, fillOpacity: 0, dashArray: '6 4' },
            onEachFeature: (feature, layer) => {
                if (feature.properties?.name) {
                    layer.bindTooltip(feature.properties.name, {
                        direction: 'center',
                        sticky: true,
                        className: 'admin-tooltip'
                    });
                }
            }
        }).addTo(adminBoundaryLayer);
    }
    adminBoundaryLayer.eachLayer(layer => {
        if (layer.bringToFront) layer.bringToFront();
    });
}

function showLandCover(show) {
    if (!show) {
        if (landCoverLayer && map.hasLayer(landCoverLayer)) map.removeLayer(landCoverLayer);
        landCoverRuntimeState = { tileErrors: 0, hasSuccessfulTile: false };
        if (activeMapType !== 'tutupan_lahan') {
            setMapRuntimeState({ overlay: 'idle', message: mapRuntimeState.basemap === 'fallback' ? mapRuntimeState.message : '' });
            updateLayerSourceInfo(activeMapType);
        }
        return;
    }
    if (!landCoverLayer) {
        landCoverLayer = L.tileLayer(
            'https://services.arcgisonline.com/ArcGIS/rest/services/ESRI_LandCover_World_2020/MapServer/tile/{z}/{y}/{x}',
            {
                attribution: 'Land cover &copy; Esri',
                opacity: landCoverOpacity,
                pane: 'base-overlay-pane',
                maxZoom: 18
            }
        );
        landCoverLayer.on('load', () => {
            if (activeMapType !== 'tutupan_lahan') return;
            landCoverRuntimeState.hasSuccessfulTile = true;
            landCoverRuntimeState.tileErrors = 0;
            setMapRuntimeState({ overlay: 'ready', message: mapRuntimeState.basemap === 'fallback' ? mapRuntimeState.message : '' });
            updateLayerSourceInfo(activeMapType);
            addLegend();
        });
        landCoverLayer.on('tileerror', () => {
            if (activeMapType !== 'tutupan_lahan') return;
            landCoverRuntimeState.tileErrors += 1;
            if (landCoverRuntimeState.hasSuccessfulTile || landCoverRuntimeState.tileErrors < 8) return;
            if (map.hasLayer(landCoverLayer)) map.removeLayer(landCoverLayer);
            setMapRuntimeState({
                overlay: 'error',
                message: 'Overlay tutupan lahan tidak berhasil dimuat. Basemap tetap aktif, tetapi layer penutup lahan sementara dinonaktifkan.'
            });
            updateLayerSourceInfo(activeMapType);
            addLegend();
        });
    }
    landCoverLayer.setOpacity(landCoverOpacity);
    landCoverLayer.addTo(map);
}

async function applyMapType(type) {
    activeMapType = mapTypeOptions[type] ? type : 'analitik';
    landCoverRuntimeState = { tileErrors: 0, hasSuccessfulTile: false };
    resetMapRuntimeState(activeMapType);
    refreshMapTypeControls();
    setBaseMap(activeMapType);
    updateLayerSourceInfo(activeMapType);
    adminBoundaryLayer.clearLayers();
    showLandCover(false);
    addLegend();
}

function initTesLayerControls() {
    const container = document.getElementById('tes-layer-controls');
    if (!container) return;
    container.innerHTML = '';

    Object.entries(tesCategories).forEach(([kat, meta]) => {
        const id = `layer-tes-${kat}`;
        const row = document.createElement('div');
        row.className = 'layer-option';
        row.innerHTML = `
            <input type="checkbox" id="${id}" data-kategori="${kat}">
            <span class="layer-symbol" style="color:${routeColors[kat]}"><i class="fa ${meta.icon}"></i></span>
            <label class="layer-label" for="${id}">${meta.label}</label>
            <span class="layer-count" id="${id}-count">0</span>
        `;
        container.appendChild(row);

        row.querySelector('input').addEventListener('change', e => {
            if (e.target.checked) activeTesCategories.add(kat);
            else activeTesCategories.delete(kat);
            localStorage.setItem('evac_tes_layers', JSON.stringify([...activeTesCategories]));
            renderTesLayers();
            e.target.blur();
        });
    });

    try {
        const saved = JSON.parse(localStorage.getItem('evac_tes_layers') || '[]');
        activeTesCategories = new Set(saved.filter(kat => tesCategories[kat]));
    } catch {
        activeTesCategories = new Set();
    }

    activeTesCategories.forEach(kat => {
        const input = document.getElementById(`layer-tes-${kat}`);
        if (input) input.checked = true;
    });
}

async function loadTesLayers() {
    try {
        const resp = await fetch(`${API_BASE}/tes-layers?level=${activeLevel}`);
        const result = await resp.json();
        tesGeoJSON = result.geojson;

        Object.entries(result.counts || {}).forEach(([kat, count]) => {
            const countEl = document.getElementById(`layer-tes-${kat}-count`);
            if (countEl) countEl.textContent = count;
        });

        renderTesLayers();
    } catch (e) {
        console.error(e);
    }
}

function renderTesLayers() {
    if (!tesLayer) return;
    tesLayer.clearLayers();
    if (!tesGeoJSON || activeTesCategories.size === 0) return;

    L.geoJSON(tesGeoJSON, {
        filter: feature => activeTesCategories.has(feature.properties.kategori),
        pointToLayer: (feature, latlng) => {
            const kat = feature.properties.kategori;
            const marker = L.marker(latlng, { icon: categoryIcons[kat], pane: 'marker-pane' });
            if (feature.properties.is_valid === false) marker.setOpacity(0.35);
            return marker;
        },
        onEachFeature: (feature, layer) => {
            const props = feature.properties;
            const kat = props.kategori;
            const meta = tesCategories[kat] || { label: kat };
            const status = props.is_valid === false
                ? `<div style="margin-top:8px; color:var(--danger); font-size:11px;">Tidak valid sebagai TES pada level ${levelLabel(activeLevel)} (berada di zona bahaya banjir)</div>`
                : '';
            layer.bindPopup(`
                <div style="min-width:180px;">
                    <b style="color:${routeColors[kat] || 'var(--accent-primary)'}">${meta.label}</b><br>
                    <span style="font-size:12px;">${props.name || 'Fasilitas TES'}</span>
                    ${status}
                </div>
            `);
        }
    }).addTo(tesLayer);
}

function onMapClick(e) {
    if (mode === 'cut') addRoadCut(e.latlng);
    else if (!markerPopupOpen) {
        if (gridPopup && map.hasLayer(gridPopup)) {
            suppressRecommendationRestore = true;
            map.closePopup(gridPopup);
            suppressRecommendationRestore = false;
        }
    }
}

function addRoadCut(latlng, skipSave = false) {
    const cut = { lat: latlng.lat, lng: latlng.lng };
    roadCuts.push(cut);
    const marker = L.circleMarker(latlng, { radius: 8, color: '#ef4444', weight: 3, fillOpacity: 0.8, fillColor: '#000', pane: 'marker-pane' })
        .bindTooltip('Blokir jalan — klik untuk menghapus', { direction: 'top' })
        .addTo(map);
    marker.on('click', e => {
        L.DomEvent.stopPropagation(e);
        roadCuts = roadCuts.filter(c => c !== cut);
        cutMarkers = cutMarkers.filter(m => m !== marker);
        map.removeLayer(marker);
        saveSession(); updateCutUI();
    });
    cutMarkers.push(marker);
    if (!skipSave) saveSession();
    updateCutUI();
}

function saveSession() {
    localStorage.setItem('evac_road_cuts', JSON.stringify(roadCuts));
}

function loadSession() {
    const saved = localStorage.getItem('evac_road_cuts');
    if (saved) {
        const cuts = JSON.parse(saved);
        cuts.forEach(c => addRoadCut(c, true));
        if (cuts.length > 0) fetchAndRenderData();
    }
}

async function resetSimulation() {
    roadCuts = []; cutMarkers.forEach(m => map.removeLayer(m)); cutMarkers = [];
    localStorage.removeItem('evac_road_cuts');
    updateCutUI();
    routeLayers.clearLayers(); contextRouteLayers.clearLayers(); if (originMarker) map.removeLayer(originMarker);
    document.getElementById('route-results').style.display = 'none';
    
    const legend = document.querySelector('.info.legend');
    if (legend) legend.classList.remove('legend-hidden');

    await fetchAndRenderData();
}

async function fetchAndRenderData(retryCount = 0) {
    if (isCalculating) return;
    isCalculating = true; showLoading(true);
    const popupSnapshot = captureActivePopupState();
    let shouldRestorePopup = false;

    // Update jalan & TES secara paralel
    const roadUpdate = document.getElementById('check-roads').checked ? loadRoads() : Promise.resolve();
    const tesUpdate = loadTesLayers();

    try {
        const resp = roadCuts.length > 0
            ? await fetch(`${API_BASE}/simulate`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ level: activeLevel, cut_roads: roadCuts }) })
            : await fetch(`${API_BASE}/baseline?level=${activeLevel}`);

        if (resp.status === 503 && retryCount < 60) {
            setTimeout(() => { isCalculating = false; fetchAndRenderData(retryCount + 1); }, 3000);
            return;
        }
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

        const result = await resp.json();
        await roadUpdate;
        await tesUpdate;

        lastLevelResult = result;
        appliedCutsSig = JSON.stringify(roadCuts);
        updateCutUI();
        setClusterNames(result.cluster_names, result.sk_key);
        addLegend(result.k_optimal);
        gridLayer.lookup = Object.fromEntries(result.data_klaster.map(d => [d.id_grid, d]));
        applyGridStyle();
        renderLevelSummary(result);
        if (compareLevel) applyCompareStyle();
        if (typeof renderRegionPanel === 'function') renderRegionPanel();
        updateRouteResultsLayout();
        shouldRestorePopup = Boolean(popupSnapshot);
    } catch (error) { console.error(error); }
    finally {
        showLoading(false);
        isCalculating = false;
        if (shouldRestorePopup && popupSnapshot) {
            setTimeout(() => restoreActivePopupState(popupSnapshot), 0);
        }
    }
}

function setLevel(key) {
    if (!LEVELS.some(l => l.key === key)) key = 'baseline';
    activeLevel = key;
    localStorage.setItem('evac_level', key);
    document.querySelectorAll('.level-btn').forEach(b => b.classList.toggle('active', b.dataset.level === key));
    fetchAndRenderData();
}

function setView(view) {
    activeView = viewModes[view] ? view : 'klaster';
    activeCluster = null;
    document.getElementById('view-mode').value = activeView;
    applyGridStyle();
    addLegend();
}

function renderLevelSummary(result) {
    const el = document.getElementById('level-summary');
    if (!el || !result) return;
    const tas = result.tas || {};
    const sim = result.simulated
        ? `<div class="summary-note sim"><i class="fa fa-flask"></i> SIMULASI: ${result.n_cut_roads} titik blokir jalan — angka di atas bukan hasil skripsi</div>` : '';
    const banner = document.getElementById('sim-banner');
    if (banner) {
        banner.hidden = !result.simulated;
        const t = document.getElementById('sim-banner-text');
        if (t && result.simulated) t.textContent = `level ${levelLabel(result.level)}, ${result.n_cut_roads} titik blokir jalan, klasterisasi ulang`;
    }
    el.innerHTML = `
        <div class="summary-grid">
            <div class="summary-tile"><span>Grid terdampak</span><b>${fmtInt(result.n_grid_terdampak)}</b></div>
            <div class="summary-tile"><span>Rata-rata waktu min.</span><b>${fmtNum(result.mean_waktu_min)} <small>mnt</small></b></div>
            <div class="summary-tile"><span>Titik Aman Semu</span><b>${fmtInt(tas.jumlah_tas)} <small>(${fmtNum(tas.persen_tas)}%)</small></b></div>
            <div class="summary-tile"><span>Rerata DI TAS / Non-TAS</span><b>${fmtNum(tas.mean_di_tas)} / ${fmtNum(tas.mean_di_non_tas)}</b></div>
        </div>${sim}`;
}

function gridStyleFor(d) {
    if (clustersHidden) return { fillColor: NEUTRAL_FILL, fillOpacity: 0.25, stroke: false };
    const dim = activeCluster !== null && activeView === 'klaster' && d.cluster_sdwfcm !== activeCluster;
    if (activeView === 'tas') {
        return d.titik_aman_semu === 1
            ? { fillColor: TAS_COLOR, fillOpacity: 0.9, stroke: false }
            : { fillColor: NEUTRAL_FILL, fillOpacity: 0.18, stroke: false };
    }
    if (activeView === 'terdampak') {
        return d.terdampak === 1
            ? { fillColor: TERDAMPAK_COLOR, fillOpacity: 0.8, stroke: false }
            : { fillColor: NEUTRAL_FILL, fillOpacity: 0.18, stroke: false };
    }
    if (activeView === 'waktu') return { fillColor: waktuColor(d.waktu_tes_min), fillOpacity: 0.8, stroke: false };
    if (activeView === 'bahaya') return { fillColor: bahayaColors[d.indeks_bahaya] || NEUTRAL_FILL, fillOpacity: 0.8, stroke: false };
    return {
        fillColor: clusterColors[d.cluster_sdwfcm] || NEUTRAL_FILL,
        fillOpacity: dim ? 0.05 : Math.max(0.45, d.membership_max || 0.7), stroke: false
    };
}

function gridStyleFromLookup(lookup) {
    return f => {
        const d = lookup[f.properties.id_grid];
        if (!d) return { fillOpacity: 0, stroke: false };
        const st = gridStyleFor(d);
        return { ...st, stroke: true, color: st.fillColor, weight: 0.6, opacity: st.fillOpacity };
    };
}

function applyGridStyle() {
    if (compareLevel) applyCompareStyle();
    if (!gridLayer || !gridLayer.lookup) return;
    const lookup = gridLayer.lookup;
    gridLayer.setStyle(f => {
        const d = lookup[f.properties.id_grid];
        if (!d) return { fillOpacity: 0, stroke: false };
        // Garis tipis sewarna isian menutup celah antialias antarsel pada zoom kecil
        // tanpa memunculkan garis putih (grid tampak bergaris).
        const st = gridStyleFor(d);
        return { ...st, stroke: true, color: st.fillColor, weight: 0.6, opacity: st.fillOpacity };
    });
}

async function loadStaticGeometry() {
    showLoading(true);
    try {
        const response = await fetch('./static_grid_kulonprogo.geojson');
        const geojsonData = await response.json();
        gridGeoJSONData = geojsonData;
        gridLayer = L.geoJSON(geojsonData, {
            renderer: L.canvas({ padding: 0.5 }),
            style: { fillColor: '#1e293b', stroke: false, fillOpacity: 0.1 },
            onEachFeature: (feature, layer) => {
                layer.on('click', e => {
                    if (mode === 'visualize') {
                        L.DomEvent.stopPropagation(e);
                        const originLatLng = layer.getBounds().getCenter();
                        originLatLng.gridAttr = gridLayer.lookup ? gridLayer.lookup[feature.properties.id_grid] : null;
                        originLatLng.id_grid = feature.properties.id_grid;
                        originLatLng.popupLatLng = e.latlng;
                        calculateRoutes(originLatLng, true);
                    }
                });
            }
        }).addTo(map);
        await fetchAndRenderData();
    } finally { showLoading(false); }
}

async function loadRoads() {
    try {
        const isFirstLoad = (roadsGeoJSON === null);
        const body = { 
            level: activeLevel,
            cut_roads: roadCuts,
            full: isFirstLoad
        };
        
        const resp = await fetch(`${API_BASE}/roads`, { 
            method: 'POST', 
            headers: { 'Content-Type': 'application/json' }, 
            body: JSON.stringify(body) 
        });
        
        const result = await resp.json();
        
        if (isFirstLoad) {
            roadsGeoJSON = result;
            roadsLayer.clearLayers().addData(roadsGeoJSON);
            roadsLayer.setStyle(f => roadStyle(f.properties.is_broken));
        } else {
            // Optimized Update: Hanya update style berdasarkan broken_ids tanpa render ulang geometri
            const brokenIds = new Set(result.broken_ids);
            roadsLayer.eachLayer(layer => {
                const id = layer.feature.properties.id_jalan;
                const isBroken = brokenIds.has(id);
                layer.setStyle(roadStyle(isBroken));
            });
        }
    } catch (e) { console.error(e); }
}



// ══════════════════════════════════════════════════════════════════════════
// PEMBANDING LEVEL (swipe): kiri = level aktif, kanan = level pembanding
// ══════════════════════════════════════════════════════════════════════════
let gridGeoJSONData = null;
let compareLevel = '';
let compareLayer = null;
let compareFraction = 0.5;
const compareLookups = {};

async function fetchLevelLookup(level) {
    if (compareLookups[level]) return compareLookups[level];
    const resp = await fetch(`${API_BASE}/baseline?level=${level}`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const result = await resp.json();
    compareLookups[level] = Object.fromEntries(result.data_klaster.map(d => [d.id_grid, d]));
    return compareLookups[level];
}

function ensureComparePane() {
    if (!map.getPane('compare-pane')) {
        map.createPane('compare-pane');
        map.getPane('compare-pane').style.zIndex = 402;
        map.getPane('compare-pane').style.pointerEvents = 'none';
    }
    if (!document.getElementById('compare-divider')) {
        const div = L.DomUtil.create('div', 'compare-divider', map.getContainer());
        div.id = 'compare-divider';
        div.innerHTML = `<div class="cd-line"></div>
            <div class="cd-handle" title="Geser untuk membandingkan"><i class="fa fa-left-right"></i></div>
            <div class="cd-label cd-left" id="cd-left"></div><div class="cd-label cd-right" id="cd-right"></div>`;
        L.DomEvent.disableClickPropagation(div);
        L.DomEvent.disableScrollPropagation(div);
        const handle = div.querySelector('.cd-handle');
        const onMove = e => {
            const rect = map.getContainer().getBoundingClientRect();
            const x = (e.touches ? e.touches[0].clientX : e.clientX) - rect.left;
            compareFraction = Math.min(0.98, Math.max(0.02, x / rect.width));
            updateCompareClip();
        };
        const stop = () => {
            document.removeEventListener('pointermove', onMove);
            document.removeEventListener('pointerup', stop);
            map.dragging.enable();
        };
        handle.addEventListener('pointerdown', e => {
            e.preventDefault(); e.stopPropagation();
            map.dragging.disable();
            document.addEventListener('pointermove', onMove);
            document.addEventListener('pointerup', stop);
        });
        map.on('move zoom resize viewreset zoomend moveend', updateCompareClip);
    }
}

function updateCompareClip() {
    const pane = map.getPane('compare-pane');
    const divider = document.getElementById('compare-divider');
    if (!pane || !divider) return;
    if (!compareLevel) { pane.style.clip = ''; divider.hidden = true; return; }
    divider.hidden = false;
    const size = map.getSize();
    const x = Math.round(size.x * compareFraction);
    const nw = map.containerPointToLayerPoint([0, 0]);
    const se = map.containerPointToLayerPoint(size);
    const cx = map.containerPointToLayerPoint([x, 0]).x;
    pane.style.clip = `rect(${nw.y}px, ${se.x}px, ${se.y}px, ${cx}px)`;
    divider.style.left = `${x}px`;
    document.getElementById('cd-left').textContent = `◀ ${levelLabel(activeLevel)}${lastLevelResult?.simulated ? ' (simulasi)' : ''}`;
    document.getElementById('cd-right').textContent = `${levelLabel(compareLevel)} ▶`;
}

function applyCompareStyle() {
    if (!compareLayer || !compareLevel || !compareLookups[compareLevel]) return;
    compareLayer.setStyle(gridStyleFromLookup(compareLookups[compareLevel]));
    updateCompareClip();
}

async function setCompareLevel(level) {
    compareLevel = level || '';
    ensureComparePane();
    if (!compareLevel) {
        if (compareLayer && map.hasLayer(compareLayer)) map.removeLayer(compareLayer);
        updateCompareClip();
        return;
    }
    try {
        showLoading(true);
        await fetchLevelLookup(compareLevel);
        if (!compareLayer) {
            compareLayer = L.geoJSON(gridGeoJSONData, {
                pane: 'compare-pane', interactive: false,
                renderer: L.canvas({ pane: 'compare-pane', padding: 0.5 }),
                style: gridStyleFromLookup(compareLookups[compareLevel])
            });
        }
        if (!map.hasLayer(compareLayer)) compareLayer.addTo(map);
        applyCompareStyle();
    } catch (e) {
        console.error(e);
        if (typeof showToast === 'function') showToast('Gagal memuat level pembanding.', 'warn');
    } finally {
        showLoading(false);
    }
}
