/**
 * Client Component for Ranking Page
 * ソート処理とクエリパラメータ管理を行う
 */

"use client"

import { useRouter, useSearchParams } from 'next/navigation'
import { useState, useEffect, useMemo, Suspense } from 'react'
import RankingUI from '@/components/RankingUI'
import type { RankingViewModel, RankingRow } from '@/lib/ranking/types'
import { loadRankingJson } from '@/lib/ranking/jsonLoader'
import { shouldRequireQualifyingPA, calculateMinPA, get1950MinGames } from '@/lib/ranking/qualifyingPA'

interface RankingPageClientProps {
  initialViewModel: RankingViewModel
}

/**
 * 指標のデフォルトソート順を取得（K%のみ昇順）
 */
function getDefaultSortOrder(metricKey: string): 'asc' | 'desc' {
  if (metricKey === 'kpct' || metricKey === 'k%') {
    return 'asc'
  }
  return 'desc'
}

/**
 * JSON行をUI用に正規化（全年度1950-2024対応: 英字名・キー名の揺れに耐性を持たせる）
 * romanName / roman_name / RomanName / player_name_en などを romanName に統一
 * name / player / player_name_ja / 選手名 などを name に統一
 */
function normalizeRankingRow(raw: Record<string, unknown>): RankingRow {
  const romanNameRaw = (
    raw['romanName'] ?? raw['roman_name'] ?? raw['RomanName'] ?? raw['name_en'] ?? raw['player_name_en'] ?? ''
  ) as string
  const romanName =
    typeof romanNameRaw === 'string' && romanNameRaw.trim() !== '' ? romanNameRaw.trim() : undefined
  const name = String(
    raw['name'] ?? raw['player'] ?? raw['player_name_ja'] ?? raw['選手名'] ?? raw['名前'] ?? raw['Name'] ?? ''
  ).trim()
  return {
    ...raw,
    rank: raw['rank'] as number,
    playerId: String(raw['playerId'] ?? raw['player_id'] ?? raw['id'] ?? ''),
    name: name || '不明',
    romanName,
    team: String(raw['team'] ?? raw['Team'] ?? raw['チーム'] ?? raw['team_name'] ?? ''),
  } as RankingRow
}

/** CSV英字名マップ用のキー（server の normalizeKey と同一） */
function romanMapKey(name: string, team: string): string {
  const n = (name ?? '').toString().replace(/\u3000/g, ' ').trim()
  const t = (team ?? '').toString().trim()
  return `${n}|${t}`
}

/** スペース除去キー（照合フォールバック用） */
function romanMapKeyNoSpace(name: string, team: string): string {
  const n = (name ?? '').toString().replace(/[\s\u3000]/g, '').trim()
  const t = (team ?? '').toString().trim()
  return `${n}|${t}`
}

/**
 * CSV参照の英字名マップを取得し、行にromanNameが無い場合に補完する
 */
async function mergeRomanNamesFromCsv(
  rows: RankingRow[],
  season: string,
  league: string
): Promise<RankingRow[]> {
  const baseUrl = typeof window === 'undefined' ? '' : window.location.origin
  const url = `${baseUrl}/api/roman-names/${season}/${league}`
  let map: Record<string, string> = {}
  try {
    const res = await fetch(url, { cache: 'no-store' })
    if (res.ok) map = (await res.json()) as Record<string, string>
  } catch {
    return rows
  }
  return rows.map(row => {
    if (row.romanName && row.romanName.trim()) return row
    const key = romanMapKey(row.name, row.team)
    const keyNoSpace = romanMapKeyNoSpace(row.name, row.team)
    const en = map[key]?.trim() || map[keyNoSpace]?.trim()
    if (!en) return row
    return { ...row, romanName: en }
  })
}

