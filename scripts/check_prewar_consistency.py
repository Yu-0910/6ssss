#!/usr/bin/env python3
# -*- coding: utf-8 -*-
print("CHECK_PREWAR: TOP OF FILE reached")

"""
check_prewar_consistency.py

_data/qualifying_pa_table.csv の戦前(PRE, year<1950)について、
「年内でチームごとのgamesが揃わない年」を自動で抽出し、
検証しやすいレポートを出力するスクリプト

【設計判断メモ】

1. diff != 0 の年の扱いについて:
   
   【仕様として許容】
   - 1936-1938: 春/秋シーズン制のため、年内でgamesが異なるのは仕様として許容
     - 1936s: 5-8試合（春シーズン、diff=3）
     - 1936f: 26-31試合（秋シーズン、diff=5）
     - 1937s: 56試合（全チーム一致、diff=0）
     - 1937f: 48-49試合（1試合差、diff=1）
     - 1938s: 35試合（全チーム一致、diff=0）
     - 1938f: 40試合（全チーム一致、diff=0）
     → season_key単位で処理するため、年内で揃っていなくても問題なし
   
   【要補正の可能性あり（史実確認が必要）】
   - 1940: 104-105試合（1試合差、diff=1）
     - 翼・南海が105試合、他7球団が104試合
     - 史実として1試合差がある可能性もあるが、データ取得ミスの可能性も
   - 1941: 84-87試合（3試合差、diff=3）
     - 大洋87試合、東京巨人86試合、他3球団85試合、他3球団84試合
     - 戦時中のため試合数が不安定だった可能性
   - 1949: 133-138試合（5試合差、diff=5）
     - 東急フライヤーズ138試合、中日・大阪タイガース137試合、他5球団133-136試合
     - リーグ再編期のため試合数が不安定だった可能性

2. PRE年（1936-1949）のgamesの扱い:
   
   【年内で揃っていることを必須とするか】
   - 1936-1938: 春/秋シーズン制のため、年内で揃っていないのは仕様として許容
   - 1939, 1942-1944, 1946-1948: 原則gamesが揃っている（diff=0）→ 必須とする
   - 1940, 1941, 1949: 例外として許容するか、要補正かは史実確認が必要
   
   【例外（戦前・戦時）として許容するか】
   - 1940, 1941: 戦時中のため、試合数のばらつきは許容範囲内の可能性
   - 1949: リーグ再編期のため、試合数のばらつきは許容範囲内の可能性
   - ただし、データ取得ミスの可能性も否定できないため、史実確認が推奨される

3. 将来のランキング計算での扱い:
   
   【推奨アプローチ】
   - 1936-1938: season_key単位で処理するため問題なし（現状の実装で対応済み）
   - 1940, 1941, 1949: 
     a) 警告ログを出し、最小値または最大値で正規化する
     b) または、該当チームを除外する
     c) または、史実に基づいて補正する（推奨）
   
   【実装方針】
   - 警告ログのみ: 最小限の対応、データの整合性は保たれるが差異は残る
   - 正規化（最小値/最大値/平均値）: 統計的な整合性は保たれるが、史実から乖離する可能性
   - 除外: データの整合性は保たれるが、該当チームのデータが使えなくなる
   - 補正（推奨）: 史実に基づいて修正するため、最も正確だが手作業が必要
"""

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

# Windows(cp932)で落ちないようにUTF-8に設定
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except (AttributeError, ValueError):
        pass  # Python 3.7以下や設定できない環境ではスキップ

# プロジェクトルートを取得
script_dir = Path(__file__).parent
project_root = script_dir.parent


def load_qualifying_pa_table(csv_path: Path) -> List[Dict[str, Any]]:
    """qualifying_pa_table.csvを読み込む"""
    data = []
    encodings = ['utf-8-sig', 'utf-8', 'shift_jis', 'cp932']
    
    for encoding in encodings:
        try:
            with open(csv_path, 'r', encoding=encoding) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # yearをintに変換
                    try:
                        row['year'] = int(row['year'])
                    except (ValueError, KeyError):
                        continue
                    data.append(row)
            return data
        except (UnicodeDecodeError, FileNotFoundError):
            continue
    
    raise ValueError(f"Failed to read {csv_path} with any encoding")


