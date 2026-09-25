function addLegend(k = lastK) {
    lastK = k;
    if (legendControl) map.removeControl(legendControl);
    legendControl = L.control({ position: 'bottomright' });
    legendControl.onAdd = () => {
        const div = L.DomUtil.create('div', 'info legend');
        div.innerHTML = buildLegendHtml(k);
        L.DomEvent.disableClickPropagation(div);
        return div;
    };
    legendControl.addTo(map);
}

function legendSwatch(color, border = null) {
    return `<i class="legend-swatch" style="background:${color};${border ? ` border:1.5px solid ${border};` : ''}"></i>`;
}

function legendTitle() {
    return `<h4 class="legend-title">${viewModes[activeView].toUpperCase()}</h4>
            <div class="legend-sub">Banjir · ${levelFullLabel(activeLevel)}${activeK ? ` · K = ${activeK}` : ''}${lastLevelResult?.simulated ? ' · <span class="legend-sim">SIMULASI</span>' : ''}</div>`;
}

function countBy(fn) {
    if (!gridLayer?.lookup) return 0;
    let n = 0;
    for (const d of Object.values(gridLayer.lookup)) if (fn(d)) n++;
    return n;
}

function buildLegendHtml(k) {
    let html = legendTitle();
    if (activeView === 'klaster') {
        for (let i = 0; i < k; i++) {
            const isActive = activeCluster === i ? 'active' : '';
            const desc = getClusterDesc(i);
            html += `<div class="legend-item ${isActive}" onclick="filterByCluster(${i})">
                        ${legendSwatch(clusterColors[i])}
                        <div><div>${getClusterName(i)}</div>${desc ? `<div class="legend-desc">${desc}</div>` : ''}</div>
                     </div>`;
        }
        html += `<div class="legend-foot">Klik tipologi untuk menyorot. Transparansi = derajat keanggotaan. Grid Tergenang tidak diklasterkan sehingga tidak ditampilkan (lihat tampilan Grid Tergenang).</div>`;
    } else if (activeView === 'tas') {
        html += `<div class="legend-static-item">${legendSwatch(TAS_COLOR, '#f5f3ff')} Titik Aman Semu <span class="legend-note">${fmtInt(countBy(d => d.titik_aman_semu === 1))}</span></div>
                 <div class="legend-static-item">${legendSwatch(NEUTRAL_FILL)} Non-TAS <span class="legend-note">${fmtInt(countBy(d => d.status_tas === 0))}</span></div>
                 <div class="legend-static-item">${legendSwatch(TERPUTUS_COLOR, '#94a3b8')} TES terdekat tidak terjangkau <span class="legend-note">${fmtInt(countBy(d => d.status_tas === 2))}</span></div>
                 <div class="legend-static-item">${legendSwatch(TERGENANG_COLOR)} Tergenang <span class="legend-note">${fmtInt(countBy(d => d.status_tas === 3))}</span></div>
                 <div class="legend-foot">TAS: Detour Index ≥ 2, T<sub>ideal</sub> ≤ 5 menit, dan T<sub>aktual</sub> ≥ 30 menit (grid non-Tergenang yang terjangkau). TES terdekat tidak terjangkau: TES terdekat secara garis lurus tidak dapat dicapai lewat jaringan jalan (berbeda dari kategori akses Terputus).</div>`;
    } else if (activeView === 'terdampak') {
        html += `<div class="legend-static-item">${legendSwatch(TERGENANG_COLOR)} Tergenang <span class="legend-note">${fmtInt(countBy(d => d.tergenang === 1))}</span></div>
                 <div class="legend-static-item">${legendSwatch(NEUTRAL_FILL)} Tidak tergenang</div>
                 <div class="legend-foot">${LEVELS.find(l => l.key === activeLevel)?.kelas || ''}</div>`;
    } else if (activeView === 'akses') {
        [0, 1, 2, 3].forEach(c => { html += `<div class="legend-static-item">${legendSwatch(AKSES_COLORS[c])} ${AKSES_LABELS[c]} <span class="legend-note">${fmtInt(countBy(d => d.kategori_akses === c))}</span></div>`; });
        html += `<div class="legend-foot">Batas waktu evakuasi 30 menit berjalan kaki (Li dkk., 2026).</div>`;
    } else if (activeView === 'waktu') {
        waktuBins.forEach(b => { html += `<div class="legend-static-item">${legendSwatch(b.color)} ${b.label}</div>`; });
        html += `<div class="legend-foot">Kecepatan berjalan kaki 80 m/menit</div>`;
    } else if (activeView === 'bahaya') {
        Object.entries(bahayaLabels).forEach(([v, lbl]) => {
            html += `<div class="legend-static-item">${legendSwatch(bahayaColors[v])} ${v} – ${lbl}</div>`;
        });
    }
    return html;
}

window.filterByCluster = (clusterId) => {
    activeCluster = activeCluster === clusterId ? null : clusterId;
    applyGridStyle();
    addLegend();
};
