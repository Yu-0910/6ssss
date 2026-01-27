/**
 * formatStat関数の簡単なテスト
 * 実行: npx tsx scripts/quick_format_test.ts
 */

import { formatStat } from '../lib/formatStat'

console.log('=== formatStat テスト ===\n')

// decimal3_no0 のテスト
console.log('【decimal3_no0】')
console.log('formatStat("OPS", 0.312) =>', formatStat('OPS', 0.312))
console.log('formatStat("打率", 0.045) =>', formatStat('打率', 0.045))
console.log('formatStat("OPS", 1.023) =>', formatStat('OPS', 1.023))
console.log('formatStat("AVG", 10.5) =>', formatStat('AVG', 10.5))
console.log('formatStat("OPS", null) =>', formatStat('OPS', null))
console.log('formatStat("OPS", "") =>', formatStat('OPS', ''))
console.log('formatStat("OPS", undefined) =>', formatStat('OPS', undefined))
console.log('')

// percent1 のテスト
console.log('【percent1】')
console.log('formatStat("BB%", 12.34) =>', formatStat('BB%', 12.34))
console.log('formatStat("K%", 0) =>', formatStat('K%', 0))
console.log('formatStat("BB%", 7.89) =>', formatStat('BB%', 7.89))
console.log('')

// decimal2 のテスト
console.log('【decimal2】')
console.log('formatStat("RC", 85.237) =>', formatStat('RC', 85.237))
console.log('formatStat("XR", 3.456) =>', formatStat('XR', 3.456))
console.log('formatStat("NOI", 0.1) =>', formatStat('NOI', 0.1))
console.log('')

// decimal3_with0 のテスト
console.log('【decimal3_with0】')
console.log('formatStat("BB/K", 0.543) =>', formatStat('BB/K', 0.543))
console.log('formatStat("BB-K", 1.234) =>', formatStat('BB-K', 1.234))
console.log('')

// int のテスト
console.log('【int】')
console.log('formatStat("HR", 132) =>', formatStat('HR', 132))
console.log('formatStat("安打", 0) =>', formatStat('安打', 0))
console.log('formatStat("打点", 85.7) =>', formatStat('打点', 85.7))
console.log('')

console.log('=== テスト完了 ===')



















