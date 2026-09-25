// ╔══════════════════════════════════════════════════════════════════════╗
// ║  results.js — Panel "Hasil Penelitian" (tabel & grafik Bab IV)       ║
// ╚══════════════════════════════════════════════════════════════════════╝
let thesisResults = null;
let activeResultsTab = 'data';
let activeProfileLevel = 'baseline';
let activeMatrixPair = 0;

const RESULT_TABS = [
    { key: 'data',       label: 'Data & Statistik' },
    { key: 'k',          label: 'Pemilihan K' },
    { key: 'algoritma',  label: 'Perbandingan Algoritma' },
    { key: 'profil',     label: 'Profil Klaster' },
    { key: 'transisi',   label: 'Transisi Klaster' },
    { key: 'tas',        label: 'Titik Aman Semu' },
    { key: 'waktu',      label: 'Waktu Tempuh' }
];

const VAR_LABELS = {
    waktu_tes_pendidikan: 'Waktu TES Pendidikan',
    waktu_tes_kesehatan: 'Waktu TES Kesehatan',
    waktu_tes_pemerintahan: 'Waktu TES Pemerintahan',
    waktu_tes_ibadah: 'Waktu TES Tempat Ibadah',
    waktu_tes_gor: 'Waktu TES GOR',
    waktu_tes_min: 'Waktu TES Minimum'
};

async function openResults() {
    document.getElementById('results-overlay').hidden = false;
    if (!thesisResults) {
        document.getElementById('results-body').innerHTML = '<p class="muted">Memuat hasil analisis...</p>';
        try {
            const resp = await fetch(`${API_BASE}/thesis-results`);
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            thesisResults = await resp.json();
        } catch (e) {
            document.getElementById('results-body').innerHTML = `<p class="muted">Gagal memuat hasil: ${e.message}</p>`;
            return;
        }
    }
    renderResultsTabs();
    renderResultsBody();
}

function closeResults() {
    document.getElementById('results-overlay').hidden = true;
    hideVizTip();
}

document.addEventListener('keydown', e => { if (e.key === 'Escape') closeResults(); });
document.addEventListener('click', e => { if (e.target?.id === 'results-overlay') closeResults(); });

function renderResultsTabs() {
    document.getElementById('results-tabs').innerHTML = RESULT_TABS.map(t =>
        `<button class="results-tab ${t.key === activeResultsTab ? 'active' : ''}" onclick="switchResultsTab('${t.key}')">${t.label}</button>`
    ).join('');
}

function switchResultsTab(key) {
    activeResultsTab = key;
    renderResultsTabs();
    renderResultsBody();
}

function renderResultsBody() {
    const r = thesisResults;
    const body = document.getElementById('results-body');
    const renderers = {
        data: renderDataTab, k: renderKTab, algoritma: renderAlgoTab, profil: renderProfileTab,
        transisi: renderTransitionTab, tas: renderTasTab, waktu: renderWaktuTab
    };
    body.innerHTML = renderers[activeResultsTab](r);
    body.scrollTop = 0;
    if (activeResultsTab === 'transisi') bindSankeyHover();
    if (activeResultsTab === 'waktu') bindBarHover();
}

// ── Helpers ──────────────────────────────────────────────────────────────────
function table(headers, rows, opts = {}) {
    const isLeft = i => i === 0 || (opts.leftLast && i === headers.length - 1);
    const head = headers.map((h, i) => `<th class="${isLeft(i) ? 'left' : ''}">${h}</th>`).join('');
    const bodyRows = rows.map(r => {
        const cls = opts.highlight && opts.highlight(r) ? ' class="hl"' : '';
        return `<tr${cls}>${r.cells.map((c, i) => `<td class="${isLeft(i) ? 'left' : ''}">${c}</td>`).join('')}</tr>`;
    }).join('');
    return `<div class="table-wrap"><table class="res-table"><thead><tr>${head}</tr></thead><tbody>${bodyRows}</tbody></table></div>`;
}

function section(title, caption, content, note = '') {
    const tools = [];
    if (content.includes('res-table')) tools.push(`<button class="sec-btn" title="Unduh tabel ini (Excel)" onclick="exportSectionTable(this)"><i class="fa fa-file-excel"></i> Excel</button>`);
    if (content.includes('<svg')) {
        const fname = title.replace(/<[^>]+>/g, '').replace(/[^\w]+/g, '_').replace(/_+/g, '_').slice(0, 50);
        tools.push(`<button class="sec-btn" title="Unduh grafik (PNG)" onclick="exportChartPNG(this, '${fname}')"><i class="fa fa-image"></i> PNG</button>`);
    }
    return `<section class="res-section">
        <div class="sec-head"><h3>${title}</h3>${tools.length ? `<div class="sec-tools">${tools.join('')}</div>` : ''}</div>${caption ? `<p class="res-caption">${caption}</p>` : ''}
        ${content}
        ${note ? `<p class="res-note">${note}</p>` : ''}
    </section>`;
}

