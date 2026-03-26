"use client"

import Link from "next/link"
import { formatStat } from "@/lib/formatStat"
import metricMap from "@/config/metric_map.json"
import {
  teamColors,
  playerRomanNames,
  standingsCL,
  standingsPL,
  type LeadersConfig,
} from "@/app/components/top/topPageConstants"

export type TopPageLayoutMode = "mobile" | "desktop"

type LeadersPanelProps = {
  data: LeadersConfig
  title: string
  leagueName: string
  leagueColor: string
  year?: number
  league?: string
  layout: TopPageLayoutMode
}

const LeaderRow = ({ leader, stat, index }: { leader: Record<string, unknown>; index: number; stat: unknown }) => {
  const formattedValue = formatStat(stat, leader.value)

  const romanName = (() => {
    if (leader.romanName && typeof leader.romanName === "string") {
      const parts = leader.romanName.trim().split(/\s+/)
      if (parts.length >= 2) {
        const lastName = parts[0]
        const firstName = parts[1]
        const initial = firstName.length > 0 ? firstName[0].toUpperCase() : ""
        return `${initial}.${lastName}`
      }
      if (parts.length === 1 && parts[0].length > 0) {
        const name = parts[0]
        return `${name[0].toUpperCase()}.${name}`
      }
      return ""
    }
    const name = typeof leader.name === "string" ? leader.name : ""
    if (playerRomanNames[name]) {
      const parts = playerRomanNames[name].split(/\s+/)
      if (parts.length >= 2) {
        const lastName = parts[0]
        const firstName = parts[1]
        const initial = firstName.length > 0 ? firstName[0].toUpperCase() : ""
        return `${initial}.${lastName}`
      }
      if (parts.length === 1 && parts[0].length > 0) {
        const n = parts[0]
        return `${n[0].toUpperCase()}.${n}`
      }
    }
    return ""
  })()

  const playerName = typeof leader.name === "string" ? leader.name : ""
  const teamKey = typeof leader.team === "string" ? leader.team : ""

  return (
    <div className="flex items-center gap-0.5 py-0.5">
      <div className="w-4 h-4 rounded-full bg-[#2a2a2a] flex items-center justify-center">
        <span className="text-white text-[10px] latin tabular-nums">{index + 1}</span>
      </div>
      <div className="w-1 h-6 mr-1" style={{ backgroundColor: teamColors[teamKey] || "#666" }} />
      <Link
        href={`/players/${playerName}?name=${encodeURIComponent((playerName || "").replace(/\s+/g, ""))}${romanName ? `&roman=${encodeURIComponent(romanName)}` : ""}`}
        className="flex-1 min-w-0 flex items-center gap-1 hover:opacity-80 transition-opacity"
      >
        <span className="text-white text-sm font-semibold leading-tight">{playerName}</span>
        {romanName && <span className="latin text-[10px] text-gray-400 leading-tight">{romanName}</span>}
      </Link>
      <div className="text-white text-base bebas tabular-nums font-normal">{formattedValue}</div>
    </div>
  )
}

const MiniLeaderRow = ({ leader, stat }: { leader: Record<string, unknown>; stat: unknown }) => {
  const formattedValue = formatStat(stat, leader.value)
  const romanName = (() => {
    const name = typeof leader.name === "string" ? leader.name : ""
    const raw = ((leader.romanName as string) || playerRomanNames[name] || "").trim()
    if (!raw) return ""
    if (/^[A-Z]\.[A-Za-z]+$/.test(raw)) return raw
    const parts = raw.split(/\s+/)
    if (parts.length >= 2) return `${parts[0][0].toUpperCase()}.${parts[1]}`
    if (parts[0].length > 0) return `${parts[0][0].toUpperCase()}.${parts[0]}`
    return ""
  })()

  const playerName = typeof leader.name === "string" ? leader.name : ""
  const teamKey = typeof leader.team === "string" ? leader.team : ""

  return (
    <div className="flex items-center gap-0.5 py-0.5">
      <div className="w-4 h-4 rounded-full bg-[#2a2a2a] flex items-center justify-center">
        <span className="text-white text-[10px] latin tabular-nums">1</span>
      </div>
      <div className="w-1 h-10 mr-1" style={{ backgroundColor: teamColors[teamKey] || "#666" }} />
      <Link
        href={`/players/${playerName}?name=${encodeURIComponent((playerName || "").replace(/\s+/g, ""))}${romanName ? `&roman=${encodeURIComponent(romanName)}` : ""}`}
        className="flex-1 min-w-0 flex flex-col hover:opacity-80 transition-opacity"
      >
        <span className="text-white text-sm font-semibold leading-tight">{playerName}</span>
        {romanName && <span className="latin text-[10px] text-gray-400 leading-tight">{romanName}</span>}
      </Link>
      <div className="text-white text-base bebas tabular-nums font-normal">{formattedValue}</div>
    </div>
  )
}

