"use client"
import { useState } from "react"
import Link from "next/link"
import Image from "next/image"
import { useRouter } from "next/navigation"
import { formatStat } from "@/lib/formatStat"
import metricMap from "@/config/metric_map.json"
import TopPageLeadersClient from "@/app/components/TopPageLeadersClient"
import ArticlesListClient from "@/app/components/ArticlesListClient"

// チーム色の定義
const teamColors: Record<string, string> = {
  H: "#ffde00", // 阪神
  G: "#ff6600", // 巨人
  DB: "#0067c0", // DeNA
  C: "#d60718", // 広島
  D: "#004ea2", // 中日
  S: "#2bbb3f", // ヤクルト
  Bs: "#b79e51", // オリックス
  M: "#222", // ロッテ
  F: "#0077c8", // 日本ハム
  E: "#7a0019", // 楽天
  L: "#004098", // 西武
  Hs: "#ffdb00", // ソフトバンク
}

const teamRomanNames: Record<string, string> = {
  H: "Hanshin Tigers",
  G: "Yomiuri Giants",
  DB: "Yokohama DeNA BayStars",
  C: "Hiroshima Toyo Carp",
  D: "Chunichi Dragons",
  S: "Tokyo Yakult Swallows",
  Bs: "Orix Buffaloes",
  M: "Chiba Lotte Marines",
  F: "Hokkaido Nippon-Ham Fighters",
  E: "Tohoku Rakuten Golden Eagles",
  L: "Saitama Seibu Lions",
  Hs: "Fukuoka SoftBank Hawks",
}

// プレイヤーのローマ字名の定義
const playerRomanNames: Record<string, string> = {
  佐藤輝明: "Sato Teruaki",
  岡本和真: "Okamoto Kazuma",
  村上宗隆: "Murakami Munetaka",
  近本光司: "Chikamoto Koji",
  牧秀悟: "Maki Shugo",
  佐野恵太: "Sano Keita",
  青柳晃洋: "Aoyagi Koyo",
  菅野智之: "Sugano Tomoyuki",
  大野雄大: "Ono Yudai",
  岩崎優: "Iwasaki Yu",
  伊勢大夢: "Ise Hiromu",
  石田健大: "Ishida Kenta",
  戸郷翔征: "Togou Shosei",
  山川穂高: "Yamakawa Hotaka",
  吉田正尚: "Yoshida Masataka",
  中村晃: "Nakamura Akira",
  源田壮亮: "Genda Sosuke",
  柳田悠岐: "Yanagita Yuki",
  浅村栄斗: "Asamura Hideto",
  周東佑京: "Shuto Ukyo",
  山本由伸: "Yamamoto Yoshinobu",
  千賀滉大: "Senga Kodai",
  佐々木朗希: "Sasaki Roki",
  宮城大弥: "Miyagi Hiroya",
  森唯斗: "Mori Yuito",
  益田直也: "Masuda Naoya",
}

// 型定義
type LeaderRow = { rank: 1 | 2 | 3; name: string; team: string; teamName: string; value: string | number }
type LeadersConfig = {
  top3Metrics: string[]
  miniMetrics: string[]
  leaders: Record<string, LeaderRow[]>
}
type StandingRow = {
  pos: number
  name: string
  abbr: string
  w: number
  l: number
  pct: number
  runs: number
  ops: string
  avg: string
  hr: number
  obp: string
  slg: string
  isod: string
  isop: string
  bb_rate_hit: string
  k_rate_hit: string
  bb_k_diff_hit: string
  runs_allowed: number
  era: string
  cg: number
  bb_rate_pitch: string
  k_rate_pitch: string
  k_bb_diff_pitch: string
}

// Article型はArticlesListClientコンポーネントで定義されているため、ここでは削除

// ダミーデータ - 打者リーダー（セ・リーグ）
const battersCL: LeadersConfig = {
  top3Metrics: ["OPS", "AVG", "HR"],
  miniMetrics: ["出塁率", "長打率", "打点", "安打", "盗塁"],
  leaders: {
    OPS: [
      { rank: 1, name: "佐藤輝明", team: "H", teamName: "阪神", value: "1.052" },
      { rank: 2, name: "岡本和真", team: "G", teamName: "巨人", value: "1.015" },
      { rank: 3, name: "村上宗隆", team: "S", teamName: "ヤクルト", value: "0.998" },
    ],
    AVG: [
      { rank: 1, name: "近本光司", team: "H", teamName: "阪神", value: ".342" },
      { rank: 2, name: "牧秀悟", team: "DB", teamName: "DeNA", value: ".338" },
      { rank: 3, name: "佐野恵太", team: "DB", teamName: "DeNA", value: ".325" },
    ],
    HR: [
      { rank: 1, name: "村上宗隆", team: "S", teamName: "ヤクルト", value: 48 },
      { rank: 2, name: "岡本和真", team: "G", teamName: "巨人", value: 45 },
      { rank: 3, name: "佐藤輝明", team: "H", teamName: "阪神", value: 42 },
    ],
    出塁率: [{ rank: 1, name: "村上宗隆", team: "S", teamName: "ヤクルト", value: ".425" }],
    長打率: [{ rank: 1, name: "佐藤輝明", team: "H", teamName: "阪神", value: ".648" }],
    打点: [{ rank: 1, name: "岡本和真", team: "G", teamName: "巨人", value: 125 }],
    安打: [{ rank: 1, name: "近本光司", team: "H", teamName: "阪神", value: 198 }],
    盗塁: [{ rank: 1, name: "近本光司", team: "H", teamName: "阪神", value: 52 }],
  },
}

