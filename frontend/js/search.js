// ╔══════════════════════════════════════════════════════════════════════╗
// ║  search.js — Pencarian wilayah & alamat (seperti Google Maps)        ║
// ║  • Kapanewon/kalurahan: dari data batas wilayah lokal (instan)       ║
// ║  • Alamat/tempat: OpenStreetMap (Photon saat mengetik,               ║
// ║    + Nominatim saat Enter) melalui /api/geocode                      ║
// ╚══════════════════════════════════════════════════════════════════════╝
let KULON_PROGO_LIST = [];   // diisi bootstrap.js dari /api/search-list

const searchInput = document.getElementById('map-search');
const searchResults = document.getElementById('search-results');
const searchClear = document.getElementById('search-clear');
let searchTimeout = null;
let searchAbort = null;
let activeSearchResultIndex = -1;
let lastSearchItems = [];

const PLACE_ICONS = {
    kapanewon: 'fa-map', kalurahan: 'fa-house-flag',
    school: 'fa-school', university: 'fa-graduation-cap', college: 'fa-graduation-cap', kindergarten: 'fa-school',
    hospital: 'fa-hospital', clinic: 'fa-house-medical', doctors: 'fa-user-doctor', pharmacy: 'fa-prescription-bottle-medical',
    place_of_worship: 'fa-place-of-worship', mosque: 'fa-mosque', church: 'fa-church',
    marketplace: 'fa-store', supermarket: 'fa-cart-shopping', restaurant: 'fa-utensils', cafe: 'fa-mug-hot',
    bank: 'fa-building-columns', townhall: 'fa-landmark', police: 'fa-shield-halved', fuel: 'fa-gas-pump',
    station: 'fa-train', bus_station: 'fa-bus', aerodrome: 'fa-plane', airport: 'fa-plane',
    village: 'fa-tree', hamlet: 'fa-tree', city: 'fa-city', town: 'fa-city', suburb: 'fa-city',
    residential: 'fa-road', primary: 'fa-road', secondary: 'fa-road', tertiary: 'fa-road', trunk: 'fa-road', road: 'fa-road',
    house: 'fa-house', gps: 'fa-location-crosshairs'
};
const iconFor = type => PLACE_ICONS[type] || 'fa-location-dot';
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

function showToast(message, tone = 'info') {
    let el = document.getElementById('app-toast');
    if (!el) {
        el = document.createElement('div');
        el.id = 'app-toast';
        document.body.appendChild(el);
    }
    el.className = `app-toast ${tone}`;
    el.innerHTML = message;
    el.hidden = false;
    clearTimeout(el._t);
    el._t = setTimeout(() => { el.hidden = true; }, 4500);
}

function hideSearchResults() {
    searchResults.style.display = 'none';
    searchResults.innerHTML = '';
    activeSearchResultIndex = -1;
    lastSearchItems = [];
}

function localMatches(query) {
    const q = query.toLowerCase();
    return KULON_PROGO_LIST
        .filter(item => item.name.toLowerCase().includes(q))
        .sort((a, b) => a.name.toLowerCase().indexOf(q) - b.name.toLowerCase().indexOf(q))
        .slice(0, 6)
        .map(item => ({ kind: 'admin', name: item.name, type: item.type, desc: item.desc }));
}

function geoToItem(r) {
    const where = [r.desa && `Kal. ${r.desa.replace(/^Kelurahan\s+/i, '')}`, r.kecamatan && `Kap. ${r.kecamatan}`].filter(Boolean).join(', ');
    return {
        kind: 'place', name: r.name, type: r.type, lat: r.lat, lng: r.lon,
        desc: r.address || '', where, inArea: r.in_kulon_progo, desa: r.desa, kecamatan: r.kecamatan
    };
}

