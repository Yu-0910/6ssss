/**
 * 2025年パ・リーグのランキングページ
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
  const { year, league } = await params
  const { metric } = await searchParams

  // 2025 PL固定でテスト
  if (year !== '2025' || league !== 'PL') {
    notFound()
  }

  try {
    // CSVを読み込み、利用可能な指標を取得（Record.csv順）
    const { rows, availableMetrics } = loadBattingCsv('2025', 'PL')

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

    // ViewModelを構築
    const viewModel: RankingViewModel = {
      title: `パ・リーグ　打撃成績ランキング (2025年)`,
      season: '2025',
      league: 'PL',
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
    console.error('Error loading ranking:', error)
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

