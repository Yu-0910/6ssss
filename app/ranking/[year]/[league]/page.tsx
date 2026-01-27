// キャッシュを無効化して強制的に動的レンダリング
export const dynamic = 'force-dynamic'
export const revalidate = 0

/**
 * 動的ルート: /ranking/[year]/[league]
 * Record.csvの全指標を順番通りに表示（CSVに存在する指標のみ）
 */

import { Suspense } from 'react'
import { notFound } from 'next/navigation'
import RankingPageClient from './RankingPageClient'
import { loadBattingCsv } from '@/lib/ranking/loaders'
import { buildRankingWithAllMetrics } from '@/lib/ranking/adapter'
import type { RankingViewModel } from '@/lib/ranking/types'

interface RankingPageProps {
  params: Promise<{
    year: string
    league: string
  }>
  searchParams: Promise<{
    metric?: string
  }>
}

export default async function RankingPage({ params, searchParams }: RankingPageProps) {
  const paramsResolved = await params
  const { year, league } = paramsResolved
  const { metric } = await searchParams
  
  // ルーティング到達ログ（devのみ、最小化）
  if (process.env.NODE_ENV === 'development') {
    console.log("[ROUTE_HIT] /ranking/[year]/[league]", { year, league, metric }, "CWD=", process.cwd())
  }

  // 年度とリーグのバリデーション
  if (!year || !league) {
    notFound()
  }

  // リーグのバリデーション（CLまたはPLのみ）
  const upperLeague = league.toUpperCase()
  if (upperLeague !== 'CL' && upperLeague !== 'PL') {
    notFound()
  }

  try {
    // CSVを読み込み、利用可能な指標を取得（Record.csv順）
    const { rows, availableMetrics, csvPath } = loadBattingCsv(year, upperLeague)

    if (availableMetrics.length === 0) {
      return (
        <div className="min-h-screen bg-black text-white flex items-center justify-center">
          <div className="text-center">
            <h1 className="text-2xl font-bold mb-4">エラー</h1>
            <p className="text-gray-400">利用可能な指標が見つかりませんでした。</p>
          </div>
        </div>
      )
    }

    // 重複player_idの統計を計算（開発時のみ）
    let duplicatePlayerIdCount = 0
    let duplicateRowCount = 0
    if (process.env.NODE_ENV === 'development') {
      const playerIdCounts = new Map<string, number>()
      for (const row of rows) {
        const playerId = (row['player_id'] || row['playerId'] || '').toString().trim()
        if (playerId && playerId !== '0') {
          playerIdCounts.set(playerId, (playerIdCounts.get(playerId) || 0) + 1)
        }
      }
      for (const count of playerIdCounts.values()) {
        if (count > 1) {
          duplicatePlayerIdCount++
          duplicateRowCount += count - 1 // 重複行数（1つを残すので count - 1）
        }
      }
    }

    // 全指標の値を含むランキングデータを生成（ソートはClient側で行う）
    const rankingRows = buildRankingWithAllMetrics(rows, availableMetrics)

    // リーグ名の表示用
    const leagueName = upperLeague === 'CL' ? 'セ・リーグ' : 'パ・リーグ'

    // ViewModelを構築
    const viewModel: RankingViewModel = {
      title: `${leagueName}　打撃成績ランキング (${year}年)`,
      season: year,
      league: upperLeague,
      metrics: availableMetrics,
      activeMetric: 'ops', // デフォルト（Client側で上書きされる）
      rows: rankingRows,
      debug: process.env.NODE_ENV === 'development' ? {
        csvPath,
        duplicatePlayerIdCount,
        duplicateRowCount,
      } : undefined,
    }

    return (
      <Suspense fallback={
        <div className="min-h-screen bg-black text-white flex items-center justify-center">
          <div className="text-center">
            <div className="text-lg">読み込み中...</div>
          </div>
        </div>
      }>
        <RankingPageClient initialViewModel={viewModel} />
      </Suspense>
    )
  } catch (error) {
    // 開発環境では例外を再スローして詳細を確認
    if (process.env.NODE_ENV === 'development') {
      console.error('[loadRankingJson] error:', error)
      throw error
    }
    
    return (
      <div className="min-h-screen bg-black text-white flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold mb-4">エラー</h1>
          <p className="text-gray-400 mb-2">
            {error instanceof Error ? error.message : 'データの読み込みに失敗しました'}
          </p>
        </div>
      </div>
    )
  }
}












