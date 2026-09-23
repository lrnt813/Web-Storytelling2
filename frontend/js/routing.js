let routeRequestSeq = 0;

function popupHeader() {
    return `<div style="min-width:240px; padding:5px;"><h4 style="margin:0 0 12px; color:var(--accent-primary); border-bottom:1px solid var(--glass-border); padding-bottom:8px; font-size:14px; letter-spacing:1px;"><i class="fa fa-bullseye"></i> DETAIL LOKASI</h4>`;
}

function openGridDetail(latlng, statusHtml) {
    // Rincian grid sudah tersedia di browser → popup langsung tampil tanpa menunggu rute.
    gridPopup = ensureGridPopup();
    const content = popupHeader()
        + (latlng.gridAttr ? renderGridAttrPopup(latlng.gridAttr) : '<p class="route-status">Grid di luar wilayah analisis.</p>')
        + `<div class="route-status" id="route-status">${statusHtml}</div></div>`;
    suppressRecommendationRestore = true;
    gridPopup.setLatLng(latlng).setContent(content).openOn(map);
    suppressRecommendationRestore = false;
    gridPopup._gridRouteState = { latlng: clonePopupLatLng(latlng), gridAttr: latlng.gridAttr, recommendations: [], isRecommendationView: false };
}

async function calculateRoutes(latlng, isGridClick = false) {
    // Klik baru membatalkan permintaan rute sebelumnya (tidak pernah diabaikan).
    if (routingAbortController) routingAbortController.abort();
    routingAbortController = new AbortController();
    const seq = ++routeRequestSeq;

    if (isGridClick) {
        routeLayers.clearLayers();
        if (!latlng.isRecommendation) contextRouteLayers.clearLayers();
        openGridDetail(latlng, '<i class="fa fa-spinner fa-spin"></i> Menghitung rute ke TES terdekat…');
    }
    const gridId = Number(latlng.id_grid);
    const body = {
        lat: latlng.lat,
        lng: latlng.lng,
        id_grid: Number.isFinite(gridId) ? Math.trunc(gridId) : null,
        level: activeLevel,
        cut_roads: roadCuts
    };

    try {
        const resp = await fetch(`${API_BASE}/route-all-tes`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body), signal: routingAbortController.signal });
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const result = await resp.json();
        if (seq !== routeRequestSeq) return;                       // sudah ada klik yang lebih baru
        if (isGridClick && !(gridPopup && map.hasLayer(gridPopup))) return;  // popup ditutup pengguna
        renderRoutes(result.routes, latlng, isGridClick, latlng.gridAttr, result.recommendations);
    } catch (error) {
        if (error.name === 'AbortError' || seq !== routeRequestSeq) return;
        console.error(error);
        const st = document.getElementById('route-status');
        if (st) st.innerHTML = '<i class="fa fa-triangle-exclamation"></i> Rute gagal dihitung. Klik grid lagi untuk mencoba ulang.';
    }
}

function runAfterMapMove(action, fallbackMs = 450) {
    let done = false;
    const finish = () => {
        if (done) return;
        done = true;
        map.off('moveend', finish);
        action();
    };
    map.once('moveend', finish);
    window.setTimeout(finish, fallbackMs);
}

function restoreIsolatedOriginView() {
    if (!isolatedOrigin) return;
    const origin = isolatedOrigin;
    map.setView(origin.latlng, 16, { animate: false });
    renderRoutes(origin.routes, origin.latlng, true, origin.gridAttr, origin.recommendations);
}

