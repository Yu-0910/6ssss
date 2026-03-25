/**
 * Pure UI Component - ランキング表示専用
 * 
 * 【重要】このコンポーネントは表示専用です
 * - データの取得・変換・フィルタリングは一切行いません
 * - props を受け取って描画するだけのPure UIです
 * - 指標の数が1でも20でも同じ構造で描画します（崩れないことが最優先）
 */

"use client"

import { Fragment } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import type { RankingViewModel, RankingRow } from '@/lib/ranking/types'
import { formatStat } from '@/lib/formatStat'

// チームカラーの定義
const teamColors: { [key: string]: string } = {
  // セ・リーグ
  阪神: "#ffde00",
  "阪神タイガース": "#ffde00",
  巨人: "#ff6600",
  "読売ジャイアンツ": "#ff6600",
  DeNA: "#0067c0",
  "横浜DeNAベイスターズ": "#0067c0",
  広島: "#d60718",
  "広島東洋カープ": "#d60718",
  中日: "#004ea2",
  "中日ドラゴンズ": "#004ea2",
  ヤクルト: "#2bbb3f",
  "東京ヤクルトスワローズ": "#2bbb3f",
  // パ・リーグ
  オリックス: "#b79e51",
  "オリックス・バファローズ": "#b79e51",
  ロッテ: "#222",
  "千葉ロッテマリーンズ": "#222",
  日本ハム: "#0077c8",
  "北海道日本ハムファイターズ": "#0077c8",
  楽天: "#7a0019",
  "東北楽天ゴールデンイーグルス": "#7a0019",
  西武: "#004098",
  "埼玉西武ライオンズ": "#004098",
  ソフトバンク: "#ffdb00",
  "福岡ソフトバンクホークス": "#ffdb00",
}

interface RankingUIProps {
  viewModel: RankingViewModel
  sortedRows: RankingRow[]
  sortKey: string
  order: 'asc' | 'desc'
  onSortChange: (metricKey: string) => void
}

/**
 * ローマ字名をイニシャル.名前形式に変換
 * 日本人選手: "Kiyomiya Kotaro" → "K.Kiyomiya" (名前のイニシャル.苗字)
 * 外国人選手: "Sandro Fabian" → "S.Fabian" (苗字のイニシャル.名前)
 * 単一の名前: "Fabian" → "F.Fabian" (最初の文字.名前全体)
 * 
 * 注意: 既に「イニシャル.名前」形式（例: "M.Kozuru", "S.Fabian"）の場合は、そのまま返す
 */
function formatRomanName(romanName: string): string {
  const trimmed = romanName.trim()
  if (!trimmed) return ''
  
  // 既に「イニシャル.名前」形式かどうかをチェック
  // パターン: 1文字の大文字 + "." + 名前（例: "M.Kozuru", "S.Fabian"）
  const alreadyFormattedPattern = /^[A-Z]\.([A-Z][a-z]+|[A-Z]+)$/
  if (alreadyFormattedPattern.test(trimmed)) {
    // 既にフォーマット済みの場合はそのまま返す
    return trimmed
  }
  
  // スペースで分割
  const parts = trimmed.split(/\s+/)
  
  if (parts.length === 0) return ''
  
  if (parts.length === 1) {
    // 名前のみの場合（外国人選手など）
    // 例: "Fabian" → "F.Fabian"
    const name = parts[0]
    if (name.length > 0) {
      return `${name[0].toUpperCase()}.${name}`
    }
    return ''
  }
  
  // 2つ以上の部分がある場合
  // 外国人選手の場合: "Sandro Fabian" → "S.Fabian" (苗字のイニシャル.名前)
  // 日本人選手の場合: "Kiyomiya Kotaro" → "K.Kiyomiya" (名前のイニシャル.苗字)
  // 
  // 判定方法: 最後の部分が名前、それ以前が苗字（複数の場合もある）
  const firstName = parts[parts.length - 1]  // 最後の部分が名前
  const lastName = parts.slice(0, -1).join(' ')  // それ以前が苗字
  
  // 苗字の最初の文字をイニシャルとして取得
  const initial = lastName.length > 0 ? lastName[0].toUpperCase() : ''
  
  // イニシャル.名前形式に変換（外国人選手形式）
  return `${initial}.${firstName}`
}

// 左ブロック（順＋フレーム＋選手）を1層にまとめ、隙間を防ぐ（問題29・二層構造の理想に合わせる）
const RANK_WIDTH = 30
const PLAYER_WIDTH = 90
const FRAME_WIDTH = 2 // 順列と選手列の間のグレーフレーム
const LEFT_BLOCK_WIDTH = RANK_WIDTH + FRAME_WIDTH + PLAYER_WIDTH // 122

