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

// ── Tab: Data & Statistik (Tabel 8, Tabel 9) ─────────────────────────────────
function renderDataTab(r) {
    const ds = r.data_summary || {};
    const tc = ds.tes_counts || {};
    const dataRows = [
        { cells: ['Grid analisis (100 × 100 m)', fmtInt(ds.n_grid)] },
        { cells: ['Segmen jaringan jalan', fmtInt(ds.n_road_segments)] },
        ...Object.entries(tesCategories).map(([k, m]) => ({ cells: [`TES ${m.label}`, fmtInt(tc[k])] })),
        { cells: ['Sistem koordinat', ds.crs || '–'] },
        { cells: ['Kecepatan berjalan kaki', `${fmtInt(r.meta?.walking_speed_m_per_min)} m/menit`] },
        { cells: ['Waktu penalti (grid terisolasi)', `${fmtNum(r.t_pen)} menit`] }
    ];
    const statRows = (r.baseline_time_stats || []).map(s => ({
        cells: [VAR_LABELS[s.variabel] || s.variabel, fmtInt(s.jumlah), fmtNum(s.mean), fmtNum(s.std),
                fmtNum(s.min), fmtNum(s.q25), fmtNum(s.median), fmtNum(s.q75), fmtNum(s.max)]
    }));
    const levelRows = LEVELS.map(l => {
        const s = r.levels?.[l.key] || {};
        const tesValid = Object.values(s.tes_valid || {}).reduce((a, b) => a + b, 0);
        return { cells: [l.label, l.kelas, fmtInt(s.n_grid_terdampak), `${fmtNum(s.persen_grid_terdampak)}%`,
                         fmtInt(s.n_roads_closed), fmtInt(tesValid), `${(s.preprocessing?.features_kept || []).length} / ${s.preprocessing?.n_features_in ?? '–'}`,
                         fmtInt(s.preprocessing?.n_components),
                         `${fmtNum((s.preprocessing?.explained_variance || 0) * 100, 1)}%`] };
    });
    return section('Ringkasan Data Penelitian', 'Data spasial Kabupaten Kulon Progo yang digunakan dalam analisis.',
                   table(['Komponen', 'Nilai'], dataRows))
        + section('Statistik Deskriptif Waktu Tempuh (Baseline)', 'Waktu tempuh berjalan kaki (menit) dari setiap grid ke TES terdekat per kategori.',
                  table(['Variabel', 'n', 'Rata-rata', 'Std', 'Min', 'Q1', 'Median', 'Q3', 'Maks'], statRows),
                  'Nilai maksimum sama dengan waktu penalti (3 × waktu tempuh maksimum tercapai) untuk grid yang tidak dapat menjangkau TES.')
        + section('Kondisi Tiap Level Banjir', 'Dampak skenario banjir terhadap grid, jaringan jalan, dan TES, serta hasil pra-pemrosesan: IQR capping 3 × IQR → seleksi fitur → Yeo-Johnson → RobustScaler → PCA (varians kumulatif ≥ 80%).',
                  table(['Level', 'Kelas ditutup', 'Grid terdampak', '% grid', 'Jalan terputus', 'TES valid', 'Fitur terpilih', 'Komponen PCA', 'Varians'], levelRows),
                  'Penanda isolasi dan jumlah opsi rute tersaring pada level dengan < 25% grid terisolasi karena IQR-nya nol (nilainya konstan setelah capping).');
}

// ── Tab: Pemilihan K (Tabel 10) ──────────────────────────────────────────────
function renderKTab(r) {
    const ks = r.k_selection || {};
    const rows = (ks.candidates || []).map(c => ({
        k: c.k,
        cells: [c.k, fmtNum(c.iidx, 3), fmtNum(c.dunn, 4), fmtNum(c.desc, 3), fmtNum(c.ketegasan_partisi, 3),
                fmtNum(c.pesc, 6), fmtNum(c.size_entropy, 3), fmtNum(c.parsimoni, 3), fmtNum(c.composite, 3)]
    }));
    return section('Evaluasi Jumlah Klaster Optimal (Baseline)',
        `Parameter SDWFCM: m = ${r.meta?.sdwfcm?.m}, α = ${r.meta?.sdwfcm?.alpha}, k-NN = ${r.meta?.sdwfcm?.knn}; ${r.meta?.sdwfcm_n_init ?? 10} inisialisasi per K. K diuji pada rentang 2–10.`,
        table(['K', 'I-Index ↑', 'Dunn ↑', 'DESC ↑', 'Ketegasan partisi ↑', 'PESC', 'Size Entropy', 'Parsimoni', 'Skor Komposit ↑'], rows,
              { highlight: row => row.k === ks.k_terpilih }),
        `K terpilih: <b>${ks.k_terpilih}</b> (skor ${fmtNum(ks.skor_terpilih, 3)}); runner-up K = ${ks.k_runner_up}
         (skor ${fmtNum(ks.skor_runner_up, 3)}), selisih <b>${fmtNum(ks.selisih_skor, 3)}</b>. Skor komposit = rata-rata
         percentile rank I-Index, Dunn, DESC, dan ketegasan partisi (1 − PE/ln K) ditambah parsimoni linear, bobot sama.`);
}