// ダミーデータ - 投手リーダー（セ・リーグ）
const pitchersCL: LeadersConfig = {
  top3Metrics: ["最多勝", "防御率", "セーブ"],
  miniMetrics: ["奪三振", "WHIP", "勝率", "完投", "投球回"],
  leaders: {
    最多勝: [
      { rank: 1, name: "青柳晃洋", team: "H", teamName: "阪神", value: 16 },
      { rank: 2, name: "菅野智之", team: "G", teamName: "巨人", value: 15 },
      { rank: 3, name: "大野雄大", team: "D", teamName: "中日", value: 14 },
    ],
    防御率: [
      { rank: 1, name: "青柳晃洋", team: "H", teamName: "阪神", value: "1.85" },
      { rank: 2, name: "大野雄大", team: "D", teamName: "中日", value: "2.05" },
      { rank: 3, name: "戸郷翔征", team: "G", teamName: "巨人", value: "2.18" },
    ],
    セーブ: [
      { rank: 1, name: "岩崎優", team: "H", teamName: "阪神", value: 42 },
      { rank: 2, name: "伊勢大夢", team: "DB", teamName: "DeNA", value: 38 },
      { rank: 3, name: "石田健大", team: "S", teamName: "ヤクルト", value: 35 },
    ],
    奪三振: [{ rank: 1, name: "戸郷翔征", team: "G", teamName: "巨人", value: 215 }],
    WHIP: [{ rank: 1, name: "青柳晃洋", team: "H", teamName: "阪神", value: "0.98" }],
    勝率: [{ rank: 1, name: "青柳晃洋", team: "H", teamName: "阪神", value: ".842" }],
    完投: [{ rank: 1, name: "大野雄大", team: "D", teamName: "中日", value: 5 }],
    投球回: [{ rank: 1, name: "青柳晃洋", team: "H", teamName: "阪神", value: "195.2" }],
  },
}

// ダミーデータ - 打者リーダー（パ・リーグ）
const battersPL: LeadersConfig = {
  top3Metrics: ["OPS", "AVG", "HR"],
  miniMetrics: ["出塁率", "長打率", "打点", "安打", "盗塁"],
  leaders: {
    OPS: [
      { rank: 1, name: "山川穂高", team: "L", teamName: "西武", value: "1.088" },
      { rank: 2, name: "吉田正尚", team: "Bs", teamName: "オリックス", value: "1.045" },
      { rank: 3, name: "中村晃", team: "Hs", teamName: "ソフトバンク", value: "1.012" },
    ],
    AVG: [
      { rank: 1, name: "吉田正尚", team: "Bs", teamName: "オリックス", value: ".355" },
      { rank: 2, name: "源田壮亮", team: "L", teamName: "西武", value: ".340" },
      { rank: 3, name: "柳田悠岐", team: "Hs", teamName: "ソフトバンク", value: ".332" },
    ],
    HR: [
      { rank: 1, name: "山川穂高", team: "L", teamName: "西武", value: 52 },
      { rank: 2, name: "中村晃", team: "Hs", teamName: "ソフトバンク", value: 46 },
      { rank: 3, name: "浅村栄斗", team: "E", teamName: "楽天", value: 43 },
    ],
    出塁率: [{ rank: 1, name: "吉田正尚", team: "Bs", teamName: "オリックス", value: ".445" }],
    長打率: [{ rank: 1, name: "山川穂高", team: "L", teamName: "西武", value: ".685" }],
    打点: [{ rank: 1, name: "山川穂高", team: "L", teamName: "西武", value: 135 }],
    安打: [{ rank: 1, name: "吉田正尚", team: "Bs", teamName: "オリックス", value: 205 }],
    盗塁: [{ rank: 1, name: "周東佑京", team: "Hs", teamName: "ソフトバンク", value: 65 }],
  },
}

// ダミーデータ - 投手リーダー（パ・リーグ）
const pitchersPL: LeadersConfig = {
  top3Metrics: ["最多勝", "防御率", "セーブ"],
  miniMetrics: ["奪三振", "WHIP", "勝率", "完投", "投球回"],
  leaders: {
    最多勝: [
      { rank: 1, name: "山本由伸", team: "Bs", teamName: "オリックス", value: 18 },
      { rank: 2, name: "千賀滉大", team: "Hs", teamName: "ソフトバンク", value: 17 },
      { rank: 3, name: "佐々木朗希", team: "M", teamName: "ロッテ", value: 16 },
    ],
    防御率: [
      { rank: 1, name: "山本由伸", team: "Bs", teamName: "オリックス", value: "1.68" },
      { rank: 2, name: "千賀滉大", team: "Hs", teamName: "ソフトバンク", value: "1.82" },
      { rank: 3, name: "佐々木朗希", team: "M", teamName: "ロッテ", value: "1.95" },
    ],
    セーブ: [
      { rank: 1, name: "宮城大弥", team: "Bs", teamName: "オリックス", value: 45 },
      { rank: 2, name: "森唯斗", team: "Hs", teamName: "ソフトバンク", value: 40 },
      { rank: 3, name: "益田直也", team: "M", teamName: "ロッテ", value: 37 },
    ],
    奪三振: [{ rank: 1, name: "佐々木朗希", team: "M", teamName: "ロッテ", value: 238 }],
    WHIP: [{ rank: 1, name: "山本由伸", team: "Bs", teamName: "オリックス", value: "0.89" }],
    勝率: [{ rank: 1, name: "山本由伸", team: "Bs", teamName: "オリックス", value: ".900" }],
    完投: [{ rank: 1, name: "千賀滉大", team: "Hs", teamName: "ソフトバンク", value: 6 }],
    投球回: [{ rank: 1, name: "山本由伸", team: "Bs", teamName: "オリックス", value: "205.1" }],
  },
}