function renderSearchResults(items, { loading = false, note = '' } = {}) {
    lastSearchItems = items;
    searchResults.innerHTML = '';
    if (!items.length && !loading && !note) { searchResults.style.display = 'none'; return; }
    searchResults.style.display = 'block';

    items.forEach((it, idx) => {
        const div = document.createElement('div');
        div.className = 'search-result-item';
        let badge = '';
        if (it.kind === 'admin') badge = `<span class="sr-badge ${it.type}">${it.type === 'kapanewon' ? 'Kapanewon' : 'Kalurahan'}</span>`;
        else if (!it.inArea) badge = '<span class="sr-badge outside">Luar Kulon Progo</span>';
        const sub = it.kind === 'admin' ? it.desc : [it.where, it.desc].filter(Boolean).join(' · ');
        div.innerHTML = `
            <div class="sr-row">
                <div class="sr-icon"><i class="fa ${iconFor(it.type)}"></i></div>
                <div class="sr-text">
                    <div class="sr-name">${esc(it.name)} ${badge}</div>
                    <div class="sr-desc">${esc(sub)}</div>
                </div>
            </div>`;
        div.addEventListener('mousedown', e => e.preventDefault());   // jaga fokus input
        div.addEventListener('click', () => selectSearchItem(it));
        div.addEventListener('mouseenter', () => setActiveSearchResult(idx, false));
        searchResults.appendChild(div);
    });
    if (loading) searchResults.insertAdjacentHTML('beforeend', '<div class="sr-status"><i class="fa fa-spinner fa-spin"></i> Mencari alamat…</div>');
    if (note) searchResults.insertAdjacentHTML('beforeend', `<div class="sr-status">${note}</div>`);
    if (items.length) setActiveSearchResult(0, false);
}

function setActiveSearchResult(index, scroll = true) {
    const els = Array.from(searchResults.querySelectorAll('.search-result-item'));
    if (!els.length) { activeSearchResultIndex = -1; return; }
    activeSearchResultIndex = ((index % els.length) + els.length) % els.length;
    els.forEach((el, i) => el.classList.toggle('active', i === activeSearchResultIndex));
    if (scroll) els[activeSearchResultIndex].scrollIntoView({ block: 'nearest' });
}

async function runSearch(query, full = false) {
    if (searchAbort) searchAbort.abort();
    searchAbort = new AbortController();
    const local = localMatches(query);
    if (query.trim().length < 3) { renderSearchResults(local); return local; }
    renderSearchResults(local, { loading: true });
    try {
        const resp = await fetch(`${API_BASE}/geocode?q=${encodeURIComponent(query.trim())}${full ? '&full=true' : ''}`, { signal: searchAbort.signal });
        const data = await resp.json();
        // buang entri OSM administratif yang sama dengan hasil kapanewon/kalurahan lokal
        const ADMIN_TYPES = new Set(['city', 'town', 'village', 'suburb', 'district', 'county', 'hamlet', 'administrative', 'locality', 'neighbourhood', 'quarter']);
        const localNames = new Set(local.map(l => l.name.toLowerCase().replace(/^(kelurahan|kalurahan|desa)\s+/, '')));
        const seenPlace = new Set();
        const places = (data.results || []).map(geoToItem).filter(p => {
            const n = p.name.toLowerCase();
            if (ADMIN_TYPES.has(p.type) && localNames.has(n)) return false;
            const k = `${n}|${p.lat.toFixed(2)}|${p.lng.toFixed(2)}`;
            if (seenPlace.has(k)) return false;
            seenPlace.add(k);
            return true;
        });
        const items = [...local, ...places];
        const note = !items.length
            ? (data.status === 'error' ? 'Layanan pencarian alamat sedang tidak tersedia.' : `Tidak ditemukan. ${full ? '' : 'Tekan <b>Enter</b> untuk pencarian alamat lengkap.'}`)
            : (!full ? '<span class="sr-hint">Enter = pencarian alamat lengkap</span>' : '');
        renderSearchResults(items, { note });
        return items;
    } catch (e) {
        if (e.name === 'AbortError') return null;
        renderSearchResults(local, { note: 'Gagal menghubungi layanan pencarian alamat.' });
        return local;
    }
}

