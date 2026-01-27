#!/usr/bin/env node
/**
 * fact_check_by_year_league.mjs
 * 
 * 既存のCSVファイルから年度・リーグ別のplayer_idを抽出し、
 * 指定年度・リーグのCSVと比較するスクリプト
 * 
 * 使用方法:
 *   node scripts/fact_check_by_year_league.mjs <YEAR> <LEAGUE>
 * 例:
 *   node scripts/fact_check_by_year_league.mjs 2025 PL
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, '..');

function loadCSV(csvPath) {
    if (!fs.existsSync(csvPath)) {
        return null;
    }
    
    try {
        let content = fs.readFileSync(csvPath, 'utf-8');
        // BOMを除去
        if (content.charCodeAt(0) === 0xFEFF) {
            content = content.slice(1);
        }
        const lines = content.split('\n').filter(line => line.trim());
        const headers = lines[0].split(',');
        
        const data = [];
        for (let i = 1; i < lines.length; i++) {
            const values = lines[i].split(',');
            const row = {};
            headers.forEach((header, idx) => {
                row[header.trim()] = values[idx]?.trim() || '';
            });
            data.push(row);
        }
        
        return { headers, data };
    } catch (error) {
        console.error(`❌ CSV読み込みエラー: ${error.message}`);
        return null;
    }
}

function findColumn(csv, patterns) {
    for (const pattern of patterns) {
        const index = csv.headers.findIndex(h => 
            pattern.some(p => h.toLowerCase().includes(p.toLowerCase()))
        );
        if (index !== -1) {
            return csv.headers[index];
        }
    }
    return null;
}

function main() {
    const args = process.argv.slice(2);
    if (args.length < 2) {
        console.log('使用方法: node fact_check_by_year_league.mjs <YEAR> <LEAGUE>');
        console.log('例: node fact_check_by_year_league.mjs 2025 PL');
        process.exit(1);
    }
    
    const year = parseInt(args[0]);
    const league = args[1].toUpperCase();
    
    console.log(`\n${'='.repeat(60)}`);
    console.log(`=== 年度・リーグ別ファクトチェック ===`);
    console.log(`${'='.repeat(60)}\n`);
    console.log(`年度: ${year}`);
    console.log(`リーグ: ${league}\n`);
    
    // 対象CSVファイル
    const targetCsvPath = path.join(
        projectRoot,
        '_data',
        'master_csv_calculated',
        `batting_${year}_${league}_from_master.csv`
    );
    
    console.log(`📖 対象CSVファイル: ${targetCsvPath}`);
    const targetCsv = loadCSV(targetCsvPath);
    
    if (!targetCsv) {
        console.error(`❌ CSVファイルが見つかりません: ${targetCsvPath}`);
        process.exit(1);
    }
    
    // カラムを特定
    const playerIdCol = findColumn(targetCsv, [['player_id']]);
    const nameCol = findColumn(targetCsv, [['player_name_ja'], ['name_ja'], ['name']]);
    const teamCol = findColumn(targetCsv, [['team']]);
    const yearCol = findColumn(targetCsv, [['year']]);
    const leagueCol = findColumn(targetCsv, [['league']]);
    
    if (!playerIdCol) {
        console.error('❌ player_idカラムが見つかりません');
        process.exit(1);
    }
    
    console.log(`✅ CSVファイルを読み込みました: ${targetCsv.data.length}行\n`);
    
    // 対象年度・リーグのplayer_idを抽出
    const targetPlayerIds = new Set();
    const targetPlayers = [];
    
    for (const row of targetCsv.data) {
        const rowYear = yearCol ? parseInt(row[yearCol]) : year;
        const rowLeague = leagueCol ? row[leagueCol].toUpperCase() : league;
        
        // 年度・リーグが一致する場合のみ
        if (rowYear === year && rowLeague === league) {
            const playerId = row[playerIdCol];
            if (playerId && playerId !== 'nan' && playerId !== '') {
                targetPlayerIds.add(playerId);
                targetPlayers.push({
                    player_id: playerId,
                    name: row[nameCol] || '',
                    team: row[teamCol] || ''
                });
            }
        }
    }
    
    console.log(`📊 対象年度・リーグの選手数: ${targetPlayerIds.size}人\n`);
    
    // 他の年度・リーグのCSVファイルから同じ年度・リーグの選手を探す
    const csvDir = path.join(projectRoot, '_data', 'master_csv_calculated');
    const allFiles = fs.readdirSync(csvDir).filter(f => 
        f.startsWith(`batting_${year}_${league}_`) && f.endsWith('.csv')
    );
    
    console.log(`🔍 同じ年度・リーグのCSVファイルを検索中...`);
    console.log(`   見つかったファイル: ${allFiles.length}件\n`);
    
    // 参照用CSV（スクレイピングデータ）を確認
    const scrapedDir = path.join(projectRoot, '_data', 'master_csv__import_1950_2024');
    const scrapedFile = `batting_${year}_${league}_from_master.csv`;
    const scrapedPath = path.join(scrapedDir, scrapedFile);
    
    if (fs.existsSync(scrapedPath)) {
        console.log(`📖 参照用CSV（スクレイピングデータ）を読み込み中...`);
        const scrapedCsv = loadCSV(scrapedPath);
        
        if (scrapedCsv) {
            const scrapedPlayerIdCol = findColumn(scrapedCsv, [['player_id']]);
            const scrapedNameCol = findColumn(scrapedCsv, [['player_name_ja'], ['name_ja'], ['name']]);
            const scrapedTeamCol = findColumn(scrapedCsv, [['team']]);
            
            const scrapedPlayerIds = new Set();
            const scrapedPlayers = [];
            
            for (const row of scrapedCsv.data) {
                const playerId = scrapedPlayerIdCol ? row[scrapedPlayerIdCol] : '';
                if (playerId && playerId !== 'nan' && playerId !== '') {
                    scrapedPlayerIds.add(playerId);
                    scrapedPlayers.push({
                        player_id: playerId,
                        name: row[scrapedNameCol] || '',
                        team: row[scrapedTeamCol] || ''
                    });
                }
            }
            
            console.log(`✅ 参照用CSVから ${scrapedPlayerIds.size}人の選手を読み込みました\n`);
            
            // 比較
            const missingInTarget = [];
            for (const playerId of scrapedPlayerIds) {
                if (!targetPlayerIds.has(playerId)) {
                    const player = scrapedPlayers.find(p => p.player_id === playerId);
                    if (player) {
                        missingInTarget.push(player);
                    }
                }
            }
            
            const extraInTarget = [];
            for (const playerId of targetPlayerIds) {
                if (!scrapedPlayerIds.has(playerId)) {
                    const player = targetPlayers.find(p => p.player_id === playerId);
                    if (player) {
                        extraInTarget.push(player);
                    }
                }
            }
            
            // 結果を表示
            console.log(`${'='.repeat(60)}`);
            console.log(`=== 比較結果 ===`);
            console.log(`${'='.repeat(60)}\n`);
            console.log(`参照用CSV（スクレイピング）: ${scrapedPlayerIds.size}人`);
            console.log(`対象CSV: ${targetPlayerIds.size}人`);
            console.log(`一致: ${scrapedPlayerIds.size - missingInTarget.length}人`);
            console.log(`対象CSVに不足: ${missingInTarget.length}人`);
            console.log(`対象CSVにのみ存在: ${extraInTarget.length}人\n`);
            
            if (missingInTarget.length > 0) {
                console.log(`⚠️ 対象CSVに存在しない選手 (${missingInTarget.length}人):\n`);
                missingInTarget.slice(0, 30).forEach((player, i) => {
                    console.log(`  ${(i + 1).toString().padStart(3)}. ${player.player_id.padEnd(10)} - ${player.name.padEnd(20)} (${player.team})`);
                });
                if (missingInTarget.length > 30) {
                    console.log(`  ... 他 ${missingInTarget.length - 30}件`);
                }
                
                // CSV形式で保存
                const outputDir = path.join(projectRoot, 'output', 'reports', 'fact_check');
                if (!fs.existsSync(outputDir)) {
                    fs.mkdirSync(outputDir, { recursive: true });
                }
                
                const outputFile = path.join(outputDir, `missing_players_${year}_${league}.csv`);
                const csvContent = [
                    'player_id,name,team',
                    ...missingInTarget.map(p => 
                        `"${p.player_id}","${p.name}","${p.team}"`
                    )
                ].join('\n');
                
                fs.writeFileSync(outputFile, csvContent, 'utf-8-sig');
                console.log(`\n✅ 不足している選手をCSV形式で保存しました: ${outputFile}`);
            } else {
                console.log('✅ すべての選手が対象CSVに含まれています\n');
            }
        }
    } else {
        console.log(`⚠️ 参照用CSVが見つかりません: ${scrapedPath}`);
        console.log(`   対象CSVのみの情報を表示します:\n`);
        console.log(`対象CSVの選手数: ${targetPlayerIds.size}人`);
        console.log(`チーム別選手数:`);
        
        const teamCounts = {};
        for (const player of targetPlayers) {
            const team = player.team || '不明';
            teamCounts[team] = (teamCounts[team] || 0) + 1;
        }
        
        Object.entries(teamCounts).sort().forEach(([team, count]) => {
            console.log(`  ${team}: ${count}人`);
        });
    }
    
    console.log('');
}

main();