export default function RankingUI({ viewModel, sortedRows, sortKey, order, onSortChange }: RankingUIProps) {
  const { title, season, league, metrics } = viewModel
  const router = useRouter()

  // 表示中の指標名を取得（2024年以前と同様に metrics をそのまま使用）
  const activeMetric = metrics.find(m => m.key === sortKey)
  const metricLabel = activeMetric?.label || '打撃成績'
  
  // タイトルを動的に生成（例：「パ・リーグ　OPSランキング (2025年)」）
  const leagueName = league === 'CL' ? 'セ・リーグ' : 'パ・リーグ'
  const displayTitle = `${leagueName}　${metricLabel}ランキング (${season}年)`

  // 年度変更ハンドラ
  const handleYearChange = (newYear: number) => {
    // 同じリーグ、同じ指標で新しい年度のランキングページに遷移
    router.push(`/ranking/${newYear}/${league}?sort=${encodeURIComponent(sortKey)}&order=${order}`)
  }

  return (
    <div className="min-h-screen bg-black text-white">
      <div className="sticky top-0 z-50 bg-black/95 backdrop-blur-sm border-b border-[#333]" style={{ zIndex: 300 }}>
        {/* Header */}
        <div className="container mx-auto px-4 py-1 border-b border-[#333] flex items-center justify-between">
          {/* Left: Back Button */}
          <button
            onClick={() => window.history.back()}
            className="flex items-center gap-1 p-1 hover:opacity-80 transition-opacity text-[#ffff44]"
            aria-label="戻る"
          >
            <span className="text-sm">←</span>
          </button>

          {/* Center: Logo */}
          <Link href="/" className="absolute left-1/2 transform -translate-x-1/2">
            <img src="/logo.png" alt="Logo" className="w-7 h-7 cursor-pointer hover:opacity-80 transition-opacity" />
          </Link>

          {/* Right: Year Selector */}
          <select
            value={season}
            onChange={(e) => handleYearChange(Number(e.target.value))}
            className="bg-[#1a1a1a] text-[#ffff44] border border-[#555] rounded px-2 py-0.5 text-sm bebas cursor-pointer hover:bg-[#2a2a2a] transition-colors"
          >
            {Array.from({ length: 77 }, (_, i) => 2026 - i).map((year) => (
              <option key={year} value={year}>
                {year}
              </option>
            ))}
          </select>
        </div>
      </div>

      <main className="max-w-[1400px] mx-auto px-2 py-3">
        {/* Title */}
        <div className="flex items-center gap-1.5 mb-1">
          <div className="w-0.5 h-5 bg-[#039850]" />
          <h1 className="text-base font-bold text-white">
            {displayTitle}
          </h1>
        </div>

        {/* ランキングテーブル */}
        <div className="bg-[#1a1a1a] overflow-hidden border border-[#333]">
          <div className="overflow-x-auto pl-0 ml-0">
            <table className="w-full border-collapse border-spacing-0" style={{ tableLayout: 'fixed' }}>
              <colgroup>
                <col style={{ width: `${LEFT_BLOCK_WIDTH}px`, minWidth: `${LEFT_BLOCK_WIDTH}px` }} />
                {metrics.map((metric) => (
                  <col key={metric.key} style={{ minWidth: '60px' }} />
                ))}
              </colgroup>
              <thead>
                {/* 層1: 順＋グレーフレーム＋選手名を1セルで一塊に（隙間防止） */}
                <tr className="bg-[#2a2a2a]">
                  <th
                    className="sticky border-r-2 border-[#555]"
                    style={{
                      position: 'sticky',
                      top: 0,
                      left: 0,
                      zIndex: 100,
                      width: `${LEFT_BLOCK_WIDTH}px`,
                      maxWidth: `${LEFT_BLOCK_WIDTH}px`,
                      boxSizing: 'border-box',
                      padding: 0,
                      verticalAlign: 'middle',
                    }}
                  >
                    <div className="flex flex-nowrap items-stretch w-full" style={{ width: LEFT_BLOCK_WIDTH }}>
                      <div className="px-2 py-3 text-[10px] font-bold bg-[#ffff44] text-black flex-shrink-0" style={{ width: RANK_WIDTH, boxSizing: 'border-box' }}>順</div>
                      <div className="flex-shrink-0 bg-[#555]" style={{ width: FRAME_WIDTH }} aria-hidden />
                      <div className="px-2 py-3 text-[10px] font-bold bg-[#ffff44] text-black flex-shrink-0" style={{ width: PLAYER_WIDTH, boxSizing: 'border-box' }}>選手名</div>
                    </div>
                  </th>
                  {metrics.map((metric, metricIdx) => {
                    const isActive = sortKey === metric.key
                    return (
                      <th
                        key={metric.key}
                        data-active={isActive}
                        className={`px-2 py-3 text-[10px] font-bold border-r border-[#333] bg-[#ffff44] text-black ${metricIdx === 0 ? 'pl-0 ml-0 -ml-[2px]' : ''}`}
                        style={{
                          minWidth: '60px',
                          backgroundColor: '#ffff44',
                          color: '#000000',
                          paddingLeft: metricIdx === 0 ? 0 : undefined,
                          marginLeft: metricIdx === 0 ? '-2px' : undefined,
                        }}
                      >
                        <button
                          type="button"
                          onClick={() => {
                            if (sortKey === metric.key) return
                            onSortChange(metric.key)
                          }}
                          className="w-full cursor-pointer hover:underline relative z-10 pointer-events-auto flex items-center justify-center gap-1"
                          style={{
                            textAlign: 'center',
                            width: '100%',
                            color: '#000000',
                            backgroundColor: 'transparent',
                            border: 'none',
                            padding: 0,
                            margin: 0,
                          }}
                        >
                          <span className="underline">{metric.label}</span>
                        </button>
                      </th>
                    )
                  })}
                </tr>
              </thead>
              <tbody>
                {sortedRows.map((row, idx) => {
                  const hasRomanName = row.romanName && row.romanName.trim()
                  const shouldShowHeader = idx > 0 && idx % 15 === 0
                  
                  return (
                    <Fragment key={`row-${row.playerId}-${idx}`}>
                      {/* 15行ごとにヘッダー行を表示 */}
                      {shouldShowHeader && (
                        <tr key={`header-${idx}`} className="bg-[#4a4a4a] text-white">
                          {/* 層1: 順＋グレーフレーム＋選手名を1セルで一塊に */}
                          <th
                            className="sticky border-r-2 border-[#555]"
                            style={{
                              position: 'sticky',
                              left: 0,
                              zIndex: 100,
                              width: `${LEFT_BLOCK_WIDTH}px`,
                              maxWidth: `${LEFT_BLOCK_WIDTH}px`,
                              boxSizing: 'border-box',
                              padding: 0,
                              verticalAlign: 'middle',
                            }}
                          >
                            <div className="flex flex-nowrap items-stretch w-full" style={{ width: LEFT_BLOCK_WIDTH }}>
                              <div className="px-2 py-3 text-[10px] font-bold bg-[#4a4a4a] text-white flex-shrink-0" style={{ width: RANK_WIDTH, boxSizing: 'border-box' }}>順</div>
                              <div className="flex-shrink-0 bg-[#555]" style={{ width: FRAME_WIDTH }} aria-hidden />
                              <div className="px-2 py-3 text-[10px] font-bold bg-[#4a4a4a] text-white flex-shrink-0" style={{ width: PLAYER_WIDTH, boxSizing: 'border-box' }}>選手名</div>
                            </div>
                          </th>
                          {metrics.map((metric, metricIdx) => {
                            const isActive = sortKey === metric.key
                            return (
                              <th
                                key={metric.key}
                                data-active={isActive}
                                className={`px-2 py-3 text-[10px] font-bold border-r border-[#333] bg-[#4a4a4a] text-white ${metricIdx === 0 ? 'pl-0 ml-0 -ml-[2px]' : ''}`}
                                style={{
                                  minWidth: '60px',
                                  backgroundColor: '#4a4a4a',
                                  color: '#ffffff',
                                  paddingLeft: metricIdx === 0 ? 0 : undefined,
                                  marginLeft: metricIdx === 0 ? '-2px' : undefined,
                                }}
                              >
                                <button
                                  type="button"
                                  onClick={() => {
                                    if (sortKey === metric.key) return
                                    onSortChange(metric.key)
                                  }}
                                  className="w-full cursor-pointer hover:underline relative z-10 pointer-events-auto flex items-center justify-center gap-1"
                                  style={{
                                    textAlign: 'center',
                                    width: '100%',
                                    color: '#ffffff',
                                    backgroundColor: 'transparent',
                                    border: 'none',
                                    padding: 0,
                                    margin: 0,
                                  }}
                                >
                                  <span className="underline">{metric.label}</span>
                                </button>
                              </th>
                            )
                          })}
                        </tr>
                      )}
                      <tr
                        key={`${row.playerId}-${idx}`}
                        className="bg-[#1f1f1f] hover:bg-[#2a2a2a] transition-colors border-b border-[#333]"
                      >
                      {/* 層1: 順位＋グレーフレーム＋選手名を1セルで一塊に */}
                      <td
                        className="sticky border-r-2 border-[#555]"
                        style={{
                          position: 'sticky',
                          left: 0,
                          zIndex: 40,
                          width: `${LEFT_BLOCK_WIDTH}px`,
                          maxWidth: `${LEFT_BLOCK_WIDTH}px`,
                          boxSizing: 'border-box',
                          padding: 0,
                          verticalAlign: 'middle',
                        }}
                      >
                        <div className="flex flex-nowrap items-stretch w-full" style={{ width: LEFT_BLOCK_WIDTH }}>
                          <div
                            className="text-center tabular-nums font-normal text-white flex-shrink-0 flex items-center justify-center"
                            style={{ width: RANK_WIDTH, minHeight: 32, backgroundColor: '#1f1f1f', padding: '2px 4px', boxSizing: 'border-box' }}
                          >
                            <span className="bebas tabular-nums text-lg tracking-wide">{row.rank}</span>
                          </div>
                          <div className="flex-shrink-0 bg-[#555]" style={{ width: FRAME_WIDTH }} aria-hidden />
                          <div
                            className="overflow-hidden flex-shrink-0 flex items-center"
                            style={{ width: PLAYER_WIDTH, minHeight: 32, backgroundColor: '#1f1f1f', padding: '2px 2px', boxSizing: 'border-box' }}
                          >
                            <div className="flex items-center gap-0.5 w-full min-w-0">
                              <div className="w-1 h-8 flex-shrink-0" style={{ backgroundColor: teamColors[row.team] || '#fff' }} />
                              <div className="flex-1 min-w-0 flex flex-col justify-center leading-[1.05] h-8">
                                <Link
                                  href={`/players/${row.playerId}?name=${encodeURIComponent(row.name.replace(/\s+/g, ''))}${hasRomanName && row.romanName ? `&roman=${encodeURIComponent(formatRomanName(row.romanName))}` : ''}`}
                                  className="block truncate"
                                >
                                  <span className="text-white hover:text-[#ffff44] text-[13px] font-semibold truncate">
                                    {row.name.replace(/\s+/g, '')}
                                  </span>
                                </Link>
                                {hasRomanName && row.romanName && (
                                  <span className="text-[10px] text-gray-400 latin truncate line-clamp-1">
                                    {formatRomanName(row.romanName)}
                                  </span>
                                )}
                              </div>
                            </div>
                          </div>
                        </div>
                      </td>
                      {/* 層2: 指標の値のみ */}
                      {metrics.map((metric, metricIdx) => {
                        const value = row[metric.key]
                        const formattedValue = value !== null && value !== undefined && !isNaN(Number(value))
                          ? formatStat(metric.label, value)
                          : '-'
                        const isActive = sortKey === metric.key
                        // アクティブな指標の場合、奇数/偶数行で背景色を変える
                        const activeBgColor = isActive ? '#3a3a3a' : 'transparent'
                        
                        return (
                          <td
                            key={metric.key}
                            className={`px-1.5 py-0.5 text-center tabular-nums font-normal border-r border-[#444] text-white ${
                              isActive ? 'bg-[#3a3a3a]' : ''
                            } ${metricIdx === 0 ? 'pl-0 ml-0 -ml-[2px]' : ''}`}
                            style={{
                              minWidth: '60px',
                              backgroundColor: activeBgColor,
                              paddingLeft: metricIdx === 0 ? 0 : undefined,
                              marginLeft: metricIdx === 0 ? '-2px' : undefined,
                            }}
                          >
                            <span className="bebas tabular-nums text-lg tracking-wide">{formattedValue}</span>
                          </td>
                        )
                      })}
                      </tr>
                    </Fragment>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      </main>
      
      {/* 開発時のみデバッグ情報を表示 */}
      {process.env.NODE_ENV === 'development' && viewModel.debug && (
        <div className="container mx-auto px-4 py-2 border-t border-[#333] text-xs text-gray-500">
          <div>DataSource: {viewModel.debug.csvPath || 'N/A'}</div>
          <div>Duplicates: {viewModel.debug.duplicatePlayerIdCount} ids / {viewModel.debug.duplicateRowCount} rows</div>
        </div>
      )}
    </div>
  )
}

