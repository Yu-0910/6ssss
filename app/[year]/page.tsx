"use client"

import { useParams } from "next/navigation"
import { TopPageRoot } from "@/app/components/top/TopPageRoot"

export default function YearTopPage() {
  const params = useParams()
  const y = Number(params?.year) || 2024

  return <TopPageRoot initialYear={y} articlesMode="dummy" />
}