function RankingPageClientInner({ initialViewModel }: RankingPageClientProps) {
  const router = useRouter()
  const searchParams = useSearchParams()

  // URLクエリパラメータからソート情報を取得
  const sortKey = searchParams.get('sort') || 'ops'
  const order = (searchParams.get('order') as 'asc' | 'desc') || getDefaultSortOrder(sortKey)

  // 案A: 表示中の指標ごとにJSONを取得して保持
  const [rowsFromJson, setRowsFromJson] = useState<RankingRow[]>([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)

  const metricDef = initialViewModel.metrics.find(m => m.key === sortKey)

  useEffect(() => {
    if (!metricDef) {
      setRowsFromJson([])
      setLoading(false)
      setLoadError(null)
      return
    }
    let cancelled = false
    setLoading(true)
    setLoadError(null)
    // loadRankingJson(year, season, metric, useAllPlayers): viewModel.season=年度, viewModel.league=seasonキー(CL/PL/PRE_spring等)として流用
    loadRankingJson(
        initialViewModel.season,
        initialViewModel.league,
        metricDef.label,
        !shouldRequireQualifyingPA(metricDef.key)
      )
      .then((data: unknown) => {
        if (cancelled) return
        const rawRows = Array.isArray(data) ? data : (data as { rows?: unknown[] })?.rows ?? []
        const rows: RankingRow[] = (rawRows as Record<string, unknown>[]).map(normalizeRankingRow)
        return mergeRomanNamesFromCsv(rows, initialViewModel.season, initialViewModel.league)
      })
      .then((rows) => {
        if (cancelled || rows == null) return
        setRowsFromJson(rows)
        setLoadError(null)
      })
      .catch((e: Error) => {
        if (cancelled) return
        setLoadError(e.message || 'データの読み込みに失敗しました')
        setRowsFromJson([])
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [initialViewModel.season, initialViewModel.league, sortKey, metricDef?.label])

  // デバッグ用（開発時のみ）
  if (typeof window !== 'undefined') {
    console.log('[RankingPageClient] Sort state:', { 
      sortKey, 
      order,
      availableMetrics: initialViewModel.metrics.map(m => ({ key: m.key, label: m.label })),
      urlParams: { sort: searchParams.get('sort'), order: searchParams.get('order') }
    })
  }

  // ソート処理（案A: rowsFromJson をソースにする）
  const sortedRows = useMemo(() => {
    const rows = rowsFromJson
    const metric = initialViewModel.metrics.find(m => m.key === sortKey)
    
    if (!metric) {
      return rows
    }

    // 規定打席フィルタを適用（指標ごとに判定）
    const requiresQualifyingPA = shouldRequireQualifyingPA(metric.key)
    
    const season = initialViewModel.season
    const league = initialViewModel.league.toUpperCase()
    const yearNum = parseInt(season, 10)
    
    // 1950-1958年（1952年除く）と1951年・1952年パ・リーグの特別ルール: 規定打数（AB）を使用
    // 1957年パ・リーグは規定打席（PA）: チーム試合数×3.1（全6チーム132試合）のため除外
    // 1958年パ・リーグは規定打席（PA）: 400打席のため除外
    const usesAB = ((yearNum >= 1950 && yearNum <= 1958 && yearNum !== 1952) || 
                   (season === '1951' && league === 'PL') ||
                   (season === '1952' && league === 'PL')) &&
                   !(season === '1957' && league === 'PL') &&
                   !(season === '1958' && league === 'PL')
    const is1951PL = season === '1951' && league === 'PL'
    const is1952PL = season === '1952' && league === 'PL'
    const is1966PL = season === '1966' && league === 'PL'
    const is1967PL = season === '1967' && league === 'PL'
    const is1950CL = season === '1950' && league === 'CL'
    
    const minPA = requiresQualifyingPA ? calculateMinPA(season, league) : 0
    const minGames1950CL = is1950CL ? get1950MinGames(season, league) : null

    // デバッグログ（開発時のみ）
    if (typeof window !== 'undefined' && process.env.NODE_ENV === 'development') {
      console.log('[RankingPageClient] Qualifying PA filter:', {
        season,
        league,
        metric: metric.key,
        requiresQualifyingPA,
        minPA,
        usesAB,
        is1951PL,
        is1952PL,
        is1950CL,
        minGames1950CL,
        totalRows: rows.length,
      })
    }

    // 規定打席フィルタを適用（Phase 4: 規定用CSV由来JSONでは全行が規定以上のため実質 no-op。従来JSONではフィルタが効き後方互換を確保）
    let filteredRows = rows
    if (requiresQualifyingPA && minPA > 0) {
      filteredRows = rows.filter(row => {
        // 1966年・1967年パ・リーグの場合はチーム別規定打席（PA）を使用
        if (is1966PL || is1967PL) {
          const team = row['team'] || row['チーム'] || ''
          const minPAForTeam = calculateMinPA(season, league, team)
          const pa = row['PA'] || row['pa'] || row['打席']
          const paValue = typeof pa === 'number' ? pa : Number(pa)
          const passes = !isNaN(paValue) && paValue >= minPAForTeam
          
          // デバッグログ（開発時のみ）
          if (typeof window !== 'undefined' && process.env.NODE_ENV === 'development') {
            const playerName = row['player'] || row['name'] || row['選手名'] || ''
            if (playerName.includes('若松') || playerName.includes('勉')) {
              console.log(`[RankingPageClient] ${season} PL PA filter check:`, {
                playerName,
                team,
                pa,
                paValue,
                minPAForTeam,
                passes,
                rowKeys: Object.keys(row),
              })
            }
          }
          
          return passes
        }
        
        // 1950-1958年（1952年除く）と1951年・1952年パ・リーグの場合は打数（AB）でフィルタリング
        if (usesAB) {
          let minAB = minPA
          
          // 1951年・1952年パ・リーグの場合はチーム別規定打数を使用
          if (is1951PL || is1952PL) {
            const team = row['team'] || row['チーム'] || ''
            minAB = calculateMinPA(season, league, team)
          }
          
          const ab = row['AB'] || row['ab'] || row['打数']
          const abValue = typeof ab === 'number' ? ab : Number(ab)
          let passes = !isNaN(abValue) && abValue >= minAB
          
          // 1950年セ・リーグの追加条件: 試合数 >= 100（1950年パ・リーグはAB >= 300のみ）
          if (is1950CL && minGames1950CL !== null) {
            const games = row['games'] || row['G'] || row['試合']
            const gamesValue = typeof games === 'number' ? games : Number(games)
            passes = passes && !isNaN(gamesValue) && gamesValue >= minGames1950CL
          }
          
          // デバッグログ（開発時のみ）
          if (typeof window !== 'undefined' && process.env.NODE_ENV === 'development') {
            const playerName = row['player'] || row['name'] || row['選手名'] || ''
            if (playerName.includes('若松') || playerName.includes('勉') || 
                ((is1951PL || is1952PL) && (row['team']?.includes('ロッテ') || row['team']?.includes('ソフトバンク')))) {
              console.log('[RankingPageClient] AB filter check:', {
                playerName,
                team: row['team'],
                ab,
                abValue,
                minAB,
                games: is1950CL ? (row['games'] || row['G'] || row['試合']) : undefined,
                minGames: minGames1950CL,
                passes,
                rowKeys: Object.keys(row),
              })
            }
          }
          
          return passes
        } else {
          // 通常の場合は打席（PA）でフィルタリング
          const pa = row['PA'] || row['pa'] || row['打席']
          const paValue = typeof pa === 'number' ? pa : Number(pa)
          const passes = !isNaN(paValue) && paValue >= minPA
          
          // デバッグログ（開発時のみ）- 若松勉のデータを確認
          if (typeof window !== 'undefined' && process.env.NODE_ENV === 'development') {
            const playerName = row['player'] || row['name'] || row['選手名'] || ''
            if (playerName.includes('若松') || playerName.includes('勉')) {
              console.log('[RankingPageClient] PA filter check:', {
                playerName,
                pa,
                paValue,
                minPA,
                passes,
                rowKeys: Object.keys(row),
              })
            }
          }
          
          return passes
        }
      })
      
      // デバッグログ（開発時のみ）
      if (typeof window !== 'undefined' && process.env.NODE_ENV === 'development') {
        console.log('[RankingPageClient] After filtering:', {
          filteredRows: filteredRows.length,
          removedRows: rows.length - filteredRows.length,
        })
      }
    }

    // in-place を禁止: コピーしてソート
    const sorted = [...filteredRows].sort((a, b) => {
      const aValue = a[metric.key]
      const bValue = b[metric.key]

      // null/undefined は最後に
      if (aValue === null || aValue === undefined) return 1
      if (bValue === null || bValue === undefined) return -1

      // NaN は最後に
      if (isNaN(Number(aValue))) return 1
      if (isNaN(Number(bValue))) return -1

      // ソート
      if (order === 'asc') {
        return Number(aValue) - Number(bValue)
      } else {
        return Number(bValue) - Number(aValue)
      }
    })

    // ランクを再計算
    return sorted.map((row, index) => ({
      ...row,
      rank: index + 1,
    }))
  }, [rowsFromJson, initialViewModel.metrics, initialViewModel.season, initialViewModel.league, sortKey, order])

  // ソート切替ハンドラ
  const handleSortChange = (metricKey: string) => {
    const currentSort = searchParams.get('sort') || sortKey
    const currentOrder = (searchParams.get('order') as 'asc' | 'desc') || order

    let newOrder: 'asc' | 'desc'
    if (currentSort === metricKey) {
      // 同じ指標を押したら order をトグル
      newOrder = currentOrder === 'asc' ? 'desc' : 'asc'
    } else {
      // 違う指標ならデフォルトソート順に戻す
      newOrder = getDefaultSortOrder(metricKey)
    }

    router.replace(`/ranking/${initialViewModel.season}/${initialViewModel.league}?sort=${encodeURIComponent(metricKey)}&order=${newOrder}`)
  }

  if (loadError) {
    return (
      <div className="min-h-screen bg-black text-white flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold mb-4">エラー</h1>
          <p className="text-gray-400">{loadError}</p>
        </div>
      </div>
    )
  }

  return (
    <RankingUI
      viewModel={{ ...initialViewModel, rows: rowsFromJson }}
      sortedRows={sortedRows}
      sortKey={sortKey}
      order={order}
      onSortChange={handleSortChange}
    />
  )
}

export default function RankingPageClient({ initialViewModel }: RankingPageClientProps) {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-black text-white flex items-center justify-center">
        <div className="text-center">
          <div className="text-lg">読み込み中...</div>
        </div>
      </div>
    }>
      <RankingPageClientInner initialViewModel={initialViewModel} />
    </Suspense>
  )
}
