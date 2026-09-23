// ╔══════════════════════════════════════════════════════════════════════╗
// ║  regions.js — Ringkasan & peringkat prioritas per wilayah            ║
// ║  Dihitung di browser dari data grid level aktif (ikut simulasi).     ║
// ╚══════════════════════════════════════════════════════════════════════╝
let regionKind = 'desa';            // 'desa' (kalurahan) | 'kecamatan' (kapanewon)
let regionSort = 'isolated_pct';
let selectedRegion = null;          // nama wilayah terpilih
let regionHighlight = null;
let lastRegionRows = [];

const REGION_SORTS = {
    isolated_pct: { label: '% grid terisolasi', desc: true },
    tas:          { label: 'Jumlah Titik Aman Semu', desc: true },
    terdampak_pct:{ label: '% grid terdampak banjir', desc: true },
    waktu:        { label: 'Rata-rata waktu minimum', desc: true },
    critical_pct: { label: '% grid klaster akses terburuk (Klaster 5)', desc: true },
    name:         { label: 'Nama wilayah (A–Z)', desc: false }
};

function cleanDesaName(n) { return String(n || '').replace(/^Kelurahan\s+/i, ''); }

function computeRegionStats(kind = regionKind) {
    const lookup = gridLayer?.lookup;
    if (!lookup || !gridAdmin) return [];
    const K = lastK || 6;
    const acc = new Map();
    for (const d of Object.values(lookup)) {
        const adm = gridAdminName(d.id_grid);
        if (!adm) continue;
        const name = kind === 'desa' ? adm.desa : adm.kecamatan;
        let r = acc.get(name);
        if (!r) {
            r = { name, display: kind === 'desa' ? cleanDesaName(name) : name, kecamatan: adm.kecamatan,
                  n: 0, clusters: new Array(K).fill(0), tas: 0, terdampak: 0, isolated: 0, waktuSum: 0, waktuN: 0 };
            acc.set(name, r);
        }
        r.n += 1;
        if (d.cluster_sdwfcm >= 0 && d.cluster_sdwfcm < K) r.clusters[d.cluster_sdwfcm] += 1;
        if (d.titik_aman_semu === 1) r.tas += 1;
        if (d.terdampak === 1) r.terdampak += 1;
        if (d.is_isolated === 1 || d.jumlah_opsi_rute === 0) r.isolated += 1;
        if (Number.isFinite(d.waktu_tes_min)) { r.waktuSum += d.waktu_tes_min; r.waktuN += 1; }
    }
    return [...acc.values()].map(r => ({
        ...r,
        isolated_pct: r.isolated / r.n * 100,
        terdampak_pct: r.terdampak / r.n * 100,
        tas_pct: r.tas / r.n * 100,
        critical_pct: r.clusters[K - 1] / r.n * 100,
        waktu: r.waktuN ? r.waktuSum / r.waktuN : null,
        dominant: r.clusters.indexOf(Math.max(...r.clusters))
    }));
}

function sortRegionRows(rows) {
    const s = REGION_SORTS[regionSort];
    return rows.sort((a, b) => {
        if (regionSort === 'name') return a.display.localeCompare(b.display, 'id');
        const va = a[regionSort] ?? -Infinity, vb = b[regionSort] ?? -Infinity;
        if (vb !== va) return s.desc ? vb - va : va - vb;
        return (b.waktu ?? 0) - (a.waktu ?? 0);   // pemecah seri: waktu tempuh lebih lama lebih prioritas
    });
}

function clusterBar(clusters, n) {
    return `<div class="cl-bar">${clusters.map((c, i) => c ? `<i style="width:${(c / n * 100).toFixed(2)}%;background:${clusterColors[i]}" title="Klaster ${i}: ${fmtInt(c)} grid"></i>` : '').join('')}</div>`;
}

