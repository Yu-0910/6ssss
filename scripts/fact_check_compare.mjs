#!/usr/bin/env node
/**
 * fact_check_compare.mjs
 * 
 * スクレイピングデータと現在のデータを比較し、抜けている選手を特定するスクリプト
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, '..');

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
        console.error(`❌ エラー: ${filePath} の読み込みに失敗しました:`, error.message);
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

function compareScrapedVsCurrent(year, league, outputDir = null) {
    const scrapedPath = path.join(projectRoot, `_data/master_csv__import_1950_2024/batting_${year}_${league}_from_master.csv`);
    const currentPath = path.join(projectRoot, `_data/master_csv_calculated/batting_${year}_${league}_from_master.csv`);
    
    const result = {
        year,
        league,
        check_date: new Date().toISOString(),
        scraped_exists: fs.existsSync(scrapedPath),
        current_exists: fs.existsSync(currentPath),
        scraped_count: 0,
        current_count: 0,
        missing_players: [],
        team_comparison: {},
        errors: []
    };
    
    if (!result.scraped_exists) {
        const errorMsg = `⚠️ スクレイピングデータが見つかりません: ${scrapedPath}`;
        console.error(errorMsg);
        result.errors.push(errorMsg);
        return result;
    }
    
    if (!result.current_exists) {
        const errorMsg = `⚠️ 現在のデータが見つかりません: ${currentPath}`;
        console.error(errorMsg);
        result.errors.push(errorMsg);
        return result;
    }
    
    // CSVを読み込む
    const scrapedData = parseCSV(scrapedPath);
    const currentData = parseCSV(currentPath);
    
    if (!scrapedData || !currentData) {
        return result;
    }
    
    result.scraped_count = scrapedData.rows.length;
    result.current_count = currentData.rows.length;
    
    console.log(`\n${'='.repeat(60)}`);
    console.log(`=== ${year}年${league}リーグ データ比較 ===`);
    console.log(`${'='.repeat(60)}\n`);
    console.log(`スクレイピングデータ: ${scrapedData.rows.length}件`);
    console.log(`現在のデータ: ${currentData.rows.length}件`);
    console.log(`差分: ${scrapedData.rows.length - currentData.rows.length}件\n`);
    
    // 選手名カラムを探す
    const nameColScraped = findColumn(scrapedData.headers, ['name', '選手']);
    const nameColCurrent = findColumn(currentData.headers, ['name', '選手']);
    
    if (!nameColScraped || !nameColCurrent) {
        const errorMsg = '⚠️ 選手名カラムが見つかりません';
        console.error(errorMsg);
        result.errors.push(errorMsg);
        return result;
    }
    
    console.log(`スクレイピングデータの選手名カラム: ${nameColScraped}`);
    console.log(`現在のデータの選手名カラム: ${nameColCurrent}\n`);
    
    // チーム名カラムを探す
    const teamColScraped = findColumn(scrapedData.headers, ['team', 'チーム']);
    const teamColCurrent = findColumn(currentData.headers, ['team', 'チーム']);
    
    // PAカラムを探す
    const paColScraped = findColumn(scrapedData.headers, ['pa']);
    const paColCurrent = findColumn(currentData.headers, ['pa']);
    
    // 選手名のセットを作成
    const scrapedNames = new Set();
    for (const row of scrapedData.rows) {
        const name = (row[nameColScraped] || '').trim();
        if (name) {
            scrapedNames.add(name);
        }
    }
    
    const currentNames = new Set();
    for (const row of currentData.rows) {
        const name = (row[nameColCurrent] || '').trim();
        if (name) {
            currentNames.add(name);
        }
    }
    
    const missingNames = new Set([...scrapedNames].filter(x => !currentNames.has(x)));
    
    if (missingNames.size > 0) {
        console.log(`⚠️ 現在のデータに存在しない選手: ${missingNames.size}件\n`);
        console.log('抜けている選手:');
        
        const missingPlayersList = [];
        const sortedMissingNames = Array.from(missingNames).sort();
        
        for (let i = 0; i < sortedMissingNames.length; i++) {
            const name = sortedMissingNames[i];
            const playerInfo = { name, team: 'N/A', pa: 'N/A' };
            
            // 該当選手の情報を取得
            for (const row of scrapedData.rows) {
                if ((row[nameColScraped] || '').trim() === name) {
                    if (teamColScraped) {
                        playerInfo.team = row[teamColScraped] || 'N/A';
                    }
                    if (paColScraped) {
                        const paVal = row[paColScraped];
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
        console.log('✅ すべての選手が現在のデータに含まれています\n');
    }
    
    // チーム別選手数の比較
    if (teamColScraped && teamColCurrent) {
        console.log('=== チーム別選手数比較 ===\n');
        
        const scrapedTeams = {};
        for (const row of scrapedData.rows) {
            const team = (row[teamColScraped] || '').trim();
            if (team) {
                scrapedTeams[team] = (scrapedTeams[team] || 0) + 1;
            }
        }
        
        const currentTeams = {};
        for (const row of currentData.rows) {
            const team = (row[teamColCurrent] || '').trim();
            if (team) {
                currentTeams[team] = (currentTeams[team] || 0) + 1;
            }
        }
        
        console.log('スクレイピングデータ:');
        for (const team of Object.keys(scrapedTeams).sort()) {
            console.log(`  ${team}: ${scrapedTeams[team]}件`);
        }
        
        console.log('\n現在のデータ:');
        for (const team of Object.keys(currentTeams).sort()) {
            console.log(`  ${team}: ${currentTeams[team]}件`);
        }
        
        console.log('\nチーム別差分:');
        const teamComparison = {};
        const allTeams = new Set([...Object.keys(scrapedTeams), ...Object.keys(currentTeams)]);
        
        for (const team of Array.from(allTeams).sort()) {
            const scrapedCount = scrapedTeams[team] || 0;
            const currentCount = currentTeams[team] || 0;
            const diff = scrapedCount - currentCount;
            
            teamComparison[team] = {
                scraped: scrapedCount,
                current: currentCount,
                diff: diff
            };
            
            if (diff !== 0) {
                console.log(`  ${team}: ${scrapedCount} → ${currentCount} (差分: ${diff > 0 ? '+' : ''}${diff})`);
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
        
        const outputFile = path.join(outputPath, `fact_check_${year}_${league}.json`);
        fs.writeFileSync(outputFile, JSON.stringify(result, null, 2), 'utf-8');
        console.log(`\n✅ 結果を保存しました: ${outputFile}`);
        
        // CSV形式でも保存（抜けている選手のみ）
        if (result.missing_players.length > 0) {
            const csvFile = path.join(outputPath, `missing_players_${year}_${league}.csv`);
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
    console.error('使用方法: node fact_check_compare.mjs <YEAR> <LEAGUE> [OUTPUT_DIR]');
    console.error('例: node fact_check_compare.mjs 2024 PL');
    console.error('例: node fact_check_compare.mjs 2024 PL output/reports/fact_check');
    process.exit(1);
}

const year = parseInt(args[0]);
const league = args[1].toUpperCase();
const outputDir = args[2] || 'output/reports/fact_check';

const result = compareScrapedVsCurrent(year, league, outputDir);

if (result.errors.length > 0) {
    process.exit(1);
} else {
    process.exit(0);
}

