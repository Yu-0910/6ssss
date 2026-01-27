#!/usr/bin/env python3
"""
add_qualifying_pa_flags.py

yearly_from_master_dedup を入力にして「規定打席フラグ付きCSV」と「規定到達者のみCSV」を生成するスクリプト

前提:
- qualifying_pa_table.csv が生成済み（year/season_key, team -> games, qual_pa）
- 打撃成績の入力は yearly_from_master_dedup のCSV群

出力:
- batting_with_qual_flag_1936_2025.csv: 全選手フラグ付き
- batting_qualified_only_1936_2025.csv: 規定到達者のみ
- qual_pa_missing_rows.csv: qual_paが引けない行（デバッグ用）
"""

import csv
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import argparse

# プロジェクトルートを取得
script_dir = Path(__file__).parent
project_root = script_dir.parent


# チーム名の正規化マッピング（yearly_from_master_dedup側と同じロジックに統一）
TEAM_ALIASES = {
    # セ・リーグ
    "読売ジャイアンツ": "読売ジャイアンツ",
    "巨人": "読売ジャイアンツ",
    "Yomiuri Giants": "読売ジャイアンツ",
    "阪神タイガース": "阪神タイガース",
    "阪神": "阪神タイガース",
    "Hanshin Tigers": "阪神タイガース",
    "中日ドラゴンズ": "中日ドラゴンズ",
    "中日": "中日ドラゴンズ",
    "名古屋ドラゴンズ": "中日ドラゴンズ",
    "Chunichi Dragons": "中日ドラゴンズ",
    "横浜DeNAベイスターズ": "横浜DeNAベイスターズ",
    "横浜": "横浜DeNAベイスターズ",
    "DeNA": "横浜DeNAベイスターズ",
    "Yokohama DeNA BayStars": "横浜DeNAベイスターズ",
    "広島東洋カープ": "広島東洋カープ",
    "広島": "広島東洋カープ",
    "Hiroshima Toyo Carp": "広島東洋カープ",
    "東京ヤクルトスワローズ": "東京ヤクルトスワローズ",
    "ヤクルト": "東京ヤクルトスワローズ",
    "Tokyo Yakult Swallows": "東京ヤクルトスワローズ",
    # パ・リーグ
    "オリックス・バファローズ": "オリックス・バファローズ",
    "オリックス": "オリックス・バファローズ",
    "Orix Buffaloes": "オリックス・バファローズ",
    "北海道日本ハムファイターズ": "北海道日本ハムファイターズ",
    "日本ハム": "北海道日本ハムファイターズ",
    "Hokkaido Nippon-Ham Fighters": "北海道日本ハムファイターズ",
    "東北楽天ゴールデンイーグルス": "東北楽天ゴールデンイーグルス",
    "楽天": "東北楽天ゴールデンイーグルス",
    "Tohoku Rakuten Golden Eagles": "東北楽天ゴールデンイーグルス",
    "埼玉西武ライオンズ": "埼玉西武ライオンズ",
    "西武": "埼玉西武ライオンズ",
    "Saitama Seibu Lions": "埼玉西武ライオンズ",
    "千葉ロッテマリーンズ": "千葉ロッテマリーンズ",
    "ロッテ": "千葉ロッテマリーンズ",
    "Chiba Lotte Marines": "千葉ロッテマリーンズ",
    "福岡ソフトバンクホークス": "福岡ソフトバンクホークス",
    "ソフトバンク": "福岡ソフトバンクホークス",
    "Fukuoka SoftBank Hawks": "福岡ソフトバンクホークス",
    # 戦前・その他
    "大東京軍": "大東京軍",
    "東京軍": "大東京軍",
    "名古屋軍": "名古屋軍",
    "大阪タイガース": "大阪タイガース",
    "阪急軍": "阪急軍",
    "阪急ブレーブス": "阪急ブレーブス",
    "阪急": "阪急ブレーブス",
    "東京セネタース": "東京セネタース",
    "セネタース": "東京セネタース",
    "名古屋金鯱軍": "名古屋金鯱軍",
    "金鯱": "名古屋金鯱軍",
    "イーグルス": "イーグルス",
    "ライオン軍": "ライオン軍",
    "ライオン": "ライオン軍",
    "翼軍": "翼軍",
    "グレートリング": "グレートリング",
    "黒鷲軍": "黒鷲軍",
    "黒鷲": "黒鷲軍",
    "南海軍": "南海軍",
    "南海ホークス": "南海ホークス",
    "南海": "南海ホークス",
    "西鉄軍": "西鉄軍",
    "西鉄ライオンズ": "西鉄ライオンズ",
    "西鉄": "西鉄ライオンズ",
    "東急フライヤーズ": "東急フライヤーズ",
    "東急": "東急フライヤーズ",
    "近鉄パールス": "近鉄パールス",
    "近鉄": "近鉄パールス",
    "大陽ロビンス": "大陽ロビンス",
    "太陽": "大陽ロビンス",
    "大映スターズ": "大映スターズ",
    "大映": "大映スターズ",
    "松竹ロビンス": "松竹ロビンス",
    "松竹": "松竹ロビンス",
    "毎日オリオンズ": "毎日オリオンズ",
    "毎日": "毎日オリオンズ",
    "高橋ユニオンズ": "高橋ユニオンズ",
    "高橋": "高橋ユニオンズ",
    "トンボユニオンズ": "トンボユニオンズ",
    "トンボ": "トンボユニオンズ",
    # 1952年PL: 現在のチーム名から1952年のチーム名へのマッピング
    # ロッテ（毎日オリオンズの後継）
    "千葉ロッテマリーンズ": "毎日オリオンズ",  # 1952年時点では毎日オリオンズ
    # 西武（西鉄ライオンズの後継）
    "埼玉西武ライオンズ": "西鉄ライオンズ",  # 1952年時点では西鉄ライオンズ
    # ソフトバンク（南海ホークスの後継）
    "福岡ソフトバンクホークス": "南海ホークス",  # 1952年時点では南海ホークス
    # オリックス（大映スターズの後継の一つ）
    "オリックス・バファローズ": "大映スターズ",  # 1952年時点では大映スターズ
    # 近鉄（近鉄パールスの後継）
    "近鉄バファローズ": "近鉄パールス",  # 1952年時点では近鉄パールス
    # 日本ハム（1952年には存在しないが、念のため）
    "北海道日本ハムファイターズ": "北海道日本ハムファイターズ",  # 1952年には存在しない
}