def analyze_prewar_consistency(data: List[Dict[str, Any]]) -> Tuple[Dict[int, Dict[str, Any]], Dict[int, List[Dict[str, Any]]], Dict[str, Dict[str, Any]], Dict[int, Dict[str, Any]], Dict[int, List[Dict[str, Any]]], Dict[int, List[str]]]:
    """
    戦前データの一貫性を分析
    
    Returns:
        (year_summary, inconsistent_data, season_key_summary, suspects_summary, deviations, source_urls)
        - year_summary: {year: {teams, min_games, max_games, diff, mean_games}}
        - inconsistent_data: {year: [{year, season_key, team, games}, ...]}
        - season_key_summary: {season_key: {teams, min_games, max_games, diff, mean_games}} (1936/1937/1938のみ)
        - suspects_summary: {year: {teams, min_games, max_games, diff, mode_games, mode_count, deviations_count}} (1936-1938を除外)
        - deviations: {year: [{year, team, games, mode_games, delta}, ...]} (1936-1938を除外)
        - source_urls: {year: [url, ...]} (unique source_urls per year)
    """
    # year<1950のデータを抽出
    prewar_data = [row for row in data if row['year'] < 1950]
    
    # 年ごとにデータを集計
    year_data = defaultdict(list)  # {year: [{season_key, team, games, source_url}, ...]}
    
    for row in prewar_data:
        year = row['year']
        try:
            games = int(row['games'])
            year_data[year].append({
                'season_key': row.get('season_key', ''),
                'team': row.get('team', ''),
                'games': games,
                'source_url': row.get('source_url', '')
            })
        except (ValueError, KeyError):
            continue
    
    # 年別サマリを計算
    year_summary = {}  # {year: {teams, min_games, max_games, diff, mean_games}}
    inconsistent_data = defaultdict(list)  # {year: [{year, season_key, team, games}, ...]}
    
    for year, rows in year_data.items():
        if not rows:
            continue
        
        games_list = [r['games'] for r in rows]
        min_games = min(games_list)
        max_games = max(games_list)
        diff = max_games - min_games
        mean_games = sum(games_list) / len(games_list) if games_list else 0
        teams = len(rows)
        
        year_summary[year] = {
            'teams': teams,
            'min_games': min_games,
            'max_games': max_games,
            'diff': diff,
            'mean_games': round(mean_games, 2)
        }
        
        # diff != 0の年の詳細データを収集
        if diff != 0:
            for row in rows:
                inconsistent_data[year].append({
                    'year': year,
                    'season_key': row['season_key'],
                    'team': row['team'],
                    'games': row['games']
                })
            
            # games降順でソート
            inconsistent_data[year].sort(key=lambda x: x['games'], reverse=True)
    
    # 1936/1937/1938のseason_key別統計
    season_key_summary = {}  # {season_key: {teams, min_games, max_games, diff, mean_games}}
    
    for year in [1936, 1937, 1938]:
        season_key_data = defaultdict(list)  # {season_key: [{team, games}, ...]}
        
        for row in prewar_data:
            if row['year'] == year:
                season_key = row.get('season_key', '')
                if not season_key:
                    continue
                
                try:
                    games = int(row['games'])
                    season_key_data[season_key].append({
                        'team': row.get('team', ''),
                        'games': games
                    })
                except (ValueError, KeyError):
                    continue
        
        for season_key, rows in season_key_data.items():
            if not rows:
                continue
            
            games_list = [r['games'] for r in rows]
            min_games = min(games_list)
            max_games = max(games_list)
            diff = max_games - min_games
            mean_games = sum(games_list) / len(games_list) if games_list else 0
            teams = len(rows)
            
            season_key_summary[season_key] = {
                'teams': teams,
                'min_games': min_games,
                'max_games': max_games,
                'diff': diff,
                'mean_games': round(mean_games, 2)
            }
    
    # diff != 0 の年（1936-1938を除外）について、mode計算とdeviation抽出
    suspects_summary = {}  # {year: {teams, min_games, max_games, diff, mode_games, mode_count, deviations_count}}
    deviations = defaultdict(list)  # {year: [{year, team, games, mode_games, delta}, ...]}
    
    for year, rows in year_data.items():
        # 1936-1938は除外（season_key単位で処理するため）
        if year in [1936, 1937, 1938]:
            continue
        
        if not rows:
            continue
        
        games_list = [r['games'] for r in rows]
        min_games = min(games_list)
        max_games = max(games_list)
        diff = max_games - min_games
        
        # diff != 0 の年のみ処理
        if diff == 0:
            continue
        
        # mode（最頻値）を計算
        games_counter = Counter(games_list)
        mode_games, mode_count = games_counter.most_common(1)[0]
        
        # deviation（modeと違うチーム）を抽出
        deviation_rows = []
        for row in rows:
            if row['games'] != mode_games:
                delta = row['games'] - mode_games
                deviation_rows.append({
                    'year': year,
                    'team': row['team'],
                    'games': row['games'],
                    'mode_games': mode_games,
                    'delta': delta
                })
        
        suspects_summary[year] = {
            'teams': len(rows),
            'min_games': min_games,
            'max_games': max_games,
            'diff': diff,
            'mode_games': mode_games,
            'mode_count': mode_count,
            'deviations_count': len(deviation_rows)
        }
        
        deviations[year] = deviation_rows
    
    # source_urlを年ごとに集計
    source_urls = defaultdict(set)  # {year: {url, ...}}
    
    for row in prewar_data:
        year = row['year']
        url = row.get('source_url', '')
        if url:
            source_urls[year].add(url)
    
    # setをlistに変換
    source_urls_dict = {year: sorted(list(urls)) for year, urls in source_urls.items()}
    
    return year_summary, dict(inconsistent_data), season_key_summary, suspects_summary, dict(deviations), source_urls_dict