// ── Tab: Perbandingan Algoritma (Tabel 11) ───────────────────────────────────
function renderAlgoTab(r) {
    const rows = (r.algorithm_comparison || []).map(a => ({
        algo: a.algoritma,
        cells: [a.algoritma, fmtNum(a.silhouette, 3), fmtNum(a.calinski_harabasz, 1), fmtNum(a.davies_bouldin, 3),
                fmtNum(a.moran_i, 3), fmtNum(a.proporsi_tetangga_sama, 3), fmtNum(a.size_entropy, 3), fmtNum(a.wcss, 1), `${fmtNum(a.time_sec, 2)} s`]
    }));
    if (!rows.length) {
        return section('Perbandingan Algoritma', '', '<p class="muted">Perbandingan algoritma belum dijalankan. Jalankan <code>python -m scripts.thesis_analysis</code> tanpa opsi <code>--skip-comparison</code>.</p>');
    }
    return section('Perbandingan Kinerja Algoritma (Baseline, K = ' + r.k + ')',
        'SDWFCM dibandingkan dengan Spatial FCM, REDCAP, dan SKATER pada ruang fitur hasil PCA yang sama.',
        table(['Algoritma', 'Silhouette ↑', 'Calinski-Harabasz ↑', 'Davies-Bouldin ↓', "Moran's I ↑", 'Tetangga berlabel sama ↑', 'Size Entropy ↑', 'WCSS ↓', 'Waktu'], rows,
              { highlight: row => row.algo === 'SDWFCM' }),
        "Semua algoritma dinomori dengan aturan yang sama (urut rata-rata waktu tempuh minimum) sebelum Moran's I dihitung (kontiguitas rook). 'Tetangga berlabel sama' = proporsi pasangan tetangga rook dengan label sama (tidak bergantung penomoran). Waktu SDWFCM = rata-rata per inisialisasi.");
}

// ── Tab: Profil Klaster (Tabel 12–15) ────────────────────────────────────────
function switchProfileLevel(key) { activeProfileLevel = key; renderResultsBody(); }

function renderProfileTab(r) {
    const lv = r.levels?.[activeProfileLevel] || {};
    const rows = (lv.cluster_profile || []).map(p => {
        const iso = ['pendidikan', 'kesehatan', 'pemerintahan', 'ibadah', 'gor']
            .reduce((a, k) => a + (p[`is_isolated_${k}`] || 0), 0) / 5;
        return { cells: [
            `${swatch(p.klaster)} Klaster ${p.klaster}`, fmtInt(p.jumlah_grid), `${fmtNum(p.persen_grid, 1)}%`,
            fmtNum(p.Road_Density_mean), fmtNum(p.banjir), fmtNum(p.waktu_tes_pendidikan), fmtNum(p.waktu_tes_kesehatan),
            fmtNum(p.waktu_tes_pemerintahan), fmtNum(p.waktu_tes_ibadah), fmtNum(p.waktu_tes_gor), fmtNum(p.waktu_tes_min),
            fmtNum(p.jumlah_opsi_rute), `${fmtNum(iso * 100, 1)}%`, p.deskripsi || ''
        ] };
    });
    return levelTabs(activeProfileLevel, 'switchProfileLevel')
        + section(`Profil Klaster Level ${levelLabel(activeProfileLevel)}`,
            'Rata-rata nilai fitur asli per klaster. Baseline: klaster diurutkan dari waktu tempuh minimum tercepat (Klaster 0). Level lain: nomor diselaraskan ke pusat klaster Baseline (Hungarian); tipologi yang tidak berpadanan ditandai.',
            table(['Klaster', 'Grid', '%', 'Kerapatan Jalan', 'Indeks Bahaya', 'Pendidikan', 'Kesehatan', 'Pemerintahan',
                   'Ibadah', 'GOR', 'Waktu Min.', 'Opsi Rute', 'Terisolasi', 'Interpretasi'], rows, { leftLast: true }),
            'Kolom waktu dalam menit. "Terisolasi" = rata-rata proporsi kategori TES yang tidak terjangkau.');
}