def normalize_team_name(team: str) -> str:
    """
    チーム名を正規化（yearly_from_master_dedup側と同じロジック）
    
    Args:
        team: 元のチーム名
        
    Returns:
        正規化されたチーム名（見つからない場合は元の名前をそのまま返す）
    """
    if not team:
        return ""
    
    team_trimmed = team.strip()
    if team_trimmed in TEAM_ALIASES:
        return TEAM_ALIASES[team_trimmed]
    
    # 見つからない場合は元の名前をそのまま返す
    return team_trimmed


def load_csv_with_encoding(csv_path: str) -> List[Dict[str, Any]]:
    """
    CSVファイルを読み込む（文字コード自動判定）
    
    Args:
        csv_path: CSVファイルのパス
        
    Returns:
        CSV行のリスト（辞書形式）
    """
    encodings = ['utf-8-sig', 'utf-8', 'shift_jis', 'cp932']
    
    for encoding in encodings:
        try:
            with open(csv_path, 'r', encoding=encoding) as f:
                reader = csv.DictReader(f)
                return list(reader)
        except (UnicodeDecodeError, FileNotFoundError):
            continue
    
    raise ValueError(f"Failed to read {csv_path} with any encoding")


def load_qual_pa_table(qual_table_path: Path) -> Dict[Tuple[str, str], Dict[str, Any]]:
    """
    qualifying_pa_table.csv を読み込んで辞書を作成
    
    Args:
        qual_table_path: qualifying_pa_table.csv のパス
        
    Returns:
        {(season_key, normalized_team): {games, qual_pa, source_url}} の辞書
    """
    if not qual_table_path.exists():
        raise FileNotFoundError(f"qualifying_pa_table.csv not found: {qual_table_path}")
    
    rows = load_csv_with_encoding(str(qual_table_path))
    
    qual_dict = {}
    for row in rows:
        season_key = row.get('season_key', '').strip()
        team = row.get('team', '').strip()
        normalized_team = normalize_team_name(team)
        
        games_str = row.get('games', '').strip()
        qual_pa_str = row.get('qual_pa', '').strip()
        source_url = row.get('source_url', '').strip()
        
        try:
            games = int(games_str) if games_str else None
            qual_pa = int(qual_pa_str) if qual_pa_str else None
        except ValueError:
            continue
        
        key = (season_key, normalized_team)
        qual_dict[key] = {
            'games': games,
            'qual_pa': qual_pa,
            'source_url': source_url
        }
    
    return qual_dict