def print_report(year_summary: Dict[int, Dict[str, Any]], inconsistent_data: Dict[int, List[Dict[str, Any]]], season_key_summary: Dict[str, Dict[str, Any]], suspects_summary: Dict[int, Dict[str, Any]], deviations: Dict[int, List[Dict[str, Any]]], source_urls: Dict[int, List[str]]):
    """レポートをコンソールに表示"""
    print("="*60)
    print("戦前データ一貫性チェックレポート")
    print("="*60)
    
    # A) 年別サマリ表（year昇順）
    print("\n年別サマリ表:")
    print(f"{'year':>6} {'teams':>6} {'min_games':>10} {'max_games':>10} {'diff':>6} {'mean_games':>10}")
    print("-" * 60)
    
    inconsistent_years = []
    for year in sorted(year_summary.keys()):
        summary = year_summary[year]
        print(f"{year:>6} {summary['teams']:>6} {summary['min_games']:>10} {summary['max_games']:>10} {summary['diff']:>6} {summary['mean_games']:>10.2f}")
        if summary['diff'] != 0:
            inconsistent_years.append(year)
    
    # diff != 0の年だけを最後にもう一度まとめて表示
    if inconsistent_years:
        print(f"\ndiff != 0 の年（再掲）: {inconsistent_years}")
        print(f"   (チームごとのgamesが揃わない年: {len(inconsistent_years)}件)")
        print("-" * 60)
        for year in sorted(inconsistent_years):
            summary = year_summary[year]
            print(f"{year:>6} {summary['teams']:>6} {summary['min_games']:>10} {summary['max_games']:>10} {summary['diff']:>6} {summary['mean_games']:>10.2f}")
    else:
        print("\ndiff != 0 の年: []")
        print("   (すべての年でチームごとのgamesが揃っています)")
    
    # C) 1936/1937/1938のseason_key単位サマリ
    if season_key_summary:
        print("\n1936/1937/1938 season_key別サマリ:")
        print(f"{'season_key':>12} {'teams':>6} {'min_games':>10} {'max_games':>10} {'diff':>6} {'mean_games':>10}")
        print("-" * 60)
        for season_key in sorted(season_key_summary.keys()):
            summary = season_key_summary[season_key]
            print(f"{season_key:>12} {summary['teams']:>6} {summary['min_games']:>10} {summary['max_games']:>10} {summary['diff']:>6} {summary['mean_games']:>10.2f}")
    
    # B) diff != 0の年の詳細（差分が見える形）
    if inconsistent_data:
        print("\ndiff != 0 の年の詳細:")
        for year in sorted(inconsistent_data.keys()):
            print(f"\n  Year {year}:")
            
            # games降順
            print("    games降順:")
            for row in inconsistent_data[year]:
                print(f"      {row['season_key']:10s} {row['team']:20s} games={row['games']:4d}")
            
            # games昇順
            print("    games昇順:")
            sorted_asc = sorted(inconsistent_data[year], key=lambda x: x['games'])
            for row in sorted_asc:
                print(f"      {row['season_key']:10s} {row['team']:20s} games={row['games']:4d}")
            
            # value_counts（何試合のチームが何球団あるか）
            games_list = [row['games'] for row in inconsistent_data[year]]
            value_counts = Counter(games_list)
            print("    value_counts:")
            for games, count in sorted(value_counts.items(), reverse=True):
                print(f"      games={games:4d}: {count}球団")
    
    # diff != 0 の年（1936-1938を除外）の補正方針判断材料
    if suspects_summary:
        print("\ndiff != 0 の年（1936-1938を除外）の補正方針判断材料:")
        print(f"{'year':>6} {'teams':>6} {'min':>6} {'max':>6} {'diff':>6} {'mode':>6} {'mode_count':>10} {'deviations':>10}")
        print("-" * 70)
        for year in sorted(suspects_summary.keys()):
            summary = suspects_summary[year]
            print(f"{year:>6} {summary['teams']:>6} {summary['min_games']:>6} {summary['max_games']:>6} {summary['diff']:>6} {summary['mode_games']:>6} {summary['mode_count']:>10} {summary['deviations_count']:>10}")
        
        # 各年のdeviation詳細
        print("\ndeviation詳細（mode基準でズレているチーム）:")
        for year in sorted(deviations.keys()):
            if not deviations[year]:
                continue
            print(f"\n  Year {year} (mode={suspects_summary[year]['mode_games']}試合):")
            for dev in sorted(deviations[year], key=lambda x: x['delta']):
                print(f"    {dev['team']:20s} games={dev['games']:4d} delta={dev['delta']:+4d} (mode={dev['mode_games']}試合)")
            
            # value_countsを表示
            games_list = [dev['games'] for dev in deviations[year]]
            games_list.append(suspects_summary[year]['mode_games'])  # modeも含める
            value_counts = Counter(games_list)
            print("    value_counts:")
            for games, count in sorted(value_counts.items(), reverse=True):
                marker = " (mode)" if games == suspects_summary[year]['mode_games'] else ""
                print(f"      games={games:4d}: {count}球団{marker}")
    
    # source_url一覧
    if source_urls:
        print("\nsource_url一覧（年ごと）:")
        for year in sorted(source_urls.keys()):
            urls = source_urls[year]
            print(f"  Year {year}: {len(urls)} unique URL(s)")
            for url in urls:
                print(f"    - {url}")
    
    print("="*60)