async function openRegionPanel(kind = null, name = null) {
    await loadGridAdmin();
    try { await loadBoundaryData(); } catch { }
    if (kind) regionKind = kind;
    document.getElementById('region-panel').hidden = false;
    document.body.classList.add('region-open');
    if (name) selectRegion(name, false); else renderRegionPanel();
}

function closeRegionPanel() {
    document.getElementById('region-panel').hidden = true;
    document.body.classList.remove('region-open');
    clearRegionHighlight();
    selectedRegion = null;
}

function setRegionKind(kind) { regionKind = kind; selectedRegion = null; clearRegionHighlight(); renderRegionPanel(); }
function setRegionSort(key) { regionSort = key; renderRegionPanel(); }

function renderRegionPanel() {
    const panel = document.getElementById('region-panel');
    if (!panel || panel.hidden) return;
    const rows = sortRegionRows(computeRegionStats());
    lastRegionRows = rows;
    const sim = lastLevelResult?.simulated ? ' <span class="legend-sim">SIMULASI</span>' : '';
    const kindLabel = regionKind === 'desa' ? 'Kalurahan' : 'Kapanewon';
    const sel = rows.find(r => r.name === selectedRegion);

    document.getElementById('region-body').innerHTML = `
        <div class="region-controls">
            <div class="seg">
                <button class="${regionKind === 'desa' ? 'active' : ''}" onclick="setRegionKind('desa')">Kalurahan (${regionKind === 'desa' ? rows.length : 88})</button>
                <button class="${regionKind === 'kecamatan' ? 'active' : ''}" onclick="setRegionKind('kecamatan')">Kapanewon (${regionKind === 'kecamatan' ? rows.length : 12})</button>
            </div>
            <label class="region-sort">Urutkan prioritas
                <select onchange="setRegionSort(this.value)">
                    ${Object.entries(REGION_SORTS).map(([k, v]) => `<option value="${k}" ${k === regionSort ? 'selected' : ''}>${v.label}</option>`).join('')}
                </select>
            </label>
            <div class="region-level">Level <b>${levelLabel(activeLevel)}</b>${sim} · klik baris untuk menyorot wilayah di peta</div>
        </div>
        ${sel ? regionDetailCard(sel, kindLabel) : ''}
        <div class="table-wrap region-table-wrap">
            <table class="res-table region-table" id="region-table">
                <thead><tr><th class="left">#</th><th class="left">${kindLabel}</th><th>Grid</th><th>Terisolasi</th><th>TAS</th><th>Terdampak</th><th>Waktu min.</th><th class="left">Komposisi klaster</th></tr></thead>
                <tbody>${rows.map((r, i) => `
                    <tr class="${r.name === selectedRegion ? 'hl' : ''}" data-name="${esc(r.name)}" onclick="selectRegion(this.dataset.name)">
                        <td class="left">${i + 1}</td>
                        <td class="left"><b>${esc(r.display)}</b>${regionKind === 'desa' ? `<div class="muted-sm">${esc(r.kecamatan)}</div>` : ''}</td>
                        <td>${fmtInt(r.n)}</td>
                        <td>${fmtNum(r.isolated_pct, 1)}%</td>
                        <td>${fmtInt(r.tas)}</td>
                        <td>${fmtNum(r.terdampak_pct, 1)}%</td>
                        <td>${fmtNum(r.waktu, 1)}</td>
                        <td class="left">${clusterBar(r.clusters, r.n)}</td>
                    </tr>`).join('')}
                </tbody>
            </table>
        </div>
        <p class="res-note">Terisolasi = grid yang tidak dapat menjangkau TES mana pun. Waktu dalam menit (berjalan kaki 80 m/menit).
            Nilai dihitung dari data grid pada level yang sedang ditampilkan.</p>`;
}

