/**
 * 指標定義（ランキングページの唯一の真実）
 */

export type MetricKey =
  | 'ops'
  | 'avg'
  | 'h'
  | 'hr'
  | 'rbi'
  | 'g'
  | 'pa'
  | 'ab'
  | 'singles'
  | 'doubles'
  | 'triples'
  | 'runs'
  | 'obp'
  | 'slg'
  | 'isop'
  | 'isod'
  | 'bbPct'
  | 'kPct'
  | 'bb'
  | 'ibb'
  | 'hbp'
  | 'so'
  | 'bbk'
  | 'tb'
  | 'sb'
  | 'cs'
  | 'sh'
  | 'sf'
  | 'gidp'
  | 'rc'
  | 'xr'
  | 'babip'
  | 'seca'
  | 'ta'
  | 'noi'
  | 'gpa'

export type SortOrder = 'desc' | 'asc'

export interface MetricDefinition {
  key: MetricKey
  label: string // 日本語表示ラベル
  csvKey: string // CSV列名（大文字小文字対応）
  needsQualification: boolean // 規定打席が必要か
  sortOrder: SortOrder // ソート順（desc=降順、asc=昇順）
  formatFn: (value: number) => string // 値のフォーマット関数
}

// 値のフォーマット関数
const formatDecimal3 = (value: number): string => {
  if (isNaN(value) || !isFinite(value)) return '-'
  return value.toFixed(3)
}

const formatDecimal2 = (value: number): string => {
  if (isNaN(value) || !isFinite(value)) return '-'
  return value.toFixed(2)
}

const formatDecimal1 = (value: number): string => {
  if (isNaN(value) || !isFinite(value)) return '-'
  return value.toFixed(1)
}

const formatInt = (value: number): string => {
  if (isNaN(value) || !isFinite(value)) return '-'
  return String(Math.round(value))
}

const formatPercent1 = (value: number): string => {
  if (isNaN(value) || !isFinite(value)) return '-'
  return value.toFixed(1)
}