def save_year_summary_csv(year_summary: Dict[int, Dict[str, Any]], output_path: Path):
    """年別サマリをCSVに保存"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    rows = []
    for year in sorted(year_summary.keys()):
        summary = year_summary[year]
        rows.append({
            'year': year,
            'teams': summary['teams'],
            'min_games': summary['min_games'],
            'max_games': summary['max_games'],
            'diff': summary['diff'],
            'mean_games': summary['mean_games']
        })
    
    with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['year', 'teams', 'min_games', 'max_games', 'diff', 'mean_games'])
        writer.writeheader()
        writer.writerows(rows)
    print(f"年別サマリを保存しました: {output_path}")


def save_inconsistent_details_csv(inconsistent_data: Dict[int, List[Dict[str, Any]]], output_path: Path):
    """diff != 0の年の詳細をCSVに保存"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    rows = []
    for year in sorted(inconsistent_data.keys()):
        for row in inconsistent_data[year]:
            rows.append(row)
    
    with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['year', 'season_key', 'team', 'games'])
        writer.writeheader()
        if rows:
            writer.writerows(rows)
    print(f"詳細データを保存しました: {output_path}")


def save_suspects_years_csv(suspects_summary: Dict[int, Dict[str, Any]], output_path: Path):
    """diff != 0 の年（1936-1938を除外）のサマリをCSVに保存"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    rows = []
    for year in sorted(suspects_summary.keys()):
        summary = suspects_summary[year]
        rows.append({
            'year': year,
            'teams': summary['teams'],
            'min_games': summary['min_games'],
            'max_games': summary['max_games'],
            'diff': summary['diff'],
            'mode_games': summary['mode_games'],
            'mode_count': summary['mode_count'],
            'deviations_count': summary['deviations_count']
        })
    
    with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['year', 'teams', 'min_games', 'max_games', 'diff', 'mode_games', 'mode_count', 'deviations_count'])
        writer.writeheader()
        if rows:
            writer.writerows(rows)
    print(f"補正方針判断材料を保存しました: {output_path}")


def save_deviations_csv(deviations: Dict[int, List[Dict[str, Any]]], output_path: Path):
    """deviation詳細をCSVに保存"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    rows = []
    for year in sorted(deviations.keys()):
        for dev in deviations[year]:
            rows.append(dev)
    
    with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['year', 'team', 'games', 'mode_games', 'delta'])
        writer.writeheader()
        if rows:
            writer.writerows(rows)
    print(f"deviation詳細を保存しました: {output_path}")