export function LeadersPanel({ data, title, leagueName, leagueColor, year = 2025, league, layout }: LeadersPanelProps) {
  const normalizeMetricKey = (metric: string): string => {
    if (metric in metricMap) {
      return metricMap[metric as keyof typeof metricMap]
    }
    const lowerMetric = metric.toLowerCase()
    for (const [key, value] of Object.entries(metricMap)) {
      if (key.toLowerCase() === lowerMetric) {
        return value
      }
    }
    return metric.toLowerCase().replace("%", "pct").replace("/", "").replace("-", "")
  }

  const getRankingUrl = (metric: string): string => {
    if (year && league) {
      const metricKey = normalizeMetricKey(metric)
      const order = metricKey === "kpct" || metricKey === "k%" ? "asc" : "desc"
      return `/ranking/${year}/${league}?sort=${encodeURIComponent(metricKey)}&order=${order}`
    }
    return `/ranking/${encodeURIComponent(metric)}`
  }

  const getStatsListUrl = (): string => {
    if (year && league) {
      return `/ranking/${year}/${league}`
    }
    return "/ranking/coming-soon"
  }

  const topGrid = layout === "desktop" ? "grid grid-cols-3 gap-1" : "grid grid-cols-1 gap-1"
  const miniGrid = layout === "desktop" ? "grid grid-cols-5 gap-1" : "grid grid-cols-2 gap-1"

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div style={{ width: "4px", height: "32px", backgroundColor: leagueColor }} />
          <div>
            <div className="text-sm font-medium">{title}</div>
            <div className="text-[10px] text-gray-400">{leagueName}</div>
          </div>
        </div>
      </div>

      <div className={topGrid}>
        {data.top3Metrics.map((metric) => (
          <div key={metric} className="bg-black border border-[#555] p-1 relative">
            <div className="flex items-stretch justify-between mb-1">
              <Link
                href={getRankingUrl(metric)}
                className="bg-black py-0.5 flex-1 text-center hover:opacity-80 transition-opacity"
              >
                <span className="latin text-[#ffff44] text-xs tracking-wider">{metric}</span>
              </Link>
              <Link
                href={getStatsListUrl()}
                className="bg-black py-0.5 px-1 text-[10px] text-[#e8e8e8] hover:text-white transition-colors flex items-center"
              >
                成績一覧
              </Link>
            </div>
            <div className="space-y-0">
              {data.leaders[metric]?.map((leader, leaderIndex) => (
                <LeaderRow key={leader.rank} leader={leader as Record<string, unknown>} stat={metric} index={leaderIndex} />
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className={miniGrid}>
        {data.miniMetrics.map((metric) => {
          const leader = data.leaders[metric]?.[0]
          if (!leader) return null
          return (
            <div key={metric} className="bg-black border border-[#555] p-0.5 relative">
              <div className="flex items-stretch justify-between mb-1">
                <Link
                  href={getRankingUrl(metric)}
                  className="bg-black py-0.5 flex-1 text-center hover:opacity-80 transition-opacity"
                >
                  <span className={`text-[#ffff44] text-xs ${/[a-zA-Z]/.test(metric) ? "latin" : ""}`}>{metric}</span>
                </Link>
                <Link
                  href={getStatsListUrl()}
                  className="bg-black py-0.5 px-0.5 text-[10px] text-[#e8e8e8] hover:text-white transition-colors flex items-center"
                >
                  成績一覧
                </Link>
              </div>
              <MiniLeaderRow leader={leader as Record<string, unknown>} stat={metric} />
            </div>
          )
        })}
      </div>
    </div>
  )
}

export function StandingsPanel({ league, leagueColor }: { league: string; leagueColor: string }) {
  const standings = league === "CL" ? standingsCL : standingsPL

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div style={{ width: "4px", height: "32px", backgroundColor: leagueColor }} />
          <div>
            <div className="text-sm font-medium">{league === "CL" ? "セ・リーグ" : "パ・リーグ"} 順位表</div>
          </div>
        </div>
      </div>
      <div className="bg-black border border-[#555] p-4">
        <table className="w-full">
          <thead>
            <tr>
              <th className="text-[10px] text-gray-400">順位</th>
              <th className="text-[10px] text-gray-400">チーム</th>
              <th className="text-[10px] text-gray-400">勝</th>
              <th className="text-[10px] text-gray-400">負</th>
              <th className="text-[10px] text-gray-400">勝率</th>
              <th className="text-[10px] text-gray-400">得点</th>
              <th className="text-[10px] text-gray-400">防御率</th>
            </tr>
          </thead>
          <tbody>
            {standings.map((team) => (
              <tr key={team.name} className="hover:bg-[#2a2a2a] transition-colors">
                <td className="text-white text-base bebas tabular-nums font-normal">{team.pos}</td>
                <td className="text-white text-base bebas tabular-nums font-normal">{team.name}</td>
                <td className="text-white text-base bebas tabular-nums font-normal">{team.w}</td>
                <td className="text-white text-base bebas tabular-nums font-normal">{team.l}</td>
                <td className="text-white text-base bebas tabular-nums font-normal">{(team.pct * 100).toFixed(1)}%</td>
                <td className="text-white text-base bebas tabular-nums font-normal">{team.runs}</td>
                <td className="text-white text-base bebas tabular-nums font-normal">{team.era}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
