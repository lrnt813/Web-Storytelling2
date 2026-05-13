function initMap() {
    map = L.map('map', { zoomControl: false }).setView([-7.83, 110.15], 11);
    map.createPane('base-overlay-pane');
    map.getPane('base-overlay-pane').style.zIndex = 240;
    map.createPane('admin-pane');
    map.getPane('admin-pane').style.zIndex = 420;
    map.getPane('admin-pane').style.pointerEvents = 'none';
    baseMapLayer = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', { attribution: '&copy; CARTO' }).addTo(map);
    L.control.zoom({ position: 'topright' }).addTo(map);

    map.createPane('route-pane');
    map.getPane('route-pane').style.zIndex = 650;
    map.getPane('route-pane').style.pointerEvents = 'none';

    map.createPane('marker-pane');
    map.getPane('marker-pane').style.zIndex = 660;

    routeLayers = L.layerGroup().addTo(map);
    tesLayer = L.layerGroup().addTo(map);
    searchBoundaryLayer = L.layerGroup().addTo(map);
    adminBoundaryLayer = L.layerGroup().addTo(map);
    roadsLayer = L.geoJSON(null, { style: { color: '#fbbf24', weight: 4, opacity: 0.4 } }).addTo(map);
    addTesLayerHoverControl();
    initMapTypeControls();
    applyMapType(activeMapType);

    map.on('click', onMapClick);
    map.on('popupopen', e => { if (e.popup !== gridPopup) markerPopupOpen = true; });
    map.on('popupclose', e => { if (e.popup !== gridPopup) markerPopupOpen = false; else gridPopup = null; });
}

function toggleMode(newMode) {
    mode = (mode === newMode) ? 'visualize' : newMode;
    document.querySelectorAll('.btn-outline').forEach(b => b.classList.remove('active'));
    document.getElementById(`btn-mode-${mode}`).classList.add('active');
}

