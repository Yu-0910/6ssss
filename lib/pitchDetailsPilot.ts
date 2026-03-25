/**
 * Phase 4: 投球詳細パイロット
 * pitch_details_kikuchi.csv から菊池涼介の打席別球種・コース情報を取得
 */

import fs from 'fs'
import path from 'path'
import { getYahooIdForPilot } from './seasonStatsPilot'

export type PitchDetailRow = {
  game_id: string
  inning: number
  top_bottom: string
  bat_order: number
  pitcher_id: string
  batter_id: string
  pitch_no: number
  pitch_type: string
  speed_kmh: string
  result: string
  zone_top_px: string
  zone_left_px: string
  zone_row: string
  zone_col: string
  zone_id: string
}

/** 打席単位にまとめた投球詳細 */
export type PlateAppearancePitches = {
  inning: number
  top_bottom: string
  bat_order: number
  game_id: string
  pitches: PitchDetailRow[]
}

export function loadPitchDetails(yahooId: string): PlateAppearancePitches[] {
  if (yahooId !== '1100082') return []

  const csvPath = path.join(
    process.cwd(),
    '_data',
    'yahoo_games_pilot',
    'pitch_details_kikuchi.csv'
  )
  if (!fs.existsSync(csvPath)) return []

  const text = fs.readFileSync(csvPath, 'utf-8')
  const lines = text.split(/\r?\n/).filter(Boolean)
  if (lines.length < 2) return []

  const header = lines[0].split(',')
  const rows: PitchDetailRow[] = []
  for (let i = 1; i < lines.length; i++) {
    const cols = lines[i].split(',')
    if (cols.length < header.length) continue
    rows.push({
      game_id: cols[0] ?? '',
      inning: parseInt(cols[1] ?? '0', 10) || 0,
      top_bottom: cols[2] ?? '',
      bat_order: parseInt(cols[3] ?? '0', 10) || 0,
      pitcher_id: cols[4] ?? '',
      batter_id: cols[5] ?? '',
      pitch_no: parseInt(cols[6] ?? '0', 10) || 0,
      pitch_type: cols[7] ?? '',
      speed_kmh: cols[8] ?? '',
      result: cols[9] ?? '',
      zone_top_px: cols[10] ?? '',
      zone_left_px: cols[11] ?? '',
      zone_row: cols[12] ?? '',
      zone_col: cols[13] ?? '',
      zone_id: cols[14] ?? '',
    })
  }

  // 打席単位にグルーピング
  const paMap = new Map<string, PlateAppearancePitches>()
  for (const r of rows) {
    const key = `${r.game_id}-${r.inning}-${r.top_bottom}-${r.bat_order}`
    let pa = paMap.get(key)
    if (!pa) {
      pa = {
        game_id: r.game_id,
        inning: r.inning,
        top_bottom: r.top_bottom,
        bat_order: r.bat_order,
        pitches: [],
      }
      paMap.set(key, pa)
    }
    pa.pitches.push(r)
  }

  return Array.from(paMap.values()).sort((a, b) => {
    if (a.inning !== b.inning) return a.inning - b.inning
    if (a.top_bottom !== b.top_bottom) return a.top_bottom === '表' ? -1 : 1
    return a.bat_order - b.bat_order
  })
}

/** 球種別成績（G-3）+ フル指標 */
export type PitchTypeStats = {
  pitch_type: string
  pitches: number
  pct: number
  avg_speed: number | null
  balls: number
  strikes: number
  strike_pct: string
  swing_miss: number
  taken: number
  foul: number
  whiff_pct: string
  ab: number
  h: number
  hr: number
  so: number
  bb: number
  hbp: number
  tb: number
  avg: string
  ops: string
}

/** 打席の決着球か（打数にカウント） */
function isSettlementResult(r: string): boolean {
  const s = (r || '').trim()
  if (/^(左飛|中飛|右飛|レフトフライ|センターフライ|ライトフライ|フライ)$/.test(s)) return true
  if (/ゴロ|ライナー|併殺/.test(s)) return true
  if (/^(空振り|見逃し)/.test(s)) return true
  if (/三振|空三振|見三振/.test(s)) return true
  if (/安打|ヒット|二塁打|三塁打|本塁打/.test(s)) return true
  return false
}

/** 安打か */
function isHit(r: string): boolean {
  const s = (r || '').trim()
  return /^(左安|右安|中安|二塁|三塁|本塁|ソロ|満塁)/.test(s) || /安打|ヒット/.test(s)
}

