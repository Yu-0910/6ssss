/**
 * クライアントコンポーネント: 指定年度・リーグの打撃成績リーダーを表示
 * LeadersPanelと同じロジックを使用
 */

"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { formatStat } from "@/lib/formatStat"
import metricMap from "@/config/metric_map.json"

type LeadersConfig = {
  top3Metrics: string[]
  miniMetrics: string[]
  leaders: Record<string, any[]>
}

type TopPageLeadersClientProps = {
  year: number | string
  league: string
}

const teamColors: Record<string, string> = {
  H: "#ffde00",
  G: "#ff6600",
  DB: "#0067c0",
  C: "#d60718",
  D: "#004ea2",
  S: "#2bbb3f",
  Bs: "#b79e51",
  M: "#222",
  F: "#0077c8",
  E: "#7a0019",
  L: "#004098",
  Hs: "#ffdb00",
}

const leagueColors: Record<string, string> = {
  CL: "#039850",
  PL: "#10b8ce",
}

const leagueNames: Record<string, { ja: string; en: string }> = {
  CL: { ja: "セ・リーグ", en: "Central League" },
  PL: { ja: "パ・リーグ", en: "Pacific League" },
}

const LeaderRow = ({ leader, stat, index }: { leader: any; index: number; stat: any }) => {
  const formattedValue = formatStat(stat, leader.value)
  const romanName = leader.romanName || ""
  
  return (
    <div className="flex items-center gap-0.5 py-0.5">
      <div className="w-4 h-4 rounded-full bg-[#2a2a2a] flex items-center justify-center">
        <span className="text-white text-[10px] latin tabular-nums">{index + 1}</span>
      </div>
      <div className="w-1 h-6 mr-1" style={{ backgroundColor: teamColors[leader.team] || "#666" }} />
      <Link
        href={`/players/${leader.name}`}
        className="flex-1 min-w-0 flex items-center gap-1 hover:opacity-80 transition-opacity"
      >
        <span className="text-white text-sm font-semibold leading-tight">{leader.name}</span>
        {romanName && (
          <span className="latin text-[10px] text-gray-400 leading-tight">{romanName}</span>
        )}
      </Link>
      <div className="text-white text-base bebas tabular-nums font-normal">{formattedValue}</div>
    </div>
  )
}

const MiniLeaderRow = ({ leader, stat }: { leader: any; stat: any }) => {
  const formattedValue = formatStat(stat, leader.value)
  const romanName = leader.romanName || ""
  
  return (
    <div className="flex items-center gap-0.5 py-0.5">
      <div className="w-4 h-4 rounded-full bg-[#2a2a2a] flex items-center justify-center">
        <span className="text-white text-[10px] latin tabular-nums">1</span>
      </div>
      <div className="w-1 h-10 mr-1" style={{ backgroundColor: teamColors[leader.team] || "#666" }} />
      <Link
        href={`/players/${leader.name}`}
        className="flex-1 min-w-0 flex flex-col hover:opacity-80 transition-opacity"
      >
        <span className="text-white text-sm font-semibold leading-tight">{leader.name}</span>
        {romanName && (
          <span className="latin text-[10px] text-gray-400 leading-tight">{romanName}</span>
        )}
      </Link>
      <div className="text-white text-base bebas tabular-nums font-normal">{formattedValue}</div>
    </div>
  )
}

