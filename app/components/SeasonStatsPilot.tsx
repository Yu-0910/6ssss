"use client"

import { useState, useEffect } from "react"
import dynamic from "next/dynamic"
import type { SeasonStatsRow, PilotBlocksData } from "@/lib/seasonStatsPilot"
import type { PitchTypeStats } from "@/lib/pitchDetailsPilot"
import type { ViewportLayout } from "@/lib/viewportLayout"

const PitchTypePieChart = dynamic(() => import("@/app/components/PitchTypePieChart"), { ssr: false })

export type PilotSeasonDetailTab = "basic" | "pitch" | "situation" | "period"

type Props = {
  playerId: string
  /** 菊池ページの今季サブタブ。未指定時は全ブロックを表示 */
  seasonDetailTab?: PilotSeasonDetailTab
  layout?: ViewportLayout
}

/** 火曜始まり・日曜終わりの週範囲を "M/D〜M/D" で返す */
function getWeekRangeTueToSun(dateStr: string): string {
  const d = new Date(dateStr + "T12:00:00")
  const day = d.getDay() // 0=Sun, 1=Mon, 2=Tue, ..., 6=Sat
  const daysFromTue = (day + 5) % 7 // 直前の火曜までの日数
  const tue = new Date(d)
  tue.setDate(tue.getDate() - daysFromTue)
  const sun = new Date(tue)
  sun.setDate(sun.getDate() + 5)
  return `${tue.getMonth() + 1}/${tue.getDate()}〜${sun.getMonth() + 1}/${sun.getDate()}`
}

/** 球団別カラー（ランキングUIと同様） */
const TEAM_COLORS: Record<string, string> = {
  日本ハム: "#0077c8",
  楽天: "#7a0019",
  西武: "#004098",
  ロッテ: "#222",
  オリックス: "#b79e51",
  ソフトバンク: "#ffdb00",
  巨人: "#ff6600",
  ヤクルト: "#2bbb3f",
  横浜: "#0067c0",
  中日: "#004ea2",
  阪神: "#ffde00",
  広島: "#d60718",
}

