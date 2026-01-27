/**
 * Client Component for Ranking Page
 * ソート処理とクエリパラメータ管理を行う
 */

"use client"

import { useRouter, useSearchParams } from 'next/navigation'
import { useMemo, Suspense } from 'react'
import RankingUI from '@/components/RankingUI'
import type { RankingViewModel, RankingRow, MetricDefinition } from '@/lib/ranking/types'

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

    // in-place を禁止: コピーしてソート
    const sorted = [...rows].sort((a, b) => {
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
  }, [initialViewModel.rows, initialViewModel.metrics, sortKey, order])

  // ソート切替ハンドラ
  const handleSortChange = (metricKey: string) => {
    const currentSort = searchParams.get('sort')
    const currentOrder = searchParams.get('order') as 'asc' | 'desc'

    let newOrder: 'asc' | 'desc'
    if (currentSort === metricKey) {
      // 同じ指標を押したら order をトグル
      newOrder = currentOrder === 'asc' ? 'desc' : 'asc'
    } else {
      // 違う指標ならデフォルトソート順に戻す
      newOrder = getDefaultSortOrder(metricKey)
    }

    router.replace(`/ranking/2025/PL?sort=${encodeURIComponent(metricKey)}&order=${newOrder}`)
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
