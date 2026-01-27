#!/usr/bin/env node
/**
 * fact_check_compare_raw.mjs
 * 
 * 生のスクレイピングデータ（_data/master_csv/）と計算済みデータ（_data/master_csv_calculated/）を比較
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, '..');

// fact_check_compare.mjsと同じロジックを使用
function parseCSV(filePath) {
    try {
        let content = fs.readFileSync(filePath, 'utf-8');
        // BOMを除去
        if (content.charCodeAt(0) === 0xFEFF) {
            content = content.slice(1);
        }
        const lines = content.split('\n').filter(line => line.trim());
        
        if (lines.length < 2) {
            return { headers: [], rows: [] };
        }
        
        // ヘッダー行を解析
        const headers = lines[0].split(',').map(h => h.trim());
        
        // データ行を解析
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

function compareRawVsCalculated(year, league, outputDir = null) {
    // 生のスクレイピングデータ（_data/master_csv/）
    const rawPath = path.join(projectRoot, `_data/master_csv/batting_${year}_${league}_from_master.csv`);
    
    // 計算済みデータ（_data/master_csv_calculated/）
    const calculatedPath = path.join(projectRoot, `_data/master_csv_calculated/batting_${year}_${league}_from_master.csv`);
    
    const result = {
        year,
        league,
        check_date: new Date().toISOString(),
        raw_exists: fs.existsSync(rawPath),
        calculated_exists: fs.existsSync(calculatedPath),
        raw_count: 0,
        calculated_count: 0,
        missing_players: [],
        team_comparison: {},
        errors: []
    };
    
    if (!result.raw_exists) {
        const errorMsg = `⚠️ 生のスクレイピングデータが見つかりません: ${rawPath}`;
        console.error(errorMsg);
        result.errors.push(errorMsg);
        return result;
    }
    
    if (!result.calculated_exists) {
        const errorMsg = `⚠️ 計算済みデータが見つかりません: ${calculatedPath}`;
        console.error(errorMsg);
        result.errors.push(errorMsg);
        return result;
    }
    
    const rawData = parseCSV(rawPath);
    const calculatedData = parseCSV(calculatedPath);
    
    if (!rawData || !calculatedData) {
        return result;
    }
    
    result.raw_count = rawData.rows.length;
    result.calculated_count = calculatedData.rows.length;
    
    console.log(`\n${'='.repeat(60)}`);
    console.log(`=== ${year}年${league}リーグ 生データ vs 計算済みデータ比較 ===`);
    console.log(`${'='.repeat(60)}\n`);
    console.log(`生のスクレイピングデータ（_data/master_csv/）: ${rawData.rows.length}件`);
    console.log(`計算済みデータ（_data/master_csv_calculated/）: ${calculatedData.rows.length}件`);
    console.log(`差分: ${rawData.rows.length - calculatedData.rows.length}件\n`);
    
    // 選手名カラムを探す
    const nameColRaw = findColumn(rawData.headers, ['name', '選手']);
    const nameColCalculated = findColumn(calculatedData.headers, ['name', '選手']);
    
    if (!nameColRaw || !nameColCalculated) {
        const errorMsg = '⚠️ 選手名カラムが見つかりません';
        console.error(errorMsg);
        result.errors.push(errorMsg);
        return result;
    }
    
    console.log(`生データの選手名カラム: ${nameColRaw}`);
    console.log(`計算済みデータの選手名カラム: ${nameColCalculated}\n`);
    
    // チーム名カラムを探す
    const teamColRaw = findColumn(rawData.headers, ['team', 'チーム']);
    const teamColCalculated = findColumn(calculatedData.headers, ['team', 'チーム']);
    
    // PAカラムを探す
    const paColRaw = findColumn(rawData.headers, ['pa']);
    const paColCalculated = findColumn(calculatedData.headers, ['pa']);
    
    // 選手名のセットを作成
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
    
    if (missingNames.size > 0) {
        console.log(`⚠️ 計算済みデータに存在しない選手: ${missingNames.size}件\n`);
        console.log('抜けている選手:');
        
        const missingPlayersList = [];
        const sortedMissingNames = Array.from(missingNames).sort();
        
        for (let i = 0; i < sortedMissingNames.length; i++) {
            const name = sortedMissingNames[i];
            const playerInfo = { name, team: 'N/A', pa: 'N/A' };
            
            // 該当選手の情報を取得
            for (const row of rawData.rows) {
                if ((row[nameColRaw] || '').trim() === name) {
                    if (teamColRaw) {
                        playerInfo.team = row[teamColRaw] || 'N/A';
                    }
                    if (paColRaw) {
                        const paVal = row[paColRaw];
                        if (paVal) {
                            try {
                                playerInfo.pa = parseInt(parseFloat(paVal));
                            } catch {
                                playerInfo.pa = paVal;
                            }
                        }
                    }
                    break;
                }
            }
            
            missingPlayersList.push(playerInfo);
            console.log(`  ${String(i + 1).padStart(3)}. ${name.padEnd(20)} (${playerInfo.team.padEnd(15)}, PA=${playerInfo.pa})`);
        }
        
        result.missing_players = missingPlayersList;
    } else {
        console.log('✅ すべての選手が計算済みデータに含まれています\n');
    }
    
    // チーム別選手数の比較
    if (teamColRaw && teamColCalculated) {
        console.log('=== チーム別選手数比較 ===\n');
        
        const rawTeams = {};
        for (const row of rawData.rows) {
            const team = (row[teamColRaw] || '').trim();
            if (team) {
                rawTeams[team] = (rawTeams[team] || 0) + 1;
            }
        }
        
        const calculatedTeams = {};
        for (const row of calculatedData.rows) {
            const team = (row[teamColCalculated] || '').trim();
            if (team) {
                calculatedTeams[team] = (calculatedTeams[team] || 0) + 1;
            }
        }
        
        console.log('生のスクレイピングデータ:');
        for (const team of Object.keys(rawTeams).sort()) {
            console.log(`  ${team}: ${rawTeams[team]}件`);
        }
        
        console.log('\n計算済みデータ:');
        for (const team of Object.keys(calculatedTeams).sort()) {
            console.log(`  ${team}: ${calculatedTeams[team]}件`);
        }
        
        console.log('\nチーム別差分:');
        const teamComparison = {};
        const allTeams = new Set([...Object.keys(rawTeams), ...Object.keys(calculatedTeams)]);
        
        for (const team of Array.from(allTeams).sort()) {
            const rawCount = rawTeams[team] || 0;
            const calculatedCount = calculatedTeams[team] || 0;
            const diff = rawCount - calculatedCount;
            
            teamComparison[team] = {
                raw: rawCount,
                calculated: calculatedCount,
                diff: diff
            };
            
            if (diff !== 0) {
                console.log(`  ${team}: ${rawCount} → ${calculatedCount} (差分: ${diff > 0 ? '+' : ''}${diff})`);
            }
        }
        
        result.team_comparison = teamComparison;
    }
    
    // 結果をファイルに保存
    if (outputDir) {
        const outputPath = path.join(projectRoot, outputDir);
        if (!fs.existsSync(outputPath)) {
            fs.mkdirSync(outputPath, { recursive: true });
        }
        
        const outputFile = path.join(outputPath, `fact_check_raw_${year}_${league}.json`);
        fs.writeFileSync(outputFile, JSON.stringify(result, null, 2), 'utf-8');
        console.log(`\n✅ 結果を保存しました: ${outputFile}`);
        
        // CSV形式でも保存（抜けている選手のみ）
        if (result.missing_players.length > 0) {
            const csvFile = path.join(outputPath, `missing_players_raw_${year}_${league}.csv`);
            const csvLines = ['name,team,pa'];
            for (const player of result.missing_players) {
                csvLines.push(`${player.name},${player.team},${player.pa}`);
            }
            // BOM付きUTF-8で保存
            const bom = '\uFEFF';
            fs.writeFileSync(csvFile, bom + csvLines.join('\n'), 'utf-8');
            console.log(`✅ 抜けている選手をCSV形式で保存しました: ${csvFile}`);
        }
    }
    
    return result;
}

// メイン処理
const args = process.argv.slice(2);
if (args.length < 2) {
    console.error('使用方法: node fact_check_compare_raw.mjs <YEAR> <LEAGUE> [OUTPUT_DIR]');
    console.error('例: node fact_check_compare_raw.mjs 2024 PL');
    console.error('例: node fact_check_compare_raw.mjs 2024 PL output/reports/fact_check_raw');
    process.exit(1);
}

const year = parseInt(args[0]);
const league = args[1].toUpperCase();
const outputDir = args[2] || 'output/reports/fact_check_raw';

const result = compareRawVsCalculated(year, league, outputDir);

if (result.errors.length > 0) {
    process.exit(1);
} else {
    process.exit(0);
}






