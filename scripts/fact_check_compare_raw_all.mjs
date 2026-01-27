#!/usr/bin/env node
/**
 * fact_check_compare_raw_all.mjs
 * 
 * 全年度・全リーグの生データ（_data/master_csv/）と計算済みデータ（_data/master_csv_calculated/）を一括比較
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, '..');

// fact_check_compare_raw.mjsと同じロジックを使用
function parseCSV(filePath) {
    try {
        let content = fs.readFileSync(filePath, 'utf-8');
        if (content.charCodeAt(0) === 0xFEFF) {
            content = content.slice(1);
        }
        const lines = content.split('\n').filter(line => line.trim());
        
        if (lines.length < 2) {
            return { headers: [], rows: [] };
        }
        
        const headers = lines[0].split(',').map(h => h.trim());
        const rows = [];
        for (let i = 1; i < lines.length; i++) {
            const values = lines[i].split(',').map(v => v.trim());
            const row = {};
            headers.forEach((header, idx) => {
                row[header] = values[idx] || '';
            });
            rows.push(row);
        }
        
        return { headers, rows };
    } catch (error) {
        return null;
    }
}

function findColumn(headers, keywords) {
    for (const header of headers) {
        const headerLower = header.toLowerCase();
        for (const keyword of keywords) {
            if (headerLower.includes(keyword)) {
                return header;
            }
        }
    }
    return null;
}

function compareRawVsCalculated(year, league) {
    const rawPath = path.join(projectRoot, `_data/master_csv/batting_${year}_${league}_from_master.csv`);
    const calculatedPath = path.join(projectRoot, `_data/master_csv_calculated/batting_${year}_${league}_from_master.csv`);
    
    if (!fs.existsSync(rawPath) || !fs.existsSync(calculatedPath)) {
        return { exists: false };
    }
    
    const rawData = parseCSV(rawPath);
    const calculatedData = parseCSV(calculatedPath);
    
    if (!rawData || !calculatedData) {
        return { exists: true, error: true };
    }
    
    const nameColRaw = findColumn(rawData.headers, ['name', '選手']);
    const nameColCalculated = findColumn(calculatedData.headers, ['name', '選手']);
    
    if (!nameColRaw || !nameColCalculated) {
        return { exists: true, error: true };
    }
    
    const rawNames = new Set();
    for (const row of rawData.rows) {
        const name = (row[nameColRaw] || '').trim();
        if (name) {
            rawNames.add(name);
        }
    }
    
    const calculatedNames = new Set();
    for (const row of calculatedData.rows) {
        const name = (row[nameColCalculated] || '').trim();
        if (name) {
            calculatedNames.add(name);
        }
    }
    
    const missingNames = new Set([...rawNames].filter(x => !calculatedNames.has(x)));
    
    return {
        exists: true,
        rawCount: rawData.rows.length,
        calculatedCount: calculatedData.rows.length,
        missingCount: missingNames.size,
        missingNames: Array.from(missingNames)
    };
}

// メイン処理
const rawDir = path.join(projectRoot, '_data/master_csv');
const outputDir = path.join(projectRoot, 'output/reports/fact_check_raw');

// 生データのファイル一覧を取得
const files = fs.readdirSync(rawDir).filter(f => f.startsWith('batting_') && f.endsWith('_from_master.csv'));

// 年度とリーグを抽出
const yearLeagueSet = new Set();
for (const file of files) {
    const match = file.match(/batting_(\d+)_(PL|CL)_from_master\.csv/);
    if (match) {
        const year = parseInt(match[1]);
        const league = match[2];
        yearLeagueSet.add(`${year},${league}`);
    }
}

// 年度順にソート
const yearLeagueList = Array.from(yearLeagueSet)
    .map(item => {
        const [year, league] = item.split(',');
        return { year: parseInt(year), league };
    })
    .sort((a, b) => {
        if (a.year !== b.year) {
            return a.year - b.year;
        }
        return a.league.localeCompare(b.league);
    });

console.log(`\n${'='.repeat(60)}`);
console.log(`全年度・全リーグの生データ vs 計算済みデータ比較を開始します`);
console.log(`対象: ${yearLeagueList.length}件の年度・リーグ`);
console.log(`${'='.repeat(60)}\n`);

const results = [];
let successCount = 0;
let errorCount = 0;
let missingPlayersTotal = 0;
let notFoundCount = 0;

for (const { year, league } of yearLeagueList) {
    const result = compareRawVsCalculated(year, league);
    
    if (!result.exists) {
        notFoundCount++;
        results.push({
            year,
            league,
            status: 'not_found',
            missingCount: 0
        });
        continue;
    }
    
    if (result.error) {
        errorCount++;
        results.push({
            year,
            league,
            status: 'error',
            missingCount: 0
        });
        continue;
    }
    
    if (result.missingCount > 0) {
        missingPlayersTotal += result.missingCount;
        results.push({
            year,
            league,
            status: 'missing',
            missingCount: result.missingCount,
            rawCount: result.rawCount,
            calculatedCount: result.calculatedCount
        });
        console.log(`⚠️ ${year}年${league}リーグ: 抜けている選手 ${result.missingCount}件 (生データ: ${result.rawCount}件, 計算済み: ${result.calculatedCount}件)`);
    } else {
        successCount++;
        results.push({
            year,
            league,
            status: 'ok',
            missingCount: 0,
            rawCount: result.rawCount,
            calculatedCount: result.calculatedCount
        });
    }
}

// サマリーを生成
console.log(`\n${'='.repeat(60)}`);
console.log(`チェック完了`);
console.log(`${'='.repeat(60)}\n`);
console.log(`総チェック数: ${yearLeagueList.length}件`);
console.log(`✅ 正常: ${successCount}件`);
console.log(`⚠️ 抜けている選手あり: ${results.filter(r => r.status === 'missing').length}件`);
console.log(`❌ エラー: ${errorCount}件`);
console.log(`📂 データなし: ${notFoundCount}件`);
console.log(`📊 抜けている選手の合計: ${missingPlayersTotal}件\n`);

// 抜けている選手がある年度・リーグをリストアップ
const missingList = results.filter(r => r.status === 'missing');
if (missingList.length > 0) {
    console.log('⚠️ 抜けている選手がある年度・リーグ:');
    for (const item of missingList) {
        console.log(`  ${item.year}年${item.league}リーグ: ${item.missingCount}件 (生データ: ${item.rawCount}件 → 計算済み: ${item.calculatedCount}件)`);
    }
    console.log('');
}

// 結果をJSONファイルに保存
const summaryFile = path.join(outputDir, 'fact_check_raw_all_summary.json');
const summary = {
    check_date: new Date().toISOString(),
    total_checks: yearLeagueList.length,
    success_count: successCount,
    missing_count: missingList.length,
    error_count: errorCount,
    not_found_count: notFoundCount,
    missing_players_total: missingPlayersTotal,
    results: results
};

fs.mkdirSync(outputDir, { recursive: true });
fs.writeFileSync(summaryFile, JSON.stringify(summary, null, 2), 'utf-8');
console.log(`✅ サマリーを保存しました: ${summaryFile}`);

// マークダウンレポートも生成
const mdFile = path.join(outputDir, 'fact_check_raw_all_summary.md');
let mdContent = `# 全年度・全リーグ 生データ vs 計算済みデータ 比較結果サマリー\n\n`;
mdContent += `## 📋 チェック実施日時\n`;
mdContent += `${new Date().toISOString()}\n\n`;
mdContent += `## 📊 チェック結果\n\n`;
mdContent += `- **総チェック数**: ${yearLeagueList.length}件\n`;
mdContent += `- **✅ 正常**: ${successCount}件\n`;
mdContent += `- **⚠️ 抜けている選手あり**: ${missingList.length}件\n`;
mdContent += `- **❌ エラー**: ${errorCount}件\n`;
mdContent += `- **📂 データなし**: ${notFoundCount}件\n`;
mdContent += `- **📊 抜けている選手の合計**: ${missingPlayersTotal}件\n\n`;

mdContent += `## 📝 データソース\n\n`;
mdContent += `- **生データ**: \`_data/master_csv/\` （スクレイピングした元データ）\n`;
mdContent += `- **計算済みデータ**: \`_data/master_csv_calculated/\` （指標計算処理後のデータ）\n\n`;

if (missingList.length > 0) {
    mdContent += `## ⚠️ 抜けている選手がある年度・リーグ\n\n`;
    mdContent += `| 年度 | リーグ | 抜けている選手数 | 生データ | 計算済み |\n`;
    mdContent += `|------|--------|------------------|----------|----------|\n`;
    for (const item of missingList) {
        mdContent += `| ${item.year} | ${item.league} | ${item.missingCount}件 | ${item.rawCount}件 | ${item.calculatedCount}件 |\n`;
    }
    mdContent += `\n`;
}

mdContent += `## 📝 詳細結果\n\n`;
mdContent += `各年度・リーグの詳細なチェック結果は、以下のJSONファイルに保存されています：\n\n`;
mdContent += `- \`fact_check_raw_{YEAR}_{LEAGUE}.json\`: 詳細な比較結果\n`;
mdContent += `- \`missing_players_raw_{YEAR}_{LEAGUE}.csv\`: 抜けている選手のリスト（該当する場合のみ）\n\n`;

fs.writeFileSync(mdFile, mdContent, 'utf-8');
console.log(`✅ マークダウンレポートを保存しました: ${mdFile}`);