// ── Tab: Transisi (Sankey, stabilitas, ARI, CDVM) ────────────────────────────
function switchMatrixPair(i) { activeMatrixPair = i; renderResultsBody(); }

function buildSankey(r) {
    const k = r.k;
    const levels = LEVELS.map(l => l.key);
    const counts = levels.map(key => (r.levels[key]?.cluster_profile || []).map(p => p.jumlah_grid));
    const total = counts[0].reduce((a, b) => a + b, 0);
    const W = 880, H = 440, padT = 28, padB = 10, nodeW = 14, gap = 8;
    const padL = 70, padR = 70;
    const colX = levels.map((_, i) => padL + i * (W - padL - padR - nodeW) / (levels.length - 1));
    const scale = (H - padT - padB - gap * (k - 1)) / total;

    const nodes = counts.map((cs, ci) => {
        let y = padT;
        return cs.map((c, j) => { const n = { x: colX[ci], y, h: c * scale, c, k: j }; y += c * scale + gap; return n; });
    });

    let links = '';
    r.transitions.forEach((t, ti) => {
        const src = nodes[ti], dst = nodes[ti + 1];
        const outOff = src.map(n => n.y), inOff = dst.map(n => n.y);
        for (let i = 0; i < k; i++) {
            for (let j = 0; j < k; j++) {
                const v = t.matrix[i][j];
                if (!v) continue;
                const h = v * scale;
                const x0 = src[i].x + nodeW, x1 = dst[j].x;
                const y0 = outOff[i], y1 = inOff[j];
                outOff[i] += h; inOff[j] += h;
                const xm = (x0 + x1) / 2;
                const d = `M${x0},${y0} C${xm},${y0} ${xm},${y1} ${x1},${y1} L${x1},${y1 + h} C${xm},${y1 + h} ${xm},${y0 + h} ${x0},${y0 + h} Z`;
                const tip = `${levelLabel(t.from_level)} Klaster ${i} → ${levelLabel(t.to_level)} Klaster ${j}<br><b>${fmtInt(v)}</b> grid (${fmtNum(v / src[i].c * 100, 1)}% dari asal)`;
                links += `<path class="sk-link" d="${d}" fill="${clusterColors[i]}" data-tip="${tip.replace(/"/g, '&quot;')}"></path>`;
            }
        }
    });

    let nodeSvg = '';
    nodes.forEach((col, ci) => {
        col.forEach(n => {
            const tip = `${levelLabel(levels[ci])} · Klaster ${n.k}<br><b>${fmtInt(n.c)}</b> grid`;
            nodeSvg += `<rect class="sk-node" x="${n.x}" y="${n.y}" width="${nodeW}" height="${Math.max(1, n.h)}" rx="2" fill="${clusterColors[n.k]}" data-tip="${tip}"></rect>`;
            if (n.h >= 11) {
                const left = ci === 0;
                const tx = left ? n.x - 6 : (ci === levels.length - 1 ? n.x + nodeW + 6 : n.x + nodeW + 4);
                const anchor = left ? 'end' : 'start';
                nodeSvg += `<text class="sk-label" x="${tx}" y="${n.y + n.h / 2 + 4}" text-anchor="${anchor}">K${n.k}</text>`;
            }
        });
        nodeSvg += `<text class="sk-col" x="${colX[ci] + nodeW / 2}" y="16" text-anchor="middle">${levelLabel(levels[ci])}</text>`;
    });
    return `<div class="chart-wrap"><svg viewBox="0 0 ${W} ${H}" class="sankey" role="img" aria-label="Diagram Sankey transisi klaster antar level">${links}${nodeSvg}</svg></div>`;
}

function bindSankeyHover() {
    document.querySelectorAll('.sankey [data-tip]').forEach(el => {
        el.addEventListener('mousemove', e => showVizTip(el.dataset.tip, e));
        el.addEventListener('mouseleave', hideVizTip);
    });
}

