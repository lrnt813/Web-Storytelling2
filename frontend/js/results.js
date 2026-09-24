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

// ── Tab: Pemilihan K (stabilitas) ────────────────────────────────────────────
function renderKTab(r) {
    const ks = r.k_selection || {};
    const rows = (ks.candidates || []).map(c => ({
        k: c.k,
        cells: [c.k, `${fmtNum(c.ari_subsampel_mean, 3)} ± ${fmtNum(c.ari_subsampel_sd, 3)}`,
                `${fmtNum(c.ari_inisialisasi_mean, 3)} ± ${fmtNum(c.ari_inisialisasi_sd, 3)}`,
                fmtNum(c.iidx, 3), `${fmtNum(c.dunn, 4)} ± ${fmtNum(c.dunn_sd, 4)}`, fmtNum(c.ketegasan_partisi, 3),
                fmtNum(c.desc, 3), fmtNum(c.silhouette, 3), fmtNum(c.komposit_dengan_desc, 3), fmtNum(c.komposit_tanpa_desc, 3)]
    }));
    return section('Pemilihan Jumlah Klaster Berbasis Stabilitas (data gabungan)',
        `SDWFCM m = ${r.meta?.sdwfcm?.m}, α = ${r.meta?.sdwfcm?.alpha}, k-NN = ${r.meta?.sdwfcm?.knn}. ARI subsampel: ${ks.B} subsampel ${fmtNum((ks.fraksi_subsampel || 0) * 100, 0)}% id_grid
         (${ks.n_init_subsampel} inisialisasi), dibandingkan dengan solusi data penuh. ARI inisialisasi: rerata ARI berpasangan 10 run (seed 42–51).`,
        table(['K', 'ARI subsampel ↑', 'ARI inisialisasi ↑', 'I-Index', 'Dunn', 'Ketegasan', 'DESC', 'Silhouette', 'Komposit (+DESC)', 'Komposit (−DESC)'], rows,
              { highlight: row => row.k === ks.k_terpilih }),
        `K terpilih: <b>${ks.k_terpilih}</b>. Aturan: K dengan rerata ARI subsampel tertinggi; bila beberapa K berselisih ≤ ${fmtNum(ks.toleransi, 2)}
         dari nilai tertinggi (${fmtNum(ks.ari_subsampel_tertinggi, 3)}), dipilih K terkecil (kandidat: ${(ks.k_dalam_toleransi || []).join(', ')}).
         Metrik pendukung dan skor komposit lama hanya dilaporkan (komposit +DESC memilih K = ${ks.k_komposit_dengan_desc}; −DESC memilih K = ${ks.k_komposit_tanpa_desc}).`);
}

// ── Tab: Perbandingan Algoritma ──────────────────────────────────────────────
function renderAlgoTab(r) {
    const status = a => a.status === 'ok' ? 'layak' : (a.status === 'degeneratif' ? '<b>degeneratif</b> (tidak layak dibandingkan)' : `<b>gagal</b>: ${a.galat || ''}`);
    const rows = (r.algorithm_comparison || []).map(a => ({
        algo: a.algoritma,
        cells: [a.algoritma, status(a), fmtNum(a.silhouette, 3), fmtNum(a.calinski_harabasz, 1), fmtNum(a.davies_bouldin, 3),
                fmtNum(a.moran_i, 3), fmtNum(a.proporsi_tetangga_sama, 3), fmtNum(a.size_entropy, 3),
                a.klaster_terbesar_persen != null ? `${fmtNum(a.klaster_terbesar_persen, 1)}%` : '–', `${fmtNum(a.time_per_init_sec, 2)} s`]
    }));
    if (!rows.length) {
        return section('Perbandingan Algoritma', '', '<p class="muted">Perbandingan algoritma belum dijalankan.</p>');
    }
    return section('Perbandingan Kinerja Algoritma (Baseline, K = ' + r.k + ')',
        'FCM (α = 0), SFCM, dan SDWFCM: praproses, K, 10 inisialisasi (J terkecil), dan aturan penomoran yang sama. REDCAP dan SKATER sebagai pembanding tambahan.',
        table(['Algoritma', 'Status', 'Silhouette ↑', 'Calinski-Harabasz ↑', 'Davies-Bouldin ↓', "Moran's I", 'Tetangga berlabel sama', 'Size Entropy ↑', 'Klaster terbesar', 'Waktu / inisialisasi'], rows,
              { highlight: row => row.algo === 'SDWFCM', leftLast: false }),
        "Moran's I label memakai 999 permutasi (kontiguitas rook). Partisi dengan klaster terbesar > 90% grid ditandai degeneratif.");
}