export default function TopPageLeadersClient({ year, league }: TopPageLeadersClientProps) {
  const [data, setData] = useState<LeadersConfig | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()
  
  // リーグ名を大文字に正規化
  const upperLeague = league.toUpperCase()
  const leagueInfo = leagueNames[upperLeague] || { ja: `${upperLeague}リーグ`, en: `${upperLeague} League` }
  const leagueColor = leagueColors[upperLeague] || "#666"
  
  useEffect(() => {
    // APIルートからデータを取得
    const apiUrl = `/api/leaders/${year}/${upperLeague}`
    console.log(`[TopPageLeadersClient] Fetching: ${apiUrl}`)
    
    fetch(apiUrl)
      .then(res => {
        console.log(`[TopPageLeadersClient] Response status: ${res.status}`)
        if (!res.ok) {
          return res.json().then(errData => {
            throw new Error(errData.error || `HTTP error! status: ${res.status}`)
          })
        }
        return res.json()
      })
      .then(data => {
        console.log(`[TopPageLeadersClient] Data received:`, data)
        // エラーレスポンスをチェック
        if (data.error) {
          throw new Error(data.error)
        }
        setData(data)
        setLoading(false)
      })
      .catch(err => {
        console.error('[TopPageLeadersClient] Error fetching leaders:', err)
        setError(err.message || 'データの取得に失敗しました')
        setLoading(false)
      })
  }, [year, upperLeague])
  
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
    return metric.toLowerCase().replace('%', 'pct').replace('/', '').replace('-', '')
  }

  const getRankingUrl = (metric: string): string => {
    const metricKey = normalizeMetricKey(metric)
    const order = (metricKey === 'kpct' || metricKey === 'k%') ? 'asc' : 'desc'
    const yearStr = String(year)
    return `/ranking/${yearStr}/${upperLeague}?sort=${encodeURIComponent(metricKey)}&order=${order}`
  }

  const getStatsListUrl = (): string => {
    const yearStr = String(year)
    const url = `/ranking/${yearStr}/${upperLeague}`
    if (process.env.NODE_ENV === 'development') {
      console.log(`[TopPageLeadersClient] getStatsListUrl: ${url}`)
    }
    return url
  }

  if (loading) {
    return (
      <div className="space-y-1">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div style={{ width: "4px", height: "32px", backgroundColor: leagueColor }} />
            <div>
              <div className="text-sm font-medium">{leagueInfo.ja} 打撃成績</div>
              <div className="text-[10px] text-gray-400">{leagueInfo.en}</div>
            </div>
          </div>
        </div>
        <div className="text-white text-sm text-center py-4">読み込み中...</div>
      </div>
    )
  }
  
  if (error || !data) {
    return (
      <div className="space-y-1">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div style={{ width: "4px", height: "32px", backgroundColor: leagueColor }} />
            <div>
              <div className="text-sm font-medium">{leagueInfo.ja} 打撃成績</div>
              <div className="text-[10px] text-gray-400">{leagueInfo.en}</div>
            </div>
          </div>
        </div>
        <div className="text-white text-sm text-center py-4">データの取得に失敗しました</div>
      </div>
    )
  }

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div style={{ width: "4px", height: "32px", backgroundColor: leagueColor }} />
          <div>
            <div className="text-sm font-medium">{leagueInfo.ja} 打撃成績</div>
            <div className="text-[10px] text-gray-400">{leagueInfo.en}</div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-1">
        {data.top3Metrics.map((metric) => (
          <div key={metric} className="bg-black border border-[#555] p-1 relative">
            <div className="flex items-stretch justify-between mb-1">
              <Link
                href={getRankingUrl(metric)}
                className="bg-black py-0.5 flex-1 text-center hover:opacity-80 transition-opacity"
              >
                <span className="latin text-[#ffff44] text-xs tracking-wider">{metric}</span>
              </Link>
              <button
                type="button"
                onClick={(e) => {
                  e.preventDefault()
                  const url = getStatsListUrl()
                  if (process.env.NODE_ENV === 'development') {
                    console.log(`[TopPageLeadersClient] 成績一覧 clicked: ${url}`)
                  }
                  router.push(url)
                }}
                className="bg-black py-0.5 px-1 text-[10px] text-[#e8e8e8] hover:text-white transition-colors flex items-center cursor-pointer"
              >
                成績一覧
              </button>
            </div>
            <div className="space-y-0">
              {data.leaders[metric]?.map((leader, leaderIndex) => (
                <LeaderRow key={leader.rank} leader={leader} stat={metric} index={leaderIndex} />
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-1">
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
                <button
                  type="button"
                  onClick={(e) => {
                    e.preventDefault()
                    const url = getStatsListUrl()
                    if (process.env.NODE_ENV === 'development') {
                      console.log(`[TopPageLeadersClient] 成績一覧 clicked: ${url}`)
                    }
                    router.push(url)
                  }}
                  className="bg-black py-0.5 px-0.5 text-[10px] text-[#e8e8e8] hover:text-white transition-colors flex items-center cursor-pointer"
                >
                  成績一覧
                </button>
              </div>
              <MiniLeaderRow leader={leader} stat={metric} />
            </div>
          )
        })}
      </div>
    </div>
  )
}