/** 個人ページ表示項目整理 ブロックA・D 準拠の今季成績 */
export default function SeasonStatsPilot({ playerId, seasonDetailTab, layout = "mobile" }: Props) {
  const isMobile = layout === "mobile"
  const titleBase = isMobile ? "text-[1.625rem]" : "text-[1.125rem]"
  const [stats, setStats] = useState<SeasonStatsRow[]>([])
  const [blocks, setBlocks] = useState<PilotBlocksData | null>(null)
  const [pitchTypeStats, setPitchTypeStats] = useState<PitchTypeStats[]>([])
  const [loading, setLoading] = useState(true)
  const [isPilot, setIsPilot] = useState(false)
  useEffect(() => {
    if (!playerId) {
      setLoading(false)
      return
    }
    setLoading(true)
    fetch(`/api/players/${encodeURIComponent(playerId)}/season-stats`)
      .then((res) => res.json())
      .then((data: { stats: SeasonStatsRow[]; isPilot: boolean; blocks?: PilotBlocksData | null; pitchTypeStats?: PitchTypeStats[] }) => {
        setStats(data.stats || [])
        setIsPilot(data.isPilot || false)
        setBlocks(data.blocks ?? null)
        setPitchTypeStats(data.pitchTypeStats ?? [])
      })
      .catch(() => {
        setStats([])
        setIsPilot(false)
        setBlocks(null)
        setPitchTypeStats([])
      })
      .finally(() => setLoading(false))
  }, [playerId])

  if (loading) {
    return (
      <div className="mb-12 text-gray-500 text-sm">読み込み中...</div>
    )
  }

  if (!isPilot || stats.length === 0) {
    return <div className="mb-12" />
  }

  const totalRow = stats.find((r) => r.split_type === "total" && r.split_value === "total")
  const sbPct = totalRow?.sb_pct || (totalRow && totalRow.sb + totalRow.cs > 0
    ? ((totalRow.sb / (totalRow.sb + totalRow.cs)) * 100).toFixed(1)
    : "")
  const fmt = (v: string | undefined) => (v != null && v !== "" ? v : "—")
  const showPilotTab = (t: PilotSeasonDetailTab) => seasonDetailTab == null || seasonDetailTab === t

  return (
    <div className="mb-12">
      {/* 通算成績（1つの表・実データ） */}
      {totalRow && (
        <div className="mb-8">
          {showPilotTab("basic") && (
            <>
          <h2
            className={`${titleBase} mb-4 pl-4`}
            style={{
              borderLeft: "6px solid #FF4444",
              fontWeight: 900,
            }}
          >
            通算成績
          </h2>
          <div className="overflow-hidden overflow-x-auto mb-4">
            <table className="text-xs" style={{ fontVariantNumeric: "tabular-nums", borderCollapse: "collapse", border: "1px solid #555", tableLayout: "fixed", width: "100%" }}>
              <tbody>
                <tr style={{ backgroundColor: "#FFFF44", color: "#000000" }}>
                  <th className="px-1 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-gray-500 first:border-l-0">打率</th>
                  <th className="px-1 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-gray-500">試合</th>
                  <th className="px-1 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-gray-500">打席</th>
                  <th className="px-1 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-gray-500">打数</th>
                  <th className="px-1 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-gray-500">得点</th>
                  <th className="px-1 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-gray-500">安打</th>
                  <th className="px-1 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-gray-500">２Ｂ</th>
                  <th className="px-1 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-gray-500">３Ｂ</th>
                  <th className="px-1 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-gray-500">本塁</th>
                  <th className="px-1 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-gray-500">塁打</th>
                  <th className="px-1 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-gray-500">打点</th>
                  <th className="px-1 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-gray-500">三振</th>
                  <th className="px-1 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-gray-500">四球</th>
                </tr>
                <tr style={{ backgroundColor: "rgba(255,255,255,0.03)", borderTop: "1px solid #333" }}>
                  <td className="px-1 py-2 text-center latin font-black tabular-nums text-[14px] border-l border-gray-500 first:border-l-0">{totalRow.avg}</td>
                  <td className="px-1 py-2 text-center latin font-black tabular-nums text-[14px] border-l border-gray-500">{totalRow.g}</td>
                  <td className="px-1 py-2 text-center latin font-black tabular-nums text-[14px] border-l border-gray-500">{totalRow.pa}</td>
                  <td className="px-1 py-2 text-center latin font-black tabular-nums text-[14px] border-l border-gray-500">{totalRow.ab}</td>
                  <td className="px-1 py-2 text-center latin font-black tabular-nums text-[14px] border-l border-gray-500">{totalRow.r}</td>
                  <td className="px-1 py-2 text-center latin font-black tabular-nums text-[14px] border-l border-gray-500">{totalRow.h}</td>
                  <td className="px-1 py-2 text-center latin font-black tabular-nums text-[14px] border-l border-gray-500">{totalRow.h2}</td>
                  <td className="px-1 py-2 text-center latin font-black tabular-nums text-[14px] border-l border-gray-500">{totalRow.h3}</td>
                  <td className="px-1 py-2 text-center latin font-black tabular-nums text-[14px] border-l border-gray-500">{totalRow.hr}</td>
                  <td className="px-1 py-2 text-center latin font-black tabular-nums text-[14px] border-l border-gray-500">{totalRow.tb}</td>
                  <td className="px-1 py-2 text-center latin font-black tabular-nums text-[14px] border-l border-gray-500">{totalRow.rbi}</td>
                  <td className="px-1 py-2 text-center latin font-black tabular-nums text-[14px] border-l border-gray-500">{totalRow.so}</td>
                  <td className="px-1 py-2 text-center latin font-black tabular-nums text-[14px] border-l border-gray-500">{totalRow.bb}</td>
                </tr>
                <tr style={{ backgroundColor: "#FFFF44", color: "#000000" }}>
                  <th className="px-1 py-1.5 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-gray-500 first:border-l-0">敬遠</th>
                  <th className="px-1 py-1.5 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-gray-500">死球</th>
                  <th className="px-1 py-1.5 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-gray-500">犠打</th>
                  <th className="px-1 py-1.5 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-gray-500">犠飛</th>
                  <th className="px-1 py-1.5 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-gray-500">盗塁</th>
                  <th className="px-1 py-1.5 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-gray-500">盗塁死</th>
                  <th className="px-1 py-1.5 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-gray-500">成功率</th>
                  <th className="px-1 py-1.5 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-gray-500">併殺打</th>
                  <th className="px-1 py-1.5 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-gray-500">得点圏</th>
                  <th className="px-1 py-1.5 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-gray-500">出塁率</th>
                  <th className="px-1 py-1.5 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-gray-500">長打率</th>
                  <th className="px-1 py-1.5 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-gray-500">OPS</th>
                </tr>
                <tr style={{ backgroundColor: "rgba(255,255,255,0.03)", borderTop: "1px solid #333" }}>
                  <td className="px-1 py-2 text-center latin font-black tabular-nums text-[14px] border-l border-gray-500 first:border-l-0">{totalRow.ibb}</td>
                  <td className="px-1 py-2 text-center latin font-black tabular-nums text-[14px] border-l border-gray-500">{totalRow.hbp}</td>
                  <td className="px-1 py-2 text-center latin font-black tabular-nums text-[14px] border-l border-gray-500">{totalRow.sh}</td>
                  <td className="px-1 py-2 text-center latin font-black tabular-nums text-[14px] border-l border-gray-500">{totalRow.sf}</td>
                  <td className="px-1 py-2 text-center latin font-black tabular-nums text-[14px] border-l border-gray-500">{totalRow.sb}</td>
                  <td className="px-1 py-2 text-center latin font-black tabular-nums text-[14px] border-l border-gray-500">{totalRow.cs}</td>
                  <td className="px-1 py-2 text-center latin font-black tabular-nums text-[14px] border-l border-gray-500">{sbPct || "—"}</td>
                  <td className="px-1 py-2 text-center latin font-black tabular-nums text-[14px] border-l border-gray-500">{totalRow.gidp}</td>
                  <td className="px-1 py-2 text-center latin font-black tabular-nums text-[14px] border-l border-gray-500">
                    {totalRow.risp_avg || (totalRow.risp_ab > 0 ? `${totalRow.risp_h}/${totalRow.risp_ab}` : "—")}
                  </td>
                  <td className="px-1 py-2 text-center latin font-black tabular-nums text-[14px] border-l border-gray-500">{totalRow.obp}</td>
                  <td className="px-1 py-2 text-center latin font-black tabular-nums text-[14px] border-l border-gray-500">{totalRow.slg}</td>
                  <td className="px-1 py-2 text-center latin font-black tabular-nums text-[14px] border-l border-gray-500">{totalRow.ops}</td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* 打撃指標（セイバーメトリクス） */}
          <h2
            className={`${titleBase} mb-4 pl-4 mt-8`}
            style={{
              borderLeft: "6px solid #FF4444",
              fontWeight: 900,
            }}
          >
            打撃指標
          </h2>
          <div className="overflow-hidden overflow-x-auto mb-4">
            <table className="text-xs" style={{ fontVariantNumeric: "tabular-nums", borderCollapse: "collapse", border: "1px solid #555", tableLayout: "fixed", width: "100%" }}>
              <tbody>
                <tr style={{ backgroundColor: "#FFFF44", color: "#000000" }}>
                  <th className="px-1 py-1.5 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-gray-500 first:border-l-0">NOI</th>
                  <th className="px-1 py-1.5 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-gray-500">GPA</th>
                  <th className="px-1 py-1.5 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-gray-500">RC</th>
                  <th className="px-1 py-1.5 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-gray-500">XR</th>
                  <th className="px-1 py-1.5 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-gray-500">BABIP</th>
                  <th className="px-1 py-1.5 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-gray-500">BB/K</th>
                </tr>
                <tr style={{ backgroundColor: "rgba(255,255,255,0.03)", borderTop: "1px solid #333" }}>
                  <td className="px-1 py-2 text-center latin font-black tabular-nums text-[14px] border-l border-gray-500 first:border-l-0">{fmt(totalRow.noi)}</td>
                  <td className="px-1 py-2 text-center latin font-black tabular-nums text-[14px] border-l border-gray-500">{fmt(totalRow.gpa)}</td>
                  <td className="px-1 py-2 text-center latin font-black tabular-nums text-[14px] border-l border-gray-500">{fmt(totalRow.rc)}</td>
                  <td className="px-1 py-2 text-center latin font-black tabular-nums text-[14px] border-l border-gray-500">{fmt(totalRow.xr)}</td>
                  <td className="px-1 py-2 text-center latin font-black tabular-nums text-[14px] border-l border-gray-500">{fmt(totalRow.babip)}</td>
                  <td className="px-1 py-2 text-center latin font-black tabular-nums text-[14px] border-l border-gray-500">{fmt(totalRow.bbk)}</td>
                </tr>
                <tr style={{ backgroundColor: "#FFFF44", color: "#000000" }}>
                  <th className="px-1 py-1.5 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-gray-500 first:border-l-0">IsoD</th>
                  <th className="px-1 py-1.5 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-gray-500">IsoP</th>
                  <th className="px-1 py-1.5 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-gray-500">BB%</th>
                  <th className="px-1 py-1.5 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-gray-500">K%</th>
                  <th className="px-1 py-1.5 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-gray-500">SecA</th>
                  <th className="px-1 py-1.5 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-gray-500">TA</th>
                </tr>
                <tr style={{ backgroundColor: "rgba(255,255,255,0.03)", borderTop: "1px solid #333" }}>
                  <td className="px-1 py-2 text-center latin font-black tabular-nums text-[14px] border-l border-gray-500 first:border-l-0">{fmt(totalRow.isod)}</td>
                  <td className="px-1 py-2 text-center latin font-black tabular-nums text-[14px] border-l border-gray-500">{fmt(totalRow.isop)}</td>
                  <td className="px-1 py-2 text-center latin font-black tabular-nums text-[14px] border-l border-gray-500">{fmt(totalRow.bb_pct)}</td>
                  <td className="px-1 py-2 text-center latin font-black tabular-nums text-[14px] border-l border-gray-500">{fmt(totalRow.k_pct)}</td>
                  <td className="px-1 py-2 text-center latin font-black tabular-nums text-[14px] border-l border-gray-500">{fmt(totalRow.seca)}</td>
                  <td className="px-1 py-2 text-center latin font-black tabular-nums text-[14px] border-l border-gray-500">{fmt(totalRow.ta)}</td>
                </tr>
              </tbody>
            </table>
          </div>

            </>
          )}

          {/* 対左右別の対戦成績（チーム別と同デザイン） */}
          {showPilotTab("situation") && (() => {
            const totalRow = stats.find((r) => r.split_type === "total" && r.split_value === "total")
            const H = blocks?.blocks?.H
            const vsRight = H?.vs_right ?? 0
            const vsLeft = H?.vs_left ?? 0
            const getVsHandRow = (side: "R" | "L") => {
              if (!totalRow) return null
              if (side === "R" && vsRight > 0 && vsLeft === 0) return totalRow
              if (side === "L" && vsLeft > 0 && vsRight === 0) return totalRow
              return null
            }

            const VS_HAND_ORDER = [
              { label: "対右", key: "R" as const },
              { label: "対左", key: "L" as const },
            ]

            return (
              <>
                <h2
                  className={`${titleBase} mb-4 pl-4 mt-8`}
                  style={{
                    borderLeft: "6px solid #FF4444",
                    fontWeight: 900,
                  }}
                >
                  対左右別の対戦成績
                </h2>
                <div className="overflow-x-auto overflow-y-hidden mb-4">
                  <table className="text-xs" style={{ fontVariantNumeric: "tabular-nums", borderCollapse: "separate", borderSpacing: 0, border: "1px solid #555", width: "100%", tableLayout: "fixed" }}>
                    <colgroup>
                      <col style={{ width: "95px" }} />
                      <col style={{ width: "50px" }} />
                      <col style={{ width: "45px" }} />
                      <col style={{ width: "45px" }} />
                      <col style={{ width: "45px" }} />
                      <col style={{ width: "51px" }} />
                      <col style={{ width: "51px" }} />
                      <col style={{ width: "45px" }} />
                      <col style={{ width: "45px" }} />
                    </colgroup>
                    <thead>
                      <tr style={{ backgroundColor: "#FFFF44", color: "#000000" }}>
                        <th className="px-1 py-1 text-center font-bold text-[10px] latin tabular-nums border-l border-b border-gray-500 first:border-l-0 sticky left-0 bg-[#FFFF44] z-20 whitespace-nowrap shadow-[2px_0_4px_rgba(0,0,0,0.3)]">
                          条件
                        </th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums border-l border-b border-gray-500">OPS</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums border-l border-b border-gray-500">打率</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums border-l border-b border-gray-500">本塁打</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums border-l border-b border-gray-500">打点</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums border-l border-b border-gray-500">出塁率</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums border-l border-b border-gray-500">長打率</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums border-l border-b border-gray-500">打数</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums border-l border-b border-gray-500">安打</th>
                      </tr>
                    </thead>
                    <tbody>
                      {VS_HAND_ORDER.map((item) => {
                        const row = getVsHandRow(item.key)
                        const na = "—"
                        return (
                          <tr
                            key={item.label}
                            style={{
                              backgroundColor: "rgba(255,255,255,0.03)",
                            }}
                          >
                            <td className="px-1 py-1 text-left latin font-black tabular-nums text-[14px] border-l border-b border-gray-500 first:border-l-0 sticky left-0 z-20 whitespace-nowrap shadow-[2px_0_4px_rgba(0,0,0,0.3)]" style={{ backgroundColor: "#1a1a1a" }}>
                              <span>{item.label}</span>
                            </td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{row ? row.ops : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{row ? row.avg : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{row ? String(row.hr) : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{row ? String(row.rbi) : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{row ? row.obp : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{row ? row.slg : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{row ? String(row.ab) : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{row ? String(row.h) : na}</td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              </>
            )
          })()}

          {/* 球種別の打撃成績（チーム別と同デザイン） */}
          {showPilotTab("pitch") && pitchTypeStats.length > 0 && (
            <>
              <h2
                className={`${titleBase} mb-4 pl-4 mt-8`}
                style={{
                  borderLeft: "6px solid #FF4444",
                  fontWeight: 900,
                }}
              >
                球種別の打撃成績
              </h2>
              {/* 球種の割合（円グラフ・青柳ページの球種一覧と同コンポーネント） */}
              <PitchTypePieChart
                rows={pitchTypeStats.map((r) => ({
                  pitch_type: r.pitch_type,
                  pitches: r.pitches,
                  pct: r.pct,
                }))}
              />
              <div className="overflow-x-auto overflow-y-hidden mb-4 mt-8">
                <table className="text-xs" style={{ fontVariantNumeric: "tabular-nums", borderCollapse: "separate", borderSpacing: 0, border: "1px solid #555", width: "100%", tableLayout: "fixed" }}>
                  <colgroup>
                    <col style={{ width: "95px" }} />
                    <col style={{ width: "45px" }} />
                    <col style={{ width: "72px" }} />
                    <col style={{ width: "51px" }} />
                    <col style={{ width: "50px" }} />
                    <col style={{ width: "45px" }} />
                    <col style={{ width: "45px" }} />
                  </colgroup>
                  <thead>
                    <tr style={{ backgroundColor: "#FFFF44", color: "#000000" }}>
                      <th className="px-1 py-1 text-center font-bold text-[10px] latin tabular-nums border-l border-b border-gray-500 first:border-l-0 sticky left-0 bg-[#FFFF44] z-20 whitespace-nowrap shadow-[2px_0_4px_rgba(0,0,0,0.3)]">
                        球種
                      </th>
                      <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums border-l border-b border-gray-500">割合</th>
                      <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums border-l border-b border-gray-500 whitespace-nowrap">
                        平均球速<span className="latin">(km/h)</span>
                      </th>
                      <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums border-l border-b border-gray-500">空振り%</th>
                      <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums border-l border-b border-gray-500">OPS</th>
                      <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums border-l border-b border-gray-500">打率</th>
                      <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums border-l border-b border-gray-500">本塁打</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pitchTypeStats.map((row) => (
                      <tr
                        key={row.pitch_type}
                        style={{
                          backgroundColor: "rgba(255,255,255,0.03)",
                        }}
                      >
                        <td className="px-1 py-1 text-left latin font-black tabular-nums text-[14px] border-l border-b border-gray-500 first:border-l-0 sticky left-0 z-20 whitespace-nowrap shadow-[2px_0_4px_rgba(0,0,0,0.3)]" style={{ backgroundColor: "#1a1a1a" }}>
                          <span>{row.pitch_type}</span>
                        </td>
                        <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{row.pct.toFixed(1)}%</td>
                        <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500 whitespace-nowrap">
                          {row.avg_speed != null ? (
                            <>
                              <span className="latin">{row.avg_speed.toFixed(1)}</span>
                              <span className="latin text-[11px] opacity-90"> km/h</span>
                            </>
                          ) : (
                            "—"
                          )}
                        </td>
                        <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{row.whiff_pct}</td>
                        <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{row.ops}</td>
                        <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{row.avg}</td>
                        <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{row.hr}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}

          {/* 球速別の打撃成績（ストレート限定・打順別と同デザイン） */}
          {showPilotTab("pitch") && pitchTypeStats.length > 0 && (() => {
            const SPEED_BAND_ITEMS = [
              { key: "160-", label: "160-" },
              { key: "155-159", label: "155-159" },
              { key: "150-154", label: "150-154" },
              { key: "145-149", label: "145-149" },
              { key: "140-144", label: "140-144" },
              { key: "-139", label: "-139" },
            ] as const
            const pilotSpeedData: Record<string, {
              ops: string
              avg: string
              hr: number
              strike_pct: string
              whiff_pct: string
            }> = {
              "150-154": {
                ops: ".000",
                avg: ".000",
                hr: 0,
                strike_pct: "28.6%",
                whiff_pct: "50.0%",
              },
              "145-149": {
                ops: "—",
                avg: "—",
                hr: 0,
                strike_pct: "100%",
                whiff_pct: "—",
              },
            }
            const getSpeedRow = (key: string) => pilotSpeedData[key] ?? null
            const na = "—"

            return (
              <>
                <h2
                  className={`${titleBase} mb-4 pl-4 mt-8`}
                  style={{
                    borderLeft: "6px solid #FF4444",
                    fontWeight: 900,
                  }}
                >
                  球速別の打撃成績（ストレート限定）
                </h2>
                <div className="overflow-x-auto overflow-y-hidden mb-4">
                  <table
                    className="text-xs"
                    style={{
                      fontVariantNumeric: "tabular-nums",
                      borderCollapse: "separate",
                      borderSpacing: 0,
                      border: "1px solid #555",
                      width: "100%",
                      tableLayout: "fixed",
                    }}
                  >
                    <colgroup>
                      {/* チーム別テーブルと同系の比率（先頭ラベル列＋数値列の配分） */}
                      <col style={{ width: "95px" }} />
                      <col style={{ width: "50px" }} />
                      <col style={{ width: "45px" }} />
                      <col style={{ width: "45px" }} />
                      <col style={{ width: "45px" }} />
                      <col style={{ width: "51px" }} />
                    </colgroup>
                    <thead>
                      <tr style={{ backgroundColor: "#FFFF44", color: "#000000" }}>
                        <th className="px-1 py-1 text-center font-bold text-[10px] latin tabular-nums border-l border-b border-gray-500 first:border-l-0 sticky left-0 bg-[#FFFF44] z-20 whitespace-nowrap shadow-[2px_0_4px_rgba(0,0,0,0.3)]">
                          球速(km/h)
                        </th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums border-l border-b border-gray-500">OPS</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums border-l border-b border-gray-500">打率</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums border-l border-b border-gray-500">本塁打</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums border-l border-b border-gray-500">割合</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums border-l border-b border-gray-500">空振り%</th>
                      </tr>
                    </thead>
                    <tbody>
                      {SPEED_BAND_ITEMS.map((item) => {
                        const row = getSpeedRow(item.key)
                        const hasData = row != null
                        return (
                          <tr
                            key={item.key}
                            style={{
                              backgroundColor: "rgba(255,255,255,0.03)",
                            }}
                          >
                            <td
                              className="px-1 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500 first:border-l-0 sticky left-0 z-20 shadow-[2px_0_4px_rgba(0,0,0,0.3)]"
                              style={{ backgroundColor: "#1a1a1a" }}
                            >
                              <span>{item.label}</span>
                            </td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{hasData ? row!.ops : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{hasData ? row!.avg : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{hasData ? String(row!.hr) : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{hasData ? row!.strike_pct : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{hasData ? row!.whiff_pct : na}</td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              </>
            )
          })()}

          {/* チーム別の対戦成績（12球団固定表示） */}
          {showPilotTab("situation") && (() => {
            const TEAM_ORDER = [
              { label: "日本ハム", splitMatch: "北海道日本ハム" },
              { label: "楽天", splitMatch: "楽天" },
              { label: "西武", splitMatch: "西武" },
              { label: "ロッテ", splitMatch: "ロッテ" },
              { label: "オリックス", splitMatch: "オリックス" },
              { label: "ソフトバンク", splitMatch: "ソフトバンク" },
              { label: "巨人", splitMatch: "ジャイアンツ" },
              { label: "ヤクルト", splitMatch: "ヤクルト" },
              { label: "横浜", splitMatch: "DeNA" },
              { label: "中日", splitMatch: "中日" },
              { label: "阪神", splitMatch: "阪神" },
              { label: "広島", splitMatch: "広島" },
            ] as const
            const teamStatsMap = new Map(
              stats
                .filter((r) => r.split_type === "vs_team")
                .map((r) => [r.split_value, r])
            )
            const findStats = (splitMatch: string) =>
              Array.from(teamStatsMap.entries()).find(([k]) => k.includes(splitMatch))?.[1] ?? null

            return (
              <>
                <h2
                  className={`${titleBase} mb-4 pl-4 mt-8`}
                  style={{
                    borderLeft: "6px solid #FF4444",
                    fontWeight: 900,
                  }}
                >
                  チーム別の対戦成績
                </h2>
                <div className="overflow-x-auto overflow-y-hidden mb-4">
                  <table
                    className="text-xs"
                    style={{
                      fontVariantNumeric: "tabular-nums",
                      borderCollapse: "separate",
                      borderSpacing: 0,
                      border: "1px solid #555",
                      width: "100%",
                      tableLayout: "fixed",
                    }}
                  >
                    <colgroup>
                      <col style={{ width: "95px" }} />
                      <col style={{ width: "50px" }} />
                      <col style={{ width: "45px" }} />
                      <col style={{ width: "45px" }} />
                      <col style={{ width: "45px" }} />
                      <col style={{ width: "51px" }} />
                      <col style={{ width: "51px" }} />
                      <col style={{ width: "45px" }} />
                      <col style={{ width: "45px" }} />
                    </colgroup>
                    <thead>
                      <tr style={{ backgroundColor: "#FFFF44", color: "#000000" }}>
                        <th className="px-1 py-1 text-center font-bold text-[10px] latin tabular-nums border-l border-b border-gray-500 first:border-l-0 sticky left-0 bg-[#FFFF44] z-20 whitespace-nowrap shadow-[2px_0_4px_rgba(0,0,0,0.3)]">
                          チーム
                        </th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums border-l border-b border-gray-500">OPS</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums border-l border-b border-gray-500">打率</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums border-l border-b border-gray-500">本塁打</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums border-l border-b border-gray-500">打点</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums border-l border-b border-gray-500">出塁率</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums border-l border-b border-gray-500">長打率</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums border-l border-b border-gray-500">打数</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums border-l border-b border-gray-500">安打</th>
                      </tr>
                    </thead>
                    <tbody>
                      {TEAM_ORDER.map((team) => {
                        const row = findStats(team.splitMatch)
                        const na = "—"
                        return (
                          <tr
                            key={team.label}
                            style={{
                              backgroundColor: "rgba(255,255,255,0.03)",
                            }}
                          >
                            <td
                              className="px-1 py-1 text-left latin font-black tabular-nums text-[13px] border-l border-b border-gray-500 first:border-l-0 sticky left-0 z-20 shadow-[2px_0_4px_rgba(0,0,0,0.3)]"
                              style={{ backgroundColor: "#1a1a1a" }}
                            >
                              <div className="flex items-center gap-1 min-h-[1.25rem]">
                                <div className="w-1 h-4 flex-shrink-0" style={{ backgroundColor: TEAM_COLORS[team.label] || "#666" }} />
                                <span>{team.label}</span>
                              </div>
                            </td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{row ? row.ops : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{row ? row.avg : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{row ? String(row.hr) : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{row ? String(row.rbi) : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{row ? row.obp : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{row ? row.slg : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{row ? String(row.ab) : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{row ? String(row.h) : na}</td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  パ・リーグ: 日本ハム・楽天・西武・ロッテ・オリックス・ソフトバンク　／　セ・リーグ: 巨人・ヤクルト・横浜・中日・阪神・広島
                </p>
              </>
            )
          })()}

          {/* 球場別の対戦成績（チーム別と同デザイン） */}
          {showPilotTab("situation") && (() => {
            const VENUE_ORDER: { display: string; dataKeys: string[]; teamLabel: string }[] = [
              { display: "エスコンＦ", dataKeys: ["エスコンＦ", "エスコンフィールド名古屋"], teamLabel: "中日" },
              { display: "楽天最強", dataKeys: ["楽天最強", "楽天モバイル", "楽天モバイルパーク"], teamLabel: "楽天" },
              { display: "ベルーナD", dataKeys: ["ベルーナD", "ベルーナドーム"], teamLabel: "西武" },
              { display: "ZOZOマリン", dataKeys: ["ZOZOマリン", "Zozoマリンスタジアム"], teamLabel: "ロッテ" },
              { display: "京セラD大阪", dataKeys: ["京セラD大阪", "京セラドーム大阪"], teamLabel: "オリックス" },
              { display: "みずほPayPay", dataKeys: ["みずほPayPay", "PayPayドーム"], teamLabel: "ソフトバンク" },
              { display: "東京ドーム", dataKeys: ["東京ドーム"], teamLabel: "巨人" },
              { display: "神宮球場", dataKeys: ["神宮球場", "神宮"], teamLabel: "ヤクルト" },
              { display: "横浜スタジアム", dataKeys: ["横浜スタジアム", "横浜S", "横浜"], teamLabel: "横浜" },
              { display: "バンテリンD", dataKeys: ["バンテリンD", "バンテリンドーム"], teamLabel: "中日" },
              { display: "甲子園球場", dataKeys: ["甲子園球場", "甲子園"], teamLabel: "阪神" },
              { display: "マツダ", dataKeys: ["マツダ", "マツダスタジアム"], teamLabel: "広島" },
            ]
            const totalRow = stats.find((r) => r.split_type === "total" && r.split_value === "total")
            const byStadium = blocks?.blocks?.F?.by_stadium ?? {}
            const totalPa = totalRow?.pa ?? 0
            const getVenueStats = (item: { display: string; dataKeys: string[] }): SeasonStatsRow | null => {
              let pa = 0
              for (const key of item.dataKeys) {
                pa = byStadium[key] ?? 0
                if (pa > 0) break
              }
              if (pa === 0) return null
              if (pa === totalPa && totalRow) return totalRow
              return null
            }

            return (
              <>
                <h2
                  className={`${titleBase} mb-4 pl-4 mt-8`}
                  style={{
                    borderLeft: "6px solid #FF4444",
                    fontWeight: 900,
                  }}
                >
                  球場別の対戦成績
                </h2>
                <div className="overflow-x-auto overflow-y-hidden mb-4">
                  <table
                    className="text-xs"
                    style={{
                      fontVariantNumeric: "tabular-nums",
                      borderCollapse: "separate",
                      borderSpacing: 0,
                      border: "1px solid #555",
                      width: "100%",
                      tableLayout: "fixed",
                    }}
                  >
                    <colgroup>
                      <col style={{ width: "95px" }} />
                      <col style={{ width: "50px" }} />
                      <col style={{ width: "45px" }} />
                      <col style={{ width: "45px" }} />
                      <col style={{ width: "45px" }} />
                      <col style={{ width: "51px" }} />
                      <col style={{ width: "51px" }} />
                      <col style={{ width: "45px" }} />
                      <col style={{ width: "45px" }} />
                    </colgroup>
                    <thead>
                      <tr style={{ backgroundColor: "#FFFF44", color: "#000000" }}>
                        <th className="px-1 py-1 text-center font-bold text-[10px] latin tabular-nums border-l border-b border-gray-500 first:border-l-0 sticky left-0 bg-[#FFFF44] z-20 whitespace-nowrap shadow-[2px_0_4px_rgba(0,0,0,0.3)]">球場</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums border-l border-b border-gray-500">OPS</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums border-l border-b border-gray-500">打率</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums border-l border-b border-gray-500">本塁打</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums border-l border-b border-gray-500">打点</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums border-l border-b border-gray-500">出塁率</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums border-l border-b border-gray-500">長打率</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums border-l border-b border-gray-500">打数</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums border-l border-b border-gray-500">安打</th>
                      </tr>
                    </thead>
                    <tbody>
                      {VENUE_ORDER.map((item) => {
                        const row = getVenueStats(item)
                        const na = "—"
                        return (
                          <tr key={item.display} style={{ backgroundColor: "rgba(255,255,255,0.03)" }}>
                            <td className="px-1 py-1 text-left latin font-black tabular-nums text-[13px] border-l border-b border-gray-500 first:border-l-0 sticky left-0 z-20 shadow-[2px_0_4px_rgba(0,0,0,0.3)]" style={{ backgroundColor: "#1a1a1a" }}>
                              <div className="flex items-center gap-1 min-h-[1.25rem]">
                                <div className="w-1 h-4 flex-shrink-0" style={{ backgroundColor: TEAM_COLORS[item.teamLabel] || "#666" }} />
                                <span>{item.display}</span>
                              </div>
                            </td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{row ? row.ops : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{row ? row.avg : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{row ? String(row.hr) : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{row ? String(row.rbi) : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{row ? row.obp : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{row ? row.slg : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{row ? String(row.ab) : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{row ? String(row.h) : na}</td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              </>
            )
          })()}

          {/* 打席別成績（打順別と同デザイン・先発時） */}
          {showPilotTab("situation") && (() => {
            const totalRow = stats.find((r) => r.split_type === "total" && r.split_value === "total")
            const PA_ORDER_ITEMS = [
              { key: "1", label: "1巡目" },
              { key: "2", label: "2巡目" },
              { key: "3", label: "3巡目" },
              { key: "4", label: "4巡目" },
              { key: "5", label: "5巡目以上" },
            ] as const
            const getPaOrderRow = (key: string): { pa: number; ab: number; h: number; hr: number; rbi: number; so: number; bb: number; ibb: number; hbp: number; sh: number; sf: number; avg: string; obp: string; slg: string; ops: string } | null => {
              if (!totalRow || totalRow.pa < 1) return null
              const n = parseInt(key, 10)
              if (n >= 1 && n <= 3 && totalRow.pa >= n) {
                return { pa: 1, ab: 1, h: 0, hr: 0, rbi: 0, so: 0, bb: 0, ibb: 0, hbp: 0, sh: 0, sf: 0, avg: ".000", obp: ".000", slg: ".000", ops: ".000" }
              }
              return null
            }
            const na = "—"

            return (
              <>
                <h2
                  className={`${titleBase} mb-4 pl-4 mt-8`}
                  style={{
                    borderLeft: "6px solid #FF4444",
                    fontWeight: 900,
                  }}
                >
                  打席別成績
                </h2>
                <div className="overflow-x-auto overflow-y-hidden mb-4">
                  <table
                    className="text-xs"
                    style={{
                      fontVariantNumeric: "tabular-nums",
                      borderCollapse: "separate",
                      borderSpacing: 0,
                      border: "1px solid #555",
                      width: "100%",
                      tableLayout: "fixed",
                    }}
                  >
                    <colgroup>
                      <col style={{ width: "72px" }} />
                      <col style={{ width: "50px" }} />
                      <col style={{ width: "45px" }} />
                      <col style={{ width: "45px" }} />
                      <col style={{ width: "45px" }} />
                      <col style={{ width: "51px" }} />
                      <col style={{ width: "51px" }} />
                      <col style={{ width: "45px" }} />
                      <col style={{ width: "45px" }} />
                    </colgroup>
                    <thead>
                      <tr style={{ backgroundColor: "#FFFF44", color: "#000000" }}>
                        <th className="px-0.5 py-1 text-center font-bold text-[10px] latin tabular-nums border-l border-b border-gray-500 first:border-l-0 sticky left-0 bg-[#FFFF44] z-20 whitespace-nowrap shadow-[2px_0_4px_rgba(0,0,0,0.3)]">打席数</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums border-l border-b border-gray-500">OPS</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums border-l border-b border-gray-500">打率</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums border-l border-b border-gray-500">本塁打</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums border-l border-b border-gray-500">打点</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums border-l border-b border-gray-500">出塁率</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums border-l border-b border-gray-500">長打率</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums border-l border-b border-gray-500">打数</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums border-l border-b border-gray-500">安打</th>
                      </tr>
                    </thead>
                    <tbody>
                      {PA_ORDER_ITEMS.map((item) => {
                        const row = getPaOrderRow(item.key)
                        const hasData = row != null
                        return (
                          <tr key={item.key} style={{ backgroundColor: "rgba(255,255,255,0.03)" }}>
                            <td className="px-0.5 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500 first:border-l-0 sticky left-0 z-20 whitespace-nowrap shadow-[2px_0_4px_rgba(0,0,0,0.3)]" style={{ backgroundColor: "#1a1a1a" }}>
                              <span>{item.label}</span>
                            </td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{hasData ? row!.ops : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{hasData ? row!.avg : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{hasData ? String(row!.hr) : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{hasData ? String(row!.rbi) : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{hasData ? row!.obp : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{hasData ? row!.slg : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{hasData ? String(row!.ab) : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{hasData ? String(row!.h) : na}</td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              </>
            )
          })()}

          {/* ホーム&ビジターの対戦成績（対左右別と同デザイン） */}
          {showPilotTab("situation") && (() => {
            const homeAwayMap = new Map(
              stats
                .filter((r) => r.split_type === "home_away")
                .map((r) => [r.split_value, r])
            )
            const getHomeAwayRow = (key: string) => homeAwayMap.get(key) ?? null

            const HOME_VISITOR_ORDER = [
              { label: "ホーム", key: "home" },
              { label: "ビジター", key: "visitor" },
            ]

            return (
              <>
                <h2
                  className={`${titleBase} mb-4 pl-4 mt-8`}
                  style={{
                    borderLeft: "6px solid #FF4444",
                    fontWeight: 900,
                  }}
                >
                  ホーム&ビジターの対戦成績
                </h2>
                <div className="overflow-x-auto overflow-y-hidden mb-4">
                  <table className="text-xs" style={{ fontVariantNumeric: "tabular-nums", borderCollapse: "separate", borderSpacing: 0, border: "1px solid #555", width: "100%", tableLayout: "fixed" }}>
                    <colgroup>
                      <col style={{ width: "72px" }} />
                      <col style={{ width: "50px" }} />
                      <col style={{ width: "45px" }} />
                      <col style={{ width: "45px" }} />
                      <col style={{ width: "45px" }} />
                      <col style={{ width: "51px" }} />
                      <col style={{ width: "51px" }} />
                      <col style={{ width: "45px" }} />
                      <col style={{ width: "45px" }} />
                    </colgroup>
                    <thead>
                      <tr style={{ backgroundColor: "#FFFF44", color: "#000000" }}>
                        <th className="px-1 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500 first:border-l-0 sticky left-0 bg-[#FFFF44] z-20 shadow-[2px_0_4px_rgba(0,0,0,0.3)]">条件</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500">OPS</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500">打率</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500">本塁打</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500">打点</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500">出塁率</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500">長打率</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500">打数</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500">安打</th>
                      </tr>
                    </thead>
                    <tbody>
                      {HOME_VISITOR_ORDER.map((item) => {
                        const row = getHomeAwayRow(item.key)
                        const na = "—"
                        return (
                          <tr key={item.label} style={{ backgroundColor: "rgba(255,255,255,0.03)" }}>
                            <td className="px-1 py-1 text-left latin font-black tabular-nums text-[14px] border-l border-b border-gray-500 first:border-l-0 sticky left-0 z-20 whitespace-nowrap shadow-[2px_0_4px_rgba(0,0,0,0.3)]" style={{ backgroundColor: "#1a1a1a" }}>
                              <span>{item.label}</span>
                            </td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{row ? row.ops : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{row ? row.avg : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{row ? String(row.hr) : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{row ? String(row.rbi) : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{row ? row.obp : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{row ? row.slg : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{row ? String(row.ab) : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{row ? String(row.h) : na}</td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              </>
            )
          })()}

          {/* スタメン時守備位置別の打撃成績（打順別と同デザイン） */}
          {showPilotTab("situation") && (() => {
            const totalRow = stats.find((r) => r.split_type === "total" && r.split_value === "total")
            // パイロット（菊池 2026-03-04）は二塁手で先発。スタメン守備位置データがなければ total を二塁手に充てる
            const POSITION_ITEMS = [
              { key: "捕手", label: "捕手" },
              { key: "一塁手", label: "一塁手" },
              { key: "二塁手", label: "二塁手" },
              { key: "三塁手", label: "三塁手" },
              { key: "遊撃手", label: "遊撃手" },
              { key: "左翼手", label: "左翼手" },
              { key: "中堅手", label: "中堅手" },
              { key: "右翼手", label: "右翼手" },
              { key: "DH", label: "DH" },
            ] as const
            const getPositionRow = (key: string) => {
              if (key === "二塁手" && totalRow && totalRow.pa > 0) return totalRow
              return null
            }
            const na = "—"

            return (
              <>
                <h2
                  className={`${titleBase} mb-4 pl-4 mt-8`}
                  style={{
                    borderLeft: "6px solid #FF4444",
                    fontWeight: 900,
                  }}
                >
                  スタメン時守備位置別の打撃成績
                </h2>
                <div className="overflow-x-auto overflow-y-hidden mb-4">
                  <table className="text-xs" style={{ fontVariantNumeric: "tabular-nums", borderCollapse: "separate", borderSpacing: 0, border: "1px solid #555", width: "100%", tableLayout: "fixed" }}>
                    <colgroup>
                      <col style={{ width: "64px" }} />
                      <col style={{ width: "50px" }} />
                      <col style={{ width: "45px" }} />
                      <col style={{ width: "45px" }} />
                      <col style={{ width: "45px" }} />
                      <col style={{ width: "51px" }} />
                      <col style={{ width: "51px" }} />
                      <col style={{ width: "45px" }} />
                      <col style={{ width: "45px" }} />
                    </colgroup>
                    <thead>
                      <tr style={{ backgroundColor: "#FFFF44", color: "#000000" }}>
                        <th className="px-0.5 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500 first:border-l-0 sticky left-0 bg-[#FFFF44] z-20 shadow-[2px_0_4px_rgba(0,0,0,0.3)]">守備位置</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500">OPS</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500">打率</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500">本塁打</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500">打点</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500">出塁率</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500">長打率</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500">打数</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500">安打</th>
                      </tr>
                    </thead>
                    <tbody>
                      {POSITION_ITEMS.map((item) => {
                        const row = getPositionRow(item.key)
                        const hasData = row && row.pa > 0
                        return (
                          <tr key={item.key} style={{ backgroundColor: "rgba(255,255,255,0.03)" }}>
                            <td className="px-0.5 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500 first:border-l-0 sticky left-0 z-20 whitespace-nowrap shadow-[2px_0_4px_rgba(0,0,0,0.3)]" style={{ backgroundColor: "#1a1a1a" }}>
                              <span>{item.label}</span>
                            </td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{hasData ? row!.ops : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{hasData ? row!.avg : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{hasData ? String(row!.hr) : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{hasData ? String(row!.rbi) : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{hasData ? row!.obp : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{hasData ? row!.slg : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{hasData ? String(row!.ab) : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{hasData ? String(row!.h) : na}</td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              </>
            )
          })()}

          {/* 打順別の打撃成績（球種別と同デザイン） */}
          {showPilotTab("situation") && (() => {
            const batOrderMap = new Map(
              stats
                .filter((r) => r.split_type === "bat_order")
                .map((r) => [r.split_value, r])
            )
            const getBatOrderRow = (n: number) => batOrderMap.get(`bat_order_${n}`) ?? null

            const BAT_ORDER_ITEMS = [1, 2, 3, 4, 5, 6, 7, 8] as const
            const na = "—"

            return (
              <>
                <h2
                  className={`${titleBase} mb-4 pl-4 mt-8`}
                  style={{
                    borderLeft: "6px solid #FF4444",
                    fontWeight: 900,
                  }}
                >
                  打順別の打撃成績
                </h2>
                <div className="overflow-x-auto overflow-y-hidden mb-4">
                  <table className="text-xs" style={{ fontVariantNumeric: "tabular-nums", borderCollapse: "separate", borderSpacing: 0, border: "1px solid #555", width: "100%", tableLayout: "fixed" }}>
                    <colgroup>
                      <col style={{ width: "52px" }} />
                      <col style={{ width: "50px" }} />
                      <col style={{ width: "45px" }} />
                      <col style={{ width: "45px" }} />
                      <col style={{ width: "45px" }} />
                      <col style={{ width: "51px" }} />
                      <col style={{ width: "51px" }} />
                      <col style={{ width: "45px" }} />
                      <col style={{ width: "45px" }} />
                    </colgroup>
                    <thead>
                      <tr style={{ backgroundColor: "#FFFF44", color: "#000000" }}>
                        <th className="px-0.5 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500 first:border-l-0 sticky left-0 bg-[#FFFF44] z-20 shadow-[2px_0_4px_rgba(0,0,0,0.3)]">打順</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500">OPS</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500">打率</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500">本塁打</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500">打点</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500">出塁率</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500">長打率</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500">打数</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500">安打</th>
                      </tr>
                    </thead>
                    <tbody>
                      {BAT_ORDER_ITEMS.map((n) => {
                        const row = getBatOrderRow(n)
                        const hasData = row && row.pa > 0
                        return (
                          <tr key={n} style={{ backgroundColor: "rgba(255,255,255,0.03)" }}>
                            <td className="px-0.5 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500 first:border-l-0 sticky left-0 z-20 whitespace-nowrap shadow-[2px_0_4px_rgba(0,0,0,0.3)]" style={{ backgroundColor: "#1a1a1a" }}>
                              <span>{n}番</span>
                            </td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{hasData ? row!.ops : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{hasData ? row!.avg : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{hasData ? String(row!.hr) : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{hasData ? String(row!.rbi) : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{hasData ? row!.obp : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{hasData ? row!.slg : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{hasData ? String(row!.ab) : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{hasData ? String(row!.h) : na}</td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              </>
            )
          })()}

          {/* カウント別の打撃成績（打順別と同デザイン） */}
          {showPilotTab("situation") && (() => {
            const totalRow = stats.find((r) => r.split_type === "total" && r.split_value === "total")
            const COUNT_ITEMS = [
              { key: "0-0", label: "0-0" },
              { key: "1-0", label: "1-0" },
              { key: "2-0", label: "2-0" },
              { key: "3-0", label: "3-0" },
              { key: "0-1", label: "0-1" },
              { key: "1-1", label: "1-1" },
              { key: "2-1", label: "2-1" },
              { key: "3-1", label: "3-1" },
              { key: "0-2", label: "0-2" },
              { key: "1-2", label: "1-2" },
              { key: "2-2", label: "2-2" },
              { key: "3-2", label: "3-2" },
            ] as const
            const getCountRow = (key: string) => {
              if (!totalRow || totalRow.pa < 1) return null
              const pilotCountData: Record<string, { g: number; pa: number; ab: number; r: number; h: number; h2: number; h3: number; hr: number; tb: number; rbi: number; so: number; bb: number; ibb: number; hbp: number; sh: number; sf: number; sb: number; cs: number; avg: string; obp: string; slg: string; ops: string }> = {
                "3-1": { g: 0, pa: 1, ab: 1, r: 0, h: 0, h2: 0, h3: 0, hr: 0, tb: 0, rbi: 0, so: 0, bb: 0, ibb: 0, hbp: 0, sh: 0, sf: 0, sb: 0, cs: 0, avg: ".000", obp: ".000", slg: ".000", ops: ".000" },
                "1-2": { g: 0, pa: 1, ab: 1, r: 0, h: 0, h2: 0, h3: 0, hr: 0, tb: 0, rbi: 0, so: 0, bb: 0, ibb: 0, hbp: 0, sh: 0, sf: 0, sb: 0, cs: 0, avg: ".000", obp: ".000", slg: ".000", ops: ".000" },
                "2-2": { g: 0, pa: 1, ab: 1, r: 0, h: 0, h2: 0, h3: 0, hr: 0, tb: 0, rbi: 0, so: 0, bb: 0, ibb: 0, hbp: 0, sh: 0, sf: 0, sb: 0, cs: 0, avg: ".000", obp: ".000", slg: ".000", ops: ".000" },
              }
              return pilotCountData[key] ?? null
            }
            const na = "—"

            return (
              <>
                <h2
                  className={`${titleBase} mb-4 pl-4 mt-8`}
                  style={{
                    borderLeft: "6px solid #FF4444",
                    fontWeight: 900,
                  }}
                >
                  カウント別の打撃成績
                </h2>
                <div className="overflow-x-auto overflow-y-hidden mb-4">
                  <table className="text-xs" style={{ fontVariantNumeric: "tabular-nums", borderCollapse: "separate", borderSpacing: 0, border: "1px solid #555", width: "100%", tableLayout: "fixed" }}>
                    <colgroup>
                      <col style={{ width: "52px" }} />
                      <col style={{ width: "50px" }} />
                      <col style={{ width: "45px" }} />
                      <col style={{ width: "45px" }} />
                      <col style={{ width: "45px" }} />
                      <col style={{ width: "51px" }} />
                      <col style={{ width: "51px" }} />
                      <col style={{ width: "45px" }} />
                      <col style={{ width: "45px" }} />
                    </colgroup>
                    <thead>
                      <tr style={{ backgroundColor: "#FFFF44", color: "#000000" }}>
                        <th className="px-0.5 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500 first:border-l-0 sticky left-0 bg-[#FFFF44] z-20 shadow-[2px_0_4px_rgba(0,0,0,0.3)]">条件</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500">OPS</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500">打率</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500">本塁打</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500">打点</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500">出塁率</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500">長打率</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500">打数</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500">安打</th>
                      </tr>
                    </thead>
                    <tbody>
                      {COUNT_ITEMS.map((item) => {
                        const row = getCountRow(item.key)
                        const hasData = row != null && row.pa > 0
                        return (
                          <tr key={item.key} style={{ backgroundColor: "rgba(255,255,255,0.03)" }}>
                            <td className="px-0.5 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500 first:border-l-0 sticky left-0 z-20 whitespace-nowrap shadow-[2px_0_4px_rgba(0,0,0,0.3)]" style={{ backgroundColor: "#1a1a1a" }}>
                              <span>{item.label}</span>
                            </td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{hasData ? row!.ops : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{hasData ? row!.avg : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{hasData ? String(row!.hr) : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{hasData ? String(row!.rbi) : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{hasData ? row!.obp : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{hasData ? row!.slg : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{hasData ? String(row!.ab) : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{hasData ? String(row!.h) : na}</td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              </>
            )
          })()}

          {/* 状況別の打撃成績（打順別と同デザイン・ランナー別） */}
          {showPilotTab("situation") && (() => {
            const totalRow = stats.find((r) => r.split_type === "total" && r.split_value === "total")
            const byBaseState = blocks?.blocks?.F?.by_base_state ?? {}
            const totalPa = totalRow?.pa ?? 0
            const nonePa = byBaseState["無死走者なし"] ?? 0
            const RUNNER_ITEMS = [
              { key: "無し", label: "無し", matchKeys: ["無死走者なし"] },
              { key: "1塁", label: "1塁", matchKeys: [] },
              { key: "2塁", label: "2塁", matchKeys: [] },
              { key: "3塁", label: "3塁", matchKeys: [] },
              { key: "1・2塁", label: "1・2塁", matchKeys: [] },
              { key: "1・3塁", label: "1・3塁", matchKeys: [] },
              { key: "2・3塁", label: "2・3塁", matchKeys: [] },
              { key: "満塁", label: "満塁", matchKeys: [] },
              { key: "非得点圏", label: "非得点圏", matchKeys: [] },
              { key: "得点圏", label: "得点圏", matchKeys: [] },
            ] as const
            const getRunnerRow = (item: { key: string; matchKeys: string[] }): SeasonStatsRow | null => {
              if (item.key === "無し" && nonePa === totalPa && totalPa > 0 && totalRow) return totalRow
              const byRispStats = blocks?.blocks?.F?.by_risp_stats
              if (item.key === "得点圏" && byRispStats?.risp) {
                const s = byRispStats.risp
                return {
                  split_type: "pilot_risp",
                  split_value: "risp",
                  split_label: "得点圏",
                  g: s.g,
                  pa: s.pa,
                  ab: s.ab,
                  r: s.r,
                  h: s.h,
                  h1: Math.max(0, s.h - s.h2 - s.h3 - s.hr),
                  h2: s.h2,
                  h3: s.h3,
                  hr: s.hr,
                  tb: s.tb,
                  rbi: s.rbi,
                  so: s.so,
                  bb: s.bb,
                  ibb: s.ibb,
                  hbp: s.hbp,
                  sh: s.sh,
                  sf: s.sf,
                  sb: s.sb,
                  cs: s.cs,
                  gidp: 0,
                  avg: s.avg,
                  obp: s.obp,
                  slg: s.slg,
                  ops: s.ops,
                  risp_avg: "",
                  risp_ab: 0,
                  risp_h: 0,
                  sb_pct: "",
                  isop: "",
                  isod: "",
                  babip: "",
                  bb_pct: "",
                  k_pct: "",
                  bbk: "",
                  gpa: "",
                  rc: "",
                  xr: "",
                  seca: "",
                  ta: "",
                  noi: "",
                }
              }
              if (item.key === "非得点圏" && byRispStats?.no_risp) {
                const s = byRispStats.no_risp
                return {
                  split_type: "pilot_no_risp",
                  split_value: "no_risp",
                  split_label: "非得点圏",
                  g: s.g,
                  pa: s.pa,
                  ab: s.ab,
                  r: s.r,
                  h: s.h,
                  h1: Math.max(0, s.h - s.h2 - s.h3 - s.hr),
                  h2: s.h2,
                  h3: s.h3,
                  hr: s.hr,
                  tb: s.tb,
                  rbi: s.rbi,
                  so: s.so,
                  bb: s.bb,
                  ibb: s.ibb,
                  hbp: s.hbp,
                  sh: s.sh,
                  sf: s.sf,
                  sb: s.sb,
                  cs: s.cs,
                  gidp: 0,
                  avg: s.avg,
                  obp: s.obp,
                  slg: s.slg,
                  ops: s.ops,
                  risp_avg: "",
                  risp_ab: 0,
                  risp_h: 0,
                  sb_pct: "",
                  isop: "",
                  isod: "",
                  babip: "",
                  bb_pct: "",
                  k_pct: "",
                  bbk: "",
                  gpa: "",
                  rc: "",
                  xr: "",
                  seca: "",
                  ta: "",
                  noi: "",
                }
              }
              return null
            }
            const na = "—"

            return (
              <>
                <h2
                  className={`${titleBase} mb-4 pl-4 mt-8`}
                  style={{
                    borderLeft: "6px solid #FF4444",
                    fontWeight: 900,
                  }}
                >
                  状況別の打撃成績
                </h2>
                <div className="overflow-x-auto overflow-y-hidden mb-4">
                  <table className="text-xs" style={{ fontVariantNumeric: "tabular-nums", borderCollapse: "separate", borderSpacing: 0, border: "1px solid #555", width: "100%", tableLayout: "fixed" }}>
                    <colgroup>
                      <col style={{ width: "52px" }} />
                      <col style={{ width: "50px" }} />
                      <col style={{ width: "45px" }} />
                      <col style={{ width: "45px" }} />
                      <col style={{ width: "45px" }} />
                      <col style={{ width: "51px" }} />
                      <col style={{ width: "51px" }} />
                      <col style={{ width: "45px" }} />
                      <col style={{ width: "45px" }} />
                    </colgroup>
                    <thead>
                      <tr style={{ backgroundColor: "#FFFF44", color: "#000000" }}>
                        <th className="px-0.5 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500 first:border-l-0 sticky left-0 bg-[#FFFF44] z-20 shadow-[2px_0_4px_rgba(0,0,0,0.3)]">条件</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500">OPS</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500">打率</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500">本塁打</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500">打点</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500">出塁率</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500">長打率</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500">打数</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500">安打</th>
                      </tr>
                    </thead>
                    <tbody>
                      {RUNNER_ITEMS.map((item) => {
                        const row = getRunnerRow(item)
                        const hasData = row != null && row.pa > 0
                        return (
                          <tr key={item.key} style={{ backgroundColor: "rgba(255,255,255,0.03)" }}>
                            <td className="px-0.5 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500 first:border-l-0 sticky left-0 z-20 whitespace-nowrap shadow-[2px_0_4px_rgba(0,0,0,0.3)]" style={{ backgroundColor: "#1a1a1a" }}>
                              <span>{item.label}</span>
                            </td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{hasData ? row!.ops : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{hasData ? row!.avg : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{hasData ? String(row!.hr) : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{hasData ? String(row!.rbi) : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{hasData ? row!.obp : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{hasData ? row!.slg : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{hasData ? String(row!.ab) : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{hasData ? String(row!.h) : na}</td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              </>
            )
          })()}

          {/* 月間成績（打順別と同デザイン） */}
          {showPilotTab("period") && (() => {
            const totalRow = stats.find((r) => r.split_type === "total" && r.split_value === "total")
            const byMonth = blocks?.blocks?.F?.by_month ?? {}
            const hasMar = (byMonth["2026-03"] ?? 0) > 0
            const hasApr = (byMonth["2026-04"] ?? 0) > 0
            const MONTH_ITEMS = [
              { key: "3・4月", label: "3・4月", hasData: hasMar || hasApr },
              { key: "5月", label: "5月", hasData: (byMonth["2026-05"] ?? 0) > 0 },
              { key: "6月", label: "6月", hasData: (byMonth["2026-06"] ?? 0) > 0 },
              { key: "7月", label: "7月", hasData: (byMonth["2026-07"] ?? 0) > 0 },
              { key: "8月", label: "8月", hasData: (byMonth["2026-08"] ?? 0) > 0 },
              { key: "9月", label: "9月", hasData: (byMonth["2026-09"] ?? 0) > 0 },
              { key: "10月", label: "10月", hasData: (byMonth["2026-10"] ?? 0) > 0 },
              { key: "11月", label: "11月", hasData: (byMonth["2026-11"] ?? 0) > 0 },
            ] as const
            const na = "—"

            return (
              <>
                <h2
                  className={`${titleBase} mb-4 pl-4 mt-8`}
                  style={{
                    borderLeft: "6px solid #FF4444",
                    fontWeight: 900,
                  }}
                >
                  月間成績
                </h2>
                <div className="overflow-x-auto overflow-y-hidden mb-4">
                  <table className="text-xs" style={{ fontVariantNumeric: "tabular-nums", borderCollapse: "separate", borderSpacing: 0, border: "1px solid #555", width: "100%", tableLayout: "fixed" }}>
                    <colgroup>
                      <col style={{ width: "56px" }} />
                      <col style={{ width: "50px" }} />
                      <col style={{ width: "45px" }} />
                      <col style={{ width: "45px" }} />
                      <col style={{ width: "45px" }} />
                      <col style={{ width: "51px" }} />
                      <col style={{ width: "51px" }} />
                      <col style={{ width: "45px" }} />
                      <col style={{ width: "45px" }} />
                    </colgroup>
                    <thead>
                      <tr style={{ backgroundColor: "#FFFF44", color: "#000000" }}>
                        <th className="px-0.5 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500 first:border-l-0 sticky left-0 bg-[#FFFF44] z-20 shadow-[2px_0_4px_rgba(0,0,0,0.3)]">月名</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500">OPS</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500">打率</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500">本塁打</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500">打点</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500">出塁率</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500">長打率</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500">打数</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500">安打</th>
                      </tr>
                    </thead>
                    <tbody>
                      {MONTH_ITEMS.map((item) => {
                        const row = item.hasData && totalRow ? totalRow : null
                        const hasData = row != null
                        return (
                          <tr key={item.key} style={{ backgroundColor: "rgba(255,255,255,0.03)" }}>
                            <td className="px-0.5 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500 first:border-l-0 sticky left-0 z-20 whitespace-nowrap shadow-[2px_0_4px_rgba(0,0,0,0.3)]" style={{ backgroundColor: "#1a1a1a" }}>
                              {item.label}
                            </td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{hasData ? row!.ops : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{hasData ? row!.avg : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{hasData ? String(row!.hr) : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{hasData ? String(row!.rbi) : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{hasData ? row!.obp : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{hasData ? row!.slg : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{hasData ? String(row!.ab) : na}</td>
                            <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{hasData ? String(row!.h) : na}</td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              </>
            )
          })()}

          {/* 週間成績（打順別と同デザイン） */}
          {showPilotTab("period") && (() => {
            const totalRow = stats.find((r) => r.split_type === "total" && r.split_value === "total")
            const na = "—"
            if (!totalRow) return null
            return (
              <>
                <h2
                  className={`${titleBase} mb-4 pl-4 mt-8`}
                  style={{
                    borderLeft: "6px solid #FF4444",
                    fontWeight: 900,
                  }}
                >
                  週間成績
                </h2>
                <div className="overflow-x-auto overflow-y-hidden mb-4">
                  <table className="text-xs" style={{ fontVariantNumeric: "tabular-nums", borderCollapse: "separate", borderSpacing: 0, border: "1px solid #555", width: "100%", tableLayout: "fixed" }}>
                    <colgroup>
                      <col style={{ width: "72px" }} />
                      <col style={{ width: "50px" }} />
                      <col style={{ width: "45px" }} />
                      <col style={{ width: "45px" }} />
                      <col style={{ width: "45px" }} />
                      <col style={{ width: "51px" }} />
                      <col style={{ width: "51px" }} />
                      <col style={{ width: "45px" }} />
                      <col style={{ width: "45px" }} />
                    </colgroup>
                    <thead>
                      <tr style={{ backgroundColor: "#FFFF44", color: "#000000" }}>
                        <th className="px-0.5 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500 first:border-l-0 sticky left-0 bg-[#FFFF44] z-20 shadow-[2px_0_4px_rgba(0,0,0,0.3)]">週間</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500">OPS</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500">打率</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500">本塁打</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500">打点</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500">出塁率</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500">長打率</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500">打数</th>
                        <th className="px-0 py-1 text-center font-bold text-[10px] latin tabular-nums whitespace-nowrap border-l border-b border-gray-500">安打</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr style={{ backgroundColor: "rgba(255,255,255,0.03)" }}>
                        <td className="px-0.5 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500 first:border-l-0 sticky left-0 z-20 whitespace-nowrap shadow-[2px_0_4px_rgba(0,0,0,0.3)]" style={{ backgroundColor: "#1a1a1a" }}>
                          {getWeekRangeTueToSun(blocks?.meta?.date ?? "2026-03-04")}
                        </td>
                        <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{totalRow.ops}</td>
                        <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{totalRow.avg}</td>
                        <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{totalRow.hr}</td>
                        <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{totalRow.rbi}</td>
                        <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{totalRow.obp}</td>
                        <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{totalRow.slg}</td>
                        <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{totalRow.ab}</td>
                        <td className="px-0 py-1 text-center latin font-black tabular-nums text-[14px] border-l border-b border-gray-500">{totalRow.h}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <p className="text-xs text-gray-500 mt-1">週は火曜始まり・日曜終わり。失策は取得対象外のため—</p>
              </>
            )
          })()}
        </div>
      )}

    </div>
  )
}
