/**
 * metric_map.json を読み込む（単一ソース）
 * Record.csvの指標名 → JSONキー名のマッピング
 */

import fs from 'fs'
import path from 'path'

let cachedMetricMap: Record<string, string> | null = null

/**
 * metric_map.jsonを読み込む（キャッシュ付き）
 */
export function loadMetricMap(): Record<string, string> {
  if (cachedMetricMap) {
    return cachedMetricMap
  }

  const metricMapPath = path.join(process.cwd(), 'config', 'metric_map.json')
  
  if (!fs.existsSync(metricMapPath)) {
    throw new Error(`metric_map.jsonが見つかりません: ${metricMapPath}`)
  }

  const content = fs.readFileSync(metricMapPath, 'utf-8')
  cachedMetricMap = JSON.parse(content)
  
  return cachedMetricMap
}

/**
 * Record.csvの指標名からJSONキー名を取得
 */
export function getJsonKey(recordMetric: string): string {
  const metricMap = loadMetricMap()
  return metricMap[recordMetric] || recordMetric.toLowerCase().replace(/\s+/g, '_')
}



















