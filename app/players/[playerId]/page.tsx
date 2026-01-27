"use client"

import type React from "react"

import Link from "next/link"
import { useState, useRef, useEffect } from "react"

// サンプルデータ
const playerData = {
  name: "近本光司",
  birthDate: "1994年11月9日",
  age: 30,
  birthPlace: "兵庫県津名郡東浦町（現：淡路市）",
  proDebut: "2018年 ドラフト1位",
  career: "社高等学校 → 関西学院大学 → 大阪ガス → 阪神 (2019 - )",
  totalSalary: "10億5000万円",
  championships: "日本一：5回、リーグ優勝：7回",
  faYear: "2027年",
}

const careerHighs = [
  { title: "OPS", value: "1.043", year: "2023年", 足: "" },
  { title: "打率", value: ".338", year: "2023年", 足: "" },
  { title: "本塁打", value: "21", year: "2023年", 足: "本" },
  { title: "打点", value: "84", year: "2023年", 足: "点" },
  { title: "出塁率", value: ".425", year: "2023年", 足: "" },
  { title: "長打率", value: ".618", year: "2023年", 足: "" },
]

const careerStats = [
  {
    year: 2019,
    age: 24,
    salary: 1200,
    ops: 0.791,
    avg: 0.271,
    hits: 146,
    hr: 8,
    rbi: 47,
    games: 143,
    pa: 638,
    ab: 539,
    obp: 0.348,
    slg: 0.443,
    runs: 94,
    doubles: 26,
    triples: 7,
    sb: 36,
    cs: 7,
    bb: 70,
    so: 131,
    isop: 0.172,
    isod: 0.077,
    bbp: 11.0,
    kp: 20.5,
    bbk: 0.53,
    sh: 24,
    sf: 5,
    hbp: 4,
  },
  {
    year: 2020,
    age: 25,
    salary: 2400,
    ops: 0.765,
    avg: 0.29,
    hits: 124,
    hr: 8,
    rbi: 38,
    games: 120,
    pa: 547,
    ab: 428,
    obp: 0.376,
    slg: 0.449,
    runs: 70,
    doubles: 20,
    triples: 5,
    sb: 24,
    cs: 8,
    bb: 67,
    so: 89,
    isop: 0.159,
    isod: 0.086,
    bbp: 12.2,
    kp: 16.3,
    bbk: 0.75,
    sh: 19,
    sf: 3,
    hbp: 5,
  },
  {
    year: 2021,
    age: 26,
    salary: 5000,
    ops: 0.756,
    avg: 0.288,
    hits: 153,
    hr: 4,
    rbi: 39,
    games: 143,
    pa: 653,
    ab: 531,
    obp: 0.364,
    slg: 0.392,
    runs: 85,
    doubles: 27,
    triples: 7,
    sb: 28,
    cs: 4,
    bb: 78,
    so: 105,
    isop: 0.104,
    isod: 0.076,
    bbp: 11.9,
    kp: 16.1,
    bbk: 0.74,
    sh: 33,
    sf: 2,
    hbp: 9,
  },
  {
    year: 2022,
    age: 27,
    salary: 9000,
    ops: 0.853,
    avg: 0.302,
    hits: 170,
    hr: 10,
    rbi: 52,
    games: 143,
    pa: 666,
    ab: 563,
    obp: 0.383,
    slg: 0.47,
    runs: 103,
    doubles: 32,
    triples: 8,
    sb: 25,
    cs: 8,
    bb: 72,
    so: 100,
    isop: 0.168,
    isod: 0.081,
    bbp: 10.8,
    kp: 15.0,
    bbk: 0.72,
    sh: 23,
    sf: 4,
    hbp: 4,
  },
  {
    year: 2023,
    age: 28,
    salary: 25000,
    ops: 1.043,
    avg: 0.338,
    hits: 181,
    hr: 21,
    rbi: 84,
    games: 140,
    pa: 641,
    ab: 536,
    obp: 0.425,
    slg: 0.618,
    runs: 115,
    doubles: 36,
    triples: 4,
    sb: 18,
    cs: 5,
    bb: 91,
    so: 94,
    isop: 0.28,
    isod: 0.087,
    bbp: 14.2,
    kp: 14.7,
    bbk: 0.97,
    sh: 7,
    sf: 5,
    hbp: 2,
  },
  {
    year: 2024,
    age: 29,
    salary: 52900,
    ops: 0.829,
    avg: 0.289,
    hits: 162,
    hr: 15,
    rbi: 67,
    games: 143,
    pa: 649,
    ab: 561,
    obp: 0.366,
    slg: 0.463,
    runs: 91,
    doubles: 28,
    triples: 6,
    sb: 22,
    cs: 6,
    bb: 66,
    so: 112,
    isop: 0.174,
    isod: 0.077,
    bbp: 10.2,
    kp: 17.3,
    bbk: 0.59,
    sh: 15,
    sf: 4,
    hbp: 3,
  },
]