// ダミーデータ - 順位表（セ・リーグ）
const standingsCL: StandingRow[] = [
  {
    pos: 1,
    name: "阪神タイガース",
    abbr: "阪神",
    w: 85,
    l: 58,
    pct: 0.594,
    runs: 725,
    ops: ".785",
    avg: ".275",
    hr: 185,
    obp: ".345",
    slg: ".440",
    isod: ".070",
    isop: ".165",
    bb_rate_hit: "9.8%",
    k_rate_hit: "20.5%",
    bb_k_diff_hit: "-10.7%",
    runs_allowed: 598,
    era: "3.42",
    cg: 12,
    bb_rate_pitch: "7.5%",
    k_rate_pitch: "22.8%",
    k_bb_diff_pitch: "15.3%",
  },
  {
    pos: 2,
    name: "読売ジャイアンツ",
    abbr: "巨人",
    w: 82,
    l: 61,
    pct: 0.573,
    runs: 702,
    ops: ".768",
    avg: ".268",
    hr: 178,
    obp: ".338",
    slg: ".430",
    isod: ".070",
    isop: ".162",
    bb_rate_hit: "9.2%",
    k_rate_hit: "21.3%",
    bb_k_diff_hit: "-12.1%",
    runs_allowed: 612,
    era: "3.58",
    cg: 9,
    bb_rate_pitch: "8.1%",
    k_rate_pitch: "21.5%",
    k_bb_diff_pitch: "13.4%",
  },
  {
    pos: 3,
    name: "横浜DeNAベイスターズ",
    abbr: "DeNA",
    w: 78,
    l: 65,
    pct: 0.545,
    runs: 685,
    ops: ".752",
    avg: ".265",
    hr: 165,
    obp: ".332",
    slg: ".420",
    isod: ".067",
    isop: ".155",
    bb_rate_hit: "8.8%",
    k_rate_hit: "22.1%",
    bb_k_diff_hit: "-13.3%",
    runs_allowed: 625,
    era: "3.68",
    cg: 7,
    bb_rate_pitch: "8.5%",
    k_rate_pitch: "20.8%",
    k_bb_diff_pitch: "12.3%",
  },
  {
    pos: 4,
    name: "広島東洋カープ",
    abbr: "広島",
    w: 75,
    l: 68,
    pct: 0.524,
    runs: 668,
    ops: ".742",
    avg: ".262",
    hr: 158,
    obp: ".328",
    slg: ".414",
    isod: ".066",
    isop: ".152",
    bb_rate_hit: "8.5%",
    k_rate_hit: "22.8%",
    bb_k_diff_hit: "-14.3%",
    runs_allowed: 645,
    era: "3.82",
    cg: 5,
    bb_rate_pitch: "8.8%",
    k_rate_pitch: "20.2%",
    k_bb_diff_pitch: "11.4%",
  },
  {
    pos: 5,
    name: "中日ドラゴンズ",
    abbr: "中日",
    w: 68,
    l: 75,
    pct: 0.476,
    runs: 632,
    ops: ".725",
    avg: ".255",
    hr: 142,
    obp: ".320",
    slg: ".405",
    isod: ".065",
    isop: ".150",
    bb_rate_hit: "8.2%",
    k_rate_hit: "23.5%",
    bb_k_diff_hit: "-15.3%",
    runs_allowed: 665,
    era: "3.95",
    cg: 8,
    bb_rate_pitch: "9.2%",
    k_rate_pitch: "19.8%",
    k_bb_diff_pitch: "10.6%",
  },
  {
    pos: 6,
    name: "東京ヤクルトスワローズ",
    abbr: "ヤクルト",
    w: 62,
    l: 81,
    pct: 0.434,
    runs: 615,
    ops: ".712",
    avg: ".250",
    hr: 138,
    obp: ".315",
    slg: ".397",
    isod: ".065",
    isop: ".147",
    bb_rate_hit: "8.0%",
    k_rate_hit: "24.2%",
    bb_k_diff_hit: "-16.2%",
    runs_allowed: 688,
    era: "4.12",
    cg: 4,
    bb_rate_pitch: "9.5%",
    k_rate_pitch: "19.2%",
    k_bb_diff_pitch: "9.7%",
  },
]

