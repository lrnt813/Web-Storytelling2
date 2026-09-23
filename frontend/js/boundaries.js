// ╔══════════════════════════════════════════════════════════════════════╗
// ║  boundaries.js — Batas wilayah kabupaten, kapanewon, kalurahan       ║
// ╚══════════════════════════════════════════════════════════════════════╝
const BOUNDARY_LEVELS = {
    kabupaten: { label: 'Kabupaten', style: { color: '#f8fafc', weight: 3, opacity: 0.95, fill: false }, labelMinZoom: 99 },
    kecamatan: { label: 'Kapanewon (Kecamatan)', style: { color: '#fde68a', weight: 1.8, opacity: 0.9, dashArray: '6 4', fill: false }, labelMinZoom: 11 },
    desa:      { label: 'Kalurahan (Desa)', style: { color: '#cbd5e1', weight: 0.9, opacity: 0.75, dashArray: '2 3', fill: false }, labelMinZoom: 13 }
};

let boundaryData = null;             // hasil /api/admin-boundaries
let gridAdmin = null;                // hasil /api/grid-admin
const boundaryLayers = {};           // key -> L.geoJSON
const boundaryLabelLayers = {};      // key -> L.layerGroup (label nama)
let activeBoundaries = new Set(['kabupaten', 'kecamatan']);
let boundaryLabelsOn = true;

try {
    const saved = JSON.parse(localStorage.getItem('evac_boundaries') || 'null');
    if (Array.isArray(saved)) activeBoundaries = new Set(saved.filter(k => BOUNDARY_LEVELS[k]));
    boundaryLabelsOn = localStorage.getItem('evac_boundary_labels') !== '0';
} catch { /* abaikan preferensi rusak */ }

async function loadBoundaryData() {
    if (boundaryData) return boundaryData;
    const resp = await fetch(`${API_BASE}/admin-boundaries`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    boundaryData = await resp.json();
    return boundaryData;
}

async function loadGridAdmin() {
    if (gridAdmin) return gridAdmin;
    try {
        const resp = await fetch(`${API_BASE}/grid-admin`);
        if (resp.ok) gridAdmin = await resp.json();
    } catch (e) { console.warn('grid-admin gagal dimuat', e); }
    return gridAdmin;
}

function gridAdminName(idGrid) {
    if (!gridAdmin || idGrid === null || idGrid === undefined) return null;
    const i = gridAdmin.grid[String(idGrid)];
    if (i === null || i === undefined) return null;
    const [desa, kec] = gridAdmin.desa[i];
    return { desa, kecamatan: kec };
}

function initBoundaryPanes() {
    map.createPane('boundary-pane');
    map.getPane('boundary-pane').style.zIndex = 430;
    map.getPane('boundary-pane').style.pointerEvents = 'none';
    map.createPane('boundary-label-pane');
    map.getPane('boundary-label-pane').style.zIndex = 640;
    map.getPane('boundary-label-pane').style.pointerEvents = 'none';
    map.on('zoomend', updateBoundaryLabels);
}

function buildBoundaryLayer(key) {
    const cfg = BOUNDARY_LEVELS[key];
    boundaryLayers[key] = L.geoJSON(boundaryData[key], {
        pane: 'boundary-pane', interactive: false, style: cfg.style
    });
    const labels = L.layerGroup();
    boundaryData[key].features.forEach(f => {
        const [lon, lat] = f.properties.label;
        L.marker([lat, lon], {
            pane: 'boundary-label-pane', interactive: false, keyboard: false,
            icon: L.divIcon({ className: `boundary-label boundary-label-${key}`, html: `<span>${f.properties.name}</span>`, iconSize: null })
        }).addTo(labels);
    });
    boundaryLabelLayers[key] = labels;
}

async function renderBoundaries() {
    try { await loadBoundaryData(); } catch (e) { console.error('Batas wilayah gagal dimuat', e); return; }
    Object.keys(BOUNDARY_LEVELS).forEach(key => {
        if (!boundaryLayers[key]) buildBoundaryLayer(key);
        const on = activeBoundaries.has(key);
        if (on && !map.hasLayer(boundaryLayers[key])) boundaryLayers[key].addTo(map);
        if (!on && map.hasLayer(boundaryLayers[key])) map.removeLayer(boundaryLayers[key]);
    });
    updateBoundaryLabels();
}

function updateBoundaryLabels() {
    const z = map.getZoom();
    Object.entries(BOUNDARY_LEVELS).forEach(([key, cfg]) => {
        const layer = boundaryLabelLayers[key];
        if (!layer) return;
        const show = boundaryLabelsOn && activeBoundaries.has(key) && z >= cfg.labelMinZoom
            // label kecamatan disembunyikan saat label desa tampil agar tidak menumpuk
            && !(key === 'kecamatan' && activeBoundaries.has('desa') && z >= BOUNDARY_LEVELS.desa.labelMinZoom);
        if (show && !map.hasLayer(layer)) layer.addTo(map);
        if (!show && map.hasLayer(layer)) map.removeLayer(layer);
    });
}

function initBoundaryControls() {
    const container = document.getElementById('boundary-controls');
    if (!container) return;
    container.innerHTML = '';
    Object.entries(BOUNDARY_LEVELS).forEach(([key, cfg]) => {
        const id = `boundary-${key}`;
        const row = document.createElement('div');
        row.className = 'layer-option';
        const dash = cfg.style.dashArray ? `border-top-style:${key === 'desa' ? 'dotted' : 'dashed'};` : '';
        row.innerHTML = `
            <input type="checkbox" id="${id}" ${activeBoundaries.has(key) ? 'checked' : ''}>
            <span class="layer-symbol"><i class="boundary-swatch" style="border-top:${Math.max(2, cfg.style.weight)}px solid ${cfg.style.color};${dash}"></i></span>
            <label class="layer-label" for="${id}">${cfg.label}</label>`;
        container.appendChild(row);
        row.querySelector('input').addEventListener('change', e => {
            if (e.target.checked) activeBoundaries.add(key); else activeBoundaries.delete(key);
            try { localStorage.setItem('evac_boundaries', JSON.stringify([...activeBoundaries])); } catch { }
            renderBoundaries();
        });
    });
    const labelRow = document.createElement('div');
    labelRow.className = 'layer-option';
    labelRow.innerHTML = `
        <input type="checkbox" id="boundary-labels" ${boundaryLabelsOn ? 'checked' : ''}>
        <span class="layer-symbol"><i class="fa fa-font"></i></span>
        <label class="layer-label" for="boundary-labels">Nama wilayah</label>`;
    container.appendChild(labelRow);
    labelRow.querySelector('input').addEventListener('change', e => {
        boundaryLabelsOn = e.target.checked;
        try { localStorage.setItem('evac_boundary_labels', boundaryLabelsOn ? '1' : '0'); } catch { }
        updateBoundaryLabels();
    });
}

// Sorot satu wilayah (dipakai hasil pencarian kapanewon/kalurahan)
function findBoundaryFeature(type, name) {
    if (!boundaryData) return null;
    const key = type === 'kapanewon' ? 'kecamatan' : (type === 'kalurahan' ? 'desa' : type);
    const fc = boundaryData[key];
    if (!fc) return null;
    const norm = s => String(s || '').toLowerCase().replace(/^(kelurahan|kalurahan|desa|kecamatan|kapanewon)\s+/, '').trim();
    return fc.features.find(f => norm(f.properties.name) === norm(name)) || null;
}