function regionDetailCard(r, kindLabel) {
    const K = r.clusters.length;
    const bars = r.clusters.map((c, i) => `
        <div class="rd-row">
            <span>${swatch(i)} Klaster ${i}<small>${esc(getClusterDesc(i))}</small></span>
            <div class="rd-track"><i style="width:${(c / r.n * 100).toFixed(1)}%;background:${clusterColors[i]}"></i></div>
            <b>${fmtInt(c)}</b>
        </div>`).join('');
    return `
        <div class="region-detail">
            <div class="rd-head">
                <div><div class="sp-kicker">${kindLabel.toUpperCase()}</div><div class="rd-name">${esc(r.display)}</div>
                ${regionKind === 'desa' ? `<div class="muted-sm">Kapanewon ${esc(r.kecamatan)}</div>` : ''}</div>
                <button class="btn-icon" title="Tutup detail" onclick="selectRegion(null)"><i class="fa fa-times"></i></button>
            </div>
            <div class="summary-grid">
                <div class="summary-tile"><span>Grid analisis</span><b>${fmtInt(r.n)}</b></div>
                <div class="summary-tile"><span>Rata-rata waktu min.</span><b>${fmtNum(r.waktu, 1)} <small>mnt</small></b></div>
                <div class="summary-tile"><span>Grid terisolasi</span><b>${fmtInt(r.isolated)} <small>(${fmtNum(r.isolated_pct, 1)}%)</small></b></div>
                <div class="summary-tile"><span>Titik Aman Semu</span><b>${fmtInt(r.tas)} <small>(${fmtNum(r.tas_pct, 1)}%)</small></b></div>
                <div class="summary-tile"><span>Grid terdampak</span><b>${fmtInt(r.terdampak)} <small>(${fmtNum(r.terdampak_pct, 1)}%)</small></b></div>
                <div class="summary-tile"><span>Klaster dominan</span><b>${swatch(r.dominant)} Klaster ${r.dominant}</b></div>
            </div>
            <div class="rd-bars">${bars}</div>
        </div>`;
}

function clearRegionHighlight() {
    if (regionHighlight && map.hasLayer(regionHighlight)) map.removeLayer(regionHighlight);
    regionHighlight = null;
}

function selectRegion(name, fly = true) {
    selectedRegion = name;
    clearRegionHighlight();
    if (name) {
        const feat = findBoundaryFeature(regionKind, name);
        if (feat) {
            regionHighlight = L.geoJSON(feat, {
                pane: 'boundary-pane', interactive: false,
                style: { color: '#38bdf8', weight: 3.5, fillColor: '#38bdf8', fillOpacity: 0.08 }
            }).addTo(map);
            if (fly) {
                const narrow = window.innerWidth <= 760;
                map.flyToBounds(regionHighlight.getBounds(), {
                    paddingTopLeft: narrow ? [20, 80] : [380, 80],
                    paddingBottomRight: narrow ? [20, Math.round(window.innerHeight * 0.5)] : [480, 40], duration: 1.0
                });
            }
        }
    }
    renderRegionPanel();
    const body = document.getElementById('region-body');
    if (body && name) body.scrollTop = 0;
}

function regionSummaryRowsForExport() {
    const kindLabel = regionKind === 'desa' ? 'Kalurahan' : 'Kapanewon';
    const K = lastK || 6;
    const head = ['Peringkat', kindLabel, ...(regionKind === 'desa' ? ['Kapanewon'] : []), 'Jumlah grid', 'Grid terisolasi', '% terisolasi',
        'Titik Aman Semu', '% TAS', 'Grid terdampak', '% terdampak', 'Rata-rata waktu min (menit)', 'Klaster dominan',
        ...Array.from({ length: K }, (_, i) => `Grid Klaster ${i}`)];
    const body = lastRegionRows.map((r, i) => [i + 1, r.display, ...(regionKind === 'desa' ? [r.kecamatan] : []), r.n, r.isolated,
        +r.isolated_pct.toFixed(2), r.tas, +r.tas_pct.toFixed(2), r.terdampak, +r.terdampak_pct.toFixed(2),
        r.waktu === null ? null : +r.waktu.toFixed(2), r.dominant, ...r.clusters]);
    return [head, ...body];
}