def save_source_urls_csv(source_urls: Dict[int, List[str]], output_path: Path):
    """source_url一覧をCSVに保存"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    rows = []
    for year in sorted(source_urls.keys()):
        urls = source_urls[year]
        rows.append({
            'year': year,
            'unique_source_urls': json.dumps(urls, ensure_ascii=False),
            'url_count': len(urls)
        })
    
    with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['year', 'unique_source_urls', 'url_count'])
        writer.writeheader()
        if rows:
            writer.writerows(rows)
    print(f"source_url一覧を保存しました: {output_path}")


def main():
    """メイン処理"""
    # パス設定
    csv_path = project_root / '_data' / 'qualifying_pa_table.csv'
    output_summary_path = project_root / '_data' / 'reports' / 'prewar_games_year_summary.csv'
    output_details_path = project_root / '_data' / 'reports' / 'prewar_games_inconsistent_details.csv'
    
    if not csv_path.exists():
        print(f"エラー: CSVファイルが見つかりません: {csv_path}")
        return 1
    
    try:
        # CSVを読み込み
        print(f"CSVファイルを読み込み中: {csv_path}")
        data = load_qualifying_pa_table(csv_path)
        print(f"  読み込み完了: {len(data)}件")
        
        # 分析
        print("\n分析中...")
        year_summary, inconsistent_data, season_key_summary, suspects_summary, deviations, source_urls = analyze_prewar_consistency(data)
        
        # レポート表示
        print_report(year_summary, inconsistent_data, season_key_summary, suspects_summary, deviations, source_urls)
        
        # CSV保存
        save_year_summary_csv(year_summary, output_summary_path)
        save_inconsistent_details_csv(inconsistent_data, output_details_path)
        
        # 新しいCSV保存
        output_suspects_path = project_root / '_data' / 'reports' / 'prewar_games_suspects_years.csv'
        output_deviations_path = project_root / '_data' / 'reports' / 'prewar_games_deviations.csv'
        output_source_urls_path = project_root / '_data' / 'reports' / 'prewar_source_urls.csv'
        
        save_suspects_years_csv(suspects_summary, output_suspects_path)
        save_deviations_csv(deviations, output_deviations_path)
        save_source_urls_csv(source_urls, output_source_urls_path)
        
        return 0
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        return 1


print("CHECK_PREWAR: file loaded (__name__=%s)" % __name__)


def _debug_entry():
    print("CHECK_PREWAR: entered _debug_entry()")
    import os
    path = os.path.join("_data", "qualifying_pa_table.csv")
    print("CHECK_PREWAR: csv exists?", os.path.exists(path), "path=", path)


try:
    if __name__ == "__main__":
        import os
        print("CHECK_PREWAR: __file__ =", __file__)
        print("CHECK_PREWAR: cwd =", os.getcwd())
        print("CHECK_PREWAR: __main__ reached, about to run")
        _debug_entry()
        # もし main() 関数があるなら呼ぶ。なければ処理本体をここに移す。
        if "main" in globals() and callable(globals()["main"]):
            print("CHECK_PREWAR: calling main()")
            globals()["main"]()
        else:
            print("CHECK_PREWAR: main() not found. Move script logic into main().")
except Exception as e:
    print("CHECK_PREWAR: EXCEPTION:", repr(e))
    raise