function swatch(k) {
    return `<i class="legend-swatch" style="background:${clusterColors[k]}"></i>`;
}

function levelTabs(current, handler) {
    return `<div class="sub-tabs">${LEVELS.map(l =>
        `<button class="sub-tab ${l.key === current ? 'active' : ''}" onclick="${handler}('${l.key}')">${l.label}</button>`
    ).join('')}</div>`;
}

let vizTip = null;
function showVizTip(html, evt) {
    if (!vizTip) {
        vizTip = document.createElement('div');
        vizTip.className = 'viz-tip';
        document.body.appendChild(vizTip);
    }
    vizTip.innerHTML = html;
    vizTip.style.display = 'block';
    const pad = 14;
    const w = vizTip.offsetWidth, h = vizTip.offsetHeight;
    let x = evt.clientX + pad, y = evt.clientY + pad;
    if (x + w > window.innerWidth - 8) x = evt.clientX - w - pad;
    if (y + h > window.innerHeight - 8) y = evt.clientY - h - pad;
    vizTip.style.left = `${x}px`;
    vizTip.style.top = `${y}px`;
}
function hideVizTip() { if (vizTip) vizTip.style.display = 'none'; }

// ── Tab: Data & Statistik ────────────────────────────────────────────────────
function renderDataTab(r) {
    const ds = r.data_summary || {};
    const tc = ds.tes_counts || {};
    const pre = r.preprocessing || {};
    const pool = r.data_gabungan || {};
    const dataRows = [
        { cells: ['Grid analisis (100 × 100 m)', fmtInt(ds.n_grid)] },
        { cells: ['Segmen jaringan jalan', fmtInt(ds.n_road_segments)] },
        ...Object.entries(tesCategories).map(([k, m]) => ({ cells: [`TES ${m.label}`, fmtInt(tc[k])] })),
        { cells: ['Sistem koordinat', ds.crs || '–'] },
        { cells: ['Kecepatan berjalan kaki', `${fmtInt(r.meta?.walking_speed_m_per_min)} m/menit`] },
        { cells: ['Waktu penalti (grid tidak menjangkau TES)', `${fmtNum(r.t_pen)} menit`] },
        { cells: ['Baris data gabungan (grid × level non-Tergenang)', fmtInt(pool.n_baris)] },
        { cells: ['Fitur klasterisasi', `${(pre.features_kept || []).length} dari ${(pre.features_in || []).length}`] },
        { cells: ['Komponen PCA (varians kumulatif)', `${fmtInt(pre.n_components)} (${fmtNum((pre.explained_variance || 0) * 100, 1)}%)`] }
    ];
    const statRows = (r.baseline_time_stats || []).map(s => ({
        cells: [VAR_LABELS[s.variabel] || s.variabel, fmtInt(s.jumlah), fmtNum(s.mean), fmtNum(s.std),
                fmtNum(s.min), fmtNum(s.q25), fmtNum(s.median), fmtNum(s.q75), fmtNum(s.max)]
    }));
    const levelRows = LEVELS.map(l => {
        const s = r.levels?.[l.key] || {};
        const tesValid = Object.values(s.tes_valid || {}).reduce((a, b) => a + b, 0);
        return { cells: [l.label, l.kelas, fmtInt(s.n_grid_tergenang), `${fmtNum(s.persen_grid_tergenang)}%`,
                         fmtInt(s.n_roads_closed), fmtInt(tesValid), fmtInt(pool.n_baris_per_level?.[l.key])] };
    });
    return section('Ringkasan Data Penelitian', 'Data spasial Kabupaten Kulon Progo yang digunakan dalam analisis.',
                   table(['Komponen', 'Nilai'], dataRows))
        + section('Statistik Deskriptif Waktu Tempuh (Baseline)', 'Waktu tempuh berjalan kaki (menit) dari centroid grid ke titik TES terdekat per kategori, termasuk ruas snapping ke/dari jaringan jalan.',
                  table(['Variabel', 'n', 'Rata-rata', 'Std', 'Min', 'Q1', 'Median', 'Q3', 'Maks'], statRows),
                  'Nilai maksimum sama dengan waktu penalti (3 × waktu tempuh maksimum tercapai di Baseline) untuk grid yang tidak dapat menjangkau TES.')
        + section('Kondisi Tiap Level Banjir', 'Level didefinisikan oleh kelas bahaya banjir InaRisk yang ditutup. Grid pada kelas tersebut berstatus <b>Tergenang</b> dan dikeluarkan dari klasterisasi serta TAS.',
                  table(['Level', 'Kelas ditutup', 'Grid Tergenang', '% grid', 'Ruas ditutup', 'TES valid', 'Baris data gabungan'], levelRows));
}

