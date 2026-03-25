/**
 * 試合・投手指定でコース別（対右/対左）投球成績を返す API
 * fetch_pitcher_zone_stats.py で生成した JSON を読み込む
 */

import { NextResponse } from 'next/server'
import fs from 'fs'
import path from 'path'

export const dynamic = 'force-dynamic'

export type ZoneStat = {
  zoneId: number
  pitches: number
  ab: number
  h: number
  hr: number
  ops: string
  avg: string
}

export type ZoneStatsResponse = {
  game_id: string
  pitcher_id: string
  vsRight: ZoneStat[]
  vsLeft: ZoneStat[]
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
    const filePath = path.join(dataDir, `zone_stats_${gameId}_${pitcherId}.json`)

    if (!fs.existsSync(filePath)) {
      return NextResponse.json(
        {
          error:
            'Zone stats not found. Run: python scripts/fetch_pitcher_zone_stats.py --game-id ' +
            gameId +
            ' --pitcher-id ' +
            pitcherId,
        },
        { status: 404 }
      )
    }

    const raw = fs.readFileSync(filePath, 'utf-8')
    const data: ZoneStatsResponse = JSON.parse(raw)
    return NextResponse.json(data)
  } catch (error) {
    console.error('[game-zone-stats] Error:', error)
    return NextResponse.json({ error: 'Failed to load zone stats' }, { status: 500 })
  }
}