/** 塁打数を取得（単打=1, 二塁=2, 三塁=3, 本塁打=4） */
function getTotalBases(r: string): number {
  const s = (r || '').trim()
  if (/本塁打|ホームラン|HR/i.test(s)) return 4
  if (/三塁打/.test(s)) return 3
  if (/二塁打/.test(s)) return 2
  if (isHit(s)) return 1
  return 0
}

/** 本塁打か */
function isHomeRun(r: string): boolean {
  return getTotalBases(r) === 4
}

/** 四球・敬遠か */
function isWalk(r: string): boolean {
  return /四球|敬遠/.test((r || '').trim())
}

/** 死球か */
function isHBP(r: string): boolean {
  return /死球/.test((r || '').trim())
}

/** 犠飛か */
function isSF(r: string): boolean {
  return /犠飛/.test((r || '').trim())
}

/** 三振か（決着球が空振り・見逃し） */
function isStrikeout(r: string): boolean {
  const s = (r || '').trim()
  return /^空振り|^見逃し|三振|空三振|見三振/.test(s)
}

/** 投球詳細から球種別成績を集計 */
export function aggregateByPitchType(plateAppearances: PlateAppearancePitches[]): PitchTypeStats[] {
  const allPitches = plateAppearances.flatMap((pa) => pa.pitches)
  if (allPitches.length === 0) return []

  const total = allPitches.length
  const byType = new Map<string, PitchDetailRow[]>()
  for (const p of allPitches) {
    const t = p.pitch_type || '不明'
    if (!byType.has(t)) byType.set(t, [])
    byType.get(t)!.push(p)
  }

  // 打席の最終球 = 決着球。その球種に打数・安打・HR・三振・四球・死球・犠飛・塁打をカウント
  const settlementByType = new Map<string, { ab: number; h: number; hr: number; tb: number; so: number; bb: number; hbp: number; sf: number }>()
  for (const pa of plateAppearances) {
    if (pa.pitches.length === 0) continue
    const last = pa.pitches[pa.pitches.length - 1]
    const t = last.pitch_type || '不明'
    if (!settlementByType.has(t)) settlementByType.set(t, { ab: 0, h: 0, hr: 0, tb: 0, so: 0, bb: 0, hbp: 0, sf: 0 })
    const rec = settlementByType.get(t)!
    if (isSettlementResult(last.result)) {
      rec.ab += 1
      if (isHit(last.result)) {
        rec.h += 1
        rec.tb += getTotalBases(last.result)
        if (isHomeRun(last.result)) rec.hr += 1
      }
    }
    if (isStrikeout(last.result)) rec.so += 1
    if (isWalk(last.result)) rec.bb += 1
    if (isHBP(last.result)) rec.hbp += 1
    if (isSF(last.result)) rec.sf += 1
  }

  const result: PitchTypeStats[] = []
  for (const [pitchType, pitches] of byType.entries()) {
    const balls = pitches.filter((p) => /^ボール/.test(p.result)).length
    const swingMiss = pitches.filter((p) => /^空振り/.test(p.result)).length
    const taken = pitches.filter((p) => /^見逃し/.test(p.result)).length
    const foul = pitches.filter((p) => /^ファウル/.test(p.result)).length
    const set = settlementByType.get(pitchType) || { ab: 0, h: 0, hr: 0, tb: 0, so: 0, bb: 0, hbp: 0, sf: 0 }
    // ストライク = 空振り+見逃し+ファウル+インプレイ（打数でアウト/安打＝三振以外のAB）
    const inPlay = set.ab - set.so
    const strikes = swingMiss + taken + foul + inPlay

    const speeds = pitches.map((p) => parseInt(p.speed_kmh, 10)).filter((n) => !isNaN(n))
    const avgSpeed = speeds.length > 0 ? speeds.reduce((a, b) => a + b, 0) / speeds.length : null

    const strikePct = pitches.length > 0 ? ((strikes / pitches.length) * 100).toFixed(1) + '%' : '—'
    const swingTotal = swingMiss + foul + set.ab
    const whiffPct = swingTotal > 0 ? ((swingMiss / swingTotal) * 100).toFixed(1) + '%' : '—'

    const avg = set.ab > 0 ? (set.h / set.ab).toFixed(3) : '—'
    const pa = set.ab + set.bb + set.hbp + set.sf
    const obp = pa > 0 ? (set.h + set.bb + set.hbp) / pa : 0
    const slg = set.ab > 0 ? set.tb / set.ab : 0
    const ops = set.ab > 0 || pa > 0 ? (obp + slg).toFixed(3) : '—'

    result.push({
      pitch_type: pitchType,
      pitches: pitches.length,
      pct: total > 0 ? (pitches.length / total) * 100 : 0,
      avg_speed: avgSpeed,
      balls,
      strikes,
      strike_pct: strikePct,
      swing_miss: swingMiss,
      taken,
      foul,
      whiff_pct: whiffPct,
      ab: set.ab,
      h: set.h,
      hr: set.hr,
      so: set.so,
      bb: set.bb,
      hbp: set.hbp,
      tb: set.tb,
      avg,
      ops,
    })
  }

  return result.sort((a, b) => b.pitches - a.pitches)
}