// ダミーデータ - 順位表（パ・リーグ）
const standingsPL: StandingRow[] = [
  {
    pos: 1,
    name: "オリックス・バファローズ",
    abbr: "オリックス",
    w: 88,
    l: 55,
    pct: 0.615,
    runs: 755,
    ops: ".812",
    avg: ".282",
    hr: 198,
    obp: ".352",
    slg: ".460",
    isod: ".070",
    isop: ".178",
    bb_rate_hit: "10.2%",
    k_rate_hit: "19.8%",
    bb_k_diff_hit: "-9.6%",
    runs_allowed: 575,
    era: "3.18",
    cg: 15,
    bb_rate_pitch: "7.2%",
    k_rate_pitch: "23.5%",
    k_bb_diff_pitch: "16.3%",
  },
  {
    pos: 2,
    name: "福岡ソフトバンクホークス",
    abbr: "ソフトバンク",
    w: 85,
    l: 58,
    pct: 0.594,
    runs: 738,
    ops: ".795",
    avg: ".278",
    hr: 192,
    obp: ".348",
    slg: ".447",
    isod: ".070",
    isop: ".169",
    bb_rate_hit: "9.8%",
    k_rate_hit: "20.5%",
    bb_k_diff_hit: "-10.7%",
    runs_allowed: 588,
    era: "3.32",
    cg: 13,
    bb_rate_pitch: "7.5%",
    k_rate_pitch: "22.8%",
    k_bb_diff_pitch: "15.3%",
  },
  {
    pos: 3,
    name: "埼玉西武ライオンズ",
    abbr: "西武",
    w: 80,
    l: 63,
    pct: 0.559,
    runs: 715,
    ops: ".778",
    avg: ".272",
    hr: 185,
    obp: ".342",
    slg: ".436",
    isod: ".070",
    isop: ".164",
    bb_rate_hit: "9.5%",
    k_rate_hit: "21.2%",
    bb_k_diff_hit: "-11.7%",
    runs_allowed: 605,
    era: "3.48",
    cg: 11,
    bb_rate_pitch: "8.0%",
    k_rate_pitch: "21.8%",
    k_bb_diff_pitch: "13.8%",
  },
  {
    pos: 4,
    name: "千葉ロッテマリーンズ",
    abbr: "ロッテ",
    w: 75,
    l: 68,
    pct: 0.524,
    runs: 688,
    ops: ".762",
    avg: ".268",
    hr: 172,
    obp: ".335",
    slg: ".427",
    isod: ".070",
    isop: ".159",
    bb_rate_hit: "9.0%",
    k_rate_hit: "21.8%",
    bb_k_diff_hit: "-12.8%",
    runs_allowed: 628,
    era: "3.62",
    cg: 9,
    bb_rate_pitch: "8.3%",
    k_rate_pitch: "21.2%",
    k_bb_diff_pitch: "12.9%",
  },
  {
    pos: 5,
    name: "東北楽天ゴールデンイーグルス",
    abbr: "楽天",
    w: 70,
    l: 73,
    pct: 0.49,
    runs: 665,
    ops: ".745",
    avg: ".263",
    hr: 165,
    obp: ".330",
    slg: ".415",
    isod: ".070",
    isop: ".152",
    bb_rate_hit: "8.7%",
    k_rate_hit: "22.5%",
    bb_k_diff_hit: "-13.8%",
    runs_allowed: 652,
    era: "3.78",
    cg: 7,
    bb_rate_pitch: "8.6%",
    k_rate_pitch: "20.5%",
    k_bb_diff_pitch: "11.9%",
  },
  {
    pos: 6,
    name: "北海道日本ハムファイターズ",
    abbr: "日本ハム",
    w: 65,
    l: 78,
    pct: 0.455,
    runs: 642,
    ops: ".728",
    avg: ".258",
    hr: 155,
    obp: ".325",
    slg: ".403",
    isod: ".067",
    isop: ".145",
    bb_rate_hit: "8.5%",
    k_rate_hit: "23.2%",
    bb_k_diff_hit: "-14.7%",
    runs_allowed: 678,
    era: "3.98",
    cg: 6,
    bb_rate_pitch: "9.0%",
    k_rate_pitch: "19.8%",
    k_bb_diff_pitch: "10.8%",
  },
]

// タブ定義
const mainTabs = [
  { id: 0, label: "TOP", type: "top" },
  { id: 1, label: "今週", type: "weekly" },
  { id: 2, label: "予想投手", type: "probables" },
  { id: 3, label: "最新情報", type: "articles" },
  { id: 4, label: "Quiz", type: "quiz" },
]

const subTabs = [
  { id: 0, label: "セ個人成績", type: "combined", league: "CL" },
  { id: 1, label: "パ個人成績", type: "combined", league: "PL" },
  { id: 2, label: "セ順位表", type: "standings", league: "CL" },
  { id: 3, label: "パ順位表", type: "standings", league: "PL" },
]

const leagueColors = {
  CL: "#039850", // セ・リーグ（緑）
  PL: "#10b8ce", // パ・リーグ（青）
}

