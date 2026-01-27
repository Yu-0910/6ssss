#!/usr/bin/env node
/**
 * fact_check_all_years_batch.mjs
 * 
 * 全年度・全リーグを段階的に実行するバッチスクリプト
 * 
 * 使用方法:
 *   node scripts/fact_check_all_years_batch.mjs [--start-year YEAR] [--end-year YEAR] [--step STEP]
 */

import { execSync } from 'child_process';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, '..');

// 引数解析
const args = process.argv.slice(2);
let startYear = 1950;
let endYear = 2025;
let step = 10; // 10年ずつ実行

for (let i = 0; i < args.length; i++) {
    if (args[i] === '--start-year' && i + 1 < args.length) {
        startYear = parseInt(args[i + 1]);
        i++;
    } else if (args[i] === '--end-year' && i + 1 < args.length) {
        endYear = parseInt(args[i + 1]);
        i++;
    } else if (args[i] === '--step' && i + 1 < args.length) {
        step = parseInt(args[i + 1]);
        i++;
    }
}

const leagues = ['PL', 'CL'];

console.log(`\n${'='.repeat(60)}`);
console.log(`=== 全年度・全リーグのファクトチェック（バッチ実行） ===`);
console.log(`${'='.repeat(60)}\n`);
console.log(`対象年度: ${startYear}年 ～ ${endYear}年`);
console.log(`実行単位: ${step}年ずつ`);
console.log(`リーグ: ${leagues.join(', ')}\n`);

// 結果を保存するディレクトリ
const outputDir = path.join(projectRoot, 'output', 'reports', 'fact_check', 'batch');
if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
}

// 実行ログ
const logFile = path.join(outputDir, `batch_execution_${Date.now()}.log`);
const summaryFile = path.join(outputDir, `batch_summary_${Date.now()}.json`);

const summary = {
    start_time: new Date().toISOString(),
    start_year: startYear,
    end_year: endYear,
    step: step,
    total_combinations: 0,
    completed: 0,
    failed: 0,
    results: []
};

function log(message) {
    const timestamp = new Date().toISOString();
    const logMessage = `[${timestamp}] ${message}`;
    console.log(logMessage);
    fs.appendFileSync(logFile, logMessage + '\n', 'utf-8');
}

// 年度を段階的に実行
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

async function runBatch() {
for (let year = startYear; year <= endYear; year += step) {
    const yearEnd = Math.min(year + step - 1, endYear);
    log(`\n${'='.repeat(60)}`);
    log(`段階実行: ${year}年 ～ ${yearEnd}年`);
    log(`${'='.repeat(60)}\n`);
    
    for (let y = year; y <= yearEnd; y++) {
        for (const league of leagues) {
            summary.total_combinations++;
            
            log(`実行中: ${y}年 ${league}リーグ`);
            
            try {
                const command = `node scripts/fact_check_npb_all_years.mjs --year ${y} --league ${league}`;
                execSync(command, { 
                    cwd: projectRoot,
                    stdio: 'inherit',
                    encoding: 'utf-8'
                });
                
                summary.completed++;
                summary.results.push({
                    year: y,
                    league: league,
                    status: 'completed',
                    timestamp: new Date().toISOString()
                });
                
                log(`✅ 完了: ${y}年 ${league}リーグ\n`);
                
                // レート制限（1秒待機）
                await sleep(1000);
                
            } catch (error) {
                summary.failed++;
                summary.results.push({
                    year: y,
                    league: league,
                    status: 'failed',
                    error: error.message,
                    timestamp: new Date().toISOString()
                });
                
                log(`❌ エラー: ${y}年 ${league}リーグ - ${error.message}\n`);
            }
        }
    }
    
    // 段階ごとのサマリーを保存
    const stageSummary = {
        stage: `${year}-${yearEnd}`,
        completed: summary.completed,
        failed: summary.failed,
        timestamp: new Date().toISOString()
    };
    
    log(`\n段階完了: ${year}年 ～ ${yearEnd}年`);
    log(`  完了: ${stageSummary.completed}件`);
    log(`  失敗: ${stageSummary.failed}件\n`);
    }
    
    // 最終サマリー
    summary.end_time = new Date().toISOString();
    summary.duration_seconds = Math.floor((new Date(summary.end_time) - new Date(summary.start_time)) / 1000);
    
    log(`\n${'='.repeat(60)}`);
    log(`=== 実行完了 ===`);
    log(`${'='.repeat(60)}\n`);
    log(`総実行数: ${summary.total_combinations}件`);
    log(`完了: ${summary.completed}件`);
    log(`失敗: ${summary.failed}件`);
    log(`実行時間: ${summary.duration_seconds}秒\n`);
    
    // サマリーを保存
    fs.writeFileSync(summaryFile, JSON.stringify(summary, null, 2), 'utf-8');
    log(`✅ サマリーを保存しました: ${summaryFile}`);
    log(`✅ ログを保存しました: ${logFile}\n`);
}

runBatch().catch(error => {
    log(`❌ 致命的エラー: ${error.message}`);
    process.exit(1);
});

