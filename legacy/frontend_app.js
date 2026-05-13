const API_BASE = "/api";
const clusterColors = { 0: "#3b82f6", 1: "#ef4444", 2: "#10b981", 3: "#f59e0b", 4: "#8b5cf6", "-1": "#475569" };
const routeColors = { 'pendidikan': '#3b82f6', 'kesehatan': '#ef4444', 'pemerintahan': '#f59e0b', 'ibadah': '#8b5cf6', 'gor': '#10b981' };
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

function initMap() {
    map = L.map('map', { zoomControl: false }).setView([-7.83, 110.15], 11);
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', { attribution: '&copy; CARTO' }).addTo(map);
    L.control.zoom({ position: 'topright' }).addTo(map);

    map.createPane('route-pane');
    map.getPane('route-pane').style.zIndex = 650;
    map.getPane('route-pane').style.pointerEvents = 'none';

    map.createPane('marker-pane');
    map.getPane('marker-pane').style.zIndex = 660;

    routeLayers = L.layerGroup().addTo(map);
    tesLayer = L.layerGroup().addTo(map);
    searchBoundaryLayer = L.layerGroup().addTo(map);
    roadsLayer = L.geoJSON(null, { style: { color: '#fbbf24', weight: 4, opacity: 0.4 } }).addTo(map);
    addTesLayerHoverControl();

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
                    <span>Lapisan TES</span>
                </div>
                <div class="tes-layer-body">
                    <div class="layer-list" id="tes-layer-controls"></div>
                </div>
            </div>
        `;
        L.DomEvent.disableClickPropagation(div);
        L.DomEvent.disableScrollPropagation(div);
        return div;
    };
    layerControl.addTo(map);
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

async function calculateRoutes(latlng, isGridClick = false) {
    if (isCalculating) return;
    if (routingAbortController) routingAbortController.abort();
    routingAbortController = new AbortController();
    
    isCalculating = true; showLoading(true);
    const body = { lat: latlng.lat, lng: latlng.lng, skenario: document.getElementById('skenario').value, intensity: parseFloat(document.getElementById('intensitas').value), cut_roads: roadCuts };

    try {
        const resp = await fetch(`${API_BASE}/route-all-tes`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body), signal: routingAbortController.signal });
        const result = await resp.json();
        renderRoutes(result.routes, latlng, isGridClick, latlng.gridAttr, result.recommendations);
    } catch (error) { if (error.name !== 'AbortError') console.error(error); }
    finally { showLoading(false); isCalculating = false; }
}

function renderRoutes(routes, latlng, isGridClick, gridAttr = null, recommendations = []) {
    routeLayers.clearLayers();
    map.closePopup(); // Tutup popup sebelumnya agar tidak tumpang tindih
    const listEl = document.getElementById('route-list');
    listEl.innerHTML = '';
    document.getElementById('route-results').style.display = 'block';

    const legend = document.querySelector('.info.legend');
    if (legend) legend.classList.add('legend-hidden');

    const foundCount = Object.values(routes).filter(r => r.found).length;
    const hasRouteAccess = foundCount > 0;
    let popupContent = `<div style="min-width:240px; padding:5px;"><h4 style="margin:0 0 12px; color:var(--accent-primary); border-bottom:1px solid var(--glass-border); padding-bottom:8px; font-size:14px; letter-spacing:1px;"><i class="fa fa-bullseye"></i> DETAIL LOKASI</h4>`;
    
    if (gridAttr) {
        const isSemu = gridAttr.titik_aman_semu === 1;
        const alrContent = renderAlrValue(gridAttr, hasRouteAccess);
        popupContent += `<div style="background:rgba(255,255,255,0.05); border-radius:12px; padding:12px; margin-bottom:15px; border:1px solid var(--glass-border);">
            <div style="display:flex; justify-content:space-between; margin-bottom:8px;"><span style="color:var(--text-dim); font-size:10px;">TIPOLOGI</span><span style="font-weight:700; color:${clusterColors[gridAttr.cluster_sdwfcm]}">Klaster ${gridAttr.cluster_sdwfcm}</span></div>
            <div style="display:flex; justify-content:space-between;"><span style="color:var(--text-dim); font-size:10px;">MEMBERSHIP</span><span style="font-weight:700;">${(gridAttr.membership_max * 100).toFixed(1)}%</span></div>
            
            ${gridAttr.psi_val !== undefined ? `
            <div style="display:flex; justify-content:space-between; margin-top:4px;"><span style="color:var(--text-dim); font-size:10px;">PSI (Instability)</span><span style="font-weight:700; color:${gridAttr.psi_val >= 0.5 ? 'var(--warning)' : 'var(--accent-primary)'}">${gridAttr.psi_val.toFixed(2)}</span></div>
            ` : ''}
            
            ${alrContent}

            ${isSemu ? `<div style="margin-top:10px; padding:6px; background:rgba(245,158,11,0.2); border:1px solid var(--warning); border-radius:8px; font-size:10px; color:var(--warning); text-align:center;"><i class="fa fa-exclamation-triangle"></i> TITIK AMAN SEMU</div>` : ''}
        </div>`;
    }

    if (foundCount === 0) {
        // Simpan data asal isolasi untuk navigasi "Kembali"
        isolatedOrigin = { latlng, routes, gridAttr, recommendations };
        
        // Tampilkan Alert Isolasi
        listEl.innerHTML = `
            <div class="isolation-alert">
                <i class="fa fa-exclamation-triangle" style="font-size:24px; margin-bottom:10px;"></i>
                <div style="font-weight:800; font-size:14px; color:#fff;">AREA TERISOLASI TOTAL</div>
                <div style="font-size:11px; color:var(--text-dim); margin-top:5px;">Tidak ada akses ke TES manapun melalui jaringan jalan saat ini.</div>
            </div>
            <h3 style="font-size:12px; color:var(--accent-primary); text-transform:uppercase; margin-bottom:15px;">Rekomendasi Navigasi</h3>
        `;

        if (recommendations && recommendations.length > 0) {
            // Cari rekomendasi terbaik (Optimal) untuk visualisasi tunggal
            const bestRec = recommendations.find(r => r.level === 'Optimal') || recommendations[0];
            
            recommendations.forEach(rec => {
                const card = document.createElement('div');
                card.className = `recommendation-card rec-${rec.color_type === 'gradient' ? 'cerah' : rec.color_type}`;
                card.innerHTML = `
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <div style="font-weight:700; font-size:13px; color:#fff;">${rec.level}</div>
                            <div style="font-size:10px; color:var(--text-dim);">${rec.desc}</div>
                        </div>
                        <div style="text-align:right;">
                            <div style="font-weight:700; color:${rec.color_type === 'gradient' || rec.color_type === 'cerah' ? '#10b981' : '#ef4444'}">${rec.dist_m}m</div>
                            <div style="font-size:9px; color:var(--text-dim);">Skor: ${rec.score}</div>
                        </div>
                    </div>
                `;
                card.onclick = () => {
                    const targetLatLng = L.latLng(rec.lat, rec.lng);
                    targetLatLng.gridAttr = getGridAttrAt(targetLatLng);
                    targetLatLng.isRecommendation = true; // Flag untuk navigasi
                    map.flyTo(targetLatLng, 16);
                    calculateRoutes(targetLatLng, true);
                };
                listEl.appendChild(card);
            });

            // Visualisasi Radius Gradasi Tunggal
            const dist = bestRec.dist_m;
            const steps = 10;
            for (let i = 1; i <= steps; i++) {
                const factor = i / steps;
                const color = interpolateColor('#ef4444', '#eab308', '#10b981', factor);
                L.circle(latlng, {
                    radius: (dist / steps) * i,
                    color: color,
                    weight: 1.5,
                    fillColor: color,
                    fillOpacity: 0.05,
                    dashArray: i === steps ? '5, 10' : null,
                    pane: 'route-pane'
                }).addTo(routeLayers);
            }

            // Garis Penunjuk ke Best Recommendation
            L.polyline([latlng, [bestRec.lat, bestRec.lng]], {
                color: '#10b981',
                weight: 3,
                dashArray: '10, 10',
                opacity: 0.7,
                className: 'route-path-animated',
                pane: 'route-pane'
            }).addTo(routeLayers);
        }
    } else {
        // Cek apakah ini navigasi dari rekomendasi atau klik baru
        if (isolatedOrigin && latlng.isRecommendation) {
            // Tambahkan tombol KEMBALI
            const backBtn = document.createElement('div');
            backBtn.className = 'recommendation-card';
            backBtn.style.background = 'rgba(255,255,255,0.05)';
            backBtn.style.border = '1px dashed var(--accent-primary)';
            backBtn.style.marginBottom = '20px';
            backBtn.innerHTML = `
                <div style="display:flex; align-items:center; gap:12px; color:var(--accent-primary);">
                    <i class="fa fa-chevron-left"></i>
                    <div style="font-weight:700; font-size:12px; text-transform:uppercase; letter-spacing:1px;">Kembali ke Titik Isolasi</div>
                </div>
            `;
            backBtn.onclick = () => {
                const origin = isolatedOrigin;
                map.flyTo(origin.latlng, 16);
                renderRoutes(origin.routes, origin.latlng, true, origin.gridAttr, origin.recommendations);
            };
            listEl.appendChild(backBtn);
        } else {
            // Klik grid baru yang tidak terisolasi, reset data isolasi
            isolatedOrigin = null;
        }

        for (const [kat, data] of Object.entries(routes)) {
            if (data.found && data.geojson) {
                // Garis Glow (Dasar)
                L.geoJSON(data.geojson, { style: { color: routeColors[kat], weight: 10, opacity: 0.2 }, pane: 'route-pane' }).addTo(routeLayers);
                // Garis Utama (Animasi)
                L.geoJSON(data.geojson, { 
                    style: { color: routeColors[kat], weight: 5, opacity: 1, className: 'route-path-animated' }, 
                    pane: 'route-pane' 
                }).addTo(routeLayers);
                
                L.marker([data.tes_coords_wgs84[1], data.tes_coords_wgs84[0]], { icon: categoryIcons[kat], pane: 'marker-pane' }).addTo(routeLayers).bindPopup(`<b>${data.tes_name}</b><br>Waktu: ${data.travel_time_min.toFixed(1)} mnt`);
    
                const card = document.createElement('div');
                card.className = 'route-card';
                card.innerHTML = `<div class="route-main"><div class="route-icon-box" style="color:${routeColors[kat]}">${categoryIcons[kat].options.html}</div><div class="route-name">${kat.toUpperCase()}</div></div><div class="route-time">${data.travel_time_min.toFixed(1)} <small>mnt</small></div>`;
                listEl.appendChild(card);
    
                popupContent += `<div style="display:flex; justify-content:space-between; font-size:12px; margin-bottom:5px;"><span style="color:${routeColors[kat]}; font-weight:600;">${kat}</span><span>${data.travel_time_min.toFixed(1)} mnt</span></div>`;
            }
        }
    }
    popupContent += `</div>`;

    if (isGridClick) {
        if (gridPopup) { gridPopup.off('remove'); map.closePopup(gridPopup); }
        gridPopup = L.popup({ maxWidth: 320, autoClose: false, closeOnClick: false }).setLatLng(latlng).setContent(popupContent).openOn(map);
        gridPopup.on('remove', () => { 
            routeLayers.clearLayers(); 
            document.getElementById('route-results').style.display = 'none';
            // Tampilkan kembali legenda saat popup ditutup
            const legend = document.querySelector('.info.legend');
            if (legend) legend.classList.remove('legend-hidden');
        });
    }
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

function addLegend(k = lastK) {
    lastK = k;
    if (legendControl) map.removeControl(legendControl);
    legendControl = L.control({ position: 'bottomright' });
    legendControl.onAdd = () => {
        const div = L.DomUtil.create('div', 'info legend');
        let html = '<h4 style="margin:0 0 15px; color:var(--accent-primary); font-size:12px; letter-spacing:1px;">LEGENDA KLASTER</h4>';
        
        // Item Klaster SDWFCM
        for (let i = 0; i < k; i++) {
            const isActive = (activeCluster === i && activeMode !== 'semu') ? 'active' : '';
            html += `<div class="legend-item ${isActive}" onclick="filterByCluster(${i})">
                        <i style="background:${clusterColors[i]}; width:12px; height:12px; border-radius:3px; margin-right:10px;"></i> 
                        KLASTER ${i}
                     </div>`;
        }

        // Item Khusus: Titik Aman Semu
        const isSemuActive = (activeMode === 'semu') ? 'active' : '';
        html += `<div style="margin-top:10px; padding-top:10px; border-top:1px solid var(--glass-border);">
                    <div class="legend-item ${isSemuActive}" onclick="filterBySemu()">
                        <i style="background:#000; width:12px; height:12px; border-radius:3px; margin-right:10px; border:1.5px solid #f59e0b;"></i> 
                        TITIK AMAN SEMU
                    </div>
                 </div>`;

        div.innerHTML = html; return div;
    };
    legendControl.addTo(map);
}

let activeMode = 'cluster'; // 'cluster' or 'semu'

window.filterByCluster = (clusterId) => {
    activeMode = 'cluster';
    if (activeCluster === clusterId) activeCluster = null;
    else activeCluster = clusterId;
    applyGridStyle(); 
    addLegend();
}

window.filterBySemu = () => {
    if (activeMode === 'semu') {
        activeMode = 'cluster';
        activeCluster = null;
    } else {
        activeMode = 'semu';
        activeCluster = null;
    }
    applyGridStyle();
    addLegend();
}

const KULON_PROGO_BOUNDS = "110.02,-7.63,110.27,-7.99"; // Bounding box for Kulon Progo (left, top, right, bottom)
// Data administratif Kulon Progo (akan di-update via /api/search-list)
let KULON_PROGO_LIST = [];

// 6. Infinite Hybrid Search Engine
const searchInput = document.getElementById('map-search');
const searchResults = document.getElementById('search-results');
const searchClear = document.getElementById('search-clear');
let searchTimeout = null;

searchInput.addEventListener('input', () => {
    clearTimeout(searchTimeout);
    const query = searchInput.value;
    
    if (query.length > 0) { searchClear.style.display = 'block'; } 
    else { searchClear.style.display = 'none'; searchResults.style.display = 'none'; return; }

    if (query.length < 2) return;

    searchTimeout = setTimeout(async () => {
        // Tampilkan hasil lokal saja sesuai permintaan
        const filteredLocal = KULON_PROGO_LIST.filter(item => 
            item.name.toLowerCase().includes(query.toLowerCase())
        ).map(item => ({ ...item, isLocal: true, source: 'Local' }));

        // Gunakan mergeSearchResults untuk deduplikasi yang benar (meskipun hanya lokal saat ini)
        const merged = mergeSearchResults(filteredLocal, [], []);
        renderSearchResults(merged);
    }, 250);
});

function mergeSearchResults(localResults, photonFeats, nominatimData) {
    const results = [];
    const seen = new Set();

    // Prioritas 1: Local Admin Results (Kecamatan/Desa)
    if (Array.isArray(localResults)) {
        localResults.forEach(res => {
            results.push(res);
            // Use composite key to allow same name for different types (e.g., Wates as district AND village)
            seen.add(`${res.name.toLowerCase()}|${res.type}`);
        });
    }

    // Prioritas 2: Nominatim (Bounded to Kulon Progo)
    if (Array.isArray(nominatimData)) {
        nominatimData.forEach(d => {
            const name = d.display_name.split(',')[0];
            const type = d.type || 'address';
            if (seen.has(`${name.toLowerCase()}|${type}`)) return;
            results.push({
                name: name,
                lat: parseFloat(d.lat),
                lng: parseFloat(d.lon),
                desc: d.display_name.split(',').slice(1, 4).join(','),
                type: type
            });
            seen.add(`${name.toLowerCase()}|${type}`);
        });
    }

    // Prioritas 3: Photon
    if (Array.isArray(photonFeats)) {
        photonFeats.forEach(f => {
            const name = f.properties.name || f.properties.city;
            const type = f.properties.type || 'poi';
            if (!name || seen.has(`${name.toLowerCase()}|${type}`)) return;
            results.push({
                name: name,
                lat: f.geometry.coordinates[1],
                lng: f.geometry.coordinates[0],
                desc: `${f.properties.city || ''} ${f.properties.country || ''}`,
                type: type
            });
            seen.add(`${name.toLowerCase()}|${type}`);
        });
    }

    return results;
}

searchClear.onclick = () => {
    searchInput.value = '';
    searchClear.style.display = 'none';
    searchResults.style.display = 'none';
    if (searchMarker) map.removeLayer(searchMarker);
};

searchInput.addEventListener('keydown', async (e) => {
    if (e.key === 'Enter') {
        const firstResult = searchResults.querySelector('.search-result-item');
        if (firstResult) firstResult.click();
    }
});

function renderSearchResults(results) {
    searchResults.innerHTML = '';
    if (results.length === 0) { searchResults.style.display = 'none'; return; }
    searchResults.style.display = 'block';
    
    results.forEach(res => {
        const div = document.createElement('div');
        div.className = 'search-result-item';
        const icon = getSearchTypeIcon(res.type);
        
        // Badge warna-warni untuk membedakan tipe
        let typeBadge = '';
        if (res.type === 'kapanewon') {
            typeBadge = `<span style="background:var(--accent-secondary); color:#fff; font-size:8px; padding:2px 6px; border-radius:4px; margin-left:8px; vertical-align:middle; text-transform:uppercase;">Kapanewon</span>`;
        } else if (res.type === 'kalurahan') {
            typeBadge = `<span style="background:var(--success); color:#fff; font-size:8px; padding:2px 6px; border-radius:4px; margin-left:8px; vertical-align:middle; text-transform:uppercase;">Kalurahan</span>`;
        } else if (res.isLocal) {
            typeBadge = `<span style="background:var(--accent-primary); color:#fff; font-size:8px; padding:2px 6px; border-radius:4px; margin-left:8px; vertical-align:middle; text-transform:uppercase;">Area KP</span>`;
        }

        div.innerHTML = `
            <div style="display:flex; align-items:center; gap:12px;">
                <div style="background:rgba(59, 130, 246, 0.1); width:32px; height:32px; border-radius:10px; display:flex; align-items:center; justify-content:center; color:var(--accent-primary);">
                    <i class="fa ${icon}"></i>
                </div>
                <div style="flex-grow:1; overflow:hidden;">
                    <div style="font-weight:700; color:var(--text-main); font-size:13px;">${res.name} ${typeBadge}</div>
                    <div style="font-size:10px; color:var(--text-dim); text-overflow:ellipsis; white-space:nowrap; overflow:hidden;">${res.desc}</div>
                </div>
            </div>
        `;
        
        div.onclick = async () => {
            showLoading(true);
            let latlng = null;
            let boundaryGeoJSON = null;
            
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 5000); // 5 detik timeout

            try {
                const resp = await fetch(`/api/boundary?name=${encodeURIComponent(res.name)}&type=${res.type}`, {
                    signal: controller.signal
                });
                const data = await resp.json();
                
                if (data && data.features && data.features.length > 0) {
                    const feat = data.features[0];
                    // Nominatim returns geometry in 'geojson' property, but /api/boundary returns a FeatureCollection
                    boundaryGeoJSON = feat.geometry;
                    // Calculate centroid if needed, but goToLocation will handle it
                    // Actually, let's use the center of the bounds
                    const tempLayer = L.geoJSON(boundaryGeoJSON);
                    const bounds = tempLayer.getBounds();
                    latlng = bounds.getCenter();
                } else {
                    alert("Data lokasi tidak ditemukan di database lokal.");
                }
            } catch (e) { 
                console.error("Gagal mengambil data wilayah lokal:", e);
                if (e.name === 'AbortError') alert("Pencarian wilayah terlalu lama.");
                else alert("Gagal menghubungi server lokal.");
            } finally {
                clearTimeout(timeoutId);
                showLoading(false);
                if (latlng) {
                    goToLocation(latlng, res.name, res.type, boundaryGeoJSON);
                    searchResults.style.display = 'none';
                    searchInput.value = res.name;
                }
            }
        };
        searchResults.appendChild(div);
    });
}

function getSearchTypeIcon(type) {
    const icons = {
        'kapanewon': 'fa-map-marked-alt', 'kalurahan': 'fa-home',
        'school': 'fa-school', 'hospital': 'fa-hospital', 'place_of_worship': 'fa-place-of-worship',
        'restaurant': 'fa-utensils', 'cafe': 'fa-coffee', 'bank': 'fa-university',
        'village': 'fa-tree', 'city': 'fa-city', 'district': 'fa-map-marked-alt'
    };
    return icons[type] || 'fa-map-pin';
}

function goToLocation(latlng, name, type = 'poi', geojson = null) {
    if (searchMarker) map.removeLayer(searchMarker);
    if (searchBoundaryLayer) searchBoundaryLayer.clearLayers();

    searchMarker = L.marker(latlng, { icon: searchIcon, zIndexOffset: 1000 }).addTo(map);
    
    if (geojson && searchBoundaryLayer) {
        const layer = L.geoJSON(geojson, {
            style: {
                color: '#ffffff',
                weight: 5,
                fillColor: '#ffffff',
                fillOpacity: 0.1,
                dashArray: '10, 10',
                opacity: 1,
                className: 'search-boundary-pulse'
            }
        }).addTo(searchBoundaryLayer);
        
        map.fitBounds(layer.getBounds(), { padding: [50, 50], duration: 1.5 });
    } else {
        const zoomLevel = ['city', 'district', 'state', 'kapanewon'].includes(type) ? 13 : 15;
        map.flyTo(latlng, zoomLevel, { duration: 1.5 });
    }
    
    const popupContent = `
        <div style="padding:5px;">
            <b style="color:var(--accent-primary)">LOKASI DITEMUKAN</b><br>
            <span style="font-size:12px; font-weight:700;">${name}</span><br>
            <span style="font-size:10px; color:var(--text-dim); text-transform:uppercase;">${type}</span><br>
            <button class="btn-premium" style="margin-top:12px; padding:10px; font-size:11px;" 
                    onclick="calculateFromSearch(${latlng.lat}, ${latlng.lng})">
                <i class="fa fa-route"></i> ANALISIS RUTE EVAKUASI
            </button>
        </div>
    `;
    
    searchMarker.bindPopup(popupContent).openPopup();
    
    // Tambahkan listener untuk membersihkan segalanya saat popup ditutup
    searchMarker.on('popupclose', () => {
        routeLayers.clearLayers();
        if (searchBoundaryLayer) searchBoundaryLayer.clearLayers();
        if (searchMarker) {
            map.removeLayer(searchMarker);
            searchMarker = null;
        }
        document.getElementById('route-results').style.display = 'none';
        const legend = document.querySelector('.info.legend');
        if (legend) legend.classList.remove('legend-hidden');
    });

    map.flyTo(latlng, zoomLevel, { duration: 1.5 });
}

window.calculateFromSearch = (lat, lng) => {
    calculateRoutes({ lat, lng }, false);
};

function locateUser() {
    if (!navigator.geolocation) { alert("GPS tidak didukung oleh browser Anda."); return; }
    showLoading(true);
    navigator.geolocation.getCurrentPosition(
        (pos) => {
            const latlng = { lat: pos.coords.latitude, lng: pos.coords.longitude };
            goToLocation(latlng, "Lokasi Anda saat ini", 'gps');
            showLoading(false);
        },
        (err) => {
            showLoading(false);
            alert("Gagal mengakses lokasi: " + err.message);
        }
    );
}

function showLoading(show) { document.getElementById('loading-overlay').style.display = show ? 'flex' : 'none'; }

window.onload = async () => { 
    initMap(); 
    initTesLayerControls();
    
    // Load search list from GPKG
    try {
        const resp = await fetch('/api/search-list');
        const data = await resp.json();
        if (data.status === 'ok') {
            KULON_PROGO_LIST = data.results;
            console.log(`Loaded ${KULON_PROGO_LIST.length} regions from GPKG.`);
        }
    } catch (e) { console.error("Gagal memuat daftar wilayah dari GPKG:", e); }

    loadStaticGeometry().then(() => {
        loadSession(); 
    });
};