// ── Tab: Profil Klaster (data gabungan) + distribusi per level ───────────────
function switchProfileLevel(key) { activeProfileLevel = key; renderResultsBody(); }

function renderProfileTab(r) {
    const rows = (r.cluster_profile || []).map(p => {
        const iso = ['pendidikan', 'kesehatan', 'pemerintahan', 'ibadah', 'gor']
            .reduce((a, k) => a + (p[`is_isolated_${k}`] || 0), 0) / 5;
        return { cells: [
            `${swatch(p.klaster)} Klaster ${p.klaster}`, fmtInt(p.jumlah_baris), `${fmtNum(p.persen_baris, 1)}%`,
            fmtNum(p.Road_Density_mean), fmtNum(p.banjir), fmtNum(p.waktu_tes_pendidikan), fmtNum(p.waktu_tes_kesehatan),
            fmtNum(p.waktu_tes_pemerintahan), fmtNum(p.waktu_tes_ibadah), fmtNum(p.waktu_tes_gor), fmtNum(p.waktu_tes_min),
            fmtNum(p.jumlah_opsi_rute), `${fmtNum(iso * 100, 1)}%`, p.deskripsi || ''
        ] };
    });
    const k = r.k;
    const distRows = LEVELS.map(l => {
        const d = r.levels?.[l.key]?.distribusi_tipologi || [];
        return { cells: [l.label, ...d.map(x => `${fmtInt(x.jumlah_grid)} <span class="muted">(${fmtNum(x.persen_semua_grid, 1)}%)</span>`)] };
    });
    return section('Profil Tipologi (data gabungan keempat level)',
            'Rata-rata nilai fitur asli per klaster pada seluruh pasangan grid–level non-Tergenang. Klaster diurutkan dari rata-rata waktu tempuh minimum tercepat (Klaster 0 = akses terbaik). Indeks bahaya hanya deskriptif (bukan fitur klasterisasi).',
            table(['Klaster', 'Baris', '%', 'Kerapatan Jalan', 'Indeks Bahaya', 'Pendidikan', 'Kesehatan', 'Pemerintahan',
                   'Ibadah', 'GOR', 'Waktu Min.', 'Opsi Rute', 'Terisolasi', 'Interpretasi'], rows, { leftLast: true }),
            'Kolom waktu dalam menit. "Terisolasi" = rata-rata proporsi kategori TES yang tidak terjangkau.')
        + section('Distribusi Tipologi per Level', 'Jumlah grid per tipologi dan Tergenang pada setiap level (persentase dari seluruh grid).',
            table(['Level', ...Array.from({ length: k }, (_, j) => `${swatch(j)} Klaster ${j}`), `<i class="legend-swatch" style="background:${TERGENANG_COLOR}"></i> Tergenang`], distRows));
}

// ── Tab: Transisi (Sankey, stabilitas, ARI, CDVM) dengan state Tergenang ─────
function switchMatrixPair(i) { activeMatrixPair = i; renderResultsBody(); }

function stateColor(s, k) { return s === k ? TERGENANG_COLOR : clusterColors[s]; }
function stateName(s, k) { return s === k ? 'Tergenang' : `Klaster ${s}`; }

