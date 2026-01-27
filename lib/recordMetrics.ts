/**
 * Record.csvから指標リストを読み込むユーティリティ
 * UIとデータの責務を分離するため、指標定義を一元管理
 */

import fs from 'fs'
import path from 'path'

export interface MetricDefinition {
  key: string
  label: string
  csvKey: string
}

/**
 * Record.csvから指標リストを抽出
 * @param recordCsvPath Record.csvのパス（省略時は自動探索）
 * @returns 指標定義の配列
 */
export function loadMetricsFromRecord(recordCsvPath?: string): MetricDefinition[] {
  // パスが指定されていない場合は自動探索
  if (!recordCsvPath) {
    const rootPath = path.join(process.cwd(), 'Record.csv')
    const dataPath = path.join(process.cwd(), '_data', 'master_csv', 'Record.csv')
    
    if (fs.existsSync(rootPath)) {
      recordCsvPath = rootPath
    } else if (fs.existsSync(dataPath)) {
      recordCsvPath = dataPath
    } else {
      console.warn('Record.csvが見つかりません。デフォルト指標を使用します。')
      return getDefaultMetrics()
    }
  }

  // CSVファイルを読み込む
  const encodings = ['utf-8-sig', 'utf-8', 'shift_jis', 'cp932']
  let firstLine: string | null = null

  for (const encoding of encodings) {
    try {
      const content = fs.readFileSync(recordCsvPath, encoding as BufferEncoding)
      firstLine = content.split('\n')[0]
      if (firstLine) break
    } catch (error) {
      continue
    }
  }

  if (!firstLine) {
    console.warn('Record.csvの読み込みに失敗しました。デフォルト指標を使用します。')
    return getDefaultMetrics()
  }

  // 改行文字を除去
  firstLine = firstLine.replace(/\r?\n$/, '')

  // 区切り文字を判定（カンマ区切りを優先）
  let metricsRaw = firstLine.split(',')
  if (metricsRaw.length === 1) {
    metricsRaw = firstLine.split('\t')
  }

  // 除外列のセット
  const excludeCols = new Set(['id', 'name', 'label', 'desc', 'description', '単位', '備考', 'unit', 'note', 'memo'])

  // 各指標名を正規化して変換
  const metrics: MetricDefinition[] = []
  for (let metric of metricsRaw) {
    // BOM除去
    metric = metric.replace(/^\ufeff/, '')
    // 前後空白除去
    metric = metric.trim()
    // 全角スペース除去
    metric = metric.replace(/\u3000/g, ' ').trim()
    // 空文字は除外
    if (!metric) continue

    // 除外列チェック
    const metricLower = metric.toLowerCase()
    if (excludeCols.has(metricLower)) continue

    // キーを生成（日本語の場合はローマ字化、英字の場合は小文字化）
    const key = normalizeMetricKey(metric)
    const csvKey = metric // CSVの元のキー名

    metrics.push({
      key,
      label: metric,
      csvKey,
    })
  }

  return metrics
}

/**
 * 指標名を正規化してキーを生成
 */
function normalizeMetricKey(metric: string): string {
  // 既に英字の場合は小文字化
  if (/^[A-Za-z0-9%\/\-]+$/.test(metric)) {
    return metric.toLowerCase()
  }

  // 日本語の場合は既知のマッピングを使用
  const japaneseToKey: Record<string, string> = {
    '打率': 'avg',
    '安打': 'hits',
    '本塁打': 'hr',
    '打点': 'rbi',
    '試合': 'games',
    '打席': 'pa',
    '打数': 'ab',
    '単打': 'singles',
    '二塁打': 'doubles',
    '三塁打': 'triples',
    '得点': 'runs',
    '出塁率': 'obp',
    '長打率': 'slg',
    '四球': 'bb',
    '敬遠': 'ibb',
    '死球': 'hbp',
    '三振': 'so',
    '塁打': 'tb',
    '盗塁': 'sb',
    '盗塁死': 'cs',
    '犠打': 'sh',
    '犠飛': 'sf',
    '併殺打': 'gidp',
  }

  return japaneseToKey[metric] || metric.toLowerCase().replace(/\s+/g, '_')
}

/**
 * デフォルト指標（Record.csvが読み込めない場合のフォールバック）
 */
function getDefaultMetrics(): MetricDefinition[] {
  return [
    { key: 'ops', label: 'OPS', csvKey: 'OPS' },
    { key: 'avg', label: '打率', csvKey: '打率' },
    { key: 'obp', label: '出塁率', csvKey: '出塁率' },
    { key: 'slg', label: '長打率', csvKey: '長打率' },
    { key: 'hr', label: 'HR', csvKey: '本塁打' },
    { key: 'rbi', label: '打点', csvKey: '打点' },
    { key: 'hits', label: '安打', csvKey: '安打' },
    { key: 'runs', label: '得点', csvKey: '得点' },
    { key: 'pa', label: '打席', csvKey: '打席' },
    { key: 'ab', label: '打数', csvKey: '打数' },
  ]
}

