/**
 * Phase 4: パイロット今季成績
 * Yahoo games pilot (2026/3/4 オープン戦5試合) の batting_stats.csv から選手別スプリット成績を取得
 */

import fs from 'fs'
import path from 'path'

/** パイロット対象選手の Yahoo ID (菊池涼介: 広島) */
export const PILOT_PLAYER_YAHOO_ID = '1100082'

/** NPB公式の player_id (master_csv / ランキングJSON で使用) */
const PILOT_PLAYER_NPB_ID = '61565135'

/** 選手名・ID → Yahoo ID マッピング（パイロットテスト用） */
const NAME_TO_YAHOO_ID: Record<string, string> = {
  '菊池涼介': PILOT_PLAYER_YAHOO_ID,
  '菊池 涼介': PILOT_PLAYER_YAHOO_ID,
  '菊池　涼介': PILOT_PLAYER_YAHOO_ID,
  [PILOT_PLAYER_NPB_ID]: PILOT_PLAYER_YAHOO_ID,
}

/** 個人ページ表示項目整理 ブロックA・D 準拠 */
export type SeasonStatsRow = {
  split_type: string
  split_value: string
  split_label: string
  // ブロックA: 基本
  g: number
  pa: number
  ab: number
  r: number
  h: number
  h1: number
  h2: number
  h3: number
  hr: number
  tb: number
  rbi: number
  so: number
  bb: number
  ibb: number
  hbp: number
  sh: number
  sf: number
  sb: number
  cs: number
  gidp: number
  avg: string
  obp: string
  slg: string
  ops: string
  risp_avg: string
  risp_ab: number
  risp_h: number
  sb_pct: string
  // ブロックD: セイバーメトリクス
  isop: string
  isod: string
  babip: string
  bb_pct: string
  k_pct: string
  bbk: string
  gpa: string
  rc: string
  xr: string
  seca: string
  ta: string
  noi: string
}

function normalizeName(name: string): string {
  return (name || '').replace(/\s/g, '').replace(/　/g, '')
}

export function getYahooIdForPilot(playerIdOrName: string): string | null {
  if (!playerIdOrName) return null
  const trimmed = String(playerIdOrName).trim()
  if (trimmed === PILOT_PLAYER_YAHOO_ID) return PILOT_PLAYER_YAHOO_ID
  if (trimmed === PILOT_PLAYER_NPB_ID) return PILOT_PLAYER_YAHOO_ID
  const norm = normalizeName(trimmed)
  if (norm === '菊池涼介') return PILOT_PLAYER_YAHOO_ID
  for (const [name, id] of Object.entries(NAME_TO_YAHOO_ID)) {
    if (normalizeName(name) === norm) return id
  }
  return null
}

function formatSplitLabel(splitType: string, splitValue: string): string {
  if (splitType === 'total') return '通算'
  if (splitType === 'day_night') return splitValue === 'day' ? 'デーゲーム' : 'ナイター'
  if (splitType === 'home_away') return splitValue === 'home' ? 'ホーム' : 'ビジター'
  if (splitType === 'vs_team') return splitValue.replace(/^vs_/, '')
  if (splitType === 'bat_order') return `打順${splitValue.replace('bat_order_', '')}`
  return splitValue
}

function fmtSlash3(n: number | null): string {
  if (n == null || !Number.isFinite(n)) return '.000'
  const s = n.toFixed(3)
  return s.startsWith('0') ? s.slice(1) : s
}

function int(v: unknown): number {
  const n = parseInt(String(v ?? '0'), 10)
  return Number.isFinite(n) ? n : 0
}

