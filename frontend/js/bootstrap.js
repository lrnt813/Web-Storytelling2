function showLoading(show) { document.getElementById('loading-overlay').style.display = show ? 'flex' : 'none'; }

window.onload = async () => { 
    if (!LEVELS.some(l => l.key === activeLevel)) activeLevel = 'baseline';
    document.querySelectorAll('.level-btn').forEach(b => b.classList.toggle('active', b.dataset.level === activeLevel));
    if (window.matchMedia('(max-width: 760px)').matches) document.getElementById('control-panel').classList.add('collapsed');
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

    loadGridAdmin();
    await initK();
    loadStaticGeometry().then(() => {
        loadSession();
        // Tautan langsung ke panel hasil, mis. #hasil-transisi
        const m = window.location.hash.match(/^#hasil(?:-(\w+))?$/);
        if (m) {
            if (m[1] && RESULT_TABS.some(t => t.key === m[1])) activeResultsTab = m[1];
            openResults();
        }
    });
};