searchInput.addEventListener('input', () => {
    clearTimeout(searchTimeout);
    const query = searchInput.value;
    searchClear.style.display = query ? 'block' : 'none';
    if (query.trim().length < 2) { if (searchAbort) searchAbort.abort(); hideSearchResults(); return; }
    renderSearchResults(localMatches(query), { loading: query.trim().length >= 3 });
    searchTimeout = setTimeout(() => runSearch(query, false), 350);
});

searchInput.addEventListener('keydown', async e => {
    const count = searchResults.querySelectorAll('.search-result-item').length;
    if (e.key === 'ArrowDown' && count) { e.preventDefault(); setActiveSearchResult(activeSearchResultIndex + 1); return; }
    if (e.key === 'ArrowUp' && count) { e.preventDefault(); setActiveSearchResult(activeSearchResultIndex - 1); return; }
    if (e.key === 'Escape') { hideSearchResults(); searchInput.blur(); return; }
    if (e.key === 'Enter') {
        e.preventDefault();
        const query = searchInput.value.trim();
        if (query.length < 2) return;
        clearTimeout(searchTimeout);
        // Pilihan yang sedang disorot pengguna diutamakan; jika belum ada, lakukan pencarian lengkap.
        if (activeSearchResultIndex > 0 && lastSearchItems[activeSearchResultIndex]) {
            selectSearchItem(lastSearchItems[activeSearchResultIndex]);
            return;
        }
        const items = await runSearch(query, true);
        if (items && items.length) selectSearchItem(items[0]);
    }
});

searchInput.addEventListener('focus', () => {
    if (searchInput.value.trim().length >= 2 && lastSearchItems.length) renderSearchResults(lastSearchItems);
});
document.addEventListener('click', e => {
    if (!e.target.closest('.search-input-wrap')) searchResults.style.display = 'none';
});

searchClear.onclick = () => {
    searchInput.value = '';
    searchClear.style.display = 'none';
    hideSearchResults();
    clearSearchResult();
    searchInput.focus();
};

function clearSearchResult() {
    if (searchMarker) { map.removeLayer(searchMarker); searchMarker = null; }
    if (searchBoundaryLayer) searchBoundaryLayer.clearLayers();
}

async function selectSearchItem(it) {
    hideSearchResults();
    searchInput.value = it.name;
    searchClear.style.display = 'block';
    searchInput.blur();
    if (it.kind === 'admin') {
        try { await loadBoundaryData(); } catch { /* ditangani di bawah */ }
        const feat = findBoundaryFeature(it.type, it.name);
        if (!feat) { showToast('Batas wilayah tidak ditemukan.', 'warn'); return; }
        const [lon, lat] = feat.properties.label;   // titik di dalam poligon
        goToLocation(L.latLng(lat, lon), it.name, it.type, feat, {
            where: it.type === 'kalurahan' ? `Kalurahan di Kapanewon ${feat.properties.kecamatan || ''}` : 'Kapanewon di Kabupaten Kulon Progo'
        });
        return;
    }
    goToLocation(L.latLng(it.lat, it.lng), it.name, it.type, null, it);
}