function buildSankey(r) {
    const k = r.k, S = k + 1;
    const levels = LEVELS.map(l => l.key);
    const counts = levels.map(key => (r.levels[key]?.distribusi_tipologi || []).map(p => p.jumlah_grid));
    const total = counts[0].reduce((a, b) => a + b, 0);
    const W = 880, H = 460, padT = 28, padB = 10, nodeW = 14, gap = 8;
    const padL = 90, padR = 90;
    const colX = levels.map((_, i) => padL + i * (W - padL - padR - nodeW) / (levels.length - 1));
    const scale = (H - padT - padB - gap * (S - 1)) / total;
    const nodes = counts.map((cs, ci) => {
        let y = padT;
        return cs.map((c, j) => { const n = { x: colX[ci], y, h: c * scale, c, k: j }; y += c * scale + gap; return n; });
    });
    let links = '';
    const seq = r.transitions.filter(t => levels.indexOf(t.to_level) === levels.indexOf(t.from_level) + 1);
    seq.forEach((t, ti) => {
        const src = nodes[ti], dst = nodes[ti + 1];
        const outOff = src.map(n => n.y), inOff = dst.map(n => n.y);
        for (let i = 0; i < S; i++) {
            for (let j = 0; j < S; j++) {
                const v = t.matrix[i][j];
                if (!v) continue;
                const h = v * scale;
                const x0 = src[i].x + nodeW, x1 = dst[j].x;
                const y0 = outOff[i], y1 = inOff[j];
                outOff[i] += h; inOff[j] += h;
                const xm = (x0 + x1) / 2;
                const d = `M${x0},${y0} C${xm},${y0} ${xm},${y1} ${x1},${y1} L${x1},${y1 + h} C${xm},${y1 + h} ${xm},${y0 + h} ${x0},${y0 + h} Z`;
                const tip = `${levelLabel(t.from_level)} ${stateName(i, k)} → ${levelLabel(t.to_level)} ${stateName(j, k)}<br><b>${fmtInt(v)}</b> grid (${fmtNum(v / src[i].c * 100, 1)}% dari asal)`;
                links += `<path class="sk-link" d="${d}" fill="${stateColor(j === k ? k : i, k)}" data-tip="${tip.replace(/"/g, '&quot;')}"></path>`;
            }
        }
    });
    let nodeSvg = '';
    nodes.forEach((col, ci) => {
        col.forEach(n => {
            if (!n.c) return;
            const tip = `${levelLabel(levels[ci])} · ${stateName(n.k, k)}<br><b>${fmtInt(n.c)}</b> grid`;
            nodeSvg += `<rect class="sk-node" x="${n.x}" y="${n.y}" width="${nodeW}" height="${Math.max(1, n.h)}" rx="2" fill="${stateColor(n.k, k)}" data-tip="${tip}"></rect>`;
            if (n.h >= 11) {
                const left = ci === 0;
                const tx = left ? n.x - 6 : n.x + nodeW + 4;
                nodeSvg += `<text class="sk-label" x="${tx}" y="${n.y + n.h / 2 + 4}" text-anchor="${left ? 'end' : 'start'}">${n.k === k ? 'Tergenang' : 'K' + n.k}</text>`;
            }
        });
        nodeSvg += `<text class="sk-col" x="${colX[ci] + nodeW / 2}" y="16" text-anchor="middle">${levelLabel(levels[ci])}</text>`;
    });
    return `<div class="chart-wrap"><svg viewBox="0 0 ${W} ${H}" class="sankey" role="img" aria-label="Diagram Sankey transisi tipologi dan Tergenang antar level">${links}${nodeSvg}</svg></div>`;
}

function bindSankeyHover() {
    document.querySelectorAll('.sankey [data-tip]').forEach(el => {
        el.addEventListener('mousemove', e => showVizTip(el.dataset.tip, e));
        el.addEventListener('mouseleave', hideVizTip);
    });
}

