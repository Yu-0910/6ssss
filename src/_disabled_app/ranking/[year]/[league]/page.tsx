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
    const { rows, availableMetrics } = loadBattingCsv(year, upperLeague)

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
      console.error('[loadBattingCsv] error:', error)
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