const getDataForPanel = (league: string, type: string): LeadersConfig => {
  if (league === "CL" && type === "batting") {
    return battersCL
  } else if (league === "CL" && type === "pitching") {
    return pitchersCL
  } else if (league === "PL" && type === "batting") {
    return battersPL
  } else if (league === "PL" && type === "pitching") {
    return pitchersPL
  }
  return { top3Metrics: [], miniMetrics: [], leaders: {} }
}

type LeadersPanelProps = {
  data: LeadersConfig
  title: string
  leagueName: string
  leagueColor: string
  year?: number
  league?: string
}

const LeaderRow = ({ leader, stat, index }: { leader: any; index: number; stat: any }) => {
  // formatStatを使用して値をフォーマット
  const formattedValue = formatStat(stat, leader.value)
  
  // romanNameを取得（データから直接取得、なければ辞書から）
  // イニシャル.苗字形式に変換（例: "Kiyomiya Kotaro" → "K.Kiyomiya"）
  const romanName = (() => {
    if (leader.romanName) {
      const parts = leader.romanName.trim().split(/\s+/)
      if (parts.length >= 2) {
        const lastName = parts[0]  // 苗字
        const firstName = parts[1]  // 名前
        const initial = firstName.length > 0 ? firstName[0].toUpperCase() : ''
        return `${initial}.${lastName}`
      } else if (parts.length === 1 && parts[0].length > 0) {
        // 名前のみの場合（外国人選手など）
        // 例: "Fabian" → "F.Fabian"
        const name = parts[0]
        return `${name[0].toUpperCase()}.${name}`
      }
      return ''
    }
    if (playerRomanNames[leader.name]) {
      const parts = playerRomanNames[leader.name].split(/\s+/)
      if (parts.length >= 2) {
        const lastName = parts[0]  // 苗字
        const firstName = parts[1]  // 名前
        const initial = firstName.length > 0 ? firstName[0].toUpperCase() : ''
        return `${initial}.${lastName}`
      } else if (parts.length === 1 && parts[0].length > 0) {
        // 名前のみの場合（外国人選手など）
        // 例: "Fabian" → "F.Fabian"
        const name = parts[0]
        return `${name[0].toUpperCase()}.${name}`
      }
    }
    return ''
  })()
  
  return (
    <div className="flex items-center gap-0.5 py-0.5">
      {/* Rank Badge */}
      <div className="w-4 h-4 rounded-full bg-[#2a2a2a] flex items-center justify-center">
        <span className="text-white text-[10px] latin tabular-nums">{index + 1}</span>
      </div>
      <div className="w-1 h-6 mr-1" style={{ backgroundColor: teamColors[leader.team] || "#666" }} />
      {/* Player Info - 横並び */}
      <Link
        href={`/players/${leader.name}?name=${encodeURIComponent((leader.name || "").replace(/\s+/g, ""))}${romanName ? `&roman=${encodeURIComponent(romanName)}` : ""}`}
        className="flex-1 min-w-0 flex items-center gap-1 hover:opacity-80 transition-opacity"
      >
        <span className="text-white text-sm font-semibold leading-tight">{leader.name}</span>
        {romanName && (
          <span className="latin text-[10px] text-gray-400 leading-tight">{romanName}</span>
        )}
      </Link>
      <div className="text-white text-base bebas tabular-nums font-normal">{formattedValue}</div>
    </div>
  )
}

const MiniLeaderRow = ({ leader, stat }: { leader: any; stat: any }) => {
  const formattedValue = formatStat(stat, leader.value)
  const romanName = (() => {
    const raw = (leader.romanName || playerRomanNames[leader.name] || "").trim()
    if (!raw) return ""
    if (/^[A-Z]\.[A-Za-z]+$/.test(raw)) return raw
    const parts = raw.split(/\s+/)
    if (parts.length >= 2) return `${parts[0][0].toUpperCase()}.${parts[1]}`
    if (parts[0].length > 0) return `${parts[0][0].toUpperCase()}.${parts[0]}`
    return ""
  })()
  
  return (
    <div className="flex items-center gap-0.5 py-0.5">
      {/* Rank Badge */}
      <div className="w-4 h-4 rounded-full bg-[#2a2a2a] flex items-center justify-center">
        <span className="text-white text-[10px] latin tabular-nums">1</span>
      </div>
      <div className="w-1 h-10 mr-1" style={{ backgroundColor: teamColors[leader.team] || "#666" }} />
      {/* Player Info - 縦並び */}
      <Link
        href={`/players/${leader.name}?name=${encodeURIComponent((leader.name || "").replace(/\s+/g, ""))}${romanName ? `&roman=${encodeURIComponent(romanName)}` : ""}`}
        className="flex-1 min-w-0 flex flex-col hover:opacity-80 transition-opacity"
      >
        <span className="text-white text-sm font-semibold leading-tight">{leader.name}</span>
        {romanName && (
          <span className="latin text-[10px] text-gray-400 leading-tight">{romanName}</span>
        )}
      </Link>
      <div className="text-white text-base bebas tabular-nums font-normal">{formattedValue}</div>
    </div>
  )
}

