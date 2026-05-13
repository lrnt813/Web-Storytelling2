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