/** 球種別成績をロード（菊池のみ） */
export function loadPitchTypeStats(yahooId: string): PitchTypeStats[] {
  const pas = loadPitchDetails(yahooId)
  return aggregateByPitchType(pas)
}

/** ゾーン別成績（25マス） */
export type ZoneStats = {
  zoneId: number
  pitches: number
  ab: number
  h: number
  hr: number
  tb: number
  bb: number
  hbp: number
  sf: number
  avg: string
  ops: string
}

/** 決着球でゾーンに何か記録されるか（AB/BB/HBP/SF） */
function isZoneSettlement(r: string): boolean {
  return isSettlementResult(r) || isWalk(r) || isHBP(r) || isSF(r)
}

/** 投球詳細からゾーン別成績を集計 */
export function aggregateByZone(
  plateAppearances: PlateAppearancePitches[]
): ZoneStats[] {
  const pitchCount = new Map<number, number>()
  const byZone = new Map<
    number,
    { ab: number; h: number; hr: number; tb: number; bb: number; hbp: number; sf: number }
  >()

  for (const pa of plateAppearances) {
    for (const p of pa.pitches) {
      const zid = parseInt(p.zone_id, 10)
      if (zid >= 1 && zid <= 25) {
        pitchCount.set(zid, (pitchCount.get(zid) ?? 0) + 1)
      }
    }
    if (pa.pitches.length > 0) {
      const last = pa.pitches[pa.pitches.length - 1]
      const zid = parseInt(last.zone_id, 10)
      if (zid >= 1 && zid <= 25 && isZoneSettlement(last.result)) {
        if (!byZone.has(zid)) {
          byZone.set(zid, { ab: 0, h: 0, hr: 0, tb: 0, bb: 0, hbp: 0, sf: 0 })
        }
        const rec = byZone.get(zid)!
        if (isWalk(last.result)) {
          rec.bb += 1
        } else if (isHBP(last.result)) {
          rec.hbp += 1
        } else if (isSF(last.result)) {
          rec.sf += 1
        } else if (isSettlementResult(last.result)) {
          rec.ab += 1
          if (isHit(last.result)) {
            rec.h += 1
            rec.tb += getTotalBases(last.result)
            if (isHomeRun(last.result)) rec.hr += 1
          }
        }
      }
    }
  }

  const result: ZoneStats[] = []
  for (let z = 1; z <= 25; z++) {
    const pitches = pitchCount.get(z) ?? 0
    const rec = byZone.get(z) ?? {
      ab: 0,
      h: 0,
      hr: 0,
      tb: 0,
      bb: 0,
      hbp: 0,
      sf: 0,
    }
    const { ab, h, hr, tb, bb, hbp, sf } = rec
    const avg = ab > 0 ? (h / ab).toFixed(3) : '—'
    const pa = ab + bb + hbp + sf
    const obp = pa > 0 ? (h + bb + hbp) / pa : 0
    const slg = ab > 0 ? tb / ab : 0
    const opsVal = obp + slg
    const ops = pa > 0 ? opsVal.toFixed(3) : '—'

    result.push({
      zoneId: z,
      pitches,
      ab: rec.ab,
      h: rec.h,
      hr: rec.hr,
      tb: rec.tb,
      bb: rec.bb,
      hbp: rec.hbp,
      sf: rec.sf,
      avg,
      ops,
    })
  }
  return result
}

/** ゾーン別成績をロード（菊池のみ） */
export function loadZoneStats(yahooId: string): ZoneStats[] {
  const pas = loadPitchDetails(yahooId)
  return aggregateByZone(pas)
}