def extract_season_key_from_filename(filename: str) -> Optional[str]:
    """
    ファイル名から season_key を推定
    
    Args:
        filename: CSVファイル名（例: "batting_2020_PL_from_master_dedup.csv", "batting_1936_SPRING_from_master_dedup.csv"）
        
    Returns:
        season_key（例: "PL", "CL", "1936s", "1936f" など）
        
    注意:
        - 1950年以降: season_key = "PL" or "CL"（リーグのみ）
        - 1936-1949: season_key = "1936s", "1936f" など（年度+シーズン区分）
    """
    # ファイル名から年度を抽出
    year_match = re.search(r'(\d{4})', filename)
    if not year_match:
        return None
    
    year = int(year_match.group(1))
    
    # 1950年以降: リーグのみを返す
    if year >= 1950:
        # リーグを抽出（PL, CL）
        league_match = re.search(r'_(PL|CL)_', filename, re.IGNORECASE)
        if league_match:
            league = league_match.group(1).upper()
            return league
        return None
    
    # 1936-1949: 年度+シーズン区分
    # シーズン区分を抽出（SPRING, FALL, UMBRELLA など）
    season_suffix_match = re.search(r'_(SPRING|FALL|UMBRELLA|s|f|u)_', filename, re.IGNORECASE)
    if season_suffix_match:
        suffix = season_suffix_match.group(1).upper()
        if suffix in ['SPRING', 'S']:
            return f"{year}s"
        elif suffix in ['FALL', 'F']:
            return f"{year}f"
        elif suffix in ['UMBRELLA', 'U']:
            return f"{year}u"
    
    # シーズン区分が無い場合は年度のみ
    return str(year)