function renderRoutes(routes, latlng, isGridClick, gridAttr = null, recommendations = []) {
    const isRecommendationView = Boolean(isolatedOrigin && latlng.isRecommendation);
    routeLayers.clearLayers();
    if (!isRecommendationView) contextRouteLayers.clearLayers();
    const listEl = document.getElementById('route-list');
    listEl.innerHTML = '';
    document.getElementById('route-results').style.display = 'block';
    updateRouteResultsLayout();

    const legend = document.querySelector('.info.legend');
    if (legend) legend.classList.add('legend-hidden');

    const foundCount = Object.values(routes).filter(r => r.found).length;
    const hasRouteAccess = foundCount > 0;
    let popupContent = popupHeader();
    
    if (gridAttr) popupContent += renderGridAttrPopup(gridAttr);

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
                    const recommendationLatLng = L.latLng(rec.lat, rec.lng);
                    const recommendationGridAttr = getGridAttrAt(recommendationLatLng);
                    const targetLatLng = recommendationGridAttr?.id_grid !== undefined && recommendationGridAttr?.id_grid !== null
                        ? (getGridCenterById(recommendationGridAttr.id_grid) || recommendationLatLng)
                        : recommendationLatLng;
                    targetLatLng.gridAttr = recommendationGridAttr;
                    targetLatLng.id_grid = recommendationGridAttr?.id_grid ?? null;
                    targetLatLng.isRecommendation = true; // Flag untuk navigasi
                    map.setView(targetLatLng, 16, { animate: false });
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
                }).addTo(contextRouteLayers);
            }

            // Garis Penunjuk ke Best Recommendation
            L.polyline([latlng, [bestRec.lat, bestRec.lng]], {
                color: '#10b981',
                weight: 3,
                dashArray: '10, 10',
                opacity: 0.7,
                className: 'route-path-animated',
                pane: 'route-pane'
            }).addTo(contextRouteLayers);
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
                restoreIsolatedOriginView();
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
    
            }
        }
    }
    popupContent += foundCount > 0
        ? `<div class="route-status ok"><i class="fa fa-route"></i> Rute ke ${foundCount} kategori TES ditampilkan di peta & panel kanan.</div>`
        : '';
    popupContent += `</div>`;
    updateRouteResultsLayout();

    if (isGridClick) {
        gridPopup = ensureGridPopup();
        suppressRecommendationRestore = true;
        gridPopup
            .setLatLng(latlng)
            .setContent(popupContent)
            .openOn(map);
        suppressRecommendationRestore = false;
        window.setTimeout(updateRouteResultsLayout, 0);
        gridPopup._gridRouteState = {
            latlng: clonePopupLatLng(latlng),
            gridAttr,
            recommendations,
            isRecommendationView
        };
    }
}


function renderGridAttrPopup(g) {
    const clr = clusterColors[g.cluster_sdwfcm] || NEUTRAL_FILL;
    const desc = getClusterDesc(g.cluster_sdwfcm);
    const waktuRows = Object.entries(tesCategories).map(([kat, meta]) => {
        const v = g[`waktu_tes_${kat}`];
        return popupRow(meta.label, v === null || v === undefined ? '–' : `${fmtNum(v, 1)} mnt`);
    }).join('');
    const isTas = g.titik_aman_semu === 1;
    const adm = typeof gridAdminName === 'function' ? gridAdminName(g.id_grid) : null;
    const lokasi = adm ? `<div class="popup-loc"><i class="fa fa-map-location-dot"></i> Kal. ${adm.desa.replace(/^Kelurahan\s+/i, '')}, Kap. ${adm.kecamatan}
        <a href="#" class="popup-link" onclick="event.preventDefault(); openRegionPanel('desa', ${JSON.stringify(adm.desa).replace(/"/g, '&quot;')})">Ringkasan kalurahan</a></div>` : '';
    return `${lokasi}<div class="popup-card">
        <div class="popup-row"><span>TIPOLOGI (${levelLabel(activeLevel)})</span><b style="color:${clr}">${getClusterName(g.cluster_sdwfcm)}</b></div>
        ${desc ? `<div class="popup-desc">${desc}</div>` : ''}
        ${popupRow('Derajat keanggotaan', `${fmtNum((g.membership_max || 0) * 100, 1)}%`)}
        ${popupRow('Indeks bahaya banjir', g.indeks_bahaya ?? '–')}
        ${popupRow('Terdampak banjir', g.terdampak === 1 ? 'Ya' : 'Tidak', g.terdampak === 1 ? TERDAMPAK_COLOR : null)}
        ${popupRow('Kerapatan jalan', fmtNum(g.road_density, 3))}
    </div>
    <div class="popup-card">
        <div class="popup-section">Waktu tempuh ke TES terdekat</div>
        ${waktuRows}
        ${popupRow('Waktu minimum', `${fmtNum(g.waktu_tes_min, 1)} mnt`)}
        ${popupRow('Jumlah opsi rute', `${g.jumlah_opsi_rute ?? '–'} / 5`)}
        <div class="popup-note"><i class="fa fa-circle-info"></i> Nilai hasil analisis skripsi. Panel <b>Rute Evakuasi</b> menelusuri jalur jalan aktual dari simpul jalan terdekat, sehingga angkanya bisa sedikit berbeda.</div>
    </div>
    <div class="popup-card">
        <div class="popup-section">Detour Index</div>
        ${popupRow('T<sub>ideal</sub> (euclidean)', `${fmtNum(g.t_ideal, 2)} mnt`)}
        ${popupRow('T<sub>aktual</sub> (jaringan)', `${fmtNum(g.t_aktual, 2)} mnt`)}
        ${popupRow('Detour Index', fmtNum(g.detour_index, 2))}
        ${isTas ? `<div class="popup-flag"><i class="fa fa-exclamation-triangle"></i> TITIK AMAN SEMU</div>` : ''}
    </div>`;
}