function computeBattingFromPaRows(rows: Array<Record<string, string>>) {
  const paRows = rows.filter((r) => r.is_pa === '1')
  const gameIds = new Set(paRows.map((r) => r.game_id).filter(Boolean))

  const ab = paRows.reduce((acc, r) => acc + int(r.ab), 0)
  const h2 = paRows.reduce((acc, r) => acc + int(r.h2), 0)
  const h3 = paRows.reduce((acc, r) => acc + int(r.h3), 0)
  const hr = paRows.reduce((acc, r) => acc + int(r.hr), 0)
  const h =
    paRows.reduce((acc, r) => acc + int(r.h), 0) +
    h2 +
    h3 +
    hr
  const h1 = Math.max(0, h - h2 - h3 - hr)

  const bb = paRows.reduce((acc, r) => acc + int(r.bb), 0)
  const ibb = paRows.reduce((acc, r) => acc + int(r.ibb), 0)
  const hbp = paRows.reduce((acc, r) => acc + int(r.hbp), 0)
  const so = paRows.reduce((acc, r) => acc + int(r.so), 0)
  const sh = paRows.reduce((acc, r) => acc + int(r.sh), 0)
  const sf = paRows.reduce((acc, r) => acc + int(r.sf), 0)
  const gidp = paRows.reduce((acc, r) => acc + int(r.gidp), 0)
  const rbi = paRows.reduce((acc, r) => acc + int(r.rbi), 0)
  const r = paRows.reduce((acc, r) => acc + int(r.r), 0)
  const sb = paRows.reduce((acc, r) => acc + int(r.sb), 0)
  const cs = paRows.reduce((acc, r) => acc + int(r.cs), 0)

  const pa = paRows.length
  const tb = h1 + h2 * 2 + h3 * 3 + hr * 4

  const avg = ab > 0 ? h / ab : null
  const obpDen = ab + bb + hbp + sf
  const obp = obpDen > 0 ? (h + bb + hbp) / obpDen : null
  const slg = ab > 0 ? tb / ab : null
  const ops = obp != null && slg != null ? obp + slg : null

  return {
    g: gameIds.size,
    pa,
    ab,
    r,
    h,
    h2,
    h3,
    hr,
    tb,
    rbi,
    so,
    bb,
    ibb,
    hbp,
    sh,
    sf,
    sb,
    cs,
    gidp,
    avg: fmtSlash3(avg),
    obp: fmtSlash3(obp),
    slg: fmtSlash3(slg),
    ops: fmtSlash3(ops),
  }
}

export function loadPilotRispStats(yahooId: string, date: string) {
  if (yahooId !== PILOT_PLAYER_YAHOO_ID) return null
  const csvPath = path.join(process.cwd(), '_data', 'yahoo_games_pilot', 'plate_appearances_normalized.csv')
  if (!fs.existsSync(csvPath)) return null

  const content = fs.readFileSync(csvPath, 'utf-8')
  const lines = content.split(/\r?\n/).filter((l) => l.trim())
  if (lines.length < 2) return null
  const headers = lines[0].split(',').map((h) => h.trim())

  const rows: Array<Record<string, string>> = []
  for (let i = 1; i < lines.length; i++) {
    const values = lines[i].split(',').map((v) => v.trim())
    const row: Record<string, string> = {}
    headers.forEach((h, idx) => {
      row[h] = values[idx] ?? ''
    })
    if (row.batter_id !== yahooId) continue
    if (row.date !== date) continue
    rows.push(row)
  }

  const rispRows = rows.filter((r) => r.risp === '1')
  const noRispRows = rows.filter((r) => r.risp !== '1')
  return {
    risp: computeBattingFromPaRows(rispRows),
    no_risp: computeBattingFromPaRows(noRispRows),
  }
}