// ── Model K yang sedang ditampilkan ─────────────────────────────────────────
function currentK(r) {
    const ks = r.k_keluaran || [];
    return ks.includes(activeK) ? activeK : (ks.includes(kUtama) ? kUtama : ks[0]);
}
function currentModel(r) { return r.model?.[String(currentK(r))] || {}; }
function kLabel(r) {
    const k = currentK(r);
    return `K = ${k}${k === kUtama ? ' (model utama)' : ' (sensitivitas)'}`;
}

// ── Tab: Pemilihan K (stabilitas) ────────────────────────────────────────────
function renderKTab(r) {
    const ks = r.k_selection || {};
    const best = ks.ari_subsampel_tertinggi;
    const rows = (ks.candidates || []).map(c => ({
        k: c.k,
        cells: [c.k, `${fmtNum(c.ari_subsampel_mean, 3)} ± ${fmtNum(c.ari_subsampel_sd, 3)}`,
                `${fmtNum(c.ari_inisialisasi_mean, 3)} ± ${fmtNum(c.ari_inisialisasi_sd, 3)}`,
                fmtNum(c.silhouette, 3), fmtNum(c.ketegasan_partisi, 3), fmtNum(c.size_entropy, 3),
                `${fmtNum(c.klaster_terbesar_persen, 1)}%`]
    }));
    const lamp = (ks.candidates || []).map(c => ({ cells: [c.k, fmtNum(c.iidx, 3), `${fmtNum(c.dunn, 4)} ± ${fmtNum(c.dunn_sd, 4)}`,
        fmtNum(c.desc, 3), fmtNum(c.pesc, 4), fmtNum(c.komposit_dengan_desc, 3), fmtNum(c.komposit_tanpa_desc, 3)] }));
    return section('Pemilihan Jumlah Klaster Berbasis Stabilitas (data gabungan)',
        `ARI subsampel: ${ks.B} subsampel ${fmtNum((ks.fraksi_subsampel || 0) * 100, 0)}% id_grid (${ks.n_init_subsampel} inisialisasi) terhadap solusi data penuh; ARI inisialisasi: rerata ARI berpasangan 10 run (seed 42–51).`,
        table(['K', 'ARI subsampel', 'ARI inisialisasi', 'Silhouette', 'Ketegasan partisi', 'Size Entropy', 'Klaster terbesar'], rows,
              { highlight: row => row.k === currentK(r) }),
        `Stabilitas subsampel dilaporkan sebagai uji ketahanan. K utama = 4 ditetapkan peneliti bersama pembimbing atas dasar substantif (memisahkan tipologi Terputus; METODOLOGI §9 (h)).`)
        + section('Lampiran: metrik pendukung lain', 'Hanya dilaporkan, tidak dipakai memilih K.',
            table(['K', 'I-Index', 'Dunn (5 sampel)', 'DESC', 'PESC', 'Komposit +DESC', 'Komposit −DESC'], lamp));
}

// ── Tab: Perbandingan Algoritma (K aktif) ────────────────────────────────────
function renderAlgoTab(r) {
    const M = currentModel(r);
    const status = a => a.status === 'ok' ? 'layak' : (a.status === 'degeneratif' ? '<b>degeneratif</b>' : `<b>gagal</b>: ${a.galat || ''}`);
    const rows = (M.algorithm_comparison || []).map(a => ({
        algo: a.algoritma,
        cells: [a.algoritma, status(a), fmtNum(a.silhouette, 3), fmtNum(a.calinski_harabasz, 1), fmtNum(a.davies_bouldin, 3),
                fmtNum(a.moran_i, 3), fmtNum(a.proporsi_tetangga_sama, 3), fmtNum(a.pc, 3), fmtNum(a.pe, 3), fmtNum(a.size_entropy, 3),
                a.klaster_terbesar_persen != null ? `${fmtNum(a.klaster_terbesar_persen, 1)}%` : '–', `${fmtNum(a.time_per_init_sec, 2)} s`]
    }));
    if (!rows.length) return section('Perbandingan Algoritma', '', '<p class="muted">Perbandingan algoritma belum dijalankan.</p>');
    return section(`Perbandingan Kinerja Algoritma (Baseline, ${kLabel(r)})`,
        'FCM (α = 0), SFCM, dan SDWFCM: m = 1,7, 10 inisialisasi (J terkecil), praproses dan penomoran sama. REDCAP dan SKATER pembanding tambahan, tanpa fallback.',
        table(['Algoritma', 'Status', 'Silhouette ↑', 'CH ↑', 'DB ↓', "Moran's I", 'Tetangga sama', 'PC ↑', 'PE ↓', 'Size Entropy', 'Klaster terbesar', 'Waktu / inisialisasi'], rows,
              { highlight: row => row.algo === 'SDWFCM' }),
        "PC = koefisien partisi, PE = entropi partisi (algoritma fuzzy). Moran's I label: 999 permutasi. Degeneratif = klaster terbesar > 90%.");
}

