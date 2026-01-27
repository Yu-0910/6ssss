/**
 * CSVファイルの値をデバッグするスクリプト
 * 数値変換の問題を特定するために使用
 */

import fs from 'fs'
import path from 'path'
import { loadBattingCsv } from '../lib/ranking/loaders'

async function debugCsvValues() {
  try {
    const { rows, availableMetrics } = loadBattingCsv('2025', 'PL')
    
    console.log(`\n=== CSV Debug Info ===`)
    console.log(`Total rows: ${rows.length}`)
    console.log(`Available metrics: ${availableMetrics.length}`)
    
    // 最初の5行のデータを表示
    console.log(`\n=== First 5 Rows ===`)
    for (let i = 0; i < Math.min(5, rows.length); i++) {
      const row = rows[i]
      console.log(`\nRow ${i + 1}:`)
      console.log(`  Name: ${row['player_name_ja'] || row['name'] || 'N/A'}`)
      console.log(`  OPS: ${row['OPS']} (type: ${typeof row['OPS']})`)
      console.log(`  AVG: ${row['打率'] || row['AVG'] || row['avg']} (type: ${typeof (row['打率'] || row['AVG'] || row['avg'])})`)
      console.log(`  PA: ${row['PA'] || row['pa'] || row['打席']} (type: ${typeof (row['PA'] || row['pa'] || row['打席'])})`)
      console.log(`  H: ${row['H'] || row['h'] || row['安打']} (type: ${typeof (row['H'] || row['h'] || row['安打'])})`)
      console.log(`  AB: ${row['AB'] || row['ab'] || row['打数']} (type: ${typeof (row['AB'] || row['ab'] || row['打数'])})`)
    }
    
    // OPSの値が異常な行を探す
    console.log(`\n=== OPS Value Check ===`)
    const opsRows = rows.filter(row => {
      const ops = row['OPS'] || row['ops']
      return ops !== undefined && ops !== null && ops !== ''
    })
    console.log(`Rows with OPS: ${opsRows.length}`)
    
    if (opsRows.length > 0) {
      const opsValues = opsRows.map(row => {
        const ops = row['OPS'] || row['ops']
        return {
          name: row['player_name_ja'] || row['name'] || 'N/A',
          ops: ops,
          type: typeof ops
        }
      })
      
      // OPSの値が1より大きい（異常値）の行を探す
      const abnormalOps = opsValues.filter(v => {
        const numOps = typeof v.ops === 'number' ? v.ops : Number(v.ops)
        return !isNaN(numOps) && numOps > 1.5
      })
      
      if (abnormalOps.length > 0) {
        console.log(`\n⚠️  Abnormal OPS values (> 1.5):`)
        abnormalOps.slice(0, 10).forEach(v => {
          console.log(`  ${v.name}: ${v.ops} (type: ${v.type})`)
        })
      }
    }
    
  } catch (error) {
    console.error('Error:', error)
  }
}

debugCsvValues()
