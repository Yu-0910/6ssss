#!/usr/bin/env node
/**
 * fact_check_npb_all_years.mjs
 * 
 * NPB公式サイトから全年度・全リーグの選手名を取得し、
 * 既存CSVと比較するスクリプト
 * 
 * 取得できなかった選手も記録し、誤判定を防ぐ
 * 
 * 使用方法:
 *   node scripts/fact_check_npb_all_years.mjs [--year YEAR] [--league LEAGUE]
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import https from 'https';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, '..');

// 全年度・全リーグのリスト
const YEARS = [];
for (let y = 1950; y <= 2025; y++) {
    YEARS.push(y);
}
const LEAGUES = ['CL', 'PL'];

function fetchHTML(url) {
    return new Promise((resolve, reject) => {
        https.get(url, { timeout: 30000 }, (res) => {
            let data = '';
            res.on('data', (chunk) => { data += chunk; });
            res.on('end', () => {
                let text = data;
                try {
                    text = Buffer.from(data, 'binary').toString('utf-8');
                } catch (e) {
                    // そのまま
                }
                resolve({ html: text, status: res.statusCode });
            });
        }).on('error', (err) => {
            reject(err);
        });
    });
}

function extractPlayersFromNPB(html, year, league) {
    const players = [];
    try {
        // 正規表現で選手名のリンクを探す
        const linkPattern = /<a[^>]*href=["']([^"']*\/bis\/players\/(\d+)[^"']*)["'][^>]*>([^<]+)<\/a>/gi;
        
        let match;
        const seen = new Set();
        
        while ((match = linkPattern.exec(html)) !== null) {
            const href = match[1];
            const playerId = match[2];
            const playerName = match[3].trim();
            
            if (playerName && playerName.length > 0 && playerName.length < 50) {
                const key = playerId || playerName;
                if (!seen.has(key)) {
                    seen.add(key);
                    players.push({
                        name: playerName,
                        player_id: playerId,
                        source: 'NPB_OFFICIAL'
                    });
                }
            }
        }
        
        return players;
    } catch (error) {
        console.error(`HTML解析エラー (${year} ${league}):`, error.message);
        return [];
    }
}

function getNPBURL(year, league) {
    const leagueLower = league.toLowerCase();
    // 複数のURLパターンを試す
    // NPB公式サイトの実際のURL構造に基づく
    return [
        `https://npb.jp/bis/${year}/stats/${leagueLower}/batting.html`,
        `https://npb.jp/bis/stats/${year}/${leagueLower}/batting.html`,
        `https://npb.jp/bis/${year}/stats/${leagueLower}/batting/`,
        `https://npb.jp/bis/stats/${year}/${leagueLower}/batting/`,
        `https://npb.jp/bis/stats/${year}/${leagueLower}/`,
        // 年度別成績ページから取得を試みる
        `https://npb.jp/bis/${year}/stats/`,
    ];
}

async function fetchPlayersFromNPB(year, league) {
    const urls = getNPBURL(year, league);
    
    for (const url of urls) {
        try {
            const { html, status } = await fetchHTML(url);
            
            if (status === 200) {
                const players = extractPlayersFromNPB(html, year, league);
                if (players.length > 0) {
                    return {
                        success: true,
                        players: players,
                        url: url,
                        status: status
                    };
                }
            }
        } catch (error) {
            // 次のURLを試す
            continue;
        }
    }
    
    return {
        success: false,
        players: [],
        url: urls[0],
        status: 0,
        error: 'ALL_URLS_FAILED'
    };
}

function loadAllPlayerIds() {
    const playerIdsPath = path.join(projectRoot, 'output', 'master', 'all_player_ids.csv');
    
    if (!fs.existsSync(playerIdsPath)) {
        return new Set();
    }
    
    const playerIds = new Set();
    try {
        let content = fs.readFileSync(playerIdsPath, 'utf-8');
        if (content.charCodeAt(0) === 0xFEFF) {
            content = content.slice(1);
        }
        const lines = content.split('\n').filter(line => line.trim());
        
        for (let i = 1; i < lines.length; i++) {
            const playerId = lines[i].trim();
            if (playerId) {
                playerIds.add(playerId);
            }
        }
        
        return playerIds;
    } catch (error) {
        console.error(`❌ player_idリストの読み込みエラー: ${error.message}`);
        return new Set();
    }
}

function loadCSVPlayers(csvPath, year, league) {
    if (!fs.existsSync(csvPath)) {
        return [];
    }
    
    try {
        let content = fs.readFileSync(csvPath, 'utf-8');
        if (content.charCodeAt(0) === 0xFEFF) {
            content = content.slice(1);
        }
        const lines = content.split('\n').filter(line => line.trim());
        const headers = lines[0].split(',').map(h => h.trim().replace(/^"|"$/g, ''));
        
        const playerIdIndex = headers.findIndex(h => h.toLowerCase().includes('player_id'));
        const nameIndex = headers.findIndex(h => 
            h.toLowerCase().includes('name') && h.toLowerCase().includes('ja')
        ) !== -1 ? headers.findIndex(h => 
            h.toLowerCase().includes('name') && h.toLowerCase().includes('ja')
        ) : headers.findIndex(h => h.toLowerCase().includes('name'));
        const yearIndex = headers.findIndex(h => h.toLowerCase().includes('year'));
        const leagueIndex = headers.findIndex(h => h.toLowerCase().includes('league'));
        
        const players = [];
        for (let i = 1; i < lines.length; i++) {
            const values = lines[i].split(',').map(v => v.trim().replace(/^"|"$/g, ''));
            const rowYear = yearIndex !== -1 ? parseInt(values[yearIndex]) : year;
            const rowLeague = leagueIndex !== -1 ? values[leagueIndex].toUpperCase() : league;
            
            if (rowYear === year && rowLeague === league) {
                const playerId = playerIdIndex !== -1 ? values[playerIdIndex] : '';
                const name = nameIndex !== -1 ? values[nameIndex] : '';
                
                if (playerId && playerId !== 'nan' && playerId !== '') {
                    players.push({
                        player_id: playerId,
                        name: name
                    });
                }
            }
        }
        
        return players;
    } catch (error) {
        console.error(`❌ CSV読み込みエラー: ${error.message}`);
        return [];
    }
}

function normalizeName(name) {
    if (!name) return '';
    return name.replace(/[　\s・]+/g, '').trim();
}

async function main() {
    const args = process.argv.slice(2);
    let targetYear = null;
    let targetLeague = null;
    
    for (let i = 0; i < args.length; i++) {
        if (args[i] === '--year' && i + 1 < args.length) {
            targetYear = parseInt(args[i + 1]);
            i++;
        } else if (args[i] === '--league' && i + 1 < args.length) {
            targetLeague = args[i + 1].toUpperCase();
            i++;
        }
    }
    
    console.log(`\n${'='.repeat(60)}`);
    console.log(`=== NPB公式サイトから全年度・全リーグの選手を取得 ===`);
    console.log(`${'='.repeat(60)}\n`);
    
    if (targetYear && targetLeague) {
        console.log(`対象: ${targetYear}年 ${targetLeague}リーグのみ\n`);
    } else {
        console.log(`対象: 全年度・全リーグ\n`);
    }
    
    // 全player_idリストを読み込む（基準となるリスト）
    console.log('📖 全player_idリストを読み込み中...');
    const allPlayerIds = loadAllPlayerIds();
    console.log(`✅ ${allPlayerIds.size}件のplayer_idを読み込みました\n`);
    
    // 年度・リーグのリストを決定
    const targetYears = targetYear ? [targetYear] : YEARS;
    const targetLeagues = targetLeague ? [targetLeague] : LEAGUES;
    
    // 結果を保存する構造
    const results = {
        fetched_players: new Map(), // player_id -> {name, year, league, source}
        failed_fetches: [], // {year, league, url, status, error}
        csv_players: new Map(), // player_id -> {name, year, league}
        missing_in_csv: [], // CSVに存在しない選手
        failed_to_fetch: new Set(), // 取得できなかったplayer_id
        comparison_results: {} // 年度・リーグ別の比較結果
    };
    
    // 各年度・リーグから選手を取得
    console.log('📡 NPB公式サイトから選手リストを取得中...\n');
    
    let totalFetched = 0;
    let totalFailed = 0;
    
    for (const year of targetYears) {
        for (const league of targetLeagues) {
            console.log(`  ${year}年 ${league}リーグ...`, { end: ' ' });
            
            const fetchResult = await fetchPlayersFromNPB(year, league);
            
            if (fetchResult.success) {
                console.log(`✅ ${fetchResult.players.length}人取得`);
                totalFetched += fetchResult.players.length;
                
                for (const player of fetchResult.players) {
                    if (player.player_id) {
                        results.fetched_players.set(player.player_id, {
                            name: player.name,
                            year: year,
                            league: league,
                            source: 'NPB_OFFICIAL'
                        });
                    }
                }
            } else {
                console.log(`❌ 取得失敗 (${fetchResult.error || 'HTTP ' + fetchResult.status})`);
                totalFailed++;
                
                results.failed_fetches.push({
                    year: year,
                    league: league,
                    url: fetchResult.url,
                    status: fetchResult.status,
                    error: fetchResult.error || 'UNKNOWN'
                });
            }
            
            // レート制限
            await new Promise(resolve => setTimeout(resolve, 500));
        }
    }
    
    console.log(`\n✅ 取得完了: ${totalFetched}人取得, ${totalFailed}件失敗\n`);
    
    // CSVから選手を読み込む
    console.log('📖 CSVファイルから選手を読み込み中...');
    
    for (const year of targetYears) {
        for (const league of targetLeagues) {
            const csvPath = path.join(
                projectRoot,
                '_data',
                'master_csv_calculated',
                `batting_${year}_${league}_from_master.csv`
            );
            
            const csvPlayers = loadCSVPlayers(csvPath, year, league);
            
            for (const player of csvPlayers) {
                if (player.player_id) {
                    results.csv_players.set(player.player_id, {
                        name: player.name,
                        year: year,
                        league: league
                    });
                }
            }
        }
    }
    
    console.log(`✅ CSVから ${results.csv_players.size}件のplayer_idを読み込みました\n`);
    
    // 比較: 取得できた選手のうち、CSVに存在しない選手
    console.log('🔍 比較中...\n');
    
    for (const [playerId, player] of results.fetched_players) {
        if (!results.csv_players.has(playerId)) {
            results.missing_in_csv.push({
                player_id: playerId,
                name: player.name,
                year: player.year,
                league: player.league
            });
        }
    }
    
    // 取得できなかったplayer_idを特定
    // （全player_idリストにあるが、取得できなかったもの）
    for (const playerId of allPlayerIds) {
        // 対象年度・リーグのplayer_idかどうかを確認
        // （簡易版: player_idから年度を推測できないため、全player_idをチェック）
        if (!results.fetched_players.has(playerId)) {
            // CSVには存在するが、取得できなかったplayer_id
            if (results.csv_players.has(playerId)) {
                const csvPlayer = results.csv_players.get(playerId);
                // 対象年度・リーグに含まれるか確認
                let isTarget = true;
                if (targetYear && csvPlayer.year !== targetYear) {
                    isTarget = false;
                }
                if (targetLeague && csvPlayer.league !== targetLeague) {
                    isTarget = false;
                }
                
                if (isTarget) {
                    results.failed_to_fetch.add(playerId);
                }
            }
        }
    }
    
    // 結果を表示
    console.log(`${'='.repeat(60)}`);
    console.log(`=== 比較結果 ===`);
    console.log(`${'='.repeat(60)}\n`);
    console.log(`取得できた選手: ${results.fetched_players.size}人`);
    console.log(`取得失敗した年度・リーグ: ${results.failed_fetches.length}件`);
    console.log(`CSV内の選手: ${results.csv_players.size}人`);
    console.log(`取得できたがCSVに不足: ${results.missing_in_csv.length}人`);
    console.log(`CSVにあるが取得できなかった: ${results.failed_to_fetch.size}人\n`);
    
    // 取得できなかった年度・リーグを表示
    if (results.failed_fetches.length > 0) {
        console.log(`⚠️ 取得できなかった年度・リーグ (${results.failed_fetches.length}件):\n`);
        results.failed_fetches.slice(0, 20).forEach((f, i) => {
            console.log(`  ${i + 1}. ${f.year}年 ${f.league}リーグ (${f.error || 'HTTP ' + f.status})`);
        });
        if (results.failed_fetches.length > 20) {
            console.log(`  ... 他 ${results.failed_fetches.length - 20}件`);
        }
        console.log('');
    }
    
    // CSVに不足している選手を表示
    if (results.missing_in_csv.length > 0) {
        console.log(`⚠️ CSVに存在しない選手 (${results.missing_in_csv.length}人):\n`);
        results.missing_in_csv.slice(0, 30).forEach((player, i) => {
            console.log(`  ${(i + 1).toString().padStart(3)}. ${player.player_id.padEnd(10)} - ${player.name.padEnd(20)} (${player.year}年 ${player.league})`);
        });
        if (results.missing_in_csv.length > 30) {
            console.log(`  ... 他 ${results.missing_in_csv.length - 30}件`);
        }
        console.log('');
    }
    
    // CSVにあるが取得できなかった選手を表示
    if (results.failed_to_fetch.size > 0) {
        console.log(`⚠️ CSVにあるが取得できなかった選手 (${results.failed_to_fetch.size}人):\n`);
        console.log(`  これらの選手は、NPB公式サイトから取得できませんでした。`);
        console.log(`  CSVには存在するため、取得方法を確認する必要があります。\n`);
        
        const failedList = Array.from(results.failed_to_fetch).slice(0, 30);
        for (const playerId of failedList) {
            const csvPlayer = results.csv_players.get(playerId);
            console.log(`  ${playerId.padEnd(10)} - ${(csvPlayer.name || 'N/A').padEnd(20)} (${csvPlayer.year}年 ${csvPlayer.league})`);
        }
        if (results.failed_to_fetch.size > 30) {
            console.log(`  ... 他 ${results.failed_to_fetch.size - 30}件`);
        }
        console.log('');
    }
    
    // 結果を保存
    const outputDir = path.join(projectRoot, 'output', 'reports', 'fact_check');
    if (!fs.existsSync(outputDir)) {
        fs.mkdirSync(outputDir, { recursive: true });
    }
    
    // JSON形式で保存
    const resultJson = {
        check_date: new Date().toISOString(),
        target_year: targetYear,
        target_league: targetLeague,
        fetched_count: results.fetched_players.size,
        failed_fetch_count: results.failed_fetches.length,
        csv_count: results.csv_players.size,
        missing_in_csv_count: results.missing_in_csv.length,
        failed_to_fetch_count: results.failed_to_fetch.size,
        failed_fetches: results.failed_fetches,
        missing_in_csv: results.missing_in_csv,
        failed_to_fetch: Array.from(results.failed_to_fetch).map(playerId => {
            const csvPlayer = results.csv_players.get(playerId);
            return {
                player_id: playerId,
                name: csvPlayer ? csvPlayer.name : '',
                year: csvPlayer ? csvPlayer.year : null,
                league: csvPlayer ? csvPlayer.league : ''
            };
        })
    };
    
    const jsonFile = path.join(outputDir, `fact_check_npb_all_${targetYear || 'all'}_${targetLeague || 'all'}.json`);
    fs.writeFileSync(jsonFile, JSON.stringify(resultJson, null, 2), 'utf-8');
    console.log(`✅ 結果をJSON形式で保存しました: ${jsonFile}`);
    
    // CSV形式で保存（不足している選手）
    if (results.missing_in_csv.length > 0) {
        const csvFile = path.join(outputDir, `missing_players_${targetYear || 'all'}_${targetLeague || 'all'}.csv`);
        const csvContent = [
            'player_id,name,year,league',
            ...results.missing_in_csv.map(p => 
                `"${p.player_id}","${p.name}","${p.year}","${p.league}"`
            )
        ].join('\n');
        // BOM付きUTF-8で保存
        const bom = '\ufeff';
        fs.writeFileSync(csvFile, bom + csvContent, 'utf-8');
        console.log(`✅ 不足している選手をCSV形式で保存しました: ${csvFile}`);
    }
    
    // CSV形式で保存（取得できなかった選手）
    if (results.failed_to_fetch.size > 0) {
        const csvFile = path.join(outputDir, `failed_to_fetch_${targetYear || 'all'}_${targetLeague || 'all'}.csv`);
        const csvContent = [
            'player_id,name,year,league,reason',
            ...Array.from(results.failed_to_fetch).map(playerId => {
                const csvPlayer = results.csv_players.get(playerId);
                return `"${playerId}","${csvPlayer ? csvPlayer.name : ''}","${csvPlayer ? csvPlayer.year : ''}","${csvPlayer ? csvPlayer.league : ''}","NOT_FETCHED_FROM_NPB"`
            })
        ].join('\n');
        // BOM付きUTF-8で保存
        const bom = '\ufeff';
        fs.writeFileSync(csvFile, bom + csvContent, 'utf-8');
        console.log(`✅ 取得できなかった選手をCSV形式で保存しました: ${csvFile}`);
    }
    
    console.log('');
    
    // 警告を表示
    if (results.failed_fetches.length > 0 || results.failed_to_fetch.size > 0) {
        console.log(`${'='.repeat(60)}`);
        console.log(`⚠️ 重要な注意事項`);
        console.log(`${'='.repeat(60)}\n`);
        console.log(`取得できなかった選手が ${results.failed_to_fetch.size}人存在します。`);
        console.log(`これらの選手は、NPB公式サイトから取得できませんでしたが、`);
        console.log(`CSVには存在するため、取得方法を確認する必要があります。\n`);
        console.log(`「CSVに不足」と表示された選手のうち、`);
        console.log(`実際には取得できなかっただけの可能性があります。\n`);
    }
}

main().catch(error => {
    console.error(`❌ エラー: ${error.message}`);
    process.exit(1);
});