// ── Tab: Profil Klaster (K aktif) ────────────────────────────────────────────
function renderProfileTab(r) {
    const M = currentModel(r), k = currentK(r);
    const tcols = ['waktu_tes_pendidikan', 'waktu_tes_kesehatan', 'waktu_tes_pemerintahan', 'waktu_tes_ibadah', 'waktu_tes_gor', 'waktu_tes_min'];
    const rows = (M.cluster_profile || []).map(p => ({ cells: [
        `${swatch(p.klaster)} ${getClusterName(p.klaster)}`, `<b>${getClusterDesc(p.klaster) || p.deskripsi || ''}</b>`, fmtInt(p.jumlah_baris), `${fmtNum(p.persen_baris, 1)}%`,
        fmtNum(p.waktu_tes_min_median), fmtNum(p.waktu_tes_min_p75), fmtNum(p.waktu_tes_min_p90), fmtNum(p.waktu_tes_min),
        `${fmtNum((p.proporsi_waktu_min_lebih_batas || 0) * 100, 1)}%`, `${fmtNum((p.proporsi_terputus || 0) * 100, 1)}%`,
        fmtNum(p.proporsi_terisolasi, 3), fmtNum(p.jumlah_opsi_rute), fmtNum(p.Road_Density_mean), fmtNum(p.banjir)] }));
    const detail = (M.cluster_profile || []).map(p => ({ cells: [`${swatch(p.klaster)} ${getClusterName(p.klaster)}`,
        ...tcols.map(c => `${fmtNum(p[`${c}_median`])} <span class="muted">(${fmtNum(p[c])}; ${fmtNum(p[`${c}_persen_penalti`], 1)}%)</span>`)] }));
    const distRows = LEVELS.map(l => {
        const d = M.distribusi?.[l.key] || [];
        return { cells: [l.label, ...d.map(x => `${fmtInt(x.jumlah_grid)} <span class="muted">(${fmtNum(x.persen_semua_grid, 1)}%)</span>`)] };
    });
    return section(`Profil Tipologi — ${kLabel(r)} (data gabungan keempat level)`,
            'Nomor tipologi = peringkat menurut rata-rata waktu tempuh minimum (Tipologi 1 = terbaik); deskripsi ditulis dari profil klaster. Grid Tergenang tidak diklasterkan. Waktu dalam menit. "> 30 mnt" = proporsi baris dengan waktu minimum melebihi batas waktu evakuasi; "Terputus" (kategori akses) = waktu minimum = penalti, tidak mencapai TES mana pun. Indeks bahaya hanya deskriptif.',
            table(['Tipologi', 'Deskripsi', 'Baris', '%', 'Median', 'P75', 'P90', 'Rerata', '> 30 mnt', 'Terputus', 'Prop. terisolasi', 'Opsi rute', 'Kerapatan jalan', 'Indeks bahaya'], rows))
        + section('Waktu per kategori TES', 'Median (rerata; % baris penalti), menit.',
            table(['Tipologi', 'Pendidikan', 'Kesehatan', 'Pemerintahan', 'Ibadah', 'GOR', 'Minimum'], detail))
        + section('Distribusi Tipologi per Level', 'Jumlah grid per tipologi (persentase dari seluruh grid). Tergenang = status di luar klasterisasi, bukan tipologi.',
            table(['Level', ...Array.from({ length: k }, (_, j) => `${swatch(j)} ${getClusterName(j)}`), `<i class="legend-swatch" style="background:${LUAR_KLASTER_COLOR}"></i> Status: ${TERGENANG_LABEL}`], distRows));
}

