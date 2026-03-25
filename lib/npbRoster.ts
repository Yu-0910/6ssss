/**
 * NPB 2026年選手名簿ローダー
 * _data/npb_roster_2026.csv を読み込み、打席・投球の利き手を提供
 */

import fs from "fs"
import path from "path"

export interface NpbRosterPlayer {
  npb_player_id: string
  name_ja: string
  name_en: string
  team: string
  team_code: string
  position: string
  uniform_no: string
  /** 投: R=右投, L=左投 */
  throw_hand: string
  /** 打: R=右打, L=左打, B=両打 */
  bat_hand: string
  /** 2026年新規支配下登録か */
  is_new_2026: string
}

let cachedRoster: NpbRosterPlayer[] | null = null

function getRosterPath(): string {
  return path.join(process.cwd(), "_data", "npb_roster_2026.csv")
}

/**
 * CSVをパースしてロスター配列を返す
 */
function parseRosterCsv(content: string): NpbRosterPlayer[] {
  const lines = content.split(/\r?\n/).filter((l) => l.trim())
  if (lines.length < 2) return []
  const headers = lines[0].split(",").map((h) => h.trim().replace(/^\ufeff/, ""))
  const rows: NpbRosterPlayer[] = []
  for (let i = 1; i < lines.length; i++) {
    const values = parseCsvLine(lines[i])
    const row: Record<string, string> = {}
    headers.forEach((h, j) => {
      row[h] = values[j] ?? ""
    })
    rows.push({
      npb_player_id: row.npb_player_id ?? "",
      name_ja: row.name_ja ?? "",
      name_en: row.name_en ?? "",
      team: row.team ?? "",
      team_code: row.team_code ?? "",
      position: row.position ?? "",
      uniform_no: row.uniform_no ?? "",
      throw_hand: row.throw_hand ?? "",
      bat_hand: row.bat_hand ?? "",
      is_new_2026: row.is_new_2026 ?? "0",
    })
  }
  return rows
}

function parseCsvLine(line: string): string[] {
  const result: string[] = []
  let current = ""
  let inQuotes = false
  for (let i = 0; i < line.length; i++) {
    const c = line[i]
    if (c === '"') {
      inQuotes = !inQuotes
    } else if (inQuotes) {
      current += c
    } else if (c === ",") {
      result.push(current)
      current = ""
    } else {
      current += c
    }
  }
  result.push(current)
  return result
}

/**
 * 2026年NPB選手名簿を取得（キャッシュあり）
 */
export function getNpbRoster2026(): NpbRosterPlayer[] {
  if (cachedRoster) return cachedRoster
  const p = getRosterPath()
  try {
    const content = fs.readFileSync(p, "utf-8")
    cachedRoster = parseRosterCsv(content)
    return cachedRoster
  } catch {
    return []
  }
}

/**
 * 選手名（日本語）から利き手を取得
 */
export function getPlayerHandedness(nameJa: string): {
  throwHand: "R" | "L" | ""
  batHand: "R" | "L" | "B" | ""
} {
  const roster = getNpbRoster2026()
  const p = roster.find((r) => r.name_ja === nameJa || r.name_ja.replace(/\s/g, "") === nameJa.replace(/\s/g, ""))
  if (!p) return { throwHand: "", batHand: "" }
  const throwHand = (p.throw_hand === "R" || p.throw_hand === "L" ? p.throw_hand : "") as "R" | "L" | ""
  const batHand = (p.bat_hand === "R" || p.bat_hand === "L" || p.bat_hand === "B" ? p.bat_hand : "") as "R" | "L" | "B" | ""
  return { throwHand, batHand }
}

/**
 * NPB player_id から利き手を取得
 */
export function getPlayerHandednessById(npbPlayerId: string): {
  throwHand: "R" | "L" | ""
  batHand: "R" | "L" | "B" | ""
} {
  const roster = getNpbRoster2026()
  const p = roster.find((r) => r.npb_player_id === String(npbPlayerId))
  if (!p) return { throwHand: "", batHand: "" }
  const throwHand = (p.throw_hand === "R" || p.throw_hand === "L" ? p.throw_hand : "") as "R" | "L" | ""
  const batHand = (p.bat_hand === "R" || p.bat_hand === "L" || p.bat_hand === "B" ? p.bat_hand : "") as "R" | "L" | "B" | ""
  return { throwHand, batHand }
}

/**
 * 2026年新規登録選手一覧
 */
export function getNewPlayers2026(): NpbRosterPlayer[] {
  return getNpbRoster2026().filter((r) => r.is_new_2026 === "1")
}
