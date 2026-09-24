// ╔══════════════════════════════════════════════════════════════════════╗
// ║  export.js — Unduh tabel (Excel .xlsx), data grid, dan grafik (PNG)  ║
// ╚══════════════════════════════════════════════════════════════════════╝
function xlsxReady() {
    if (typeof XLSX === 'undefined') {
        showToast('Pustaka Excel belum termuat. Periksa koneksi internet lalu muat ulang halaman.', 'warn');
        return false;
    }
    return true;
}

function fileStamp() {
    const d = new Date();
    const p = n => String(n).padStart(2, '0');
    return `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}`;
}

// "1.234,56" / "45,4%" → angka; teks lain dibiarkan
function parseIdCell(text) {
    const t = String(text).replace(/\s+/g, ' ').trim();
    if (t === '–' || t === '') return null;
    const m = t.match(/^(-?[\d.]+(?:,\d+)?)\s*(?:%|s|mnt|menit)?$/);
    if (m && /^-?\d{1,3}(\.\d{3})*(,\d+)?$|^-?\d+(,\d+)?$/.test(m[1])) {
        return Number(m[1].replace(/\./g, '').replace(',', '.'));
    }
    return t;
}

function tableToAoa(table) {
    return Array.from(table.querySelectorAll('tr')).map(tr =>
        Array.from(tr.children).map((cell, i) => {
            const text = cell.innerText ?? cell.textContent;
            return tr.parentElement.tagName === 'THEAD' ? String(text).replace(/\s+/g, ' ').trim() : parseIdCell(text);
        }));
}

function safeSheetName(name, used) {
    let base = String(name).replace(/[\\/?*[\]:]/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 28) || 'Tabel';
    let n = base, i = 2;
    while (used.has(n)) n = `${base.slice(0, 25)} ${i++}`;
    used.add(n);
    return n;
}

function downloadWorkbook(sheets, filename) {
    if (!xlsxReady()) return;
    const wb = XLSX.utils.book_new();
    const used = new Set();
    sheets.forEach(({ name, aoa }) => {
        const ws = XLSX.utils.aoa_to_sheet(aoa);
        ws['!cols'] = (aoa[0] || []).map((_, c) => ({ wch: Math.min(40, Math.max(8, ...aoa.map(r => String(r[c] ?? '').length))) }));
        XLSX.utils.book_append_sheet(wb, ws, safeSheetName(name, used));
    });
    XLSX.writeFile(wb, filename, { compression: true });
    showToast(`<i class="fa fa-check"></i> ${filename} diunduh.`);
}

// ── Tabel pada panel Hasil Penelitian ────────────────────────────────────────
function exportSectionTable(btn) {
    const sec = btn.closest('.res-section');
    const tables = sec ? sec.querySelectorAll('table.res-table') : [];
    if (!tables.length) return;
    const title = sec.querySelector('h3')?.textContent || 'Tabel';
    downloadWorkbook(Array.from(tables).map((t, i) => ({ name: tables.length > 1 ? `${title} ${i + 1}` : title, aoa: tableToAoa(t) })),
        `${title.replace(/[^\w\-]+/g, '_').replace(/_+/g, '_').replace(/^_|_$/g, '').slice(0, 60)}_${fileStamp()}.xlsx`);
}

function exportAllResults() {
    if (!thesisResults || !xlsxReady()) return;
    const sheets = [];
    const collect = (html, prefix) => {
        const box = document.createElement('div');
        box.innerHTML = html;
        box.querySelectorAll('.res-section').forEach(sec => {
            const title = sec.querySelector('h3')?.textContent || prefix;
            sec.querySelectorAll('table.res-table').forEach(t => sheets.push({ name: title, aoa: tableToAoa(t) }));
        });
    };
    const keepLevel = activeProfileLevel, keepPair = activeMatrixPair;
    collect(renderDataTab(thesisResults), 'Data');
    collect(renderKTab(thesisResults), 'Pemilihan K');
    collect(renderAlgoTab(thesisResults), 'Algoritma');
    LEVELS.forEach(l => { activeProfileLevel = l.key; collect(renderProfileTab(thesisResults), `Profil ${l.label}`); });
    (thesisResults.transitions || []).forEach((t, i) => {
        activeMatrixPair = i;
        const html = renderTransitionTab(thesisResults);
        const box = document.createElement('div'); box.innerHTML = html;
        const secs = box.querySelectorAll('.res-section');
        if (i === 0) secs.forEach((sec, j) => { if (j === 1) sec.querySelectorAll('table.res-table').forEach(tb => sheets.push({ name: 'Stabilitas Transisi', aoa: tableToAoa(tb) })); });
        const last = secs[secs.length - 1];
        last?.querySelectorAll('table.res-table').forEach(tb => sheets.push({ name: `Matriks ${levelLabel(t.from_level)}-${levelLabel(t.to_level)}`, aoa: tableToAoa(tb) }));
    });
    collect(renderTasTab(thesisResults), 'TAS');
    collect(renderWaktuTab(thesisResults), 'Waktu');
    activeProfileLevel = keepLevel; activeMatrixPair = keepPair;
    downloadWorkbook(sheets, `Hasil_Penelitian_Bab_IV_${fileStamp()}.xlsx`);
}

