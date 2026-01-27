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

  // 動的ルートに委譲（2025/PL固定の制約を削除）
  // このファイルは削除するか、動的ルートにリダイレクトすることを推奨

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

    // デバッグ: 最初の数行のデータを確認
    if (process.env.NODE_ENV === 'development' && rankingRows.length > 0) {
      const sampleRow = rankingRows[0]
      console.log('[RankingPage] Sample row data:', {
        name: sampleRow.name,
        ops: sampleRow.ops,
        slg: sampleRow.slg,
        obp: sampleRow.obp,
        avg: sampleRow.avg,
        allKeys: Object.keys(sampleRow).filter(k => !['rank', 'playerId', 'name', 'romanName', 'team', 'valueText'].includes(k)).slice(0, 10)
      })
      
      // OPS, SLG, OBPが存在する行を確認
      const rowsWithOPS = rankingRows.filter(r => r.ops !== undefined && r.ops !== null)
      const rowsWithSLG = rankingRows.filter(r => r.slg !== undefined && r.slg !== null)
      const rowsWithOBP = rankingRows.filter(r => r.obp !== undefined && r.obp !== null)
      console.log('[RankingPage] Data availability:', {
        totalRows: rankingRows.length,
        rowsWithOPS: rowsWithOPS.length,
        rowsWithSLG: rowsWithSLG.length,
        rowsWithOBP: rowsWithOBP.length,
        firstRowWithOPS: rowsWithOPS[0] ? {
          name: rowsWithOPS[0].name,
          ops: rowsWithOPS[0].ops,
          slg: rowsWithOPS[0].slg,
          obp: rowsWithOPS[0].obp
        } : null
      })
    }

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

