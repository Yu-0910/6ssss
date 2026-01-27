/**
 * API Route: 2025年CLの打撃成績リーダーを取得
 */

import { get2025CLBattingLeaders } from '@/lib/ranking/leaders'
import { NextResponse } from 'next/server'

export async function GET() {
  try {
    const data = get2025CLBattingLeaders()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Error fetching 2025 CL batting leaders:', error)
    return NextResponse.json(
      { error: 'Failed to fetch leaders' },
      { status: 500 }
    )
  }
}