const LeadersPanel = ({ data, title, leagueName, leagueColor, year = 2025, league }: LeadersPanelProps) => {
  // 指標名を内部キーに変換する関数
  const normalizeMetricKey = (metric: string): string => {
    // metric_map.jsonから取得
    if (metric in metricMap) {
      return metricMap[metric as keyof typeof metricMap]
    }
    // 大文字小文字を無視して検索
    const lowerMetric = metric.toLowerCase()
    for (const [key, value] of Object.entries(metricMap)) {
      if (key.toLowerCase() === lowerMetric) {
        return value
      }
    }
    // 見つからない場合は小文字化して返す
    return metric.toLowerCase().replace('%', 'pct').replace('/', '').replace('-', '')
  }

  // ランキングページのURLを生成
  const getRankingUrl = (metric: string): string => {
    if (year && league) {
      const metricKey = normalizeMetricKey(metric)
      // K%のみ昇順、それ以外は降順
      const order = (metricKey === 'kpct' || metricKey === 'k%') ? 'asc' : 'desc'
      return `/ranking/${year}/${league}?sort=${encodeURIComponent(metricKey)}&order=${order}`
    }
    // フォールバック: 旧形式のURL
    return `/ranking/${encodeURIComponent(metric)}`
  }

  // 「成績一覧」リンクのURLを生成（全年度・全リーグで有効）
  const getStatsListUrl = (): string => {
    if (year && league) {
      return `/ranking/${year}/${league}`
    }
    return '/ranking/coming-soon'
  }

  return (
    <div className="space-y-1">
      {/* Title Section */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div style={{ width: "4px", height: "32px", backgroundColor: leagueColor }} />
          <div>
            <div className="text-sm font-medium">{title}</div>
            <div className="text-[10px] text-gray-400">{leagueName}</div>
          </div>
        </div>
      </div>

      {/* TOP 3 Cards - OPS, AVG, HR */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-1">
        {data.top3Metrics.map((metric, index) => (
          <div key={metric} className="bg-black border border-[#555] p-1 relative">
            <div className="flex items-stretch justify-between mb-1">
              {/* Metric Name */}
              <Link
                href={getRankingUrl(metric)}
                className="bg-black py-0.5 flex-1 text-center hover:opacity-80 transition-opacity"
              >
                <span className="latin text-[#ffff44] text-xs tracking-wider">{metric}</span>
              </Link>
              {/* Stats List Link */}
              <Link
                href={getStatsListUrl()}
                className="bg-black py-0.5 px-1 text-[10px] text-[#e8e8e8] hover:text-white transition-colors flex items-center"
              >
                成績一覧
              </Link>
            </div>
            {/* Top 3 Players */}
            <div className="space-y-0">
              {data.leaders[metric]?.map((leader, leaderIndex) => (
                <LeaderRow key={leader.rank} leader={leader} stat={metric} index={leaderIndex} />
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Mini Cards (5 metrics) */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-1">
        {data.miniMetrics.map((metric, index) => {
          const leader = data.leaders[metric]?.[0]
          if (!leader) return null
          return (
            <div key={metric} className="bg-black border border-[#555] p-0.5 relative">
              <div className="flex items-stretch justify-between mb-1">
                {/* Metric Name */}
                <Link
                  href={getRankingUrl(metric)}
                  className="bg-black py-0.5 flex-1 text-center hover:opacity-80 transition-opacity"
                >
                  <span className={`text-[#ffff44] text-xs ${/[a-zA-Z]/.test(metric) ? "latin" : ""}`}>{metric}</span>
                </Link>
                {/* Stats List Link */}
                <Link
                  href={getStatsListUrl()}
                  className="bg-black py-0.5 px-0.5 text-[10px] text-[#e8e8e8] hover:text-white transition-colors flex items-center"
                >
                  成績一覧
                </Link>
              </div>
              {/* 1st Place Player with english name below */}
              <MiniLeaderRow leader={leader} stat={metric} />
            </div>
          )
        })}
      </div>
    </div>
  )
}

const StandingsPanel = ({ league, leagueColor }: { league: string; leagueColor: string }) => {
  const standings = league === "CL" ? standingsCL : standingsPL

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div style={{ width: "4px", height: "32px", backgroundColor: leagueColor }} />
          <div>
            <div className="text-sm font-medium">{league === "CL" ? "セ・リーグ" : "パ・リーグ"} 順位表</div>
          </div>
        </div>
      </div>
      <div className="bg-black border border-[#555] p-4">
        <table className="w-full">
          <thead>
            <tr>
              <th className="text-[10px] text-gray-400">順位</th>
              <th className="text-[10px] text-gray-400">チーム</th>
              <th className="text-[10px] text-gray-400">勝</th>
              <th className="text-[10px] text-gray-400">負</th>
              <th className="text-[10px] text-gray-400">勝率</th>
              <th className="text-[10px] text-gray-400">得点</th>
              <th className="text-[10px] text-gray-400">防御率</th>
            </tr>
          </thead>
          <tbody>
            {standings.map((team) => (
              <tr key={team.name} className="hover:bg-[#2a2a2a] transition-colors">
                <td className="text-white text-base bebas tabular-nums font-normal">{team.pos}</td>
                <td className="text-white text-base bebas tabular-nums font-normal">{team.name}</td>
                <td className="text-white text-base bebas tabular-nums font-normal">{team.w}</td>
                <td className="text-white text-base bebas tabular-nums font-normal">{team.l}</td>
                <td className="text-white text-base bebas tabular-nums font-normal">{(team.pct * 100).toFixed(1)}%</td>
                <td className="text-white text-base bebas tabular-nums font-normal">{team.runs}</td>
                <td className="text-white text-base bebas tabular-nums font-normal">{team.era}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default function Page() {
  const [activeMainTab, setActiveMainTab] = useState(0) // TOP
  const [activeSubTab, setActiveSubTab] = useState(0) // セ個人成績
  const [selectedYear, setSelectedYear] = useState(2025)
  const [isMenuOpen, setIsMenuOpen] = useState(false)

  const router = useRouter()

  const handleYearChange = (year: number) => {
    setSelectedYear(year)
    if (year === 2025) {
      router.push("/")
    } else {
      router.push(`/${year}`)
    }
  }

  return (
    <div className="min-h-screen bg-black text-white">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-black/95 backdrop-blur-sm border-b border-[#333] py-1 px-3">
        <div className="flex items-center justify-between relative">
          {/* Hamburger Menu */}
          <button
            onClick={() => setIsMenuOpen(true)}
            className="p-1 hover:bg-[#2a2a2a] rounded transition-colors"
            aria-label="メニューを開く"
          >
            <div className="w-5 h-4 flex flex-col justify-between">
              <span className="block w-full h-0.5 bg-[#ffff44]" />
              <span className="block w-full h-0.5 bg-[#ffff44]" />
              <span className="block w-full h-0.5 bg-[#ffff44]" />
            </div>
          </button>

          {/* Logo */}
          <Link href="/" className="absolute left-1/2 -translate-x-1/2 hover:opacity-80 transition-opacity">
            <Image src="/logo.png" alt="Short-Stop" width={28} height={28} className="object-contain" />
          </Link>

          {/* Year Selector */}
          <select
            value={selectedYear}
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
      </header>

      {/* Hamburger Menu Overlay */}
      {isMenuOpen && (
        <>
          <div className="fixed inset-0 bg-black/70 z-[100]" onClick={() => setIsMenuOpen(false)} />
          <div className="fixed top-0 left-0 h-full w-64 bg-[#1a1a1a] z-[101] overflow-y-auto shadow-xl">
            {/* Menu content */}
            <div className="p-4">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-lg font-bold text-[#ffff44]">メニュー</h2>
                <button
                  onClick={() => setIsMenuOpen(false)}
                  className="text-white hover:text-[#ffff44] text-2xl leading-none"
                  aria-label="メニューを閉じる"
                >
                  ×
                </button>
              </div>

              <nav className="space-y-2">
                <Link
                  href="/"
                  className="block py-2 px-3 hover:bg-[#2a2a2a] rounded transition-colors text-sm"
                  onClick={() => setIsMenuOpen(false)}
                >
                  トップページ
                </Link>
                <Link
                  href="/ranking/2025/PL"
                  className="block py-2 px-3 hover:bg-[#2a2a2a] rounded transition-colors text-sm"
                  onClick={() => setIsMenuOpen(false)}
                >
                  成績一覧
                </Link>
                <Link
                  href="#"
                  className="block py-2 px-3 hover:bg-[#2a2a2a] rounded transition-colors text-sm"
                  onClick={() => setIsMenuOpen(false)}
                >
                  ドラフト情報
                </Link>

                {/* Articles with team dropdowns */}
                <div>
                  <button
                    onClick={() => (window.location.href = "#")}
                    className="w-full text-left py-2 px-3 hover:bg-[#2a2a2a] rounded transition-colors text-sm flex items-center justify-between"
                  >
                    記事
                    <span className="text-xs">▼</span>
                  </button>

                  {/* Central League */}
                  <div className="border-l-2 border-[#039850] pl-2">
                    <div className="text-xs font-bold text-[#039850] mb-1">セ・リーグ</div>
                    <Link
                      href="#"
                      className="block py-1 text-xs hover:text-[#ffff44] transition-colors"
                      onClick={() => setIsMenuOpen(false)}
                    >
                      読売ジャイアンツ
                    </Link>
                    <Link
                      href="#"
                      className="block py-1 text-xs hover:text-[#ffff44] transition-colors"
                      onClick={() => setIsMenuOpen(false)}
                    >
                      阪神タイガース
                    </Link>
                    <Link
                      href="#"
                      className="block py-1 text-xs hover:text-[#ffff44] transition-colors"
                      onClick={() => setIsMenuOpen(false)}
                    >
                      横浜DeNAベイスターズ
                    </Link>
                    <Link
                      href="#"
                      className="block py-1 text-xs hover:text-[#ffff44] transition-colors"
                      onClick={() => setIsMenuOpen(false)}
                    >
                      中日ドラゴンズ
                    </Link>
                    <Link
                      href="#"
                      className="block py-1 text-xs hover:text-[#ffff44] transition-colors"
                      onClick={() => setIsMenuOpen(false)}
                    >
                      広島東洋カープ
                    </Link>
                    <Link
                      href="#"
                      className="block py-1 text-xs hover:text-[#ffff44] transition-colors"
                      onClick={() => setIsMenuOpen(false)}
                    >
                      東京ヤクルトスワローズ
                    </Link>
                  </div>

                  {/* Pacific League */}
                  <div className="border-l-2 border-[#10b8ce] pl-2">
                    <div className="text-xs font-bold text-[#10b8ce] mb-1">パ・リーグ</div>
                    <Link
                      href="#"
                      className="block py-1 text-xs hover:text-[#ffff44] transition-colors"
                      onClick={() => setIsMenuOpen(false)}
                    >
                      福岡ソフトバンクホークス
                    </Link>
                    <Link
                      href="#"
                      className="block py-1 text-xs hover:text-[#ffff44] transition-colors"
                      onClick={() => setIsMenuOpen(false)}
                    >
                      オリックス・バファローズ
                    </Link>
                    <Link
                      href="#"
                      className="block py-1 text-xs hover:text-[#ffff44] transition-colors"
                      onClick={() => setIsMenuOpen(false)}
                    >
                      埼玉西武ライオンズ
                    </Link>
                    <Link
                      href="#"
                      className="block py-1 text-xs hover:text-[#ffff44] transition-colors"
                      onClick={() => setIsMenuOpen(false)}
                    >
                      千葉ロッテマリーンズ
                    </Link>
                    <Link
                      href="#"
                      className="block py-1 text-xs hover:text-[#ffff44] transition-colors"
                      onClick={() => setIsMenuOpen(false)}
                    >
                      北海道日本ハムファイターズ
                    </Link>
                    <Link
                      href="#"
                      className="block py-1 text-xs hover:text-[#ffff44] transition-colors"
                      onClick={() => setIsMenuOpen(false)}
                    >
                      東北楽天ゴールデンイーグルス
                    </Link>
                  </div>
                </div>
              </nav>
            </div>
          </div>
        </>
      )}

      {/* Main Navigation Tabs */}
      <div className="grid grid-cols-5 gap-1 px-2 py-1 bg-black">
        {mainTabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => {
              setActiveMainTab(tab.id)
              if (tab.id === 0) setActiveSubTab(0)
            }}
            className={`relative overflow-hidden group transition-all duration-200 flex items-center justify-center ${
              activeMainTab === tab.id ? "bg-[#ffff44] text-black" : "bg-[#1a1a1a] text-white hover:bg-[#2a2a2a]"
            } border border-[#555] py-1.5 px-3 text-xs font-semibold whitespace-nowrap`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Sub Tabs - Fixed at Bottom (only when TOP tab is active) */}
      {activeMainTab === 0 && (
        <div className="fixed bottom-0 left-0 right-0 z-40 bg-black border-t border-[#555] animate-in slide-in-from-bottom duration-300 backdrop-blur-sm bg-opacity-95">
          <div className="grid grid-cols-4 gap-0">
            {subTabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveSubTab(tab.id)}
                className={`py-3 text-xs border border-[#555] transition-all duration-200 ease-in-out text-center flex items-center justify-center ${
                  activeSubTab === tab.id
                    ? "bg-[#ffff44] text-black font-semibold shadow-lg"
                    : "bg-[#1a1a1a] text-white hover:bg-[#2a2a2a] hover:text-[#ffff44] hover:scale-105"
                }`}
              >
                <span className="latin">{tab.label}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Tab Content */}
      <div className={`container mx-auto px-2 py-2 ${activeMainTab === 0 ? "pb-16" : ""}`}>
        <div className="animate-in fade-in duration-300">
          {/* TOP tab content */}
          {activeMainTab === 0 && (
            <div>
              {subTabs[activeSubTab].type === "combined" && (
                <div className="space-y-4">
                  {/* Batting stats */}
                  <TopPageLeadersClient 
                    year={selectedYear}
                    league={subTabs[activeSubTab].league || "CL"}
                  />
                  {/* Pitching stats */}
                  <div>
                    <LeadersPanel
                      title={`${subTabs[activeSubTab].league === "CL" ? "セ・リーグ" : "パ・リーグ"} 投球成績`}
                      leagueName={subTabs[activeSubTab].league === "CL" ? "Central League" : "Pacific League"}
                      leagueColor={subTabs[activeSubTab].league === "CL" ? "#039850" : "#10b8ce"}
                      data={getDataForPanel(subTabs[activeSubTab].league || "CL", "pitching")}
                      year={selectedYear}
                      league={subTabs[activeSubTab].league || "CL"}
                    />
                  </div>
                </div>
              )}
              {subTabs[activeSubTab].type === "standings" && (
                <StandingsPanel
                  league={subTabs[activeSubTab].league || "CL"}
                  leagueColor={subTabs[activeSubTab].league === "CL" ? "#039850" : "#10b8ce"}
                />
              )}
            </div>
          )}

          {/* Weekly stats */}
          {activeMainTab === 1 && <div className="text-white text-center py-8">今週の成績（準備中）</div>}

          {/* Probables */}
          {activeMainTab === 2 && <div className="text-white text-center py-8">予想投手（準備中）</div>}

          {/* Articles */}
          {activeMainTab === 3 && (
            <ArticlesListClient />
          )}

          {/* Quiz */}
          {activeMainTab === 4 && <div className="text-white text-center py-8">Quiz（準備中）</div>}
        </div>
      </div>
    </div>
  )
}
