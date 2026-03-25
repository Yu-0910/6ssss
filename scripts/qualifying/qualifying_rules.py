#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
qualifying_rules.py

1936-2025年の「規定到達者（打撃）」ルールを定義・管理するモジュール

参考URL: https://www.my-favorite-giants.net/npb/regulation.htm
"""

from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Dict, Optional, Set, Any


class QualifyingBasis(Enum):
    """規定到達の基準"""
    AB_FIXED = "AB_FIXED"  # 規定打数が固定値
    AB_TEAMGAMES_MULT = "AB_TEAMGAMES_MULT"  # 規定打数 = team_games * multiplier
    PA_TEAMGAMES_MULT = "PA_TEAMGAMES_MULT"  # 規定打席 = team_games * 3.1（基本）
    PA_FIXED = "PA_FIXED"  # 規定打席が固定値（1958=400）
    AB_TEAM_GROUP = "AB_TEAM_GROUP"  # チーム群で規定打数が分岐（1952PLなど）


def round_half_up(x: float) -> int:
    """
    NPB想定の「四捨五入(half-up)」を明示実装（decimal使用で銀行丸めを避ける）
    """
    d = Decimal(str(x))
    return int(d.quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def get_rounding_mode(year: int) -> str:
    """
    年度に応じた端数処理モードを返す
    
    Returns:
        "floor": 2008年まで（小数点以下切り捨て）
        "round_half_up": 2009年以降（四捨五入・0.5は切り上げ）
    """
    if year <= 2008:
        return "floor"
    else:
        return "round_half_up"


def apply_rounding(value: float, rounding_mode: str) -> int:
    """
    端数処理を適用
    
    Args:
        value: 処理する値
        rounding_mode: "floor" または "round_half_up"
    
    Returns:
        処理後の整数値
    """
    if rounding_mode == "floor":
        return int(value)
    elif rounding_mode == "round_half_up":
        return round_half_up(value)
    else:
        raise ValueError(f"Unknown rounding_mode: {rounding_mode}")


# 1952年PLのチーム群定義
PL_1952_TOP4_TEAMS: Set[str] = {
    "南海ホークス",
    "毎日オリオンズ",
    "西鉄ライオンズ",
    "大映スターズ"
}


def get_qualifying_rule(year: int, league: str, season_code: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    年度・リーグ・シーズンコードから規定到達ルールを取得
    
    Args:
        year: 年度
        league: リーグ（"PRE", "CL", "PL"）
        season_code: シーズンコード（"1936s", "1936f"など、戦前の春秋シーズン用）
    
    Returns:
        ルール辞書、またはNone（1945年など規定なしの場合）
        {
            "basis": QualifyingBasis,
            "threshold": int | None,  # 固定値の場合
            "multiplier": float | None,  # team_games * multiplier の場合
            "team_groups": Dict[str, int] | None,  # AB_TEAM_GROUP の場合
            "min_player_games": int | None,  # 追加条件（選手試合数）
            "special_measures": bool,  # 特別措置フラグ（2004, 2008など）
            "rule_source": str
        }
    """
    rule_source = "my-favorite-giants (npb/regulation.htm) + user supplied 1936-1938 split AB"
    rounding_mode = get_rounding_mode(year)
    
    # 1リーグ時代（PRE）
    if league == "PRE":
        if year == 1936:
            if season_code == "1936s":
                # 1936s（春）は規定なしまたは未定義の可能性があるが、暫定的に1936fと同じルールを適用
                # 実際のデータに基づいて調整が必要
                return {
                    "basis": QualifyingBasis.AB_FIXED,
                    "threshold": 55,
                    "multiplier": None,
                    "team_groups": None,
                    "min_player_games": None,
                    "special_measures": False,
                    "rule_source": rule_source,
                    "rounding_mode": rounding_mode
                }
            elif season_code == "1936f":
                return {
                    "basis": QualifyingBasis.AB_FIXED,
                    "threshold": 55,
                    "multiplier": None,
                    "team_groups": None,
                    "min_player_games": None,
                    "special_measures": False,
                    "rule_source": rule_source,
                    "rounding_mode": rounding_mode
                }
            else:
                # season_codeが指定されていない場合はNoneを返す
                return None
        elif year == 1937:
            if season_code == "1937s":
                return {
                    "basis": QualifyingBasis.AB_FIXED,
                    "threshold": 101,
                    "multiplier": None,
                    "team_groups": None,
                    "min_player_games": None,
                    "special_measures": False,
                    "rule_source": rule_source,
                    "rounding_mode": rounding_mode
                }
            elif season_code == "1937f":
                return {
                    "basis": QualifyingBasis.AB_FIXED,
                    "threshold": 100,
                    "multiplier": None,
                    "team_groups": None,
                    "min_player_games": None,
                    "special_measures": False,
                    "rule_source": rule_source,
                    "rounding_mode": rounding_mode
                }
            else:
                return None
        elif year == 1938:
            if season_code == "1938s":
                return {
                    "basis": QualifyingBasis.AB_FIXED,
                    "threshold": 101,
                    "multiplier": None,
                    "team_groups": None,
                    "min_player_games": None,
                    "special_measures": False,
                    "rule_source": rule_source,
                    "rounding_mode": rounding_mode
                }
            elif season_code == "1938f":
                return {
                    "basis": QualifyingBasis.AB_FIXED,
                    "threshold": 100,
                    "multiplier": None,
                    "team_groups": None,
                    "min_player_games": None,
                    "special_measures": False,
                    "rule_source": rule_source,
                    "rounding_mode": rounding_mode
                }
            else:
                return None
        elif year == 1939:
            return {
                "basis": QualifyingBasis.AB_FIXED,
                "threshold": 200,
                "multiplier": None,
                "team_groups": None,
                "min_player_games": None,
                "special_measures": False,
                "rule_source": rule_source,
                "rounding_mode": rounding_mode
            }
        elif year == 1940:
            return {
                "basis": QualifyingBasis.AB_FIXED,
                "threshold": 250,
                "multiplier": None,
                "team_groups": None,
                "min_player_games": None,
                "special_measures": False,
                "rule_source": rule_source,
                "rounding_mode": rounding_mode
            }
        elif year == 1941:
            return {
                "basis": QualifyingBasis.AB_FIXED,
                "threshold": 201,
                "multiplier": None,
                "team_groups": None,
                "min_player_games": None,
                "special_measures": False,
                "rule_source": rule_source,
                "rounding_mode": rounding_mode
            }
        elif year == 1942:
            return {
                "basis": QualifyingBasis.AB_FIXED,
                "threshold": 300,
                "multiplier": None,
                "team_groups": None,
                "min_player_games": None,
                "special_measures": False,
                "rule_source": rule_source,
                "rounding_mode": rounding_mode
            }
        elif year == 1943:
            return {
                "basis": QualifyingBasis.AB_FIXED,
                "threshold": 240,
                "multiplier": None,
                "team_groups": None,
                "min_player_games": None,
                "special_measures": False,
                "rule_source": rule_source,
                "rounding_mode": rounding_mode
            }
        elif year == 1944:
            return {
                "basis": QualifyingBasis.AB_FIXED,
                "threshold": 100,
                "multiplier": None,
                "team_groups": None,
                "min_player_games": None,
                "special_measures": False,
                "rule_source": rule_source,
                "rounding_mode": rounding_mode
            }
        elif year == 1945:
            # 開催なし
            return None
        elif year == 1946:
            return {
                "basis": QualifyingBasis.AB_FIXED,
                "threshold": 300,
                "multiplier": None,
                "team_groups": None,
                "min_player_games": None,
                "special_measures": False,
                "rule_source": rule_source,
                "rounding_mode": rounding_mode
            }
        elif year == 1947:
            return {
                "basis": QualifyingBasis.AB_FIXED,
                "threshold": 330,
                "multiplier": None,
                "team_groups": None,
                "min_player_games": None,
                "special_measures": False,
                "rule_source": rule_source,
                "rounding_mode": rounding_mode
            }
        elif year == 1948:
            return {
                "basis": QualifyingBasis.AB_FIXED,
                "threshold": 400,
                "multiplier": None,
                "team_groups": None,
                "min_player_games": None,
                "special_measures": False,
                "rule_source": rule_source,
                "rounding_mode": rounding_mode
            }
        elif year == 1949:
            return {
                "basis": QualifyingBasis.AB_FIXED,
                "threshold": 300,
                "multiplier": None,
                "team_groups": None,
                "min_player_games": 100,
                "special_measures": False,
                "rule_source": rule_source,
                "rounding_mode": rounding_mode
            }
        else:
            raise ValueError(f"PRE年で未対応の年度: {year}")
    
    # セ・リーグ（1950-2025）
    elif league == "CL":
        if year == 1950:
            return {
                "basis": QualifyingBasis.AB_FIXED,
                "threshold": 300,
                "multiplier": None,
                "team_groups": None,
                "min_player_games": 100,
                "special_measures": False,
                "rule_source": rule_source,
                "rounding_mode": rounding_mode
            }
        elif year == 1951:
            return {
                "basis": QualifyingBasis.AB_FIXED,
                "threshold": 280,
                "multiplier": None,
                "team_groups": None,
                "min_player_games": None,
                "special_measures": False,
                "rule_source": rule_source,
                "rounding_mode": rounding_mode
            }
        elif year == 1952:
            return {
                "basis": QualifyingBasis.AB_FIXED,
                "threshold": 300,
                "multiplier": None,
                "team_groups": None,
                "min_player_games": None,
                "special_measures": False,
                "rule_source": rule_source,
                "rounding_mode": rounding_mode
            }
        elif year == 1953:
            return {
                "basis": QualifyingBasis.AB_FIXED,
                "threshold": 325,
                "multiplier": None,
                "team_groups": None,
                "min_player_games": None,
                "special_measures": False,
                "rule_source": rule_source,
                "rounding_mode": rounding_mode
            }
        elif year == 1954:
            return {
                "basis": QualifyingBasis.AB_FIXED,
                "threshold": 338,
                "multiplier": None,
                "team_groups": None,
                "min_player_games": None,
                "special_measures": False,
                "rule_source": rule_source,
                "rounding_mode": rounding_mode
            }
        elif year == 1955:
            return {
                "basis": QualifyingBasis.AB_FIXED,
                "threshold": 335,
                "multiplier": None,
                "team_groups": None,
                "min_player_games": None,
                "special_measures": False,
                "rule_source": rule_source,
                "rounding_mode": rounding_mode
            }
        elif year == 1956:
            return {
                "basis": QualifyingBasis.AB_FIXED,
                "threshold": 338,
                "multiplier": None,
                "team_groups": None,
                "min_player_games": None,
                "special_measures": False,
                "rule_source": rule_source,
                "rounding_mode": rounding_mode
            }
        elif year == 1957:
            return {
                "basis": QualifyingBasis.PA_TEAMGAMES_MULT,
                "threshold": None,
                "multiplier": 3.1,
                "team_groups": None,
                "min_player_games": None,
                "special_measures": False,
                "rule_source": rule_source,
                "rounding_mode": rounding_mode
            }
        elif year == 1958:
            return {
                "basis": QualifyingBasis.PA_FIXED,
                "threshold": 400,
                "multiplier": None,
                "team_groups": None,
                "min_player_games": None,
                "special_measures": False,
                "rule_source": rule_source,
                "rounding_mode": rounding_mode
            }
        # 1959-2025: 規定打席 = チーム試合数 × 3.1（2025年は2024年以前と同じルールで踏襲）
        elif 1959 <= year <= 2025:
            special_measures = (year == 2004 or year == 2008)
            return {
                "basis": QualifyingBasis.PA_TEAMGAMES_MULT,
                "threshold": None,
                "multiplier": 3.1,
                "team_groups": None,
                "min_player_games": None,
                "special_measures": special_measures,
                "rule_source": rule_source,
                "rounding_mode": rounding_mode
            }
        else:
            raise ValueError(f"CL年で未対応の年度: {year}")
    
    # パ・リーグ（1950-2025）
    elif league == "PL":
        if year == 1950:
            return {
                "basis": QualifyingBasis.AB_FIXED,
                "threshold": 300,
                "multiplier": None,
                "team_groups": None,
                "min_player_games": None,
                "special_measures": False,
                "rule_source": rule_source,
                "rounding_mode": rounding_mode
            }
        elif year == 1951:
            return {
                "basis": QualifyingBasis.AB_TEAMGAMES_MULT,
                "threshold": None,
                "multiplier": 2.5,
                "team_groups": None,
                "min_player_games": None,
                "special_measures": False,
                "rule_source": rule_source,
                "rounding_mode": rounding_mode
            }
        elif year == 1952:
            return {
                "basis": QualifyingBasis.AB_TEAM_GROUP,
                "threshold": None,
                "multiplier": None,
                "team_groups": {
                    "top4": 300,  # 上位4球団
                    "else": 270,  # 下位3球団
                    "teams_top4": list(PL_1952_TOP4_TEAMS)  # チーム名リスト（オプション）
                },
                "min_player_games": None,
                "special_measures": False,
                "rule_source": rule_source,
                "rounding_mode": rounding_mode
            }
        elif year == 1953:
            return {
                "basis": QualifyingBasis.AB_FIXED,
                "threshold": 300,
                "multiplier": None,
                "team_groups": None,
                "min_player_games": None,
                "special_measures": False,
                "rule_source": rule_source,
                "rounding_mode": rounding_mode
            }
        elif year == 1954:
            return {
                "basis": QualifyingBasis.AB_FIXED,
                "threshold": 360,
                "multiplier": None,
                "team_groups": None,
                "min_player_games": None,
                "special_measures": False,
                "rule_source": rule_source,
                "rounding_mode": rounding_mode
            }
        elif year == 1955:
            return {
                "basis": QualifyingBasis.AB_FIXED,
                "threshold": 360,
                "multiplier": None,
                "team_groups": None,
                "min_player_games": None,
                "special_measures": False,
                "rule_source": rule_source,
                "rounding_mode": rounding_mode
            }
        elif year == 1956:
            return {
                "basis": QualifyingBasis.AB_FIXED,
                "threshold": 400,
                "multiplier": None,
                "team_groups": None,
                "min_player_games": None,
                "special_measures": False,
                "rule_source": rule_source,
                "rounding_mode": rounding_mode
            }
        elif year == 1957:
            return {
                "basis": QualifyingBasis.PA_TEAMGAMES_MULT,
                "threshold": None,
                "multiplier": 3.1,
                "team_groups": None,
                "min_player_games": None,
                "special_measures": False,
                "rule_source": rule_source,
                "rounding_mode": rounding_mode
            }
        elif year == 1958:
            return {
                "basis": QualifyingBasis.PA_FIXED,
                "threshold": 400,
                "multiplier": None,
                "team_groups": None,
                "min_player_games": None,
                "special_measures": False,
                "rule_source": rule_source,
                "rounding_mode": rounding_mode
            }
        # 1959-2025: 規定打席 = チーム試合数 × 3.1（2025年は2024年以前と同じルールで踏襲）
        elif 1959 <= year <= 2025:
            special_measures = (year == 2004 or year == 2008)
            return {
                "basis": QualifyingBasis.PA_TEAMGAMES_MULT,
                "threshold": None,
                "multiplier": 3.1,
                "team_groups": None,
                "min_player_games": None,
                "special_measures": special_measures,
                "rule_source": rule_source,
                "rounding_mode": rounding_mode
            }
        else:
            raise ValueError(f"PL年で未対応の年度: {year}")
    
    else:
        raise ValueError(f"未対応のリーグ: {league}")