// ── Tab: Transisi (K aktif) ─────────────────────────────────────────────────
function switchMatrixPair(i) { activeMatrixPair = i; renderResultsBody(); }
function stateColor(s, k) { return s === k ? LUAR_KLASTER_COLOR : clusterColors[s]; }
function stateName(s, k) { return s === k ? TERGENANG_LABEL : getClusterName(s); }

// Transisi antartipologi saja: submatriks tipologi × tipologi (grid Tergenang di salah satu level dikeluarkan).
function transTipologi(t, k) {
    const m = t.matrix.slice(0, k).map(row => row.slice(0, k));
    const n = m.flat().reduce((a, b) => a + b, 0);
    let diag = 0, best = null, edges = 0;
    const p0 = Array(k).fill(0), p1 = Array(k).fill(0);
    m.forEach((row, i) => row.forEach((v, j) => {
        p0[i] += v; p1[j] += v;
        if (i === j) { diag += v; return; }
        if (v > 0) edges++;
        if (!best || v > best.count) best = { from: i, to: j, count: v };
    }));
    const cdvm = n ? 0.5 * p0.reduce((a, _, i) => a + Math.abs(p1[i] - p0[i]) / n, 0) : null;
    return { matrix: m, n, sr: n ? diag / n * 100 : null, dominan: best && best.count > 0 ? best : null, edges, cdvm };
}

function buildSankey(r) {
    const M = currentModel(r), k = currentK(r), S = k;
    const levels = LEVELS.map(l => l.key);
    const counts = levels.map(key => (M.distribusi?.[key] || []).filter(p => p.state < k).sort((a, b) => a.state - b.state).map(p => p.jumlah_grid));
    const total = counts[0].reduce((a, b) => a + b, 0);
    const W = 880, H = 460, padT = 28, padB = 10, nodeW = 14, gap = 8, padL = 90, padR = 90;
    const colX = levels.map((_, i) => padL + i * (W - padL - padR - nodeW) / (levels.length - 1));
    const scale = (H - padT - padB - gap * (S - 1)) / total;
    const nodes = counts.map((cs, ci) => { let y = padT; return cs.map((c, j) => { const n = { x: colX[ci], y, h: c * scale, c, k: j }; y += c * scale + gap; return n; }); });
    let links = '';
    const seq = (M.transitions || []).filter(t => levels.indexOf(t.to_level) === levels.indexOf(t.from_level) + 1);
    seq.forEach((t, ti) => {
        const src = nodes[ti], dst = nodes[ti + 1];
        const outOff = src.map(n => n.y), inOff = dst.map(n => n.y);
        for (let i = 0; i < S; i++) for (let j = 0; j < S; j++) {
            const v = t.matrix[i][j]; if (!v) continue;   // hanya i, j < k: transisi antartipologi
            const h = v * scale, x0 = src[i].x + nodeW, x1 = dst[j].x, y0 = outOff[i], y1 = inOff[j];
            outOff[i] += h; inOff[j] += h;
            const xm = (x0 + x1) / 2;
            const d = `M${x0},${y0} C${xm},${y0} ${xm},${y1} ${x1},${y1} L${x1},${y1 + h} C${xm},${y1 + h} ${xm},${y0 + h} ${x0},${y0 + h} Z`;
            const tip = `${levelLabel(t.from_level)} ${stateName(i, k)} → ${levelLabel(t.to_level)} ${stateName(j, k)}<br><b>${fmtInt(v)}</b> grid (${fmtNum(v / src[i].c * 100, 1)}% dari asal)`;
            links += `<path class="sk-link" d="${d}" fill="${stateColor(i, k)}" data-tip="${tip.replace(/"/g, '&quot;')}"></path>`;
        }
    });
    let nodeSvg = '';
    nodes.forEach((col, ci) => {
        col.forEach(n => {
            if (!n.c) return;
            nodeSvg += `<rect class="sk-node" x="${n.x}" y="${n.y}" width="${nodeW}" height="${Math.max(1, n.h)}" rx="2" fill="${stateColor(n.k, k)}" data-tip="${levelLabel(levels[ci])} · ${stateName(n.k, k)}<br><b>${fmtInt(n.c)}</b> grid"></rect>`;
            if (n.h >= 11) nodeSvg += `<text class="sk-label" x="${ci === 0 ? n.x - 6 : n.x + nodeW + 4}" y="${n.y + n.h / 2 + 4}" text-anchor="${ci === 0 ? 'end' : 'start'}">${'T' + (n.k + 1)}</text>`;
        });
        nodeSvg += `<text class="sk-col" x="${colX[ci] + nodeW / 2}" y="16" text-anchor="middle">${levelLabel(levels[ci])}</text>`;
    });
    return `<div class="chart-wrap"><svg viewBox="0 0 ${W} ${H}" class="sankey" role="img" aria-label="Diagram Sankey transisi tipologi">${links}${nodeSvg}</svg></div>`;
}

