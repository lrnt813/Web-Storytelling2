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


