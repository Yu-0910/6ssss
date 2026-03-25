/**
 * Phase 4: パイロット今季成績 API
 * 菊池涼介（広島）のみ、Yahoo pilot の打撃スプリット成績とブロック集計を返す
 */

import { NextResponse } from 'next/server'
import {
  getYahooIdForPilot,
  loadPilotBattingStats,
  loadPilotBlocksData,
  loadPilotRispStats,
} from '@/lib/seasonStatsPilot'
import { loadPitchTypeStats } from '@/lib/pitchDetailsPilot'

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
      return NextResponse.json({ stats: [], isPilot: false, blocks: null, pitchTypeStats: [] })
    }
    const stats = loadPilotBattingStats(yahooId)
    const blocks = loadPilotBlocksData(yahooId)
    if (blocks?.meta?.date && blocks.blocks?.F) {
      const byRispStats = loadPilotRispStats(yahooId, blocks.meta.date)
      if (byRispStats) {
        blocks.blocks.F.by_risp_stats = byRispStats
      }
    }
    const pitchTypeStats = loadPitchTypeStats(yahooId)
    return NextResponse.json({ stats, isPilot: true, blocks, pitchTypeStats })
  } catch (error) {
    console.error('[season-stats] Error:', error)
    return NextResponse.json(
      { error: 'Failed to load season stats', stats: [], blocks: null, pitchTypeStats: [] },
      { status: 500 }
    )
  }
}