function bindSankeyHover() {
    document.querySelectorAll('.sankey [data-tip]').forEach(el => {
        el.addEventListener('mousemove', e => showVizTip(el.dataset.tip, e));
        el.addEventListener('mouseleave', hideVizTip);
    });
}

function renderTransitionTab(r) {
    const M = currentModel(r), k = currentK(r), S = k;
    if (!M.transitions?.length) return '<p class="muted">Data transisi tidak tersedia.</p>';
    const rows = M.transitions.map(t => {
        const tt = transTipologi(t, k), d = tt.dominan;
        return { cells: [`${levelLabel(t.from_level)} → ${levelLabel(t.to_level)}`, fmtInt(tt.n),
            tt.sr != null ? `${fmtNum(tt.sr, 1)}%` : '–', fmtNum(t.ari, 3),
            d ? `${stateName(d.from, k)} → ${stateName(d.to, k)} (${fmtInt(d.count)})` : '–',
            `${tt.edges} / ${S * (S - 1)}`, fmtNum(tt.cdvm, 3)] };
    });
    const t = { ...M.transitions[Math.min(activeMatrixPair, M.transitions.length - 1)] };
    t.matrix = transTipologi(t, k).matrix;
    const pairTabs = `<div class="sub-tabs">${M.transitions.map((p, i) =>
        `<button class="sub-tab ${i === activeMatrixPair ? 'active' : ''}" onclick="switchMatrixPair(${i})">${levelLabel(p.from_level)} → ${levelLabel(p.to_level)}</button>`).join('')}</div>`;
    const maxV = Math.max(...t.matrix.flat());
    const sw = s => `<i class="legend-swatch" style="background:${stateColor(s, k)}"></i>`;
    const mRows = t.matrix.map((row, i) => ({ cells: [`${sw(i)} ${stateName(i, k)}`,
        ...row.map((v, j) => `<span class="cell-val${i === j ? ' diag' : ''}" style="background:rgba(59,130,246,${(v ? 0.12 + 0.6 * v / maxV : 0).toFixed(2)})">${fmtInt(v)}</span>`)] }));
    return section(`Alur Perpindahan Tipologi Antar Level — ${kLabel(r)}`, 'Pita = jumlah grid yang tetap atau berpindah tipologi ketika level naik. Grid Tergenang tidak diklasterkan sehingga tidak termasuk transisi tipologi.', buildSankey(r))
        + section('Ringkasan Transisi Tipologi', 'Hanya grid yang tidak Tergenang di kedua level. CDVM = ½ Σ |p<sub>s</sub>(tujuan) − p<sub>s</sub>(asal)| atas tipologi.',
                  table(['Transisi', 'Grid (non-Tergenang di kedua level)', 'Stability Rate', 'ARI', 'Transisi dominan', 'Edge aktif', 'CDVM'], rows))
        + section('Matriks Transisi', 'Baris = state asal, kolom = state tujuan.',
                  pairTabs + table(['Asal \\ Tujuan', ...Array.from({ length: S }, (_, j) => stateName(j, k))], mRows));
}

