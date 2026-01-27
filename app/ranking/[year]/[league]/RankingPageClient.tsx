/**
 * Client Component for Ranking Page
 * ソート処理とクエリパラメータ管理を行う
 */

"use client"

import { useRouter, useSearchParams } from 'next/navigation'
import { useMemo, Suspense } from 'react'
import RankingUI from '@/components/RankingUI'
import type { RankingViewModel, RankingRow, MetricDefinition } from '@/lib/ranking/types'
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

function RankingPageClientInner({ initialViewModel }: RankingPageClientProps) {
  const router = useRouter()
  const searchParams = useSearchParams()

  // URLクエリパラメータからソート情報を取得
  const sortKey = searchParams.get('sort') || 'ops'
  const order = (searchParams.get('order') as 'asc' | 'desc') || getDefaultSortOrder(sortKey)

  // デバッグ用（開発時のみ）
  if (typeof window !== 'undefined') {
    console.log('[RankingPageClient] Sort state:', { 
      sortKey, 
      order,
      availableMetrics: initialViewModel.metrics.map(m => ({ key: m.key, label: m.label })),
      urlParams: { sort: searchParams.get('sort'), order: searchParams.get('order') }
    })
  }

  // ソート処理
  const sortedRows = useMemo(() => {
    const rows = initialViewModel.rows
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

    // 規定打席フィルタを適用
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
  }, [initialViewModel.rows, initialViewModel.metrics, initialViewModel.season, initialViewModel.league, sortKey, order])

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

  return (
    <RankingUI
      viewModel={initialViewModel}
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
