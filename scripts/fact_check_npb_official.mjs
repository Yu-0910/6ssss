#!/usr/bin/env node
/**
 * fact_check_npb_official.mjs
 * 
 * NPB公式サイトから選手リストを取得し、CSVファイルと比較するスクリプト
 * 
 * 使用方法:
 *   node scripts/fact_check_npb_official.mjs <YEAR> <LEAGUE>
 * 例:
 *   node scripts/fact_check_npb_official.mjs 2025 PL
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import https from 'https';
// HTMLパーサーなしで正規表現を使用

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, '..');

function fetchHTML(url) {
    return new Promise((resolve, reject) => {
        https.get(url, (res) => {
            const chunks = [];
            res.on('data', (chunk) => { chunks.push(chunk); });
            res.on('end', () => {
                // バイナリデータを結合
                const buffer = Buffer.concat(chunks);
                
                // エンコーディングを検出して変換
                let text = '';
                try {
                    // Content-Typeヘッダーからエンコーディングを取得
                    const contentType = res.headers['content-type'] || '';
                    let encoding = 'utf-8';
                    if (contentType.includes('charset=')) {
                        const match = contentType.match(/charset=([^;]+)/i);
                        if (match) {
                            encoding = match[1].toLowerCase().replace(/['"]/g, '');
                        }
                    }
                    
                    // HTMLのmetaタグからもエンコーディングを取得
                    const htmlPreview = buffer.toString('utf-8', 0, Math.min(5000, buffer.length));
                    const metaMatch = htmlPreview.match(/<meta[^>]*charset=["']?([^"'\s>]+)["']?/i);
                    if (metaMatch) {
                        encoding = metaMatch[1].toLowerCase();
                    }
                    
                    // エンコーディングに応じて変換
                    if (encoding === 'utf-8' || encoding === 'utf8') {
                        text = buffer.toString('utf-8');
                    } else if (encoding === 'shift_jis' || encoding === 'sjis') {
                        // Shift_JISの場合はiconv-liteが必要だが、まずはUTF-8として試行
                        text = buffer.toString('utf-8');
                    } else {
                        text = buffer.toString(encoding);
                    }
                } catch (e) {
                    // 失敗した場合はUTF-8として試行
                    try {
                        text = buffer.toString('utf-8');
                    } catch (e2) {
                        // それでも失敗した場合はlatin1として試行（最後の手段）
                        text = buffer.toString('latin1');
                    }
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
        // 2025年のページではリンクがないため、テーブルから直接選手名を抽出
        if (year >= 2025) {
            // HTMLテーブルから選手名を抽出
            // パターン1: <td>選手名<span class="stteam">(チーム)</span></td>
            const cellPattern1 = /<td>([^<]+)<span[^>]*class=["']stteam["'][^>]*>\(([^)]+)\)<\/span><\/td>/g;
            let match1;
            let foundCount1 = 0;
            while ((match1 = cellPattern1.exec(html)) !== null) {
                foundCount1++;
                let playerName = match1[1].trim();
                const teamCode = match1[2].trim();
                
                // 全角スペースを正規化（全角スペースを半角スペースに統一）
                playerName = playerName.replace(/\u3000/g, ' ').replace(/\s+/g, ' ').trim();
                
                if (playerName && playerName.length > 0 && playerName.length < 50) {
                    // チーム略称を正式名に変換
                    const teamCodeMap = {
                        '巨': '読売ジャイアンツ', '神': '阪神タイガース', 'デ': '横浜DeNAベイスターズ',
                        '横': '横浜DeNAベイスターズ', '広': '広島東洋カープ', '中': '中日ドラゴンズ',
                        'ヤ': '東京ヤクルトスワローズ', 'オ': 'オリックス・バファローズ',
                        '西': '埼玉西武ライオンズ', 'ロ': '千葉ロッテマリーンズ',
                        '楽': '東北楽天ゴールデンイーグルス', 'ソ': '福岡ソフトバンクホークス',
                        '日': '北海道日本ハムファイターズ', 'ハ': '北海道日本ハムファイターズ'
                    };
                    const team = teamCodeMap[teamCode] || teamCode;
                    
                    // デバッグ: 最初の5件のみ表示
                    if (players.length < 5) {
                        console.log(`      [DEBUG] 抽出: "${playerName}" (${teamCode} -> ${team})`);
                    }
                    
                    players.push({
                        name: playerName,
                        team: team,
                        player_id: '',  // 2025年のページではplayer_idが取得できない
                        source: 'NPB_OFFICIAL'
                    });
                }
            }
            
            if (foundCount1 > 0) {
                console.log(`  📊 パターン1で ${foundCount1}件のセルを発見、${players.length}件の選手を抽出`);
            }
            
            // パターン2: マークダウン形式のテーブル（|順位|選手(チーム)|...）
            if (players.length === 0) {
                const tableRowPattern = /\|(\d+)\|([^|]+)\(([^)]+)\)\|/g;
                let match2;
                while ((match2 = tableRowPattern.exec(html)) !== null) {
                    const playerNameWithTeam = match2[2].trim();
                    const teamCode = match2[3].trim();
                    
                    // 選手名から括弧内のチーム名を除去
                    const playerName = playerNameWithTeam.replace(/\([^)]+\)/g, '').trim();
                    
                    if (playerName && playerName.length > 0 && playerName.length < 50) {
                        const teamCodeMap = {
                            '巨': '読売ジャイアンツ', '神': '阪神タイガース', 'デ': '横浜DeNAベイスターズ',
                            '横': '横浜DeNAベイスターズ', '広': '広島東洋カープ', '中': '中日ドラゴンズ',
                            'ヤ': '東京ヤクルトスワローズ', 'オ': 'オリックス・バファローズ',
                            '西': '埼玉西武ライオンズ', 'ロ': '千葉ロッテマリーンズ',
                            '楽': '東北楽天ゴールデンイーグルス', 'ソ': '福岡ソフトバンクホークス',
                            '日': '北海道日本ハムファイターズ', 'ハ': '北海道日本ハムファイターズ'
                        };
                        const team = teamCodeMap[teamCode] || teamCode;
                        
                        players.push({
                            name: playerName,
                            team: team,
                            player_id: '',
                            source: 'NPB_OFFICIAL'
                        });
                    }
                }
            }
        } else {
            // 旧形式: リンクから抽出
            const linkPattern = /<a[^>]*href=["']([^"']*\/bis\/players\/(\d+)[^"']*)["'][^>]*>([^<]+)<\/a>/gi;
            const playerIdPattern = /\/bis\/players\/(\d+)/;
            
            let match;
            while ((match = linkPattern.exec(html)) !== null) {
                const href = match[1];
                const playerId = match[2] || (href.match(playerIdPattern)?.[1] || '');
                const playerName = match[3].trim();
                
                if (playerName && playerName.length > 0 && playerName.length < 50) {
                    // 選手名が含まれる行の前後を確認してチーム名を探す
                    const contextStart = Math.max(0, match.index - 200);
                    const contextEnd = Math.min(html.length, match.index + match[0].length + 200);
                    const context = html.substring(contextStart, contextEnd);
                    
                    // チーム名のパターンを探す（簡易版）
                    let team = '';
                    const teamPatterns = [
                        /(巨人|阪神|DeNA|横浜|広島|中日|ヤクルト|オリックス|西武|ロッテ|楽天|ソフトバンク|日本ハム|北海道日本ハム)/g
                    ];
                    
                    for (const pattern of teamPatterns) {
                        const teamMatch = context.match(pattern);
                        if (teamMatch) {
                            team = teamMatch[0];
                            break;
                        }
                    }
                    
                    players.push({
                        name: playerName,
                        team: team,
                        player_id: playerId,
                        source: 'NPB_OFFICIAL'
                    });
                }
            }
        }
        
        // 重複を除去（player_idで）
        const seen = new Set();
        const uniquePlayers = [];
        for (const player of players) {
            const key = player.player_id || player.name;
            if (!seen.has(key)) {
                seen.add(key);
                uniquePlayers.push(player);
            }
        }
        
        return uniquePlayers;
    } catch (error) {
        console.error('HTML解析エラー:', error);
        return [];
    }
}

function loadCSVPlayers(csvPath) {
    if (!fs.existsSync(csvPath)) {
        console.error(`❌ CSVファイルが見つかりません: ${csvPath}`);
        return [];
    }
    
    try {
        // BOMを除去してUTF-8として読み込む
        let content = fs.readFileSync(csvPath, 'utf-8');
        if (content.charCodeAt(0) === 0xFEFF) {
            content = content.slice(1);  // BOMを除去
        }
        const lines = content.split('\n');
        const headers = lines[0].split(',');
        
        // 選手名カラムとplayer_idカラムを探す
        const nameColIndex = headers.findIndex(h => 
            h.toLowerCase().includes('name') && h.toLowerCase().includes('ja')
        ) !== -1 ? headers.findIndex(h => 
            h.toLowerCase().includes('name') && h.toLowerCase().includes('ja')
        ) : headers.findIndex(h => h.toLowerCase().includes('name'));
        
        const playerIdColIndex = headers.findIndex(h => 
            h.toLowerCase().includes('player_id')
        );
        
        const teamColIndex = headers.findIndex(h => 
            h.toLowerCase().includes('team')
        );
        
        const players = [];
        for (let i = 1; i < lines.length; i++) {
            const line = lines[i].trim();
            if (!line) continue;
            
            // CSVのパース（クォートやカンマを含む値を正しく処理）
            const values = [];
            let current = '';
            let inQuotes = false;
            for (let i = 0; i < line.length; i++) {
                const char = line[i];
                if (char === '"') {
                    inQuotes = !inQuotes;
                } else if (char === ',' && !inQuotes) {
                    values.push(current.trim());
                    current = '';
                } else {
                    current += char;
                }
            }
            values.push(current.trim());  // 最後の値
            
            const name = values[nameColIndex]?.trim().replace(/^"|"$/g, '');
            if (name && name !== 'nan' && name !== '') {
                players.push({
                    name: name,
                    team: (values[teamColIndex]?.trim().replace(/^"|"$/g, '') || ''),
                    player_id: (values[playerIdColIndex]?.trim().replace(/^"|"$/g, '') || ''),
                    source: 'CSV'
                });
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
    // 全角スペースを半角スペースに統一、連続するスペースを1つに
    return name.replace(/[　]+/g, ' ').replace(/\s+/g, ' ').trim();
}

function comparePlayers(externalPlayers, csvPlayers) {
    const externalNames = new Map();
    for (const p of externalPlayers) {
        const normName = normalizeName(p.name);
        if (normName) {
            externalNames.set(normName, p);
        }
    }
    
    const csvNames = new Map();
    for (const p of csvPlayers) {
        const normName = normalizeName(p.name);
        if (normName) {
            csvNames.set(normName, p);
        }
    }
    
    const missingInCSV = [];
    const matched = [];
    
    for (const [normName, player] of externalNames) {
        if (csvNames.has(normName)) {
            matched.push({
                external: player,
                csv: csvNames.get(normName)
            });
        } else {
            missingInCSV.push(player);
        }
    }
    
    const extraInCSV = [];
    for (const [normName, player] of csvNames) {
        if (!externalNames.has(normName)) {
            extraInCSV.push(player);
        }
    }
    
    return {
        external_count: externalPlayers.length,
        csv_count: csvPlayers.length,
        matched_count: matched.length,
        missing_in_csv: missingInCSV,
        extra_in_csv: extraInCSV
    };
}

async function main() {
    const args = process.argv.slice(2);
    if (args.length < 2) {
        console.log('使用方法: node fact_check_npb_official.mjs <YEAR> <LEAGUE>');
        console.log('例: node fact_check_npb_official.mjs 2025 PL');
        process.exit(1);
    }
    
    const year = parseInt(args[0]);
    const league = args[1].toUpperCase();
    
    const csvPath = path.join(
        projectRoot,
        '_data',
        'master_csv_calculated',
        `batting_${year}_${league}_from_master.csv`
    );
    
    console.log(`\n${'='.repeat(60)}`);
    console.log(`=== 外部データソースとのファクトチェック ===`);
    console.log(`${'='.repeat(60)}\n`);
    console.log(`年度: ${year}`);
    console.log(`リーグ: ${league}`);
    console.log(`CSVファイル: ${csvPath}\n`);
    
    // NPB公式サイトから選手リストを取得
    const leagueLower = league.toLowerCase();
    // 2025年以降はURL構造が変更されている
    let npbUrl;
    if (year >= 2025) {
        // 新しいURL構造: https://npb.jp/bis/2025/stats/bat_p.html (PL) or bat_c.html (CL)
        const leagueCode = league.toUpperCase() === 'PL' ? 'p' : 'c';
        npbUrl = `https://npb.jp/bis/${year}/stats/bat_${leagueCode}.html`;
    } else {
        // 旧URL構造: https://npb.jp/bis/stats/2024/pl/batting.html
        npbUrl = `https://npb.jp/bis/stats/${year}/${leagueLower}/batting.html`;
    }
    
    console.log(`📡 NPB公式サイトから選手リストを取得中: ${npbUrl}`);
    
    try {
        const { html, status } = await fetchHTML(npbUrl);
        
        if (status !== 200) {
            console.error(`❌ HTTPステータス: ${status}`);
            console.log('\n⚠️ NPB公式サイトからデータを取得できませんでした。');
            console.log('   手動で確認するか、別のデータソースを使用してください。');
            process.exit(1);
        }
        
        const externalPlayers = extractPlayersFromNPB(html, year, league);
        console.log(`✅ ${externalPlayers.length}人の選手を取得しました`);
        
        // デバッグ: 最初の5件の選手名を表示
        if (externalPlayers.length > 0) {
            console.log(`  [DEBUG] 外部選手名の例（最初の5件）:`);
            for (let i = 0; i < Math.min(5, externalPlayers.length); i++) {
                const p = externalPlayers[i];
                console.log(`      ${i + 1}. "${p.name}" (${p.team})`);
            }
        }
        console.log('');
        
        if (externalPlayers.length === 0) {
            console.log('⚠️ 選手を抽出できませんでした。');
            console.log('   HTMLの構造が予想と異なる可能性があります。');
            process.exit(1);
        }
        
        // CSVから選手リストを読み込む
        console.log(`📖 CSVファイルから選手リストを読み込み中...`);
        const csvPlayers = loadCSVPlayers(csvPath);
        console.log(`✅ ${csvPlayers.length}人の選手を読み込みました\n`);
        
        // 比較
        console.log('🔍 選手リストを比較中...\n');
        const comparison = comparePlayers(externalPlayers, csvPlayers);
        
        // 結果を表示
        console.log(`${'='.repeat(60)}`);
        console.log(`=== 比較結果 ===`);
        console.log(`${'='.repeat(60)}\n`);
        console.log(`外部データソース: ${comparison.external_count}人`);
        console.log(`CSVファイル: ${comparison.csv_count}人`);
        console.log(`一致: ${comparison.matched_count}人`);
        console.log(`CSVに不足: ${comparison.missing_in_csv.length}人`);
        console.log(`CSVにのみ存在: ${comparison.extra_in_csv.length}人\n`);
        
        // 不足している選手を表示
        if (comparison.missing_in_csv.length > 0) {
            console.log(`⚠️ CSVに存在しない選手 (${comparison.missing_in_csv.length}人):\n`);
            comparison.missing_in_csv.slice(0, 50).forEach((player, i) => {
                console.log(`  ${(i + 1).toString().padStart(3)}. ${player.name.padEnd(20)} (${player.team.padEnd(15)}, ID: ${player.player_id})`);
            });
            if (comparison.missing_in_csv.length > 50) {
                console.log(`  ... 他 ${comparison.missing_in_csv.length - 50}件`);
            }
            
            // CSV形式で保存
            const outputDir = path.join(projectRoot, 'output', 'reports', 'fact_check');
            if (!fs.existsSync(outputDir)) {
                fs.mkdirSync(outputDir, { recursive: true });
            }
            
            const outputFile = path.join(outputDir, `missing_players_${year}_${league}_external.csv`);
            const csvContent = [
                'name,team,player_id,source',
                ...comparison.missing_in_csv.map(p => 
                    `"${p.name}","${p.team}","${p.player_id}","${p.source}"`
                )
            ].join('\n');
            
            // BOM付きUTF-8で書き込む
            const bom = Buffer.from([0xEF, 0xBB, 0xBF]);
            fs.writeFileSync(outputFile, Buffer.concat([bom, Buffer.from(csvContent, 'utf-8')]));
            console.log(`\n✅ 不足している選手をCSV形式で保存しました: ${outputFile}`);
        } else {
            console.log('✅ すべての選手がCSVファイルに含まれています\n');
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
            external_count: comparison.external_count,
            csv_count: comparison.csv_count,
            matched_count: comparison.matched_count,
            missing_in_csv: comparison.missing_in_csv,
            extra_in_csv: comparison.extra_in_csv
        };
        
        const jsonFile = path.join(outputDir, `fact_check_${year}_${league}_external.json`);
        fs.writeFileSync(jsonFile, JSON.stringify(resultJson, null, 2), 'utf-8');
        console.log(`✅ 結果をJSON形式で保存しました: ${jsonFile}\n`);
        
        if (comparison.missing_in_csv.length > 0) {
            process.exit(1);
        } else {
            process.exit(0);
        }
        
    } catch (error) {
        console.error(`❌ エラー: ${error.message}`);
        process.exit(1);
    }
}

main();

