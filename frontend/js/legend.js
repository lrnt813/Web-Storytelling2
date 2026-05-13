function addLegend(k = lastK) {
    lastK = k;
    if (legendControl) map.removeControl(legendControl);
    legendControl = L.control({ position: 'bottomright' });
    legendControl.onAdd = () => {
        const div = L.DomUtil.create('div', 'info legend');
        div.innerHTML = buildLegendHtml(k);
        return div;
    };
    legendControl.addTo(map);
}

function buildLegendHtml(k) {
    return buildClusterLegendHtml(k);
}

function buildClusterLegendHtml(k) {
    let html = '<h4 style="margin:0 0 5px; color:var(--accent-primary); font-size:12px; letter-spacing:1px;">LEGENDA KLASTER</h4>';

    for (let i = 0; i < k; i++) {
        const isActive = (activeCluster === i && activeMode !== 'semu') ? 'active' : '';
        html += `<div class="legend-item ${isActive}" onclick="filterByCluster(${i})">
                    <i style="background:${clusterColors[i]}; width:12px; height:12px; border-radius:3px; margin-right:10px;"></i>
                    KLASTER ${i}
                 </div>`;
    }

    const isSemuActive = (activeMode === 'semu') ? 'active' : '';
    html += `<div style="margin-top:10px; padding-top:10px; border-top:1px solid var(--glass-border);">
                <div class="legend-item ${isSemuActive}" onclick="filterBySemu()">
                    <i style="background:#000; width:12px; height:12px; border-radius:3px; margin-right:10px; border:1.5px solid #f59e0b;"></i>
                    TITIK AMAN SEMU
                </div>
             </div>`;
    return html;
}
let activeMode = 'cluster';

window.filterByCluster = (clusterId) => {
    activeMode = 'cluster';
    if (activeCluster === clusterId) activeCluster = null;
    else activeCluster = clusterId;
    applyGridStyle();
    addLegend();
};

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
};
