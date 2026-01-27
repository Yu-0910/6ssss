#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
regulation_rules.py

my-favorite-giants.net の「各年度規定条件」を根拠に、
規定到達者（打撃の規定）を年・リーグごとに判定する関数

参考URL: https://www.my-favorite-giants.net/npb/regulation.htm
"""

import math
from typing import Dict, Optional, Any


def round_half_up(x: float) -> int:
    """
    NPB想定の「四捨五入(half-up)」を明示実装
    """
    return int(math.floor(x + 0.5))


def get_batting_qual_rule(
    year: int,
    league: str,
    team_games: Optional[int] = None,
    team_rank: Optional[int] = None,
    teams_in_league: Optional[int] = None
) -> Dict[str, Any]:
    """
    年度・リーグから打撃の規定到達条件を取得
    
    Args:
        year: 年度
        league: リーグ（"PRE", "CL", "PL"）
        team_games: チーム試合数（計算式が必要な場合に使用）
        team_rank: チーム順位（順位分岐が必要な場合に使用）
        teams_in_league: リーグ内チーム数（順位分岐が必要な場合に使用）
    
    Returns:
        {
            "basis": "AB" or "PA",
            "threshold": int,
            "notes": str,
            "source": "my-favorite-giants regulation.htm"
        }
    """
    source = "my-favorite-giants regulation.htm"
    
    # 1リーグ時代（～1949）
    if league == "PRE":
        if year == 1936:
            # 1936年は春・秋シーズン制だが、規定条件は統一
            return {
                "basis": "AB",
                "threshold": 200,  # 推定値、要確認
                "notes": "1936年（春・秋シーズン制）",
                "source": source
            }
        elif year == 1937:
            return {
                "basis": "AB",
                "threshold": 200,  # 推定値、要確認
                "notes": "1937年（春・秋シーズン制）",
                "source": source
            }
        elif year == 1938:
            return {
                "basis": "AB",
                "threshold": 200,  # 推定値、要確認
                "notes": "1938年（春・秋シーズン制）",
                "source": source
            }
        elif year == 1939:
            return {
                "basis": "AB",
                "threshold": 200,
                "notes": "固定値",
                "source": source
            }
        elif year == 1940:
            return {
                "basis": "AB",
                "threshold": 250,
                "notes": "固定値",
                "source": source
            }
        elif year == 1941:
            return {
                "basis": "AB",
                "threshold": 201,
                "notes": "固定値",
                "source": source
            }
        elif year == 1942:
            return {
                "basis": "AB",
                "threshold": 300,
                "notes": "固定値",
                "source": source
            }
        elif year == 1943:
            return {
                "basis": "AB",
                "threshold": 240,
                "notes": "固定値",
                "source": source
            }
        elif year == 1944:
            return {
                "basis": "AB",
                "threshold": 100,
                "notes": "固定値",
                "source": source
            }
        elif year == 1945:
            return {
                "basis": "AB",
                "threshold": 0,
                "notes": "戦時中のため開催なし",
                "source": source
            }
        elif year == 1946:
            return {
                "basis": "AB",
                "threshold": 300,
                "notes": "固定値",
                "source": source
            }
        elif year == 1947:
            return {
                "basis": "AB",
                "threshold": 330,
                "notes": "固定値",
                "source": source
            }
        elif year == 1948:
            return {
                "basis": "AB",
                "threshold": 400,
                "notes": "固定値",
                "source": source
            }
        elif year == 1949:
            return {
                "basis": "AB",
                "threshold": 300,
                "notes": "AB>=300 AND games>=100（両方の条件を満たす必要あり）",
                "source": source
            }
        else:
            raise ValueError(f"PRE年で未対応の年度: {year}")
    
    # セ・リーグ（1950-1956）
    elif league == "CL":
        if year == 1950:
            return {
                "basis": "AB",
                "threshold": 300,
                "notes": "AB>=300 AND games>=100（両方の条件を満たす必要あり）",
                "source": source
            }
        elif year == 1951:
            return {
                "basis": "AB",
                "threshold": 280,
                "notes": "固定値",
                "source": source
            }
        elif year == 1952:
            return {
                "basis": "AB",
                "threshold": 300,
                "notes": "固定値",
                "source": source
            }
        elif year == 1953:
            return {
                "basis": "AB",
                "threshold": 325,
                "notes": "固定値",
                "source": source
            }
        elif year == 1954:
            return {
                "basis": "AB",
                "threshold": 338,
                "notes": "固定値",
                "source": source
            }
        elif year == 1955:
            return {
                "basis": "AB",
                "threshold": 335,
                "notes": "固定値",
                "source": source
            }
        elif year == 1956:
            return {
                "basis": "AB",
                "threshold": 338,
                "notes": "固定値",
                "source": source
            }
        elif year == 1957:
            if team_games is None:
                raise ValueError(f"{year}年{league}ではteam_gamesが必要です")
            return {
                "basis": "PA",
                "threshold": round_half_up(team_games * 3.1),
                "notes": f"PA>=round_half_up(team_games*3.1), team_games={team_games}の場合 threshold={round_half_up(team_games * 3.1)}",
                "source": source
            }
        elif year == 1958:
            return {
                "basis": "AB",
                "threshold": 400,
                "notes": "固定値（basis='AB'または'PA'でもよいが、threshold=400の固定値として扱う）",
                "source": source
            }
        elif year == 1959:
            if team_games is None:
                raise ValueError(f"{year}年{league}ではteam_gamesが必要です")
            return {
                "basis": "PA",
                "threshold": round_half_up(team_games * 3.1),
                "notes": f"PA>=round_half_up(team_games*3.1), team_games={team_games}の場合 threshold={round_half_up(team_games * 3.1)}",
                "source": source
            }
        else:
            raise ValueError(f"CL年で未対応の年度: {year}")
    
    # パ・リーグ（1950-1956）
    elif league == "PL":
        if year == 1950:
            return {
                "basis": "AB",
                "threshold": 300,
                "notes": "固定値",
                "source": source
            }
        elif year == 1951:
            if team_games is None:
                raise ValueError(f"{year}年{league}ではteam_gamesが必要です")
            threshold = round_half_up(team_games * 2.5)
            return {
                "basis": "AB",
                "threshold": threshold,
                "notes": f"AB>=round_half_up(team_games*2.5), team_games={team_games}の場合 threshold={threshold}",
                "source": source
            }
        elif year == 1952:
            if team_rank is None or teams_in_league is None:
                raise ValueError(f"{year}年{league}ではteam_rankとteams_in_leagueが必要です（上位4球団はAB>=300、下位3球団はAB>=270）")
            if team_rank <= 4:
                return {
                    "basis": "AB",
                    "threshold": 300,
                    "notes": f"上位4球団: AB>=300（team_rank={team_rank}）",
                    "source": source
                }
            else:
                return {
                    "basis": "AB",
                    "threshold": 270,
                    "notes": f"下位3球団: AB>=270（team_rank={team_rank}, teams_in_league={teams_in_league}）",
                    "source": source
                }
        elif year == 1953:
            return {
                "basis": "AB",
                "threshold": 300,
                "notes": "固定値",
                "source": source
            }
        elif year == 1954:
            return {
                "basis": "AB",
                "threshold": 360,
                "notes": "固定値",
                "source": source
            }
        elif year == 1955:
            return {
                "basis": "AB",
                "threshold": 360,
                "notes": "固定値",
                "source": source
            }
        elif year == 1956:
            return {
                "basis": "AB",
                "threshold": 400,
                "notes": "固定値",
                "source": source
            }
        elif year == 1957:
            if team_games is None:
                raise ValueError(f"{year}年{league}ではteam_gamesが必要です")
            return {
                "basis": "PA",
                "threshold": round_half_up(team_games * 3.1),
                "notes": f"PA>=round_half_up(team_games*3.1), team_games={team_games}の場合 threshold={round_half_up(team_games * 3.1)}",
                "source": source
            }
        elif year == 1958:
            return {
                "basis": "AB",
                "threshold": 400,
                "notes": "固定値（basis='AB'または'PA'でもよいが、threshold=400の固定値として扱う）",
                "source": source
            }
        elif year == 1959:
            if team_games is None:
                raise ValueError(f"{year}年{league}ではteam_gamesが必要です")
            return {
                "basis": "PA",
                "threshold": round_half_up(team_games * 3.1),
                "notes": f"PA>=round_half_up(team_games*3.1), team_games={team_games}の場合 threshold={round_half_up(team_games * 3.1)}",
                "source": source
            }
        else:
            raise ValueError(f"PL年で未対応の年度: {year}")
    
    else:
        raise ValueError(f"未対応のリーグ: {league}")


if __name__ == '__main__':
    # 簡易テスト
    print("規定到達条件テスト:")
    
    # 1940年PRE
    rule = get_batting_qual_rule(1940, "PRE")
    print(f"1940年PRE: {rule}")
    assert rule["basis"] == "AB" and rule["threshold"] == 250
    
    # 1949年PRE
    rule = get_batting_qual_rule(1949, "PRE")
    print(f"1949年PRE: {rule}")
    assert "games>=100" in rule["notes"]
    
    # 1951年PL
    rule = get_batting_qual_rule(1951, "PL", team_games=120)
    print(f"1951年PL (team_games=120): {rule}")
    expected = round_half_up(120 * 2.5)
    assert rule["threshold"] == expected
    
    # 1957年CL
    rule = get_batting_qual_rule(1957, "CL", team_games=130)
    print(f"1957年CL (team_games=130): {rule}")
    expected = round_half_up(130 * 3.1)
    assert rule["threshold"] == expected
    
    print("すべてのテストが成功しました！")