function renderTransitionTab(r) {
    if (!r.transitions?.length) return '<p class="muted">Data transisi tidak tersedia.</p>';
    const k = r.k, S = k + 1;
    const rows = r.transitions.map(t => {
        const d = t.dominant_transition;
        return { cells: [
            `${levelLabel(t.from_level)} → ${levelLabel(t.to_level)}`,
            `${fmtInt(t.masuk_tergenang)} (${fmtNum(t.persen_masuk_tergenang_semua_grid, 1)}%)`,
            t.stability_rate != null ? `${fmtNum(t.stability_rate, 1)}%` : '–', fmtNum(t.ari, 3),
            d ? `${stateName(d.from, k)} → ${stateName(d.to, k)} (${fmtInt(d.count)}; ${d.menuju})` : '–',
            `${t.active_edges} / ${S * (S - 1)}`, fmtNum(t.cdvm, 3)
        ] };
    });
    const t = r.transitions[activeMatrixPair];
    const pairTabs = `<div class="sub-tabs">${r.transitions.map((p, i) =>
        `<button class="sub-tab ${i === activeMatrixPair ? 'active' : ''}" onclick="switchMatrixPair(${i})">${levelLabel(p.from_level)} → ${levelLabel(p.to_level)}</button>`).join('')}</div>`;
    const maxV = Math.max(...t.matrix.flat());
    const sw = s => `<i class="legend-swatch" style="background:${stateColor(s, k)}"></i>`;
    const mRows = t.matrix.map((row, i) => ({ cells: [
        `${sw(i)} ${stateName(i, k)}`,
        ...row.map((v, j) => {
            const a = v ? 0.12 + 0.6 * v / maxV : 0;
            return `<span class="cell-val${i === j ? ' diag' : ''}" style="background:rgba(59,130,246,${a.toFixed(2)})">${fmtInt(v)}</span>`;
        })
    ] }));
    return section('Alur Perpindahan Grid Antar Level', 'Setiap pita menunjukkan jumlah grid yang berpindah tipologi atau menjadi Tergenang ketika level banjir naik. Arahkan kursor untuk detail.',
                   buildSankey(r))
        + section('Ringkasan Transisi', 'Stability rate dan ARI dihitung hanya pada grid yang non-Tergenang di kedua level. CDVM = ½ Σ |p<sub>s</sub>(tujuan) − p<sub>s</sub>(asal)| atas state tipologi + Tergenang.',
                  table(['Transisi', 'Masuk Tergenang', 'Stability Rate', 'ARI', 'Transisi dominan (di luar diagonal)', 'Edge aktif', 'CDVM'], rows))
        + section('Matriks Transisi', 'Baris = state asal, kolom = state tujuan. Diagonal = grid yang tetap.',
                  pairTabs + table(['Asal \\ Tujuan', ...Array.from({ length: S }, (_, j) => stateName(j, k))], mRows));
}

// ── Tab: Titik Aman Semu (4 kategori) ────────────────────────────────────────
function renderTasTab(r) {
    const rows = LEVELS.map(l => {
        const s = r.levels?.[l.key]?.tas || {};
        const sen = s.sensitivitas_di_absolut || {};
        return { cells: [l.label, fmtInt(s.jumlah_tas), fmtInt(s.jumlah_non_tas), fmtInt(s.jumlah_terputus), fmtInt(s.jumlah_tergenang),
                         `${fmtNum(s.persen_tas_non_tergenang)}%`, fmtNum(s.mean_di_tas, 3), fmtNum(s.mean_di_non_tas, 3),
                         fmtNum(s.p25_t_ideal), fmtNum(s.p75_di, 3), fmtInt(sen.jumlah_tas),
                         sen.persen_tas_juga_lolos_absolut != null ? `${fmtNum(sen.persen_tas_juga_lolos_absolut, 1)}%` : '–'] };
    });
    return section('Deteksi Titik Aman Semu (Detour Index)',
        'DI = T<sub>aktual</sub> / T<sub>ideal</sub>; keduanya mengukur perjalanan centroid → titik TES (batas minimum 50 m). Grid <b>Tergenang</b> dikeluarkan; grid non-Tergenang yang tidak menjangkau TES = <b>Terputus</b>. Pada sisanya, TAS bila T<sub>ideal</sub> ≤ P25 dan DI ≥ P75.',
        table(['Level', 'TAS', 'Non-TAS', 'Terputus', 'Tergenang', '% TAS (non-Tergenang)', 'Rerata DI TAS', 'Rerata DI Non-TAS', 'P25 T<sub>ideal</sub> (mnt)', 'P75 DI', 'TAS (DI ≥ 2)', 'TAS yang juga DI ≥ 2'], rows),
        'Uji sensitivitas: ambang absolut DI ≥ 2. Pilih tampilan peta "Titik Aman Semu" untuk melihat sebarannya.');
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
