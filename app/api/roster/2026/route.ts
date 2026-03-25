/**
 * 2026年NPB選手名簿API
 * データページで打・投の利き手を活用するためのエンドポイント
 */

import { NextResponse } from "next/server"
import { getNpbRoster2026 } from "@/lib/npbRoster"

export async function GET() {
  const roster = getNpbRoster2026()
  return NextResponse.json({
    year: 2026,
    count: roster.length,
    players: roster,
  })
}