def calc_qual_threshold(
    rule: Dict[str, Any],
    team_games: int,
    team_name: Optional[str] = None,
    rounding: Optional[str] = None
) -> Optional[int]:
    """
    ルールとチーム情報から規定到達しきい値を計算
    
    Args:
        rule: get_qualifying_rule() で取得したルール辞書
        team_games: チーム試合数
        team_name: チーム名（AB_TEAM_GROUP の場合に必要）
        rounding: 端数処理モード（Noneの場合はruleから取得）
    
    Returns:
        規定到達しきい値（AB_TEAM_GROUP で team_name が None の場合は None）
    """
    if rule is None:
        raise ValueError("rule is None")
    
    basis = rule["basis"]
    rounding_mode = rounding or rule.get("rounding_mode", "round_half_up")
    
    if basis == QualifyingBasis.AB_FIXED or basis == QualifyingBasis.PA_FIXED:
        return rule["threshold"]
    
    elif basis == QualifyingBasis.AB_TEAMGAMES_MULT or basis == QualifyingBasis.PA_TEAMGAMES_MULT:
        multiplier = rule["multiplier"]
        value = team_games * multiplier
        return apply_rounding(value, rounding_mode)
    
    elif basis == QualifyingBasis.AB_TEAM_GROUP:
        if team_name is None:
            print(f"   [WARNING] AB_TEAM_GROUP で team_name が None のため、しきい値を計算できません（スキップ可能）")
            return None
        
        team_groups = rule["team_groups"]
        
        # team_groups に teams_top4 キーがある場合はそれを使用
        if "teams_top4" in team_groups:
            teams_top4 = set(team_groups["teams_top4"])
            if team_name in teams_top4:
                return team_groups["top4"]
            else:
                return team_groups["else"]
        else:
            # フォールバック: PL_1952_TOP4_TEAMS を使用
            if team_name in PL_1952_TOP4_TEAMS:
                return team_groups["top4"]
            else:
                return team_groups["else"]
    
    else:
        raise ValueError(f"Unknown basis: {basis}")


