/**
 * ランキングJSONデータローダー
 * プロキシ経由（/data/rankings/...）でランキングJSONファイルを取得
 */

import { getRankingsUrl } from './url'

/**
 * ランキングJSONファイルを取得
 * 
 * @param year 年度（例: '2025'）
 * @param league リーグ（例: 'PL' または 'CL'）
 * @param metric 指標名（例: 'OPS' または '打率'）
 * @returns ランキングデータ（JSON形式）
 */
export async function loadRankingJson(
  year: string,
  league: string,
  metric: string
): Promise<any> {
  // パスを生成（プロキシ経由）
  const path = `data/rankings/${year}/${league}/${metric}.json`
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
 * @param league リーグ
 * @param metrics 指標名の配列
 * @returns 指標名をキーとしたランキングデータのマップ
 */
export async function loadRankingJsons(
  year: string,
  league: string,
  metrics: string[]
): Promise<Record<string, any>> {
  const results: Record<string, any> = {}
  
  // 並列で取得（パフォーマンス向上）
  const promises = metrics.map(async (metric) => {
    try {
      const data = await loadRankingJson(year, league, metric)
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