function toggleRoads(show) {
    if (show) { loadRoads(); roadsLayer.setStyle({ opacity: 0.6 }); }
    else roadsLayer.setStyle({ opacity: 0 });
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
                        <div class="layer-section-title">Kategori TES</div>
                        <div class="layer-list" id="tes-layer-controls"></div>
                    </div>
                </div>
            </div>
        `;
        L.DomEvent.disableClickPropagation(div);
        L.DomEvent.disableScrollPropagation(div);
        return div;
    };
    layerControl.addTo(map);
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

function getBaseLayerConfig(type) {
    if (type === 'jalan') {
        return {
            url: 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',
            options: { attribution: '&copy; OpenStreetMap contributors &copy; CARTO', maxZoom: 20 }
        };
    }
    if (type === 'terrain') {
        return {
            url: 'https://tiles.stadiamaps.com/tiles/stamen_terrain/{z}/{x}/{y}.png',
            options: { attribution: '&copy; Stadia Maps &copy; Stamen Design', maxZoom: 18 }
        };
    }
    if (type === 'satelit') {
        return {
            url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            options: { attribution: 'Tiles &copy; Esri', maxZoom: 19 }
        };
    }
    if (type === 'administrasi' || type === 'tutupan_lahan') {
        return {
            url: 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
            options: { attribution: '&copy; OpenStreetMap contributors &copy; CARTO', maxZoom: 20 }
        };
    }
    return {
        url: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
        options: { attribution: '&copy; CARTO', maxZoom: 20 }
    };
}

function getFallbackBaseLayerConfig(type) {
    if (type === 'analitik') return getBaseLayerConfig('analitik');
    return {
        url: 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
        options: { attribution: '&copy; OpenStreetMap contributors &copy; CARTO', maxZoom: 20 }
    };
}

function attachBaseLayerGuards(layer, type) {
    layer.once('loading', () => {
        setMapRuntimeState({ basemap: 'ready', message: '' });
        updateLayerSourceInfo(activeMapType);
    });
    layer.on('tileerror', () => {
        if (layer._fallbackApplied || activeMapType !== type) return;
        layer._fallbackApplied = true;
        const fallback = getFallbackBaseLayerConfig(type);
        if (baseMapLayer && map.hasLayer(baseMapLayer)) map.removeLayer(baseMapLayer);
        baseMapLayer = L.tileLayer(fallback.url, fallback.options).addTo(map);
        setMapRuntimeState({
            basemap: 'fallback',
            message: `Basemap ${mapTypeOptions[type].label} sedang bermasalah. Sistem memakai basemap cadangan agar peta tetap tampil.`
        });
        updateLayerSourceInfo(activeMapType);
        addLegend();
    });
}

function setBaseMap(type) {
    const cfg = getBaseLayerConfig(type);
    if (baseMapLayer) map.removeLayer(baseMapLayer);
    baseMapLayer = L.tileLayer(cfg.url, cfg.options).addTo(map);
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
        const skenario = document.getElementById('skenario').value;
        const intensitas = parseFloat(document.getElementById('intensitas').value);
        const resp = await fetch(`${API_BASE}/tes-layers?skenario=${skenario}&intensity=${intensitas}`);
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
                ? '<div style="margin-top:8px; color:var(--danger); font-size:11px;">Tidak aktif pada skenario ini</div>'
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
    else if (gridPopup && !markerPopupOpen) { map.closePopup(gridPopup); gridPopup = null; }
}

function addRoadCut(latlng, skipSave = false) {
    roadCuts.push({ lat: latlng.lat, lng: latlng.lng });
    const marker = L.circleMarker(latlng, { radius: 8, color: '#ef4444', weight: 3, fillOpacity: 0.8, fillColor: '#000' }).addTo(map);
    cutMarkers.push(marker);
    if (!skipSave) saveSession();
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
    routeLayers.clearLayers(); if (originMarker) map.removeLayer(originMarker);
    document.getElementById('route-results').style.display = 'none';
    
    const legend = document.querySelector('.info.legend');
    if (legend) legend.classList.remove('legend-hidden');

    await fetchAndRenderData();
}

async function fetchAndRenderData(retryCount = 0) {
    if (isCalculating) return;
    isCalculating = true; showLoading(true);
    const skenario = document.getElementById('skenario').value;
    const intensitas = document.getElementById('intensitas').value;

    // Trigger update jalan secara paralel jika checkbox aktif
    const roadUpdate = document.getElementById('check-roads').checked ? loadRoads() : Promise.resolve();
    const tesUpdate = loadTesLayers();

    try {
        const endpoint = (roadCuts.length > 0 || parseFloat(intensitas) > 0) ? 'simulate' : 'baseline';
        const resp = (endpoint === 'simulate') 
            ? await fetch(`${API_BASE}/simulate`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ skenario, intensity: parseFloat(intensitas), cut_roads: roadCuts }) })
            : await fetch(`${API_BASE}/baseline?skenario=${skenario}&intensity=${intensitas}`);

        if (resp.status === 503 && retryCount < 5) {
            setTimeout(() => { isCalculating = false; fetchAndRenderData(retryCount + 1); }, 3000);
            return;
        }

        const result = await resp.json();
        
        // Pastikan update jalan selesai sebelum menghilangkan loading
        await roadUpdate;
        await tesUpdate;

        addLegend(result.k_optimal);
        const lookup = Object.fromEntries(result.data_klaster.map(d => [d.id_grid, d]));
        gridLayer.lookup = lookup;
        applyGridStyle();
    } catch (error) { console.error(error); }
    finally { showLoading(false); isCalculating = false; }
}

function applyGridStyle() {
    if (!gridLayer || !gridLayer.lookup) return;
    const lookup = gridLayer.lookup;
    gridLayer.setStyle(f => {
        const d = lookup[f.properties.id_grid];
        if (!d) return { fillOpacity: 0, weight: 0 };
        
        let opacity = d.membership_max || 0.7;
        
        // Logika Filtering Legend
        if (activeMode === 'semu') {
            if (d.titik_aman_semu !== 1) opacity = 0.05;
        } else if (activeCluster !== null) {
            if (d.cluster_sdwfcm !== activeCluster) opacity = 0.05;
        }

        // Feature request: Gray mode
        if (clustersHidden) {
            return { fillColor: '#475569', fillOpacity: opacity * 0.4, color: '#fff', weight: 0.1 };
        }

        if (d.titik_aman_semu === 1) {
            return { 
                fillColor: '#000', 
                fillOpacity: opacity > 0.1 ? 0.9 : 0.05, 
                color: '#f59e0b', 
                weight: activeMode === 'semu' ? 2.5 : 1.5 
            };
        }
        
        return { fillColor: clusterColors[d.cluster_sdwfcm] || '#475569', fillOpacity: opacity, color: '#fff', weight: 0.2 };
    });
}

async function loadStaticGeometry() {
    showLoading(true);
    try {
        const response = await fetch('./static_grid_kulonprogo.geojson');
        const geojsonData = await response.json();
        gridLayer = L.geoJSON(geojsonData, {
            style: { fillColor: '#1e293b', color: 'white', weight: 0.1, fillOpacity: 0.1 },
            onEachFeature: (feature, layer) => {
                layer.on('click', e => {
                    if (mode === 'visualize') {
                        L.DomEvent.stopPropagation(e);
                        e.latlng.gridAttr = gridLayer.lookup ? gridLayer.lookup[feature.properties.id_grid] : null;
                        calculateRoutes(e.latlng, true);
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
            skenario: document.getElementById('skenario').value, 
            intensity: parseFloat(document.getElementById('intensitas').value), 
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
            roadsLayer.setStyle(f => ({ 
                color: f.properties.is_broken ? '#ef4444' : '#fbbf24', 
                weight: f.properties.is_broken ? 3 : 5, 
                opacity: 0.5 
            }));
        } else {
            // Optimized Update: Hanya update style berdasarkan broken_ids tanpa render ulang geometri
            const brokenIds = new Set(result.broken_ids);
            roadsLayer.eachLayer(layer => {
                const id = layer.feature.properties.id_jalan;
                const isBroken = brokenIds.has(id);
                layer.setStyle({ 
                    color: isBroken ? '#ef4444' : '#fbbf24', 
                    weight: isBroken ? 3 : 5, 
                    opacity: isBroken ? 0.8 : 0.5 
                });
            });
        }
    } catch (e) { console.error(e); }
}