def is_player_qualified(
    player_row: Dict[str, Any],
    threshold: int,
    basis: QualifyingBasis,
    min_player_games: Optional[int] = None
) -> bool:
    """
    選手が規定到達者かどうかを判定
    
    Args:
        player_row: 選手データ行（"PA", "AB", "G" などのキーを持つ）
        threshold: 規定到達しきい値
        basis: 規定到達の基準
        min_player_games: 最小選手試合数（追加条件）
    
    Returns:
        True: 規定到達者、False: 非到達者
    """
    # 基本条件チェック
    if basis in [QualifyingBasis.AB_FIXED, QualifyingBasis.AB_TEAMGAMES_MULT, QualifyingBasis.AB_TEAM_GROUP]:
        ab_raw = player_row.get("AB") or player_row.get("ab") or 0
        # 文字列の場合は数値に変換
        try:
            ab = int(float(ab_raw)) if ab_raw else 0
        except (ValueError, TypeError):
            ab = 0
        if ab < threshold:
            return False
    elif basis in [QualifyingBasis.PA_FIXED, QualifyingBasis.PA_TEAMGAMES_MULT]:
        pa_raw = player_row.get("PA") or player_row.get("pa") or 0
        # 文字列の場合は数値に変換
        try:
            pa = int(float(pa_raw)) if pa_raw else 0
        except (ValueError, TypeError):
            pa = 0
        if pa < threshold:
            return False
    else:
        raise ValueError(f"Unknown basis: {basis}")
    
    # 追加条件チェック（min_player_games）
    if min_player_games is not None:
        games_raw = player_row.get("G") or player_row.get("games") or player_row.get("Games") or 0
        # 文字列の場合は数値に変換
        try:
            games = int(float(games_raw)) if games_raw else 0
        except (ValueError, TypeError):
            games = 0
        if games < min_player_games:
            return False
    
    return True