// ── Tab: Titik Aman Semu (aturan utama v4; sensitivitas 20/40 menit, absolut v3, persentil) ──
function renderTasTab(r) {
    const q = d => d && d.n ? `${fmtNum(d.median, 2)} [${fmtNum(d.p25, 2)}–${fmtNum(d.p75, 2)}; P90 ${fmtNum(d.p90, 2)}]` : '–';
    const rows = LEVELS.map(l => {
        const s = r.levels?.[l.key]?.tas || {};
        const sw = s.sensitivitas_ambang_waktu || {};
        return { cells: [l.label, fmtInt(s.jumlah_tas), fmtInt(s.jumlah_non_tas), fmtInt(s.jumlah_tes_terdekat_tidak_terjangkau), fmtInt(s.jumlah_tergenang),
                         `${fmtNum(s.persen_tas_non_tergenang)}%`, fmtInt(sw['20']?.jumlah_tas), fmtInt(sw['40']?.jumlah_tas),
                         `${fmtNum((sw['40']?.proporsi_tas_utama_yang_tetap_tas ?? 0) * 100, 1)}%`,
                         fmtInt(s.sensitivitas_absolut_v3?.jumlah_tas), fmtInt(s.sensitivitas_persentil?.jumlah_tas),
                         fmtNum(s.median_t_ideal_tas), fmtNum(s.median_t_aktual_tas)] };
    });
    const chg = LEVELS.slice(1).map(l => {
        const c = r.levels?.[l.key]?.tas_perubahan_vs_baseline || {};
        return { cells: [l.label, fmtInt(c.tas_baru), fmtInt(c.tas_hilang), fmtInt(c.tas_hilang_jadi_tergenang), fmtInt(c.tas_hilang_jadi_tes_terdekat_tidak_terjangkau), fmtInt(c.tas_hilang_lainnya)] };
    });
    const dist = LEVELS.map(l => { const s = r.levels?.[l.key]?.tas || {}; return { cells: [l.label, q(s.sebaran_di_tas), q(s.sebaran_di_non_tas)] }; });
    const grpAtr = ['dipicu banjir', 'diperparah banjir', 'tidak berubah', 'lainnya'];
    const atrRows = LEVELS.slice(1).filter(l => r.levels?.[l.key]?.atribusi_banjir).map(l => {
        const a = r.levels[l.key].atribusi_banjir;
        return { cells: [l.label, fmtInt(a.jumlah_tas), ...grpAtr.map(g => `${fmtInt(a.kelompok?.[g]?.jumlah)} <span class="muted">(${fmtNum(a.kelompok?.[g]?.persen, 1)}%)</span>`),
                         fmtNum(a.median_waktu_baseline_dipicu), fmtNum(a.median_tambahan_waktu_dipicu), fmtNum(a.median_tambahan_waktu_diperparah)] };
    });
    const kat = Object.keys(tesCategories);
    const katRows = LEVELS.map(l => { const s = r.levels?.[l.key]?.tas || {}; return { cells: [l.label, ...kat.map(k => fmtInt(s.tas_per_kategori_tes_terdekat?.[k] || 0))] }; });
    const aksesRows = [];
    LEVELS.forEach(l => ['20', '30', '40'].forEach(t => {
        const a = r.levels?.[l.key]?.kategori_akses?.[t];
        if (a) aksesRows.push({ cells: [l.label, `${t} menit`, ...['Terjangkau', 'Jauh', 'Terputus', 'Tergenang'].map(c => `${fmtInt(a[c]?.jumlah_grid)} <span class="muted">(${fmtNum(a[c]?.persen, 1)}%)</span>`)] });
    }));
    return section('Deteksi Titik Aman Semu (Detour Index)',
        'Aturan utama: TAS bila DI<sub>t</sub> ≥ 2, T<sub>ideal</sub> ≤ 5 menit, dan T<sub>aktual</sub> ≥ 30 menit (batas waktu evakuasi; Li dkk., 2026), pada grid non-Tergenang yang terjangkau. Sensitivitas: T<sub>aktual</sub> ≥ 20 / 40 menit, aturan absolut v3 (tanpa syarat T<sub>aktual</sub>), dan aturan persentil.',
        table(['Level', 'TAS', 'Non-TAS', 'TES terdekat tidak terjangkau', 'Tergenang', '% TAS', 'TAS (≥ 20 mnt)', 'TAS (≥ 40 mnt)', 'TAS utama yang tetap pada 40 mnt', 'Absolut v3', 'Persentil', 'Median T<sub>ideal</sub> TAS', 'Median T<sub>aktual</sub> TAS'], rows))
        + section('Perubahan TAS terhadap Baseline', 'TAS baru = bukan TAS di Baseline, menjadi TAS di level ini. TAS hilang dipecah menurut status di level ini.',
            table(['Level', 'TAS baru akibat banjir', 'TAS hilang', 'jadi Tergenang', 'jadi TES terdekat tidak terjangkau', 'lainnya'], chg))
        + (atrRows.length ? section('Atribusi Banjir pada TAS', 'TES sama = TES terdekat (Euclidean) identik dengan Baseline. Dipicu = bukan TAS di Baseline dan waktu Baseline ke TES itu &lt; 30 menit; diperparah = TAS di Baseline dan T<sub>aktual</sub> naik &gt; 1 menit; tidak berubah = TAS di Baseline, perubahan ≤ 1 menit; lainnya = selain itu.',
            table(['Level', 'TAS', 'Dipicu banjir', 'Diperparah banjir', 'Tidak berubah', 'Lainnya', 'Median waktu Baseline (dipicu)', 'Median tambahan (dipicu)', 'Median tambahan (diperparah)'], atrRows)) : '')
        + section('Sebaran Detour Index', 'Deskriptif; perbedaan DI TAS vs Non-TAS mengikuti definisi aturan, bukan bukti keberhasilan deteksi.',
            table(['Level', 'DI TAS: median [P25–P75; P90]', 'DI Non-TAS: median [P25–P75; P90]'], dist))
        + section('TAS per kategori TES terdekat', '', table(['Level', ...kat.map(k => tesCategories[k].label)], katRows))
        + section('Kategori Akses per Level', 'Padanan Li dkk. (2026): Terjangkau, Jauh (remote), Terputus (isolated), Tergenang (flooded), untuk batas 20/30/40 menit.',
            table(['Level', 'Batas', 'Terjangkau', 'Jauh', 'Terputus', 'Tergenang'], aksesRows));
}

