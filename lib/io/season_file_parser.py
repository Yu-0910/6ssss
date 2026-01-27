"""
ファイル名パース関数（batting CSV用）

戦前の春秋シーズンCSVと通常のfrom_master CSVの両方をサポート
"""
import re
from typing import Optional, Dict, Any


def parse_batting_filename(filename: str) -> Optional[Dict[str, Any]]:
    """
    batting CSVファイル名をパース
    
    @param filename: ファイル名（例: "batting_2025_PL_from_master.csv" または "batting_1936_spring_PRE.csv"）
    @returns: パース結果の辞書、またはNone（パース失敗時）
    
    返却値の構造:
    {
        "year": int,                    # 年度（例: 1936, 2025）
        "league": str,                  # リーグ（"PL"|"CL"|"PRE"）
        "league_key": str,              # 出力用リーグキー（"PL"|"CL"|"PRE"|"PRE_spring"|"PRE_fall"）
        "season_tag": Optional[str],    # シーズンタグ（None|"spring"|"fall"）
        "kind": str                     # 種類（"from_master"|"pre_season"）
    }
    """
    # パターン1: 正規（from_master）
    # batting_YYYY_(PL|CL|PRE)_from_master.csv
    pattern1 = r'^batting_(\d{4})_(PL|CL|PRE)_from_master\.csv$'
    match1 = re.match(pattern1, filename)
    if match1:
        year = int(match1.group(1))
        league = match1.group(2)
        return {
            "year": year,
            "league": league,
            "league_key": league,
            "season_tag": None,
            "kind": "from_master"
        }
    
    # パターン2: 戦前春秋シーズン
    # batting_YYYY_(spring|fall)_PRE.csv
    pattern2 = r'^batting_(\d{4})_(spring|fall)_PRE\.csv$'
    match2 = re.match(pattern2, filename)
    if match2:
        year = int(match2.group(1))
        season_tag = match2.group(2)  # "spring" or "fall"
        league = "PRE"
        league_key = f"PRE_{season_tag}"
        return {
            "year": year,
            "league": league,
            "league_key": league_key,
            "season_tag": season_tag,
            "kind": "pre_season"
        }
    
    # パターンに一致しない
    return None


def build_calculated_filename(parsed: Dict[str, Any]) -> str:
    """
    パース結果から計算済みCSVのファイル名を生成
    
    @param parsed: parse_batting_filename()の結果
    @returns: 計算済みCSVのファイル名
    
    例:
    - 入力: batting_2025_PL_from_master.csv
      出力: batting_2025_PL_from_master.csv（そのまま）
    
    - 入力: batting_1936_spring_PRE.csv
      出力: batting_1936_PRE_spring_from_master.csv
    """
    year = parsed["year"]
    league_key = parsed["league_key"]
    
    if parsed["kind"] == "from_master":
        # 既存命名はそのまま
        return f"batting_{year}_{parsed['league']}_from_master.csv"
    else:
        # 戦前春秋: league_key を使って "from_master" 形式に統一
        return f"batting_{year}_{league_key}_from_master.csv"


def build_rankings_output_path(year: int, league_key: str) -> str:
    """
    ランキングJSONの出力パス（相対パス）を生成
    
    @param year: 年度
    @param league_key: リーグキー（"PL"|"CL"|"PRE"|"PRE_spring"|"PRE_fall"）
    @returns: 出力パス（例: "1936/PRE_spring"）
    """
    return f"{year}/{league_key}"


