// 指標定義マップ
export const METRICS: Record<MetricKey, MetricDefinition> = {
  ops: {
    key: 'ops',
    label: 'OPS',
    csvKey: 'OPS',
    needsQualification: true,
    sortOrder: 'desc',
    formatFn: formatDecimal3,
  },
  avg: {
    key: 'avg',
    label: '打率',
    csvKey: 'AVG',
    needsQualification: true,
    sortOrder: 'desc',
    formatFn: formatDecimal3,
  },
  h: {
    key: 'h',
    label: '安打',
    csvKey: 'H',
    needsQualification: false,
    sortOrder: 'desc',
    formatFn: formatInt,
  },
  hr: {
    key: 'hr',
    label: '本塁打',
    csvKey: 'HR',
    needsQualification: false,
    sortOrder: 'desc',
    formatFn: formatInt,
  },
  rbi: {
    key: 'rbi',
    label: '打点',
    csvKey: 'RBI',
    needsQualification: false,
    sortOrder: 'desc',
    formatFn: formatInt,
  },
  g: {
    key: 'g',
    label: '試合',
    csvKey: 'G',
    needsQualification: false,
    sortOrder: 'desc',
    formatFn: formatInt,
  },
  pa: {
    key: 'pa',
    label: '打席',
    csvKey: 'PA',
    needsQualification: false,
    sortOrder: 'desc',
    formatFn: formatInt,
  },
  ab: {
    key: 'ab',
    label: '打数',
    csvKey: 'AB',
    needsQualification: false,
    sortOrder: 'desc',
    formatFn: formatInt,
  },
  singles: {
    key: 'singles',
    label: '単打',
    csvKey: '1B',
    needsQualification: false,
    sortOrder: 'desc',
    formatFn: formatInt,
  },
  doubles: {
    key: 'doubles',
    label: '二塁打',
    csvKey: '2B',
    needsQualification: false,
    sortOrder: 'desc',
    formatFn: formatInt,
  },
  triples: {
    key: 'triples',
    label: '三塁打',
    csvKey: '3B',
    needsQualification: false,
    sortOrder: 'desc',
    formatFn: formatInt,
  },
  runs: {
    key: 'runs',
    label: '得点',
    csvKey: 'R',
    needsQualification: false,
    sortOrder: 'desc',
    formatFn: formatInt,
  },
  obp: {
    key: 'obp',
    label: '出塁率',
    csvKey: 'OBP',
    needsQualification: true,
    sortOrder: 'desc',
    formatFn: formatDecimal3,
  },
  slg: {
    key: 'slg',
    label: '長打率',
    csvKey: 'SLG',
    needsQualification: true,
    sortOrder: 'desc',
    formatFn: formatDecimal3,
  },
  isop: {
    key: 'isop',
    label: 'IsoP',
    csvKey: 'IsoP',
    needsQualification: true,
    sortOrder: 'desc',
    formatFn: formatDecimal3,
  },
  isod: {
    key: 'isod',
    label: 'IsoD',
    csvKey: 'IsoD',
    needsQualification: true,
    sortOrder: 'desc',
    formatFn: formatDecimal3,
  },
  bbPct: {
    key: 'bbPct',
    label: 'BB%',
    csvKey: 'BB%',
    needsQualification: true,
    sortOrder: 'desc',
    formatFn: formatPercent1,
  },
  kPct: {
    key: 'kPct',
    label: 'K%',
    csvKey: 'K%',
    needsQualification: true,
    sortOrder: 'asc', // 例外：小さいほど良い
    formatFn: formatPercent1,
  },
  bb: {
    key: 'bb',
    label: '四球',
    csvKey: 'BB',
    needsQualification: false,
    sortOrder: 'desc',
    formatFn: formatInt,
  },
  ibb: {
    key: 'ibb',
    label: '敬遠',
    csvKey: 'IBB',
    needsQualification: false,
    sortOrder: 'desc',
    formatFn: formatInt,
  },
  hbp: {
    key: 'hbp',
    label: '死球',
    csvKey: 'HBP',
    needsQualification: false,
    sortOrder: 'desc',
    formatFn: formatInt,
  },
  so: {
    key: 'so',
    label: '三振',
    csvKey: 'SO',
    needsQualification: false,
    sortOrder: 'desc',
    formatFn: formatInt,
  },
  bbk: {
    key: 'bbk',
    label: 'BB/K',
    csvKey: 'BB/K',
    needsQualification: true,
    sortOrder: 'desc',
    formatFn: formatDecimal3,
  },
  tb: {
    key: 'tb',
    label: '塁打',
    csvKey: 'TB',
    needsQualification: false,
    sortOrder: 'desc',
    formatFn: formatInt,
  },
  sb: {
    key: 'sb',
    label: '盗塁',
    csvKey: 'SB',
    needsQualification: false,
    sortOrder: 'desc',
    formatFn: formatInt,
  },
  cs: {
    key: 'cs',
    label: '盗塁死',
    csvKey: 'CS',
    needsQualification: false,
    sortOrder: 'desc',
    formatFn: formatInt,
  },
  sh: {
    key: 'sh',
    label: '犠打',
    csvKey: 'SH',
    needsQualification: false,
    sortOrder: 'desc',
    formatFn: formatInt,
  },
  sf: {
    key: 'sf',
    label: '犠飛',
    csvKey: 'SF',
    needsQualification: false,
    sortOrder: 'desc',
    formatFn: formatInt,
  },
  gidp: {
    key: 'gidp',
    label: '併殺打',
    csvKey: 'GDP',
    needsQualification: false,
    sortOrder: 'desc',
    formatFn: formatInt,
  },
  rc: {
    key: 'rc',
    label: 'RC',
    csvKey: 'RC',
    needsQualification: true,
    sortOrder: 'desc',
    formatFn: formatDecimal1, // 小数1桁
  },
  xr: {
    key: 'xr',
    label: 'XR',
    csvKey: 'XR',
    needsQualification: true,
    sortOrder: 'desc',
    formatFn: formatDecimal1, // 小数1桁
  },
  babip: {
    key: 'babip',
    label: 'BABIP',
    csvKey: 'BABIP',
    needsQualification: true,
    sortOrder: 'desc',
    formatFn: formatDecimal3,
  },
  seca: {
    key: 'seca',
    label: 'SecA',
    csvKey: 'SecA',
    needsQualification: true,
    sortOrder: 'desc',
    formatFn: formatDecimal3,
  },
  ta: {
    key: 'ta',
    label: 'TA',
    csvKey: 'TA',
    needsQualification: true,
    sortOrder: 'desc',
    formatFn: formatDecimal3,
  },
  noi: {
    key: 'noi',
    label: 'NOI',
    csvKey: 'NOI',
    needsQualification: true,
    sortOrder: 'desc',
    formatFn: formatDecimal2,
  },
  gpa: {
    key: 'gpa',
    label: 'GPA',
    csvKey: 'GPA',
    needsQualification: true,
    sortOrder: 'desc',
    formatFn: formatDecimal3,
  },
}

/**
 * metric文字列からMetricDefinitionを取得
 */
export function getMetric(key: string): MetricDefinition | null {
  const normalized = key.toLowerCase().trim()
  return METRICS[normalized as MetricKey] || null
}

/**
 * 規定打席の閾値（暫定）
 */
export const QUAL_PA = 443 // 143試合 × 3.1 を四捨五入

/**
 * 全指標定義を取得
 */
export function getAllMetrics(): MetricDefinition[] {
  return Object.values(METRICS)
}