export default function PlayerPage() {
  const [sliderValue, setSliderValue] = useState(0)
  const scrollerRef = useRef<HTMLDivElement>(null)
  const [maxScroll, setMaxScroll] = useState(0)

  useEffect(() => {
    const updateMaxScroll = () => {
      if (scrollerRef.current) {
        const max = scrollerRef.current.scrollWidth - scrollerRef.current.clientWidth
        setMaxScroll(max)
      }
    }

    updateMaxScroll()
    window.addEventListener("resize", updateMaxScroll)
    return () => window.removeEventListener("resize", updateMaxScroll)
  }, [])

  const handleScroll = () => {
    if (scrollerRef.current && maxScroll > 0) {
      const scrollLeft = scrollerRef.current.scrollLeft
      const value = Math.round((scrollLeft / maxScroll) * 100)
      setSliderValue(value)
    }
  }

  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = Number.parseInt(e.target.value)
    setSliderValue(value)
    if (scrollerRef.current && maxScroll > 0) {
      scrollerRef.current.scrollLeft = (maxScroll * value) / 100
    }
  }

  return (
    <div
      className="min-h-screen text-white"
      style={{
        background: "linear-gradient(135deg, #000000 0%, #1a1a1a 100%)",
      }}
    >
      {/* Header */}
      <header className="border-b" style={{ borderColor: "#333333" }}>
        <div className="container mx-auto px-5 py-4 max-w-[800px]">
          <Link href="/" className="text-yellow-400 hover:text-yellow-300 text-sm inline-block mb-2">
            ← トップに戻る
          </Link>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-5 py-8 max-w-[800px]" style={{ paddingLeft: "20px", paddingRight: "20px" }}>
        {/* Player Name */}
        <h1
          className="text-[2.5rem] md:text-[2.0rem] leading-tight mb-8 pl-4"
          style={{
            borderLeft: "6px solid #FF4444",
            textShadow: "2px 2px 4px rgba(0,0,0,0.5)",
            fontWeight: 900,
            fontFamily: "var(--font-sans)",
          }}
        >
          {playerData.name}
        </h1>

        {/* Profile Table */}
        <div className="mb-12">
          <table className="w-full border-collapse" style={{ border: "1px solid #333333" }}>
            <tbody style={{ fontWeight: 900, lineHeight: 1.35 }}>
              <tr>
                <td
                  className="px-4 py-3"
                  style={{
                    backgroundColor: "#FFFF44",
                    color: "#000000",
                    border: "1px solid #333333",
                    width: "120px",
                    fontWeight: 900,
                  }}
                >
                  生年月日
                </td>
                <td className="px-4 py-3" style={{ border: "1px solid #333333" }}>
                  {playerData.birthDate}（{playerData.age}歳）
                </td>
              </tr>
              <tr>
                <td
                  className="px-4 py-3"
                  style={{
                    backgroundColor: "#FFFF44",
                    color: "#000000",
                    border: "1px solid #333333",
                    fontWeight: 900,
                  }}
                >
                  出身地
                </td>
                <td className="px-4 py-3" style={{ border: "1px solid #333333" }}>
                  {playerData.birthPlace}
                </td>
              </tr>
              <tr>
                <td
                  className="px-4 py-3"
                  style={{
                    backgroundColor: "#FFFF44",
                    color: "#000000",
                    border: "1px solid #333333",
                    fontWeight: 900,
                  }}
                >
                  プロ入り
                </td>
                <td className="px-4 py-3" style={{ border: "1px solid #333333" }}>
                  {playerData.proDebut}
                </td>
              </tr>
              <tr>
                <td
                  className="px-4 py-3"
                  style={{
                    backgroundColor: "#FFFF44",
                    color: "#000000",
                    border: "1px solid #333333",
                    fontWeight: 900,
                  }}
                >
                  経歴
                </td>
                <td className="px-4 py-3" style={{ border: "1px solid #333333" }}>
                  {playerData.career}
                </td>
              </tr>
              <tr>
                <td
                  className="px-4 py-3"
                  style={{
                    backgroundColor: "#FFFF44",
                    color: "#000000",
                    border: "1px solid #333333",
                    fontWeight: 900,
                  }}
                >
                  生涯年俸
                </td>
                <td className="px-4 py-3" style={{ border: "1px solid #333333" }}>
                  {playerData.totalSalary}
                </td>
              </tr>
              <tr>
                <td
                  className="px-4 py-3"
                  style={{
                    backgroundColor: "#FFFF44",
                    color: "#000000",
                    border: "1px solid #333333",
                    fontWeight: 900,
                  }}
                >
                  チーム成績
                </td>
                <td className="px-4 py-3" style={{ border: "1px solid #333333" }}>
                  {playerData.championships}
                </td>
              </tr>
              <tr>
                <td
                  className="px-4 py-3"
                  style={{
                    backgroundColor: "#FFFF44",
                    color: "#000000",
                    border: "1px solid #333333",
                    fontWeight: 900,
                  }}
                >
                  FA取得（推定）
                </td>
                <td className="px-4 py-3" style={{ border: "1px solid #333333" }}>
                  {playerData.faYear}
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* Section Title */}
        <h2
          className="text-[1.8rem] md:text-[1.25rem] mb-6 pl-4"
          style={{
            borderLeft: "6px solid #FF4444",
            fontWeight: 900,
          }}
        >
          キャリアハイの打撃成績（2023年）
        </h2>

        {/* Career High Grid */}
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-12">
          {careerHighs.map((stat, idx) => (
            <div
              key={idx}
              className="overflow-hidden"
              style={{
                background: "linear-gradient(145deg, #0c0c0c, #000000)",
                border: "1.6px solid #555555",
                borderRadius: "0",
                boxShadow: "0 4px 10px rgba(0,0,0,0.5)",
                aspectRatio: "3 / 2",
                display: "flex",
                flexDirection: "column",
              }}
            >
              <div
                className="px-2 py-1 text-center"
                style={{
                  backgroundColor: "#FFFF44",
                  color: "#000000",
                  fontSize: "1.05rem",
                  fontWeight: 900,
                }}
              >
                {stat.title}
              </div>
              <div className="flex-1 flex flex-col items-center justify-center px-2">
                <div
                  className="text-[4.2rem] md:text-[3.2rem] font-black leading-none mb-4"
                  style={{
                    fontFamily: "Bebas Neue, sans-serif",
                    letterSpacing: "1.2px",
                    fontVariantNumeric: "tabular-nums",
                  }}
                >
                  {stat.value}
                </div>
              </div>
              {stat.year && (
                <div className="px-2 py-1 text-center text-sm" style={{ backgroundColor: "#1f1f1f" }}>
                  {stat.year}
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Section Title */}
        <h2
          className="text-[1.8rem] md:text-[1.25rem] mb-6 pl-4"
          style={{
            borderLeft: "6px solid #FF4444",
            fontWeight: 900,
          }}
        >
          通算の打撃成績
        </h2>

        {/* Career Stats Table */}
        <div className="mb-4" style={{ maxWidth: "760px" }}>
          <div className="rounded overflow-hidden">
            <div
              ref={scrollerRef}
              onScroll={handleScroll}
              className="overflow-x-auto"
              style={{
                scrollbarWidth: "none",
                msOverflowStyle: "none",
                WebkitOverflowScrolling: "touch",
              }}
            >
              <style jsx>{`
                div::-webkit-scrollbar {
                  display: none;
                }
              `}</style>
              <table className="w-full" style={{ minWidth: "980px", fontVariantNumeric: "tabular-nums" }}>
                <thead>
                  <tr style={{ backgroundColor: "#FFFF44", color: "#000000" }}>
                    <th
                      className="px-2 py-2 text-center font-black text-sm"
                      style={{ position: "sticky", left: 0, zIndex: 4, backgroundColor: "#FFFF44", minWidth: "70px" }}
                    >
                      年度
                    </th>
                    <th
                      className="px-2 py-2 text-center font-black text-sm"
                      style={{
                        position: "sticky",
                        left: "70px",
                        zIndex: 3,
                        backgroundColor: "#FFFF44",
                        minWidth: "70px",
                      }}
                    >
                      年齢
                    </th>
                    <th className="px-2 py-2 text-center font-black text-sm" style={{ minWidth: "80px" }}>
                      年俸
                      <br />
                      (万)
                    </th>
                    <th className="px-2 py-2 text-center font-black text-sm" style={{ minWidth: "70px" }}>
                      OPS
                    </th>
                    <th className="px-2 py-2 text-center font-black text-sm" style={{ minWidth: "70px" }}>
                      打率
                    </th>
                    <th className="px-2 py-2 text-center font-black text-sm" style={{ minWidth: "60px" }}>
                      安打
                    </th>
                    <th className="px-2 py-2 text-center font-black text-sm" style={{ minWidth: "60px" }}>
                      本塁打
                    </th>
                    <th className="px-2 py-2 text-center font-black text-sm" style={{ minWidth: "60px" }}>
                      打点
                    </th>
                    <th className="px-2 py-2 text-center font-black text-sm" style={{ minWidth: "60px" }}>
                      試合
                    </th>
                    <th className="px-2 py-2 text-center font-black text-sm" style={{ minWidth: "60px" }}>
                      打席
                    </th>
                    <th className="px-2 py-2 text-center font-black text-sm" style={{ minWidth: "60px" }}>
                      打数
                    </th>
                    <th className="px-2 py-2 text-center font-black text-sm" style={{ minWidth: "70px" }}>
                      出塁率
                    </th>
                    <th className="px-2 py-2 text-center font-black text-sm" style={{ minWidth: "70px" }}>
                      長打率
                    </th>
                    <th className="px-2 py-2 text-center font-black text-sm" style={{ minWidth: "60px" }}>
                      得点
                    </th>
                    <th className="px-2 py-2 text-center font-black text-sm" style={{ minWidth: "60px" }}>
                      二塁打
                    </th>
                    <th className="px-2 py-2 text-center font-black text-sm" style={{ minWidth: "60px" }}>
                      三塁打
                    </th>
                    <th className="px-2 py-2 text-center font-black text-sm" style={{ minWidth: "60px" }}>
                      盗塁
                    </th>
                    <th className="px-2 py-2 text-center font-black text-sm" style={{ minWidth: "60px" }}>
                      盗塁死
                    </th>
                    <th className="px-2 py-2 text-center font-black text-sm" style={{ minWidth: "60px" }}>
                      四球
                    </th>
                    <th className="px-2 py-2 text-center font-black text-sm" style={{ minWidth: "60px" }}>
                      三振
                    </th>
                    <th className="px-2 py-2 text-center font-black text-sm" style={{ minWidth: "70px" }}>
                      IsoP
                    </th>
                    <th className="px-2 py-2 text-center font-black text-sm" style={{ minWidth: "70px" }}>
                      IsoD
                    </th>
                    <th className="px-2 py-2 text-center font-black text-sm" style={{ minWidth: "60px" }}>
                      BB%
                    </th>
                    <th className="px-2 py-2 text-center font-black text-sm" style={{ minWidth: "60px" }}>
                      K%
                    </th>
                    <th className="px-2 py-2 text-center font-black text-sm" style={{ minWidth: "70px" }}>
                      BB/K
                    </th>
                    <th className="px-2 py-2 text-center font-black text-sm" style={{ minWidth: "60px" }}>
                      犠打
                    </th>
                    <th className="px-2 py-2 text-center font-black text-sm" style={{ minWidth: "60px" }}>
                      犠飛
                    </th>
                    <th className="px-2 py-2 text-center font-black text-sm" style={{ minWidth: "60px" }}>
                      死球
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {careerStats.map((stat, idx) => (
                    <tr
                      key={idx}
                      style={{
                        backgroundColor: idx % 2 === 0 ? "rgba(255,255,255,0.05)" : "transparent",
                      }}
                    >
                      <td
                        className="px-2 py-2 text-center font-mono text-sm"
                        style={{
                          position: "sticky",
                          left: 0,
                          zIndex: 4,
                          backgroundColor: "#FFFF44",
                          color: "#000000",
                          fontWeight: 900,
                          minWidth: "70px",
                        }}
                      >
                        {stat.year}
                      </td>
                      <td
                        className="px-2 py-2 text-center font-mono text-sm"
                        style={{
                          position: "sticky",
                          left: "70px",
                          zIndex: 3,
                          backgroundColor: idx % 2 === 0 ? "#1d1d1d" : "#111",
                          minWidth: "70px",
                        }}
                      >
                        {stat.age}
                      </td>
                      <td className="px-2 py-2 text-center font-mono text-sm">{stat.salary.toLocaleString()}</td>
                      <td className="px-2 py-2 text-center font-mono text-sm">{stat.ops.toFixed(3)}</td>
                      <td className="px-2 py-2 text-center font-mono text-sm">{stat.avg.toFixed(3)}</td>
                      <td className="px-2 py-2 text-center font-mono text-sm">{stat.hits}</td>
                      <td className="px-2 py-2 text-center font-mono text-sm">{stat.hr}</td>
                      <td className="px-2 py-2 text-center font-mono text-sm">{stat.rbi}</td>
                      <td className="px-2 py-2 text-center font-mono text-sm">{stat.games}</td>
                      <td className="px-2 py-2 text-center font-mono text-sm">{stat.pa}</td>
                      <td className="px-2 py-2 text-center font-mono text-sm">{stat.ab}</td>
                      <td className="px-2 py-2 text-center font-mono text-sm">{stat.obp.toFixed(3)}</td>
                      <td className="px-2 py-2 text-center font-mono text-sm">{stat.slg.toFixed(3)}</td>
                      <td className="px-2 py-2 text-center font-mono text-sm">{stat.runs}</td>
                      <td className="px-2 py-2 text-center font-mono text-sm">{stat.doubles}</td>
                      <td className="px-2 py-2 text-center font-mono text-sm">{stat.triples}</td>
                      <td className="px-2 py-2 text-center font-mono text-sm">{stat.sb}</td>
                      <td className="px-2 py-2 text-center font-mono text-sm">{stat.cs}</td>
                      <td className="px-2 py-2 text-center font-mono text-sm">{stat.bb}</td>
                      <td className="px-2 py-2 text-center font-mono text-sm">{stat.so}</td>
                      <td className="px-2 py-2 text-center font-mono text-sm">{stat.isop.toFixed(3)}</td>
                      <td className="px-2 py-2 text-center font-mono text-sm">{stat.isod.toFixed(3)}</td>
                      <td className="px-2 py-2 text-center font-mono text-sm">{stat.bbp.toFixed(1)}</td>
                      <td className="px-2 py-2 text-center font-mono text-sm">{stat.kp.toFixed(1)}</td>
                      <td className="px-2 py-2 text-center font-mono text-sm">{stat.bbk.toFixed(2)}</td>
                      <td className="px-2 py-2 text-center font-mono text-sm">{stat.sh}</td>
                      <td className="px-2 py-2 text-center font-mono text-sm">{stat.sf}</td>
                      <td className="px-2 py-2 text-center font-mono text-sm">{stat.hbp}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Slider Controls */}
          <div className="mt-3 flex justify-center">
            <input
              type="range"
              min="0"
              max="100"
              step="1"
              value={sliderValue}
              onChange={handleSliderChange}
              className="w-full max-w-md"
              style={{
                accentColor: "#FFFF44",
                height: "8px",
              }}
            />
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t mt-12 py-8" style={{ backgroundColor: "#000000", borderColor: "#333333" }}>
        <div className="container mx-auto px-5 text-center" style={{ color: "#999" }}>
          <p className="text-sm">© 2025 NPB打撃成績ランキング</p>
        </div>
      </footer>
    </div>
  )
}
