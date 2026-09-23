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
            <div class="legend-sub">Banjir · Level ${levelLabel(activeLevel)}${lastLevelResult?.simulated ? ' · <span class="legend-sim">SIMULASI</span>' : ''}</div>`;
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
        html += `<div class="legend-foot">Klik klaster untuk menyorot. Transparansi = derajat keanggotaan.</div>`;
    } else if (activeView === 'tas') {
        html += `<div class="legend-static-item">${legendSwatch(TAS_COLOR, '#f5f3ff')} Titik Aman Semu <span class="legend-note">${fmtInt(countBy(d => d.titik_aman_semu === 1))}</span></div>
                 <div class="legend-static-item">${legendSwatch(NEUTRAL_FILL)} Bukan TAS</div>
                 <div class="legend-foot">TAS: T<sub>ideal</sub> ≤ P25 dan Detour Index ≥ P75</div>`;
    } else if (activeView === 'terdampak') {
        html += `<div class="legend-static-item">${legendSwatch(TERDAMPAK_COLOR)} Grid terdampak <span class="legend-note">${fmtInt(countBy(d => d.terdampak === 1))}</span></div>
                 <div class="legend-static-item">${legendSwatch(NEUTRAL_FILL)} Tidak terdampak</div>`;
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