// ── Data per grid & ringkasan wilayah ───────────────────────────────────────
async function exportGridData() {
    if (!gridLayer?.lookup || !xlsxReady()) return;
    await loadGridAdmin();
    const kat = Object.keys(tesCategories);
    const head = ['id_grid', 'Kalurahan', 'Kapanewon', 'Klaster SDWFCM', 'Interpretasi klaster', 'Derajat keanggotaan',
        'Indeks bahaya banjir', 'Terdampak (1=ya)', 'Kerapatan jalan', ...kat.map(k => `Waktu TES ${tesCategories[k].label} (menit)`),
        'Waktu TES minimum (menit)', 'Jumlah opsi rute', 'Terisolasi (1=ya)', 'T ideal (menit)', 'T aktual (menit)', 'Detour Index',
        'Titik Aman Semu (1=ya)', 'Status TAS'];
    const rows = Object.values(gridLayer.lookup).sort((a, b) => a.id_grid - b.id_grid).map(d => {
        const adm = gridAdminName(d.id_grid) || {};
        return [d.id_grid, cleanDesaName(adm.desa), adm.kecamatan ?? null, d.cluster_sdwfcm, getClusterDesc(d.cluster_sdwfcm), d.membership_max,
            d.indeks_bahaya, d.terdampak, d.road_density, ...kat.map(k => d[`waktu_tes_${k}`]), d.waktu_tes_min, d.jumlah_opsi_rute,
            d.is_isolated, d.t_ideal, d.t_aktual, d.detour_index, d.titik_aman_semu,
            ({ 0: 'Non-TAS', 1: 'TAS', 2: 'Terputus' })[d.status_tas] ?? null];
    });
    const sim = lastLevelResult?.simulated ? '_simulasi' : '';
    downloadWorkbook([{ name: `Grid ${levelLabel(activeLevel)}${sim ? ' (simulasi)' : ''}`, aoa: [head, ...rows] }],
        `Data_Grid_Level_${levelLabel(activeLevel)}${sim}_${fileStamp()}.xlsx`);
}

function exportRegionSummary() {
    if (!lastRegionRows.length) { showToast('Buka panel prioritas wilayah terlebih dahulu.', 'warn'); return; }
    const kind = regionKind === 'desa' ? 'Kalurahan' : 'Kapanewon';
    const sim = lastLevelResult?.simulated ? '_simulasi' : '';
    downloadWorkbook([{ name: `${kind} ${levelLabel(activeLevel)}`, aoa: regionSummaryRowsForExport() }],
        `Prioritas_${kind}_Level_${levelLabel(activeLevel)}${sim}_${fileStamp()}.xlsx`);
}

// ── Grafik SVG → PNG ────────────────────────────────────────────────────────
const SVG_STYLE_PROPS = ['fill', 'fill-opacity', 'stroke', 'stroke-width', 'stroke-opacity', 'stroke-dasharray',
    'font-size', 'font-weight', 'font-family', 'text-anchor', 'opacity'];

function exportChartPNG(btn, filename) {
    const svg = btn.closest('.res-section')?.querySelector('svg');
    if (!svg) return;
    const clone = svg.cloneNode(true);
    const src = svg.querySelectorAll('*'), dst = clone.querySelectorAll('*');
    src.forEach((el, i) => {
        const cs = getComputedStyle(el);
        dst[i].setAttribute('style', SVG_STYLE_PROPS.map(p => `${p}:${cs.getPropertyValue(p)}`).join(';'));
    });
    const vb = svg.viewBox.baseVal;
    const scale = 2;
    clone.setAttribute('width', vb.width * scale);
    clone.setAttribute('height', vb.height * scale);
    const bg = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    bg.setAttribute('x', vb.x); bg.setAttribute('y', vb.y); bg.setAttribute('width', vb.width); bg.setAttribute('height', vb.height);
    bg.setAttribute('fill', '#0f172a');
    clone.insertBefore(bg, clone.firstChild);
    const data = new XMLSerializer().serializeToString(clone);
    const img = new Image();
    img.onload = () => {
        const canvas = document.createElement('canvas');
        canvas.width = vb.width * scale; canvas.height = vb.height * scale;
        canvas.getContext('2d').drawImage(img, 0, 0);
        canvas.toBlob(blob => {
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = `${filename}_${fileStamp()}.png`;
            document.body.appendChild(a); a.click(); a.remove();
            setTimeout(() => URL.revokeObjectURL(a.href), 2000);
            showToast(`<i class="fa fa-check"></i> ${a.download} diunduh.`);
        }, 'image/png');
    };
    img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(data);
}
