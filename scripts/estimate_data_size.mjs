#!/usr/bin/env node
/**
 * 年データ（json/csv/ndjson/gz）の実サイズをサンプル年で集計し、
 * 1950-2025 の総容量を推定。R2 移行要否を判定する。
 * 前提: 画像・共通アセットは除外。対象拡張子のみ。実測はファイルシステム。
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = path.resolve(__dirname, '..');

const TARGET_EXT = new Set(['.json', '.csv', '.ndjson', '.gz']);
const YEAR_RANGE = { min: 1950, max: 2025 };
const SPAN_YEARS = YEAR_RANGE.max - YEAR_RANGE.min + 1; // 76
const RANDOM_SEED = 42;
const THRESHOLD_MB_OPTIONAL = 300;
const THRESHOLD_MB_REQUIRED = 1000;

// 野手/投手のパスキーワード（小文字で比較）
const CATEGORY_KEYWORDS = {
  batter: ['batting', '打撃', 'batter', '野手', 'rankings'],
  pitcher: ['pitching', '投手', 'pitcher'],
};

function seededRandom(seed) {
  return function () {
    seed = (seed * 1664525 + 1013904223) >>> 0;
    return seed / 0xffffffff;
  };
}

function isYearDirName(name) {
  return /^\d{4}$/.test(name) && parseInt(name, 10) >= 1900 && parseInt(name, 10) <= 2100;
}

function getCategoryFromPath(relativePath) {
  const lower = relativePath.toLowerCase().replace(/\\/g, '/');
  for (const kw of CATEGORY_KEYWORDS.pitcher) {
    if (lower.includes(kw)) return 'pitcher';
  }
  for (const kw of CATEGORY_KEYWORDS.batter) {
    if (lower.includes(kw)) return 'batter';
  }
  return 'unknown';
}

function collectYearDirsUnder(rootAbs) {
  const years = [];
  try {
    const entries = fs.readdirSync(rootAbs, { withFileTypes: true });
    for (const e of entries) {
      if (e.isDirectory() && isYearDirName(e.name)) {
        years.push(parseInt(e.name, 10));
      }
    }
  } catch (_) {
    // ignore
  }
  return [...new Set(years)].sort((a, b) => a - b);
}

function* walkFiles(dirAbs, rootAbs, extensions) {
  let entries;
  try {
    entries = fs.readdirSync(dirAbs, { withFileTypes: true });
  } catch (_) {
    return;
  }
  for (const e of entries) {
    const full = path.join(dirAbs, e.name);
    const rel = path.relative(rootAbs, full);
    if (e.isDirectory()) {
      yield* walkFiles(full, rootAbs, extensions);
    } else if (e.isFile()) {
      const ext = path.extname(e.name).toLowerCase();
      if (extensions.has(ext)) {
        yield { full, rel, ext };
      }
    }
  }
}

function measureDir(dirAbs, rootAbs, byCategory = false) {
  let totalBytes = 0;
  let fileCount = 0;
  const byCat = { batter: { bytes: 0, count: 0 }, pitcher: { bytes: 0, count: 0 }, unknown: { bytes: 0, count: 0 } };
  for (const { full, rel } of walkFiles(dirAbs, rootAbs, TARGET_EXT)) {
    const stat = fs.statSync(full);
    if (!stat.isFile()) continue;
    totalBytes += stat.size;
    fileCount += 1;
    if (byCategory) {
      const cat = getCategoryFromPath(rel);
      byCat[cat].bytes += stat.size;
      byCat[cat].count += 1;
    }
  }
  return { totalBytes, fileCount, byCat };
}

function findYearDataRoots() {
  const publicData = path.join(PROJECT_ROOT, 'public', 'data');
  const candidates = [];
  try {
    const entries = fs.readdirSync(publicData, { withFileTypes: true });
    for (const e of entries) {
      if (!e.isDirectory()) continue;
      const subPath = path.join(publicData, e.name);
      const years = collectYearDirsUnder(subPath);
      if (years.length > 0) {
        candidates.push({ root: subPath, name: e.name, years });
      }
    }
    // public/data 直下が年ディレクトリの場合
    const yearsAtRoot = collectYearDirsUnder(publicData);
    if (yearsAtRoot.length > 0) {
      candidates.push({ root: publicData, name: 'data', years: yearsAtRoot });
    }
  } catch (_) {
    // no public/data
  }
  return candidates;
}

function pickSampleYears(allYears) {
  if (allYears.length === 0) return [];
  const minY = Math.min(...allYears);
  const maxY = Math.max(...allYears);
  const set = new Set([minY, maxY]);
  if (allYears.includes(1980)) set.add(1980);
  if (allYears.includes(2000)) set.add(2000);
  const remaining = allYears.filter((y) => !set.has(y));
  const rand = seededRandom(RANDOM_SEED);
  for (let i = 0; set.size < 7 && remaining.length > 0; i++) {
    const idx = Math.floor(rand() * remaining.length);
    set.add(remaining.splice(idx, 1)[0]);
  }
  return [...set].sort((a, b) => a - b);
}

function formatMB(bytes) {
  return (bytes / (1024 * 1024)).toFixed(2);
}

function main() {
  const out = [];
  const log = (s) => {
    out.push(s);
    console.log(s);
  };

  log('# 年データ容量推定レポート');
  log('');

  // 1) 年データ格納場所の特定
  const roots = findYearDataRoots();
  if (roots.length === 0) {
    log('対象: public/data 配下に年別ディレクトリが見つかりませんでした。');
    log('public/data/rankings を直接スキャンします。');
    const rankingsPath = path.join(PROJECT_ROOT, 'public', 'data', 'rankings');
    if (fs.existsSync(rankingsPath)) {
      const years = collectYearDirsUnder(rankingsPath);
      roots.push({ root: rankingsPath, name: 'rankings', years });
    }
  }

  if (roots.length === 0) {
    log('エラー: 年データの格納場所がありません。');
    writeEstimateMd(out);
    process.exit(1);
  }

  const allYearsGlobal = [...new Set(roots.flatMap((r) => r.years))].sort((a, b) => a - b);
  const yearsInRange = allYearsGlobal.filter((y) => y >= YEAR_RANGE.min && y <= YEAR_RANGE.max);
  log('## 1) 年データ格納場所');
  for (const r of roots) {
    log(`- \`public/data/${r.name}\` (年: ${r.years.length}件, ${r.years[0]}–${r.years[r.years.length - 1]})`);
  }
  // リーグ・規定分割の検出（代表年で1回）
  const probeYear = roots[0].years.includes(2000) ? 2000 : roots[0].years[Math.floor(roots[0].years.length / 2)];
  const yearDir = path.join(roots[0].root, String(probeYear));
  try {
    const subdirs = fs.readdirSync(yearDir, { withFileTypes: true }).filter((e) => e.isDirectory()).map((e) => e.name);
    log(`- 年あたりの分割（${probeYear}年）: リーグ等 ${subdirs.length} 件 (${subdirs.join(', ')})。規定/非規定は _qualified・_all 等でファイル分岐済みのため、すべて合算して集計。`);
  } catch (_) {}
  log('');

  // 2) サンプル年: 1950, 2025, 中間(1980,2000), ランダム3 (seed固定) = 最大7年（1950-2025に限定）
  const sampleYears = pickSampleYears(yearsInRange.length > 0 ? yearsInRange : allYearsGlobal);
  log('## 2) サンプル年（7年）');
  log(`- 採用: ${sampleYears.join(', ')}`);
  log('');

  // 年度別サイズ（全ルート合算）
  const yearStats = {};
  for (const r of roots) {
    for (const y of r.years) {
      const yearDir = path.join(r.root, String(y));
      if (!fs.existsSync(yearDir)) continue;
      const m = measureDir(yearDir, r.root, true);
      if (!yearStats[y]) {
        yearStats[y] = { bytes: 0, count: 0, byCat: { batter: { bytes: 0, count: 0 }, pitcher: { bytes: 0, count: 0 }, unknown: { bytes: 0, count: 0 } } };
      }
      yearStats[y].bytes += m.totalBytes;
      yearStats[y].count += m.fileCount;
      for (const c of ['batter', 'pitcher', 'unknown']) {
        yearStats[y].byCat[c].bytes += m.byCat[c].bytes;
        yearStats[y].byCat[c].count += m.byCat[c].count;
      }
    }
  }

  const sampleSizes = sampleYears.map((y) => (yearStats[y] ? yearStats[y].bytes : 0));
  const hasPitcher = Object.values(yearStats).some((s) => s.byCat.pitcher.bytes > 0);

  // 3) 推定
  const sortedSizes = sampleSizes.filter((b) => b > 0).sort((a, b) => a - b);
  const n = sortedSizes.length;
  const sum = sortedSizes.reduce((a, b) => a + b, 0);
  const avgPerYear = n > 0 ? sum / n : 0;
  const medianPerYear = n > 0 ? (n % 2 === 1 ? sortedSizes[(n - 1) / 2] : (sortedSizes[n / 2 - 1] + sortedSizes[n / 2]) / 2) : 0;
  const minPerYear = n > 0 ? Math.min(...sortedSizes) : 0;
  const maxPerYear = n > 0 ? Math.max(...sortedSizes) : 0;

  // 1950-2025 の年数でスケール（実在する年のみで平均を取っているので、76年で外挿）
  const estimatedTotalBytes = medianPerYear * SPAN_YEARS;
  const estimatedTotalBytesAvg = avgPerYear * SPAN_YEARS;

  // 4) 現状総量（生成済み全年度）
  let actualTotalBytes = 0;
  let actualFileCount = 0;
  for (const y of Object.keys(yearStats).map(Number)) {
    actualTotalBytes += yearStats[y].bytes;
    actualFileCount += yearStats[y].count;
  }

  // 5)(6) 表・推定・判定・出力
  log('## 3) サンプル年ごとのサイズ（MB）・ファイル数');
  log('| 年 | サイズ(MB) | ファイル数 | 野手相当(MB) | 投手相当(MB) |');
  log('|----|------------|------------|--------------|--------------|');
  for (const y of sampleYears) {
    const s = yearStats[y];
    if (!s) {
      log(`| ${y} | 0.00 | 0 | - | - |`);
      continue;
    }
    const batterMb = (s.byCat.batter.bytes + s.byCat.unknown.bytes) / (1024 * 1024);
    const pitcherMb = s.byCat.pitcher.bytes / (1024 * 1024);
    log(`| ${y} | ${formatMB(s.bytes)} | ${s.count} | ${batterMb.toFixed(2)} | ${pitcherMb.toFixed(2)} |`);
  }
  log('');

  log('## 4) 統計（1年あたり）');
  log(`- 中央値: ${formatMB(medianPerYear)} MB`);
  log(`- 平均:   ${formatMB(avgPerYear)} MB`);
  log(`- 最小:   ${formatMB(minPerYear)} MB`);
  log(`- 最大:   ${formatMB(maxPerYear)} MB`);
  log('');

  log('## 5) 1950–2025 総量推定（76年スケール）');
  const estMB = estimatedTotalBytes / (1024 * 1024);
  const estAvgMB = estimatedTotalBytesAvg / (1024 * 1024);
  log(`- 中央値ベース: ${estMB.toFixed(2)} MB (${(estMB / 1024).toFixed(2)} GB)`);
  log(`- 平均ベース:   ${estAvgMB.toFixed(2)} MB (${(estAvgMB / 1024).toFixed(2)} GB)`);
  log('');

  log('## 6) 現状総量（実測・全年度）');
  const actualMB = actualTotalBytes / (1024 * 1024);
  log(`- 合計: ${actualMB.toFixed(2)} MB (${(actualMB / 1024).toFixed(2)} GB)`);
  log(`- ファイル数: ${actualFileCount}`);
  log('');

  const forJudge = actualTotalBytes > 0 ? actualTotalBytes : estimatedTotalBytes;
  const forJudgeMB = forJudge / (1024 * 1024);
  const pct300 = (forJudgeMB / THRESHOLD_MB_OPTIONAL) * 100;
  const pct1000 = (forJudgeMB / THRESHOLD_MB_REQUIRED) * 100;

  log('## 7) 閾値に対する割合');
  log(`- 300MB に対する割合: ${pct300.toFixed(1)}%`);
  log(`- 1GB に対する割合:   ${pct1000.toFixed(1)}%`);
  log('');

  // 判定
  let necessity = '任意';
  let reason = '';
  if (forJudgeMB > THRESHOLD_MB_REQUIRED) {
    necessity = 'ほぼ必須';
    reason = `年データ総量が ${forJudgeMB.toFixed(0)}MB で 1GB を超えており、Vercel 同梱は現実的でない。`;
  } else if (forJudgeMB > THRESHOLD_MB_OPTIONAL) {
    necessity = '推奨';
    reason = `年データ総量が ${forJudgeMB.toFixed(0)}MB で 300MB を超えており、デプロイ・ビルド負荷と今後の増加を考慮すると R2 移行を推奨する。`;
  } else {
    necessity = '必須ではない（任意・将来の保険）';
    reason = `年データ総量は ${forJudgeMB.toFixed(0)}MB で 300MB 以下。現状は Vercel 同梱も可能だが、年×指標×条件の増加見込みがあれば R2 を推奨。`;
  }

  log('## 8) R2 移行要否');
  log(`- **判定**: ${necessity}`);
  log(`- **理由（データ総量）**: ${reason}`);
  log(`- **理由（運用リスク）**: 年データを Vercel に含めるとデプロイサイズ・ビルド時間が増大し、Function 制限に触れるリスクがある。R2 へ外出しすればアプリ本体のみの軽量デプロイが可能。`);
  log('');
  log('---');
  log('（以上、estimate_data_size.mjs の出力）');

  writeEstimateMd(out);
}

function writeEstimateMd(lines) {
  const mdPath = path.join(PROJECT_ROOT, 'estimates.md');
  try {
    fs.writeFileSync(mdPath, lines.join('\n'), 'utf8');
    console.log(`\nWritten: ${mdPath}`);
  } catch (e) {
    console.error('Could not write estimates.md:', e.message);
  }
}

main();
