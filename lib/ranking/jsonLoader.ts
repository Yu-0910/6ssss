/**
 * ランキングJSONデータローダー
 * プロキシ経由（/data/rankings/...）でランキングJSONファイルを取得
 */

import { getRankingsUrl } from './url'

import { sanitizeMetricForPath } from './url'

/**
 * ランキングJSONファイルを取得
 * パス形式: data/rankings/{year}/{season}/{metric}.json または {metric}_all.json
 * R2 およびローカル構造と一致。
 *
 * @param year 年度（例: '2025'）
 * @param season シーズン識別子（例: 'CL', 'PL', 'PRE_spring', 'PRE_fall'）
 * @param metric 指標名（例: 'OPS' または '打率'、'BB/K' は 'BB_K' にサニタイズ）
 * @param useAllPlayers 規定打席不要の指標で全選手データを使う場合 true（安打・本塁打などは _all.json を取得）
 * @returns ランキングデータ（JSON形式）
 */
export async function loadRankingJson(
  year: string,
  season: string,
  metric: string,
  useAllPlayers?: boolean
): Promise<any> {
  // 2026年は2025年データを流用
  const dataYear = year === '2026' ? '2025' : year
  const fileBase = sanitizeMetricForPath(metric)
  const fileName = useAllPlayers ? `${fileBase}_all.json` : `${fileBase}.json`
  const path = `data/rankings/${dataYear}/${season}/${fileName}`
  const url = getRankingsUrl(path)
  
  // サーバーサイドでは絶対URLが必要
  const baseUrl = typeof window === 'undefined' 
    ? process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000'
    : window.location.origin
  
  const fullUrl = `${baseUrl}${url}`
  
  if (process.env.NODE_ENV === 'development') {
    console.log(`[loadRankingJson] Fetching: ${fullUrl}`)
  }
  
  const response = await fetch(fullUrl, {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
    },
    // サーバーサイドではキャッシュを無効化
    cache: 'no-store',
  })
  
  if (!response.ok) {
    throw new Error(`Failed to fetch ranking data: ${response.status} ${response.statusText}`)
  }
  
  const data = await response.json()
  return data
}

/**
 * 複数のランキングJSONファイルを取得
 *
 * @param year 年度
 * @param season シーズン識別子（CL/PL/PRE_spring/PRE_fall 等）
 * @param metrics 指標名の配列
 * @returns 指標名をキーとしたランキングデータのマップ
 */
export async function loadRankingJsons(
  year: string,
  season: string,
  metrics: string[]
): Promise<Record<string, any>> {
  const results: Record<string, any> = {}
  
  // 並列で取得（パフォーマンス向上）
  const promises = metrics.map(async (metric) => {
    try {
      const data = await loadRankingJson(year, season, metric)
      return { metric, data }
    } catch (error) {
      console.error(`[loadRankingJsons] Failed to load ${metric}:`, error)
      return { metric, data: null }
    }
  })
  
  const resolved = await Promise.all(promises)
  
  for (const { metric, data } of resolved) {
    if (data !== null) {
      results[metric] = data
    }
  }
  
  return results
}
