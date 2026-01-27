"use client"

import { useEffect, useState } from "react"
import type { ComponentType } from "react"

export default function AnalyticsWrapper() {
  const [Analytics, setAnalytics] = useState<ComponentType | null>(null)

  useEffect(() => {
    // 開発環境では無効化（vendor-chunk問題を回避）
    if (process.env.NODE_ENV !== 'production') {
      return
    }

    // 動的インポートで@vercel/analyticsを読み込む
    import("@vercel/analytics/next")
      .then((mod) => {
        setAnalytics(() => mod.Analytics)
      })
      .catch((err) => {
        console.warn('@vercel/analytics could not be loaded:', err)
      })
  }, [])

  if (!Analytics) {
    return null
  }

  return <Analytics />
}
