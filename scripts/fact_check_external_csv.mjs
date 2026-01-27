#!/usr/bin/env node
/**
 * fact_check_external_csv.mjs
 * 
 * 外部データソース（手動で取得したCSV）と自分のCSVを比較するスクリプト
 * 
 * 使用方法:
 *   1. NPB公式サイトなどから選手リストをCSV形式で保存
 *   2. node scripts/fact_check_external_csv.mjs <YEAR> <LEAGUE> <EXTERNAL_CSV_PATH>
 * 
 * 例:
 *   node scripts/fact_check_external_csv.mjs 2025 PL external_players_2025_PL.csv
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
        const headers = lines[0].split(',').map(h => h.trim().replace(/^"|"$/g, ''));
        
        const data = [];
        for (let i = 1; i < lines.length; i++) {
            const values = lines[i].split(',').map(v => v.trim().replace(/^"|"$/g, ''));
            const row = {};
            headers.forEach((header, idx) => {
                row[header] = values[idx] || '';
            });
            if (Object.values(row).some(v => v)) { // 空行でない場合のみ
                data.push(row);
            }
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

function normalizeName(name) {
    if (!name) return '';
    // 全角スペース、半角スペース、・などを除去
    return name.replace(/[　\s・]+/g, '').trim();
}

function main() {
    const args = process.argv.slice(2);
    if (args.length < 3) {
        console.log('使用方法: node fact_check_external_csv.mjs <YEAR> <LEAGUE> <EXTERNAL_CSV_PATH>');
        console.log('例: node fact_check_external_csv.mjs 2025 PL external_players_2025_PL.csv');
        console.log('');
        console.log('外部CSVファイルの形式:');
        console.log('  - player_id, name, team のいずれかのカラムが必要');
        console.log('  - または player_id のみでも可');
        process.exit(1);
    }
    
    const year = parseInt(args[0]);
    const league = args[1].toUpperCase();
    const externalCsvPath = args[2];
    
    console.log(`\n${'='.repeat(60)}`);
    console.log(`=== 外部データソースとのファクトチェック ===`);
    console.log(`${'='.repeat(60)}\n`);
    console.log(`年度: ${year}`);
    console.log(`リーグ: ${league}`);
    console.log(`外部CSV: ${externalCsvPath}`);
    
    // 対象CSVファイル
    const targetCsvPath = path.join(
        projectRoot,
        '_data',
        'master_csv_calculated',
        `batting_${year}_${league}_from_master.csv`
    );
    
    console.log(`対象CSV: ${targetCsvPath}\n`);
    
    // 外部CSVを読み込む
    console.log(`📖 外部CSVファイルを読み込み中...`);
    const externalCsv = loadCSV(externalCsvPath);
    
    if (!externalCsv) {
        console.error(`❌ 外部CSVファイルが見つかりません: ${externalCsvPath}`);
        process.exit(1);
    }
    
    console.log(`✅ 外部CSVを読み込みました: ${externalCsv.data.length}行\n`);
    
    // 対象CSVを読み込む
    console.log(`📖 対象CSVファイルを読み込み中...`);
    const targetCsv = loadCSV(targetCsvPath);
    
    if (!targetCsv) {
        console.error(`❌ 対象CSVファイルが見つかりません: ${targetCsvPath}`);
        process.exit(1);
    }
    
    console.log(`✅ 対象CSVを読み込みました: ${targetCsv.data.length}行\n`);
    
    // カラムを特定
    const externalPlayerIdCol = findColumn(externalCsv, [['player_id'], ['id']]);
    const externalNameCol = findColumn(externalCsv, [['name'], ['player_name'], ['選手名']]);
    const externalTeamCol = findColumn(externalCsv, [['team'], ['チーム']]);
    
    const targetPlayerIdCol = findColumn(targetCsv, [['player_id']]);
    const targetNameCol = findColumn(targetCsv, [['player_name_ja'], ['name_ja'], ['name']]);
    const targetTeamCol = findColumn(targetCsv, [['team']]);
    
    if (!externalPlayerIdCol && !externalNameCol) {
        console.error('❌ 外部CSVにplayer_idまたはnameカラムが見つかりません');
        process.exit(1);
    }
    
    if (!targetPlayerIdCol) {
        console.error('❌ 対象CSVにplayer_idカラムが見つかりません');
        process.exit(1);
    }
    
    // 外部CSVからplayer_idまたはnameのセットを作成
    const externalPlayers = new Map();
    for (const row of externalCsv.data) {
        const playerId = externalPlayerIdCol ? row[externalPlayerIdCol] : '';
        const name = externalNameCol ? row[externalNameCol] : '';
        const team = externalTeamCol ? row[externalTeamCol] : '';
        
        if (playerId || name) {
            const key = playerId || normalizeName(name);
            externalPlayers.set(key, {
                player_id: playerId,
                name: name,
                team: team
            });
        }
    }
    
    // 対象CSVからplayer_idのセットを作成
    const targetPlayers = new Map();
    for (const row of targetCsv.data) {
        const playerId = row[targetPlayerIdCol];
        const name = row[targetNameCol] || '';
        const team = row[targetTeamCol] || '';
        
        if (playerId && playerId !== 'nan' && playerId !== '') {
            targetPlayers.set(playerId, {
                player_id: playerId,
                name: name,
                team: team
            });
        }
    }
    
    // 比較
    const missingInTarget = [];
    const matched = [];
    
    for (const [key, player] of externalPlayers) {
        if (player.player_id && targetPlayers.has(player.player_id)) {
            matched.push(player);
        } else if (!player.player_id && targetNameCol) {
            // player_idがない場合は名前で比較
            const normName = normalizeName(player.name);
            let found = false;
            for (const [targetId, targetPlayer] of targetPlayers) {
                if (normalizeName(targetPlayer.name) === normName) {
                    matched.push(player);
                    found = true;
                    break;
                }
            }
            if (!found) {
                missingInTarget.push(player);
            }
        } else {
            missingInTarget.push(player);
        }
    }
    
    // 結果を表示
    console.log(`${'='.repeat(60)}`);
    console.log(`=== 比較結果 ===`);
    console.log(`${'='.repeat(60)}\n`);
    console.log(`外部データソース: ${externalPlayers.size}人`);
    console.log(`対象CSV: ${targetPlayers.size}人`);
    console.log(`一致: ${matched.length}人`);
    console.log(`対象CSVに不足: ${missingInTarget.length}人\n`);
    
    if (missingInTarget.length > 0) {
        console.log(`⚠️ 対象CSVに存在しない選手 (${missingInTarget.length}人):\n`);
        missingInTarget.slice(0, 50).forEach((player, i) => {
            const id = player.player_id || 'N/A';
            const name = player.name || 'N/A';
            const team = player.team || 'N/A';
            console.log(`  ${(i + 1).toString().padStart(3)}. ${id.padEnd(10)} - ${name.padEnd(20)} (${team})`);
        });
        if (missingInTarget.length > 50) {
            console.log(`  ... 他 ${missingInTarget.length - 50}件`);
        }
        
        // CSV形式で保存
        const outputDir = path.join(projectRoot, 'output', 'reports', 'fact_check');
        if (!fs.existsSync(outputDir)) {
            fs.mkdirSync(outputDir, { recursive: true });
        }
        
        const outputFile = path.join(outputDir, `missing_players_${year}_${league}_external.csv`);
        const csvContent = [
            'player_id,name,team',
            ...missingInTarget.map(p => 
                `"${p.player_id || ''}","${p.name || ''}","${p.team || ''}"`
            )
        ].join('\n');
        
        fs.writeFileSync(outputFile, csvContent, 'utf-8-sig');
        console.log(`\n✅ 不足している選手をCSV形式で保存しました: ${outputFile}`);
    } else {
        console.log('✅ すべての選手が対象CSVに含まれています\n');
    }
    
    // 結果をJSON形式で保存
    const outputDir = path.join(projectRoot, 'output', 'reports', 'fact_check');
    if (!fs.existsSync(outputDir)) {
        fs.mkdirSync(outputDir, { recursive: true });
    }
    
    const resultJson = {
        year: year,
        league: league,
        check_date: new Date().toISOString(),
        external_count: externalPlayers.size,
        target_count: targetPlayers.size,
        matched_count: matched.length,
        missing_in_target: missingInTarget
    };
    
    const jsonFile = path.join(outputDir, `fact_check_${year}_${league}_external.json`);
    fs.writeFileSync(jsonFile, JSON.stringify(resultJson, null, 2), 'utf-8');
    console.log(`✅ 結果をJSON形式で保存しました: ${jsonFile}\n`);
    
    if (missingInTarget.length > 0) {
        process.exit(1);
    } else {
        process.exit(0);
    }
}

main();




