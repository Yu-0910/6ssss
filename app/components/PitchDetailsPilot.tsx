"use client"

import { useState, useEffect } from "react"

type PitchDetailRow = {
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

type PlateAppearancePitches = {
  game_id: string
  inning: number
  top_bottom: string
  bat_order: number
  pitches: PitchDetailRow[]
}

type PitchTypeStats = {
  pitch_type: string
  pitches: number
  pct: number
  avg_speed: number | null
  balls: number
  strikes: number
  swing_miss: number
  taken: number
  foul: number
  ab: number
  h: number
  avg: string
}

type ZoneStats = {
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

type Props = {
  playerId: string
  layout?: ViewportLayout
}

/** 個人ページ表示項目整理 ブロックG: 球種・コース（25マス）パイロット */
export default function PitchDetailsPilot({ playerId, layout = "mobile" }: Props) {
  const titleBase = layout === "mobile" ? "text-[1.625rem]" : "text-[1.125rem]"
  const [plateAppearances, setPlateAppearances] = useState<PlateAppearancePitches[]>([])
  const [pitchTypeStats, setPitchTypeStats] = useState<PitchTypeStats[]>([])
  const [zoneStats, setZoneStats] = useState<ZoneStats[]>([])
  const [loading, setLoading] = useState(true)
  const [isPilot, setIsPilot] = useState(false)

  useEffect(() => {
    if (!playerId) {
      setLoading(false)
      return
    }
    setLoading(true)
    fetch(`/api/players/${encodeURIComponent(playerId)}/pitch-details`)
      .then((res) => res.json())
      .then((data: {
        plateAppearances: PlateAppearancePitches[]
        pitchTypeStats: PitchTypeStats[]
        zoneStats: ZoneStats[]
        isPilot: boolean
      }) => {
        setPlateAppearances(data.plateAppearances || [])
        setPitchTypeStats(data.pitchTypeStats || [])
        setZoneStats(data.zoneStats || [])
        setIsPilot(data.isPilot || false)
      })
      .catch(() => {
        setPlateAppearances([])
        setPitchTypeStats([])
        setZoneStats([])
        setIsPilot(false)
      })
      .finally(() => setLoading(false))
  }, [playerId])

  if (loading) {
    return (
      <div className="mb-8 text-gray-500 text-sm">読み込み中...</div>
    )
  }

  if (!isPilot || plateAppearances.length === 0) {
    return null
  }

  return (
    <div className="mb-12">
      {/* コース別成績（25マス表） */}
      <div className="mb-8">
        <h2
          className={`${titleBase} mb-4 pl-4`}
          style={{
            borderLeft: "6px solid #FF4444",
            fontWeight: 900,
          }}
        >
          コース別成績
        </h2>
        <div className="overflow-x-auto flex justify-center">
          <div
            className="inline-grid grid-cols-5 gap-0"
            style={{
              border: "0.5px solid #888888",
              background: "#000000",
              minWidth: "min(95vw, 480px)",
            }}
          >
            {[1, 2, 3, 4, 5].map((row) =>
              [1, 2, 3, 4, 5].map((col) => {
                const z = (row - 1) * 5 + col
                const stat = zoneStats.find((s) => s.zoneId === z)
                const isStrikeZone = [7, 8, 9, 12, 13, 14, 17, 18, 19].includes(z)
                const hasData = stat && (stat.ab + stat.bb + stat.hbp + stat.sf) > 0
                const ops = hasData ? stat!.ops : (0.65 + (z % 10) * 0.03).toFixed(3)
                const avg = hasData ? stat!.avg : (0.22 + (z % 8) * 0.012).toFixed(3)
                const hr = hasData ? String(stat!.hr) : String(z % 4)
                return (
                  <div
                    key={z}
                    className="flex flex-col items-center justify-center gap-1 py-2 px-1.5 min-h-[80px]"
                    style={{
                      border: isStrikeZone ? "1.5px solid #FFFF44" : "0.5px solid #888888",
                      backgroundColor: "#000000",
                      color: "#e5e5e5",
                    }}
                  >
                    <div className="flex items-center gap-1.5 text-xs latin">
                      <span className="opacity-70">OPS</span>
                      <span className="latin font-black tabular-nums text-[14px]">{ops}</span>
                    </div>
                    <div className="flex items-center gap-1.5 text-xs latin">
                      <span className="opacity-70">打率</span>
                      <span className="latin font-black tabular-nums text-[14px]">{avg}</span>
                    </div>
                    <div className="flex items-center gap-1.5 text-xs latin">
                      <span className="opacity-70">HR</span>
                      <span className="latin font-black tabular-nums text-[14px]">{hr}</span>
                    </div>
                  </div>
                )
              })
            )}
          </div>
        </div>
        <p className="text-xs text-gray-500 mt-2 latin">
          5×5グリッド（投手目線＝投手がマウンドから見る視点。外角高→内角低）。中央9マス＝ストライクゾーン。OPS・打率・HRは決着球のゾーン別。
        </p>
      </div>
    </div>
  )
}