function goToLocation(latlng, name, type = 'place', feature = null, info = {}) {
    clearSearchResult();
    // hasil pencarian baru menggantikan detail grid/rute sebelumnya
    if (gridPopup && map.hasLayer(gridPopup)) { suppressRecommendationRestore = true; map.closePopup(gridPopup); suppressRecommendationRestore = false; }
    routeLayers.clearLayers(); contextRouteLayers.clearLayers();
    document.getElementById('route-results').style.display = 'none';
    searchMarker = L.marker(latlng, { icon: searchIcon, zIndexOffset: 1000, pane: 'marker-pane' }).addTo(map);

    if (feature) {
        const outline = L.geoJSON(feature, {
            pane: 'boundary-pane', interactive: false,
            style: { color: '#ffffff', weight: 4, fillColor: '#ffffff', fillOpacity: 0.06, dashArray: '10 8', className: 'search-boundary-pulse' }
        }).addTo(searchBoundaryLayer);
        map.flyToBounds(outline.getBounds(), { paddingTopLeft: [380, 60], paddingBottomRight: [60, 40], duration: 1.2 });
    } else {
        map.flyTo(latlng, 17, { duration: 1.2 });
    }

    const grid = typeof getGridAttrAt === 'function' ? getGridAttrAt(latlng) : null;
    const where = info.where || '';
    const outside = info.inArea === false;
    const canAnalyze = !feature && grid;
    const content = `
        <div class="search-popup">
            <div class="sp-kicker">${feature ? 'WILAYAH' : type === 'gps' ? 'LOKASI ANDA' : 'LOKASI DITEMUKAN'}</div>
            <div class="sp-name">${esc(name)}</div>
            ${info.desc ? `<div class="sp-desc">${esc(info.desc)}</div>` : ''}
            ${where ? `<div class="sp-where"><i class="fa fa-map-location-dot"></i> ${esc(where)}</div>` : ''}
            ${outside ? '<div class="sp-warn"><i class="fa fa-circle-info"></i> Di luar wilayah analisis (Kulon Progo).</div>' : ''}
            ${feature ? `<button class="btn-premium sp-btn" onclick="openRegionPanel('${type === 'kapanewon' ? 'kecamatan' : 'desa'}', ${esc(JSON.stringify(feature.properties.name))})"><i class="fa fa-ranking-star"></i> Ringkasan wilayah</button>` : ''}
            ${canAnalyze ? `<button class="btn-premium sp-btn" onclick="analyzeSearchPoint(${latlng.lat}, ${latlng.lng})"><i class="fa fa-route"></i> Lihat detail grid &amp; rute evakuasi</button>` : ''}
        </div>`;
    searchMarker.bindPopup(content, { maxWidth: 280, className: 'search-popup-wrap' }).openPopup();
    searchMarker.on('popupclose', () => {
        // biarkan marker tetap sebagai penanda; hapus saat pencarian dibersihkan
    });
}

window.analyzeSearchPoint = (lat, lng) => {
    const latlng = L.latLng(lat, lng);
    const attr = getGridAttrAt(latlng);
    if (searchMarker) searchMarker.closePopup();
    if (!attr) { showToast('Titik ini berada di luar grid analisis.', 'warn'); return; }
    latlng.gridAttr = attr;
    latlng.id_grid = attr.id_grid;
    calculateRoutes(latlng, true);
};

function locateUser() {
    if (!navigator.geolocation) { showToast('GPS tidak didukung oleh browser ini.', 'warn'); return; }
    showToast('<i class="fa fa-spinner fa-spin"></i> Mencari lokasi Anda…');
    navigator.geolocation.getCurrentPosition(
        pos => {
            const latlng = L.latLng(pos.coords.latitude, pos.coords.longitude);
            const adm = (typeof gridAdminName === 'function' && getGridAttrAt(latlng)) ? gridAdminName(getGridAttrAt(latlng).id_grid) : null;
            goToLocation(latlng, 'Lokasi Anda saat ini', 'gps', null, {
                where: adm ? `Kal. ${adm.desa}, Kap. ${adm.kecamatan}` : '', inArea: !!getGridAttrAt(latlng)
            });
            document.getElementById('app-toast').hidden = true;
        },
        err => showToast(`Gagal mengakses lokasi: ${esc(err.message)}. Pastikan izin lokasi di browser aktif.`, 'warn'),
        { enableHighAccuracy: false, timeout: 10000, maximumAge: 60000 }
    );
}
