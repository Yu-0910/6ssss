/**
 * Phase 4: 投球詳細パイロット API
 * 菊池涼介のみ、打席別の球種・コース（25マス）情報を返す
 */

import { NextResponse } from 'next/server'
import { getYahooIdForPilot } from '@/lib/seasonStatsPilot'
import { loadPitchDetails, loadPitchTypeStats, loadZoneStats } from '@/lib/pitchDetailsPilot'

export const dynamic = 'force-dynamic'

export async function GET(
  _request: Request,
  context: { params: Promise<{ playerId: string }> | { playerId: string } }
) {
  try {
    const { playerId } =
      context.params instanceof Promise ? await context.params : context.params
    const yahooId = getYahooIdForPilot(playerId)
    if (!yahooId) {
      return NextResponse.json({
        plateAppearances: [],
        pitchTypeStats: [],
        zoneStats: [],
        isPilot: false,
      })
    }
    const plateAppearances = loadPitchDetails(yahooId)
    const pitchTypeStats = loadPitchTypeStats(yahooId)
    const zoneStats = loadZoneStats(yahooId)
    return NextResponse.json({
      plateAppearances,
      pitchTypeStats,
      zoneStats,
      isPilot: plateAppearances.length > 0,
    })
  } catch (error) {
    console.error('[pitch-details] Error:', error)
    return NextResponse.json(
      { error: 'Failed to load pitch details' },
      { status: 500 }
    )
  }
}
