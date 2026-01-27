/**
 * ランキング関連の型定義
 */

export interface MetricDefinition {
  key: string
  label: string
  csvKey: string // CSVの実際の列名（日本語/英語の可能性）
}

export interface RankingRow {
  rank: number
  playerId: string
  name: string
  romanName?: string
  team: string
  valueText: string // 整形済みの値（UI表示用）
  subText?: string // 補足情報（任意）
  rawValue?: number // ソート用の生の値（任意）
  [key: string]: any // 全指標の値を含める（metric.key でアクセス）
}

export interface RankingViewModel {
  title: string
  season: string
  league: string
  metrics: MetricDefinition[] // Record.csv順の利用可能な指標
  activeMetric: string // 現在選択中の指標キー
  rows: RankingRow[]
  debug?: {
    csvPath: string
    duplicatePlayerIdCount: number
    duplicateRowCount: number
  }
}

export interface BattingCsvRow {
  [key: string]: string | number | undefined
}

