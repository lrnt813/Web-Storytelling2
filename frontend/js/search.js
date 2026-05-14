const KULON_PROGO_BOUNDS = "110.02,-7.63,110.27,-7.99"; // Bounding box for Kulon Progo (left, top, right, bottom)
// Data administratif Kulon Progo (akan di-update via /api/search-list)
let KULON_PROGO_LIST = [];

// 6. Infinite Hybrid Search Engine
const searchInput = document.getElementById('map-search');
const searchResults = document.getElementById('search-results');
const searchClear = document.getElementById('search-clear');
let searchTimeout = null;
let activeSearchResultIndex = -1;
let searchReadyForFreshInput = false;

function hideSearchRecommendations() {
    searchResults.style.display = 'none';
    searchResults.innerHTML = '';
    activeSearchResultIndex = -1;
}

function closeSearchRecommendations() {
    searchResults.style.display = 'none';
    activeSearchResultIndex = -1;
}

function resetSearchInputForNextQuery() {
    searchInput.value = '';
    searchClear.style.display = 'none';
    hideSearchRecommendations();
    searchReadyForFreshInput = false;
    searchInput.focus();
}

function getSearchResultItems() {
    return Array.from(searchResults.querySelectorAll('.search-result-item'));
}

function setActiveSearchResult(index) {
    const items = getSearchResultItems();
    if (!items.length) {
        activeSearchResultIndex = -1;
        return;
    }

    const normalizedIndex = ((index % items.length) + items.length) % items.length;
    activeSearchResultIndex = normalizedIndex;

    items.forEach((item, idx) => {
        item.classList.toggle('active', idx === normalizedIndex);
    });

    items[normalizedIndex].scrollIntoView({ block: 'nearest' });
}

searchInput.addEventListener('input', () => {
    clearTimeout(searchTimeout);
    const query = searchInput.value;
    searchReadyForFreshInput = false;
    
    if (query.length > 0) { searchClear.style.display = 'block'; } 
    else { searchClear.style.display = 'none'; hideSearchRecommendations(); return; }

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
    hideSearchRecommendations();
    if (searchMarker) map.removeLayer(searchMarker);
};

searchInput.addEventListener('keydown', async (e) => {
    const items = getSearchResultItems();
    if (e.key === 'ArrowDown' && items.length) {
        e.preventDefault();
        setActiveSearchResult(activeSearchResultIndex + 1);
        return;
    }

    if (e.key === 'ArrowUp' && items.length) {
        e.preventDefault();
        setActiveSearchResult(activeSearchResultIndex <= 0 ? items.length - 1 : activeSearchResultIndex - 1);
        return;
    }

    if (e.key === 'Escape') {
        hideSearchRecommendations();
        return;
    }

    if (e.key === 'Enter') {
        e.preventDefault();
        const target = activeSearchResultIndex >= 0 ? items[activeSearchResultIndex] : items[0];
        if (target) {
            closeSearchRecommendations();
            target.click();
        }
    }
});

searchInput.addEventListener('focus', () => {
    if (!searchReadyForFreshInput) return;
    resetSearchInputForNextQuery();
});

function renderSearchResults(results) {
    searchResults.innerHTML = '';
    if (results.length === 0) { hideSearchRecommendations(); return; }
    searchResults.style.display = 'block';
    activeSearchResultIndex = -1;
    
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
            closeSearchRecommendations();
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
                    searchReadyForFreshInput = true;
                    resetSearchInputForNextQuery();
                }
            }
        };
        searchResults.appendChild(div);
    });

    setActiveSearchResult(0);
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
        if (contextRouteLayers) contextRouteLayers.clearLayers();
        if (searchBoundaryLayer) searchBoundaryLayer.clearLayers();
        if (searchMarker) {
            map.removeLayer(searchMarker);
            searchMarker = null;
        }
        document.getElementById('route-results').style.display = 'none';
        const legend = document.querySelector('.info.legend');
        if (legend) legend.classList.remove('legend-hidden');
        searchReadyForFreshInput = true;
        resetSearchInputForNextQuery();
    });

    if (!geojson) {
        map.flyTo(latlng, zoomLevel, { duration: 1.5 });
    }
}

window.calculateFromSearch = (lat, lng) => {
    calculateRoutes({ lat, lng }, false);
};

function locateUser() {
    if (!navigator.geolocation) { alert("GPS tidak didukung oleh browser Anda."); return; }
    showLoading(true);

    let finished = false;
    const stopLoading = () => {
        if (finished) return false;
        finished = true;
        showLoading(false);
        return true;
    };

    const fallbackTimer = setTimeout(() => {
        if (stopLoading()) {
            alert("Lokasi belum berhasil didapatkan. Pastikan izin lokasi di browser aktif, lalu coba lagi.");
        }
    }, 12000);

    navigator.geolocation.getCurrentPosition(
        (pos) => {
            if (!stopLoading()) return;
            clearTimeout(fallbackTimer);
            const latlng = { lat: pos.coords.latitude, lng: pos.coords.longitude };
            goToLocation(latlng, "Lokasi Anda saat ini", 'gps');
        },
        (err) => {
            if (!stopLoading()) return;
            clearTimeout(fallbackTimer);
            alert("Gagal mengakses lokasi: " + err.message);
        },
        {
            enableHighAccuracy: false,
            timeout: 10000,
            maximumAge: 60000
        }
    );
}