def process_batting_csv(
    csv_path: Path,
    qual_dict: Dict[Tuple[str, str], Dict[str, Any]],
    missing_rows: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    打撃成績CSVを処理してフラグを付与
    
    Args:
        csv_path: 打撃成績CSVのパス
        qual_dict: qual_pa辞書
        missing_rows: 欠損行を追加するリスト
        
    Returns:
        フラグ付与後の行リスト
    """
    rows = load_csv_with_encoding(str(csv_path))
    
    # ファイル名から season_key を推定
    season_key = extract_season_key_from_filename(csv_path.name)
    if not season_key and rows:
        # CSV内の year/league 列から推定（フォールバック）
        first_row = rows[0]
        year_str = first_row.get('year', '').strip()
        league = first_row.get('league', '').strip().upper()
        season_col = first_row.get('season_key', '').strip()
        
        if season_col:
            season_key = season_col
        elif year_str and league:
            try:
                year = int(year_str)
                if year >= 1950:
                    if league in ['PL', 'CL']:
                        season_key = league
                else:
                    # 戦前: yearのみ、またはseason_suffixを探す
                    season_key = year_str
            except ValueError:
                pass
    
    result_rows = []
    
    for row in rows:
        # 必須列のチェック
        team = row.get('team', '').strip()
        pa_str = row.get('PA', '').strip() or row.get('pa', '').strip() or row.get('打席', '').strip()
        player_id = row.get('player_id', '').strip() or row.get('playerId', '').strip()
        name = row.get('player_name_ja', '').strip() or row.get('name', '').strip()
        
        if not team or not pa_str:
            # team または PA が無い場合はスキップ（ただし行は保持）
            new_row = row.copy()
            new_row['team_games'] = ''
            new_row['qual_pa'] = ''
            new_row['is_qualified'] = 'NA'
            result_rows.append(new_row)
            continue
        
        # PAを数値に変換
        try:
            pa = int(float(pa_str))
        except (ValueError, TypeError):
            pa = None
        
        # チーム名を正規化
        normalized_team = normalize_team_name(team)
        
        # qual_dictから取得
        key = (season_key, normalized_team)
        qual_info = qual_dict.get(key)
        
        if not qual_info:
            # 見つからない場合は欠損行に追加
            missing_rows.append({
                'season_key': season_key or '',
                'raw_team': team,
                'normalized_team': normalized_team,
                'player_id': player_id,
                'name': name,
                'PA': pa_str,
                'source_file': str(csv_path.name),
                'source_url': ''
            })
            
            # 行は保持（is_qualified は 'NA'）
            new_row = row.copy()
            new_row['team_games'] = ''
            new_row['qual_pa'] = ''
            new_row['is_qualified'] = 'NA'
            result_rows.append(new_row)
            continue
        
        # フラグを付与
        games = qual_info['games']
        qual_pa = qual_info['qual_pa']
        
        # is_qualified を計算（PA >= qual_pa）
        if pa is not None and qual_pa is not None:
            is_qualified = 1 if pa >= qual_pa else 0
        else:
            is_qualified = 'NA'
        
        new_row = row.copy()
        new_row['team_games'] = games if games is not None else ''
        new_row['qual_pa'] = qual_pa if qual_pa is not None else ''
        new_row['is_qualified'] = is_qualified
        result_rows.append(new_row)
    
    return result_rows


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description='規定打席フラグ付きCSVを生成')
    parser.add_argument('--input-dir', type=str, help='yearly_from_master_dedup のディレクトリパス')
    parser.add_argument('--qual-table', type=str, help='qualifying_pa_table.csv のパス')
    parser.add_argument('--output-dir', type=str, help='出力先ディレクトリ')
    parser.add_argument('--year', type=int, help='処理対象年度（指定した場合、その年度のみ処理）')
    parser.add_argument('--max-year', type=int, help='最大年度（指定した場合、その年度まで処理）')
    args = parser.parse_args()
    
    print("="*60)
    print("📊 規定打席フラグ付きCSV生成スクリプト")
    print("="*60)
    
    # パスを確定
    if args.input_dir:
        input_dir = Path(args.input_dir)
    else:
        # デフォルト: プロジェクトルートから探す
        input_dir = project_root / "yearly_from_master_dedup"
    
    if args.qual_table:
        qual_table_path = Path(args.qual_table)
    else:
        qual_table_path = project_root / "_data" / "qualifying_pa_table.csv"
    
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = project_root / "_data"
    
    print(f"\n📁 入力ディレクトリ: {input_dir}")
    print(f"📁 規定打席テーブル: {qual_table_path}")
    print(f"📁 出力ディレクトリ: {output_dir}")
    
    # ディレクトリの存在確認
    if not input_dir.exists():
        print(f"❌ エラー: 入力ディレクトリが見つかりません: {input_dir}")
        return 1
    
    if not qual_table_path.exists():
        print(f"❌ エラー: 規定打席テーブルが見つかりません: {qual_table_path}")
        return 1
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # STEP 1: qual_pa辞書を作成
    print(f"\n📖 規定打席テーブルを読み込み中...")
    qual_dict = load_qual_pa_table(qual_table_path)
    print(f"✅ {len(qual_dict)}件の規定打席データを読み込みました")
    
    # STEP 2: yearly_from_master_dedup を走査
    print(f"\n🔍 打撃成績CSVを走査中...")
    batting_csvs = list(input_dir.glob("batting_*.csv"))
    
    if args.year:
        # 指定年度のみ処理
        batting_csvs = [f for f in batting_csvs if str(args.year) in f.name]
    
    if args.max_year:
        # 最大年度まで処理
        batting_csvs = [f for f in batting_csvs if any(str(y) in f.name for y in range(1936, args.max_year + 1))]
    
    print(f"   処理対象: {len(batting_csvs)}ファイル")
    
    all_rows = []
    missing_rows = []
    
    for csv_path in sorted(batting_csvs):
        print(f"   📄 処理中: {csv_path.name}")
        rows = process_batting_csv(csv_path, qual_dict, missing_rows)
        all_rows.extend(rows)
    
    print(f"\n✅ {len(all_rows)}件の行を処理しました")
    print(f"⚠️  欠損行: {len(missing_rows)}件")
    
    # STEP 3: 出力
    print(f"\n📁 CSV出力中...")
    
    # A) 全選手フラグ付き
    output_path_all = output_dir / "batting_with_qual_flag_1936_2025.csv"
    print(f"   A) {output_path_all.name}")
    
    if all_rows:
        # 全列名を取得（元の列 + 追加列）
        all_fieldnames = set()
        for row in all_rows:
            all_fieldnames.update(row.keys())
        
        # 順序を保持（元の列の順序 + 追加列）
        if all_rows:
            original_fields = list(all_rows[0].keys())
            new_fields = ['team_games', 'qual_pa', 'is_qualified']
            fieldnames = [f for f in original_fields if f not in new_fields] + new_fields
            # 残りの列も追加
            for f in all_fieldnames:
                if f not in fieldnames:
                    fieldnames.append(f)
        else:
            fieldnames = sorted(all_fieldnames)
        
        with open(output_path_all, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_rows)
    else:
        # 空のCSVを出力
        with open(output_path_all, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['team_games', 'qual_pa', 'is_qualified'])
            writer.writeheader()
    
    # B) 規定到達者のみ
    output_path_qualified = output_dir / "batting_qualified_only_1936_2025.csv"
    print(f"   B) {output_path_qualified.name}")
    
    qualified_rows = [row for row in all_rows if row.get('is_qualified') == 1]
    
    if qualified_rows:
        with open(output_path_qualified, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(qualified_rows)
        print(f"      ✅ {len(qualified_rows)}件の規定到達者を出力しました")
    else:
        # 空のCSVを出力
        with open(output_path_qualified, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames if all_rows else ['team_games', 'qual_pa', 'is_qualified'])
            writer.writeheader()
        print(f"      ⚠️  規定到達者が0件です")
    
    # C) 欠損行ログ
    output_path_missing = output_dir / "qual_pa_missing_rows.csv"
    print(f"   C) {output_path_missing.name}")
    
    if missing_rows:
        with open(output_path_missing, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['season_key', 'raw_team', 'normalized_team', 'player_id', 'name', 'PA', 'source_file', 'source_url'])
            writer.writeheader()
            writer.writerows(missing_rows)
        print(f"      ⚠️  {len(missing_rows)}件の欠損行を出力しました")
    else:
        # 空のCSVを出力
        with open(output_path_missing, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['season_key', 'raw_team', 'normalized_team', 'player_id', 'name', 'PA', 'source_file', 'source_url'])
            writer.writeheader()
        print(f"      ✅ 欠損行なし")
    
    # STEP 4: 検証ログ
    print(f"\n🧪 検証ログ")
    print("="*60)
    
    # 2020 PL: qual_pa=372 が適用されている行をサンプル出力
    test_2020_pl = [row for row in all_rows if row.get('qual_pa') == '372' and '2020' in str(row.get('year', ''))]
    if test_2020_pl:
        print(f"\n✅ 2020年 PL (qual_pa=372) のサンプル:")
        for i, row in enumerate(test_2020_pl[:3]):
            name = row.get('player_name_ja', '') or row.get('name', '')
            team = row.get('team', '')
            pa = row.get('PA', '') or row.get('pa', '')
            is_qualified = row.get('is_qualified', '')
            print(f"   {i+1}. {name} ({team}): PA={pa}, is_qualified={is_qualified}")
    else:
        print(f"\n⚠️  2020年 PL (qual_pa=372) の行が見つかりません")
    
    # missing_rows 件数と上位の raw_team を集計
    if missing_rows:
        from collections import Counter
        team_counter = Counter([row['raw_team'] for row in missing_rows if row['raw_team']])
        print(f"\n⚠️  欠損行の上位チーム:")
        for team, count in team_counter.most_common(10):
            print(f"   - {team}: {count}件")
    
    print("\n" + "="*60)
    print(f"✅ 完了: {len(all_rows)}件のデータを処理しました")
    print(f"   - 全選手フラグ付き: {output_path_all}")
    print(f"   - 規定到達者のみ: {output_path_qualified}")
    print(f"   - 欠損行ログ: {output_path_missing}")
    print("="*60)
    
    return 0 if len(missing_rows) == 0 else 1


if __name__ == '__main__':
    exit(main())