// ── Tab: Waktu Tempuh (Gambar 18) ────────────────────────────────────────────
function buildBarChart(items, unit) {
    const W = 640, H = 280, padL = 48, padR = 16, padT = 26, padB = 34;
    const maxV = Math.max(...items.map(d => d.value)) * 1.12;
    const step = maxV > 100 ? 25 : (maxV > 40 ? 10 : 5);
    const plotW = W - padL - padR, plotH = H - padT - padB;
    const bw = Math.min(64, plotW / items.length * 0.5);
    const y = v => padT + plotH - v / maxV * plotH;
    let grid = '';
    for (let v = 0; v <= maxV; v += step) {
        grid += `<line class="bar-grid" x1="${padL}" x2="${W - padR}" y1="${y(v)}" y2="${y(v)}"></line>
                 <text class="bar-axis" x="${padL - 8}" y="${y(v) + 4}" text-anchor="end">${v}</text>`;
    }
    let bars = '';
    items.forEach((d, i) => {
        const cx = padL + plotW * (i + 0.5) / items.length;
        const top = y(d.value), h = padT + plotH - top;
        const r = Math.min(4, h);
        const x0 = cx - bw / 2;
        const path = `M${x0},${padT + plotH} V${top + r} Q${x0},${top} ${x0 + r},${top} H${x0 + bw - r} Q${x0 + bw},${top} ${x0 + bw},${top + r} V${padT + plotH} Z`;
        bars += `<path class="bar" d="${path}" data-tip="${d.label}<br><b>${fmtNum(d.value)} ${unit}</b>"></path>
                 <rect class="bar-hit" x="${cx - plotW / items.length / 2}" y="${padT}" width="${plotW / items.length}" height="${plotH}" data-tip="${d.label}<br><b>${fmtNum(d.value)} ${unit}</b>"></rect>
                 <text class="bar-value" x="${cx}" y="${top - 7}" text-anchor="middle">${fmtNum(d.value)}</text>
                 <text class="bar-axis" x="${cx}" y="${H - 12}" text-anchor="middle">${d.label}</text>`;
    });
    return `<div class="chart-wrap"><svg viewBox="0 0 ${W} ${H}" class="barchart" role="img" aria-label="Grafik batang">${grid}
        <line class="bar-base" x1="${padL}" x2="${W - padR}" y1="${padT + plotH}" y2="${padT + plotH}"></line>${bars}</svg></div>`;
}

function bindBarHover() {
    document.querySelectorAll('.barchart .bar-hit').forEach(el => {
        el.addEventListener('mousemove', e => { showVizTip(el.dataset.tip, e); el.previousElementSibling.classList.add('hover'); });
        el.addEventListener('mouseleave', () => { hideVizTip(); el.previousElementSibling.classList.remove('hover'); });
    });
}

function renderWaktuTab(r) {
    const items = LEVELS.map(l => ({ label: l.label, value: r.levels?.[l.key]?.mean_waktu_min || 0 }));
    const rows = LEVELS.map(l => {
        const s = r.levels?.[l.key] || {};
        return { cells: [l.label, ...Object.keys(tesCategories).map(k => fmtNum(s.mean_waktu?.[k])),
                         fmtNum(s.mean_waktu_min), fmtNum(s.median_waktu_min)] };
    });
    return section('Rata-rata Waktu Tempuh Minimum ke TES', 'Rata-rata waktu tempuh minimum (menit) grid non-Tergenang pada setiap level banjir (termasuk ruas snapping).',
                   buildBarChart(items, 'menit'))
        + section('Rata-rata Waktu Tempuh per Kategori TES', 'Satuan menit, grid non-Tergenang. Grid yang tidak menjangkau TES diberi waktu penalti.',
                  table(['Level', ...Object.values(tesCategories).map(m => m.label), 'Minimum', 'Median Min.'], rows));
}
