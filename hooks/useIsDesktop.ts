"use client"

import { useEffect, useState } from "react"
import { useSearchParams } from "next/navigation"

/** Tailwind の `md` と同じ 768px */
const DESKTOP_MEDIA = "(min-width: 768px)"

/** URL に `?mobile=1` または `?view=mobile` があると PC 幅でもスマホ版 UI を表示（確認用） */
function useForceMobileFromSearch(): boolean {
  const searchParams = useSearchParams()
  return searchParams.get("mobile") === "1" || searchParams.get("view") === "mobile"
}

export function useIsDesktop(): boolean | undefined {
  const forceMobile = useForceMobileFromSearch()
  const [isDesktop, setIsDesktop] = useState<boolean | undefined>(undefined)

  useEffect(() => {
    if (forceMobile) {
      setIsDesktop(false)
      return
    }
    const mq = window.matchMedia(DESKTOP_MEDIA)
    const update = () => setIsDesktop(mq.matches)
    update()
    mq.addEventListener("change", update)
    return () => mq.removeEventListener("change", update)
  }, [forceMobile])

  return isDesktop
}