function renderTransitionTab(r) {
    if (!r.transitions?.length) return '<p class="muted">Data transisi tidak tersedia.</p>';
    const rows = r.transitions.map(t => ({ cells: [
        `${levelLabel(t.from_level)} → ${levelLabel(t.to_level)}`, `${fmtNum(t.stability_rate, 1)}%`, fmtNum(t.ari, 3),
        fmtInt(t.n_moved), `Klaster ${t.dominant_transition.from} → ${t.dominant_transition.to} (${fmtInt(t.dominant_transition.count)})`,
        `${t.active_edges} / ${r.k * (r.k - 1)}`, fmtNum(r.cdvm_vs_baseline?.[t.to_level], 3)
    ] }));
    const t = r.transitions[activeMatrixPair];
    const k = r.k;
    const pairTabs = `<div class="sub-tabs">${r.transitions.map((p, i) =>
        `<button class="sub-tab ${i === activeMatrixPair ? 'active' : ''}" onclick="switchMatrixPair(${i})">${levelLabel(p.from_level)} → ${levelLabel(p.to_level)}</button>`).join('')}</div>`;
    const maxV = Math.max(...t.matrix.flat());
    const mRows = t.matrix.map((row, i) => ({ cells: [
        `${swatch(i)} Klaster ${i}`,
        ...row.map((v, j) => {
            const a = v ? 0.12 + 0.6 * v / maxV : 0;
            return `<span class="cell-val${i === j ? ' diag' : ''}" style="background:rgba(59,130,246,${a.toFixed(2)})">${fmtInt(v)}</span>`;
        })
    ] }));
    return section('Alur Perpindahan Grid Antar Level', 'Setiap pita menunjukkan jumlah grid yang berpindah dari satu klaster ke klaster lain ketika level banjir naik. Arahkan kursor untuk detail.',
                   buildSankey(r))
        + section('Stabilitas Transisi', 'Stability rate = proporsi grid yang tetap pada nomor klaster yang sama; ARI = Adjusted Rand Index antara partisi dua level berurutan.',
                  table(['Transisi', 'Stability Rate', 'ARI', 'Grid berpindah', 'Transisi dominan', 'Edge aktif', 'CDVM vs Baseline'], rows),
                  'CDVM vs Baseline = ½ Σ |p<sub>k</sub>(level) − p<sub>k</sub>(Baseline)|, yaitu besarnya perubahan distribusi ukuran klaster relatif terhadap Baseline.')
        + section('Matriks Transisi', 'Baris = klaster asal, kolom = klaster tujuan. Diagonal = grid yang tetap.',
                  pairTabs + table(['Asal \\ Tujuan', ...Array.from({ length: k }, (_, j) => `Klaster ${j}`)], mRows));
}

// ── Tab: Titik Aman Semu (Tabel 16) ──────────────────────────────────────────
function renderTasTab(r) {
    const rows = LEVELS.map(l => {
        const s = r.levels?.[l.key]?.tas || {};
        const sen = s.sensitivitas_di_absolut || {};
        return { cells: [l.label, fmtInt(s.jumlah_tas), fmtInt(s.jumlah_non_tas), fmtInt(s.jumlah_terputus), `${fmtNum(s.persen_tas)}%`,
                         fmtNum(s.mean_di_tas, 3), fmtNum(s.mean_di_non_tas, 3), fmtNum(s.delta_di, 3), fmtNum(s.p25_t_ideal), fmtNum(s.p75_di, 3),
                         fmtInt(sen.jumlah_tas)] };
    });
    return section('Deteksi Titik Aman Semu (Detour Index)',
        'DI = T<sub>aktual</sub> / T<sub>ideal</sub> (jarak Euclidean minimum 50 m). Pada grid yang terjangkau, TAS bila T<sub>ideal</sub> ≤ persentil ke-25 namun DI ≥ persentil ke-75. Grid dengan T<sub>aktual</sub> = waktu penalti digolongkan <b>Terputus</b> dan tidak ikut persentil maupun rata-rata DI.',
        table(['Level', 'TAS', 'Non-TAS', 'Terputus', '% TAS', 'Rerata DI TAS', 'Rerata DI Non-TAS', 'Selisih DI', 'P25 T<sub>ideal</sub> (mnt)', 'P75 DI', 'TAS (DI ≥ 2)'], rows),
        'Kolom terakhir: uji sensitivitas dengan ambang absolut DI ≥ 2. Pilih tampilan peta "Titik Aman Semu" untuk melihat sebarannya.');
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
    return section('Rata-rata Waktu Tempuh Minimum ke TES', 'Rata-rata waktu tempuh minimum (menit) seluruh grid pada setiap level banjir.',
                   buildBarChart(items, 'menit'))
        + section('Rata-rata Waktu Tempuh per Kategori TES', 'Satuan menit. Grid yang tidak menjangkau TES diberi waktu penalti.',
                  table(['Level', ...Object.values(tesCategories).map(m => m.label), 'Minimum', 'Median Min.'], rows));
}
