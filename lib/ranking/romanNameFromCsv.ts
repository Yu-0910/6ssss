/**
 * CSV（player_name_en列）を参照して英字名マップを取得
 * ランキングページでJSONにromanNameが無い場合の補完に使用
 */

import path from 'path'
import fs from 'fs'

/** マップキー用: 名前とチームを正規化（全角→半角、trim） */
function normalizeKey(name: string, team: string): string {
  const n = (name ?? '').toString().replace(/\u3000/g, ' ').trim()
  const t = (team ?? '').toString().trim()
  return `${n}|${t}`
}

/** スペースを除去したキー（照合の確実性のため両方登録） */
function normalizeKeyNoSpace(name: string, team: string): string {
  const n = (name ?? '').toString().replace(/[\s\u3000]/g, '').trim()
  const t = (team ?? '').toString().trim()
  return `${n}|${t}`
}

/**
 * 打撃CSVのパスを探索（from_master 優先、なければ qualifying）
 */
function findBattingCsvForRoman(year: string, league: string): string | null {
  const upperLeague = league.toUpperCase()
  const baseNames = [
    `batting_${year}_${upperLeague}_from_master.csv`,
    `batting_${year}_${upperLeague}_qualifying.csv`,
  ]
  const dirs = [
    path.join(process.cwd(), '_data', 'master_csv_calculated'),
    path.join(process.cwd(), '_data', 'master_csv'),
    process.cwd(),
  ]
  for (const base of baseNames) {
    for (const dir of dirs) {
      const csvPath = path.join(dir, base)
      if (fs.existsSync(csvPath)) return csvPath
    }
  }
  return null
}

/** 簡易CSVパース（loaders.parseCsv と同様のロジック） */
function parseCsvSimple(content: string): Record<string, string>[] {
  const lines = content.split(/\r?\n/).filter(line => line.trim())
  if (lines.length < 2) return []
  const headerLine = lines[0].replace(/^\ufeff/, '')
  const headers = headerLine.split(',').map(h => h.trim().replace(/^["']|["']$/g, ''))
  const rows: Record<string, string>[] = []
  for (let i = 1; i < lines.length; i++) {
    const line = lines[i].trim()
    if (!line) continue
    const values: string[] = []
    let current = ''
    let inQuotes = false
    for (let j = 0; j < line.length; j++) {
      const c = line[j]
      if (c === '"') inQuotes = !inQuotes
      else if (c === ',' && !inQuotes) {
        values.push(current.trim())
        current = ''
      } else current += c
    }
    values.push(current.trim())
    const row: Record<string, string> = {}
    headers.forEach((h, idx) => { row[h] = values[idx] ?? '' })
    rows.push(row)
  }
  return rows
}

/**
 * 指定年度・リーグのCSVから「名前|チーム」→ 英字名 のマップを取得
 * CSVの player_name_ja + team をキー、player_name_en を値とする
 */
export function getRomanNameMap(year: string, league: string): Record<string, string> {
  // 2026年は2025年データを流用
  const dataYear = year === '2026' ? '2025' : year
  const csvPath = findBattingCsvForRoman(dataYear, league)
  if (!csvPath) return {}

  let content: string | null = null
  const encodings: BufferEncoding[] = ['utf-8-sig', 'utf-8', 'shift_jis', 'cp932']
  for (const enc of encodings) {
    try {
      content = fs.readFileSync(csvPath, enc)
      break
    } catch {
      continue
    }
  }
  if (!content) return {}

  const rows = parseCsvSimple(content)
  const map: Record<string, string> = {}
  for (const row of rows) {
    const name = (row['player_name_ja'] ?? row['name'] ?? row['player'] ?? '').trim()
    const team = (row['team'] ?? row['Team'] ?? row['チーム'] ?? '').trim()
    const en = (row['player_name_en'] ?? row['romanName'] ?? row['name_en'] ?? '').trim()
    if (!en) continue
    const key = normalizeKey(name, team)
    map[key] = en
    const keyNoSpace = normalizeKeyNoSpace(name, team)
    if (keyNoSpace !== key) map[keyNoSpace] = en
  }
  return map
}
