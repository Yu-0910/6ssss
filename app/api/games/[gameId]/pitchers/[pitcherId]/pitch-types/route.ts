/**
 * 試合・投手指定で球種別成績を返す API
 * fetch_game_pitch_types.py で生成した JSON を読み込む
 */

import { NextResponse } from 'next/server'
import fs from 'fs'
import path from 'path'

export const dynamic = 'force-dynamic'

export type GamePitchTypeRow = {
  pitch_type: string
  pitches: number
  pct: number
  avg_speed_kmh: number | null
  swing_miss: number
  taken: number
  foul: number
  balls: number
  strike_pct: string
  whiff_pct: string
  avg: string
  ab: number
  h: number
  hr: number
  so: number
  bb: number
  hbp: number
}

export type GamePitchTypesResponse = {
  game_id: string
  pitcher_id: string
  pitches_total: number
  rows: GamePitchTypeRow[]
  total_row: GamePitchTypeRow
}

export async function GET(
  _request: Request,
  context: {
    params: Promise<{ gameId: string; pitcherId: string }> | { gameId: string; pitcherId: string }
  }
) {
  try {
    const params = context.params instanceof Promise ? await context.params : context.params
    const { gameId, pitcherId } = params
    if (!gameId || !pitcherId) {
      return NextResponse.json({ error: 'gameId and pitcherId required' }, { status: 400 })
    }

    const dataDir = path.join(process.cwd(), '_data', 'yahoo_games_pilot')
    const filePath = path.join(dataDir, `pitch_by_type_${gameId}_${pitcherId}.json`)

    if (!fs.existsSync(filePath)) {
      return NextResponse.json(
        { error: 'Pitch type data not found. Run: python scripts/fetch_game_pitch_types.py --game-id ' + gameId + ' --pitcher-id ' + pitcherId },
        { status: 404 }
      )
    }

    const raw = fs.readFileSync(filePath, 'utf-8')
    const data: GamePitchTypesResponse = JSON.parse(raw)
    return NextResponse.json(data)
  } catch (error) {
    console.error('[game-pitch-types] Error:', error)
    return NextResponse.json({ error: 'Failed to load pitch types' }, { status: 500 })
  }
}