export function loadPilotBattingStats(yahooId: string): SeasonStatsRow[] {
  const csvPath = path.join(
    process.cwd(),
    '_data',
    'yahoo_games_pilot',
    'batting_stats.csv'
  )
  if (!fs.existsSync(csvPath)) return []

  const content = fs.readFileSync(csvPath, 'utf-8')
  const lines = content.split(/\r?\n/).filter((l) => l.trim())
  if (lines.length < 2) return []

  const headers = lines[0].split(',').map((h) => h.trim())
  const rows: SeasonStatsRow[] = []

  for (let i = 1; i < lines.length; i++) {
    const values = lines[i].split(',').map((v) => v.trim())
    const row: Record<string, string> = {}
    headers.forEach((h, idx) => {
      row[h] = values[idx] ?? ''
    })
    if (row.player_id !== yahooId) continue

    const splitType = row.split_type || ''
    const splitValue = row.split_value || ''
    const h1 = parseInt(row.h1 || '0', 10)
    const h2 = parseInt(row.h2 || '0', 10)
    const h3 = parseInt(row.h3 || '0', 10)
    const hr = parseInt(row.hr || '0', 10)
    const tb = h1 + h2 * 2 + h3 * 3 + hr * 4
    rows.push({
      split_type: splitType,
      split_value: splitValue,
      split_label: formatSplitLabel(splitType, splitValue),
      g: parseInt(row.g || '0', 10),
      pa: parseInt(row.pa || '0', 10),
      ab: parseInt(row.ab || '0', 10),
      r: parseInt(row.r || '0', 10),
      h: parseInt(row.h || '0', 10),
      h1,
      h2,
      h3,
      hr,
      tb,
      rbi: parseInt(row.rbi || '0', 10),
      so: parseInt(row.so || '0', 10),
      bb: parseInt(row.bb || '0', 10),
      ibb: parseInt(row.ibb || '0', 10),
      hbp: parseInt(row.hbp || '0', 10),
      sh: parseInt(row.sh || '0', 10),
      sf: parseInt(row.sf || '0', 10),
      sb: parseInt(row.sb || '0', 10),
      cs: parseInt(row.cs || '0', 10),
      gidp: parseInt(row.gidp || '0', 10),
      avg: row.avg || '.000',
      obp: row.obp || '.000',
      slg: row.slg || '.000',
      ops: row.ops || '.000',
      risp_avg: row.risp_avg ?? '',
      risp_ab: parseInt(row.risp_ab || '0', 10),
      risp_h: parseInt(row.risp_h || '0', 10),
      sb_pct: row.sb_pct ?? '',
      isop: row.isop ?? '',
      isod: row.isod ?? '',
      babip: row.babip ?? '',
      bb_pct: row.bb_pct ?? '',
      k_pct: row.k_pct ?? '',
      bbk: row.bbk ?? '',
      gpa: row.gpa ?? '',
      rc: row.rc ?? '',
      xr: row.xr ?? '',
      seca: row.seca ?? '',
      ta: row.ta ?? '',
      noi: row.noi ?? '',
    })
  }

  // 通算を先頭に、それ以外は split_type, split_value 順
  const total = rows.filter((r) => r.split_type === 'total')
  const rest = rows
    .filter((r) => r.split_type !== 'total')
    .sort((a, b) => {
      if (a.split_type !== b.split_type) return a.split_type.localeCompare(b.split_type)
      return a.split_value.localeCompare(b.split_value)
    })
  return [...total, ...rest]
}

/** 菊池涼介 2026-03-04 ブロック集計データ（D,E,F,G,H,I,J） */
export type PilotBlocksData = {
  meta: { batter_id: string; batter_name: string; date: string; pa_count: number; game_ids: string[] }
  blocks: {
    D?: { source: string; rows: Record<string, unknown>[] }
    E?: { source: string; available: boolean; note?: string }
    F?: {
      by_month: Record<string, number>
      by_day_night: Record<string, number>
      by_stadium: Record<string, number>
      by_base_state: Record<string, number>
      by_risp: Record<string, number>
      by_risp_stats?: {
        risp: { pa: number; ab: number; r: number; h: number; h2: number; h3: number; hr: number; tb: number; rbi: number; so: number; bb: number; ibb: number; hbp: number; sh: number; sf: number; sb: number; cs: number; g: number; avg: string; obp: string; slg: string; ops: string }
        no_risp: { pa: number; ab: number; r: number; h: number; h2: number; h3: number; hr: number; tb: number; rbi: number; so: number; bb: number; ibb: number; hbp: number; sh: number; sf: number; sb: number; cs: number; g: number; avg: string; obp: string; slg: string; ops: string }
      }
    }
    G?: {
      hit_direction: Record<string, number>
      course: Record<string, number>
      pitch_type: Record<string, number>
    }
    H?: {
      ground_fly: Record<string, number>
      vs_left: number
      vs_right: number
      vs_unknown: number
    }
    I?: {
      by_inning: Record<string, number>
      by_outs: Record<string, number>
      by_base_state: Record<string, number>
    }
    J?: { sb: number; cs: number; hr: number; clutch_hr_risp: number; recent_date: string }
  }
}

export function loadPilotBlocksData(yahooId: string): PilotBlocksData | null {
  if (yahooId !== PILOT_PLAYER_YAHOO_ID) return null
  const jsonPath = path.join(process.cwd(), '_data', 'yahoo_games_pilot', 'kikuchi_20260304_blocks.json')
  if (!fs.existsSync(jsonPath)) return null
  try {
    const raw = fs.readFileSync(jsonPath, 'utf-8')
    return JSON.parse(raw) as PilotBlocksData
  } catch {
    return null
  }
}

