#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fact_check_internal_consistency.py

内部整合性チェックスクリプト

複数のCSVディレクトリ間で選手リストを比較し、欠けている選手を特定します。
外部ソースに依存せず、既存のデータのみを使用します。

使用方法:
    python scripts/fact_check_internal_consistency.py [--year YEAR] [--league LEAGUE] [--all]
"""

import sys
import csv
import json
from pathlib import Path
from typing import Dict, List, Set, Optional
from collections import defaultdict
from datetime import datetime

# WindowsでのUnicode出力対応
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# プロジェクトルートを取得
script_dir = Path(__file__).parent
project_root = script_dir.parent


def load_players_from_csv(csv_path: Path, year: int, league: str) -> Set[str]:
    """CSVからplayer_idのセットを読み込む"""
    players = set()
    if not csv_path.exists():
        return players
    
    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            # BOMを手動で除去
            content = f.read()
            if content.startswith('\ufeff'):
                content = content[1:]
            
            reader = csv.DictReader(content.splitlines())
            for row in reader:
                # yearカラムがある場合は確認
                row_year = None
                if 'year' in row:
                    try:
                        row_year = int(row['year'])
                    except (ValueError, TypeError):
                        pass
                
                # leagueカラムがある場合は確認
                row_league = None
                if 'league' in row:
                    row_league = row['league'].upper().strip()
                
                # year/leagueが一致するか、カラムがない場合は全て含める
                if (row_year is None or row_year == year) and (row_league is None or row_league == league):
                    player_id = row.get('player_id', '').strip()
                    if player_id and player_id != 'nan' and player_id != '':
                        players.add(player_id)
    except Exception as e:
        print(f"⚠️ CSV読み込みエラー ({csv_path}): {e}")
    
    return players


def check_internal_consistency(year: int, league: str, project_root: Path) -> Dict:
    """内部整合性をチェック"""
    
    # 各CSVディレクトリから選手リストを読み込む
    sources = {
        'imported': project_root / '_data' / 'master_csv__import_1950_2024' / f'batting_{year}_{league}_from_master.csv',
        'calculated': project_root / '_data' / 'master_csv_calculated' / f'batting_{year}_{league}_from_master.csv',
        'master': project_root / '_data' / 'master_csv' / f'batting_{year}_{league}_from_master.csv',
    }
    
    players_by_source = {}
    for source_name, csv_path in sources.items():
        players = load_players_from_csv(csv_path, year, league)
        players_by_source[source_name] = players
    
    # 全ソースの和集合（全選手）
    all_players = set()
    for players in players_by_source.values():
        all_players.update(players)
    
    # 各ソースで欠けている選手を特定
    missing_by_source = {}
    for source_name, players in players_by_source.items():
        missing = all_players - players
        if missing:
            missing_by_source[source_name] = missing
    
    # 統計情報
    stats = {
        'total_players': len(all_players),
        'players_by_source': {k: len(v) for k, v in players_by_source.items()},
        'missing_by_source': {k: len(v) for k, v in missing_by_source.items()},
    }
    
    return {
        'year': year,
        'league': league,
        'all_players': all_players,
        'players_by_source': players_by_source,
        'missing_by_source': missing_by_source,
        'stats': stats,
    }


def detect_statistical_anomalies(project_root: Path, target_year: Optional[int] = None, target_league: Optional[str] = None) -> Dict:
    """統計的な異常を検出"""
    
    # 年度・リーグのリスト
    years = range(1950, 2026) if target_year is None else [target_year]
    leagues = ['CL', 'PL'] if target_league is None else [target_league.upper()]
    
    # 各年度・リーグの選手数を集計
    player_counts = defaultdict(lambda: defaultdict(int))
    player_years = defaultdict(set)  # player_id -> {year, ...}
    
    for year in years:
        for league in leagues:
            csv_path = project_root / '_data' / 'master_csv_calculated' / f'batting_{year}_{league}_from_master.csv'
            players = load_players_from_csv(csv_path, year, league)
            player_counts[year][league] = len(players)
            
            for player_id in players:
                player_years[player_id].add(year)
    
    # 異常検出
    anomalies = {
        'year_to_year_drops': [],  # 前年比で異常な減少
        'team_anomalies': [],  # チーム別の異常
        'missing_years': [],  # 特定の選手が特定の年度だけ欠けている
    }
    
    # 前年比で異常な減少を検出
    for year in sorted(years):
        if year - 1 not in years:
            continue
        for league in leagues:
            current = player_counts[year][league]
            previous = player_counts[year - 1][league]
            if previous > 0:
                drop_rate = (previous - current) / previous
                if drop_rate > 0.2:  # 20%以上の減少
                    anomalies['year_to_year_drops'].append({
                        'year': year,
                        'league': league,
                        'previous': previous,
                        'current': current,
                        'drop_rate': drop_rate,
                    })
    
    # 特定の選手が特定の年度だけ欠けているパターンを検出
    for player_id, years_set in player_years.items():
        if len(years_set) < 2:
            continue
        
        sorted_years = sorted(years_set)
        # 連続する年度で欠けているパターンを検出
        for i in range(len(sorted_years) - 1):
            if sorted_years[i + 1] - sorted_years[i] > 1:
                # 年度が飛んでいる
                missing_years = list(range(sorted_years[i] + 1, sorted_years[i + 1]))
                anomalies['missing_years'].append({
                    'player_id': player_id,
                    'missing_years': missing_years,
                    'before': sorted_years[i],
                    'after': sorted_years[i + 1],
                })
    
    return {
        'player_counts': dict(player_counts),
        'anomalies': anomalies,
    }


def main():
    args = sys.argv[1:]
    
    target_year = None
    target_league = None
    check_all = False
    
    i = 0
    while i < len(args):
        if args[i] == '--year' and i + 1 < len(args):
            target_year = int(args[i + 1])
            i += 2
        elif args[i] == '--league' and i + 1 < len(args):
            target_league = args[i + 1].upper()
            i += 2
        elif args[i] == '--all':
            check_all = True
            i += 1
        else:
            i += 1
    
    print(f"\n{'='*60}")
    print(f"=== 内部整合性チェック ===")
    print(f"{'='*60}\n")
    
    if check_all:
        print("全年度・全リーグをチェック中...\n")
        years = range(1950, 2026)
        leagues = ['CL', 'PL']
    else:
        if target_year is None:
            print("❌ エラー: --year を指定するか、--all を指定してください")
            print("使用方法: python scripts/fact_check_internal_consistency.py --year 1972 --league CL")
            print("          python scripts/fact_check_internal_consistency.py --all")
            sys.exit(1)
        
        years = [target_year]
        leagues = [target_league] if target_league else ['CL', 'PL']
    
    # 結果を保存
    all_results = []
    output_dir = project_root / 'output' / 'reports' / 'fact_check'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for year in years:
        for league in leagues:
            print(f"\n{year}年 {league}リーグ:")
            result = check_internal_consistency(year, league, project_root)
            all_results.append(result)
            
            print(f"  全選手数: {result['stats']['total_players']}人")
            for source_name, count in result['stats']['players_by_source'].items():
                print(f"  {source_name}: {count}人")
            
            if result['missing_by_source']:
                print(f"  ⚠️ 欠けている選手:")
                for source_name, missing in result['missing_by_source'].items():
                    print(f"    {source_name}: {len(missing)}人")
                    for player_id in sorted(missing)[:5]:
                        print(f"      - {player_id}")
                    if len(missing) > 5:
                        print(f"      ... 他 {len(missing) - 5}人")
            else:
                print(f"  ✅ すべてのソースで整合性があります")
    
    # 統計的な異常を検出
    print(f"\n{'='*60}")
    print(f"=== 統計的な異常検出 ===")
    print(f"{'='*60}\n")
    
    anomaly_result = detect_statistical_anomalies(project_root, target_year, target_league)
    
    if anomaly_result['anomalies']['year_to_year_drops']:
        print("⚠️ 前年比で異常な減少:")
        for anomaly in anomaly_result['anomalies']['year_to_year_drops'][:10]:
            print(f"  {anomaly['year']}年 {anomaly['league']}: {anomaly['previous']}人 → {anomaly['current']}人 (減少率: {anomaly['drop_rate']:.1%})")
    
    if anomaly_result['anomalies']['missing_years']:
        print(f"\n⚠️ 特定の年度だけ欠けている選手: {len(anomaly_result['anomalies']['missing_years'])}件")
        for anomaly in anomaly_result['anomalies']['missing_years'][:10]:
            print(f"  player_id {anomaly['player_id']}: {anomaly['before']}年 → {anomaly['after']}年 (欠けている年度: {anomaly['missing_years']})")
    
    # 結果をJSON形式で保存
    result_json = {
        'check_date': datetime.now().isoformat(),
        'target_year': target_year,
        'target_league': target_league,
        'check_all': check_all,
        'results': [
            {
                'year': r['year'],
                'league': r['league'],
                'stats': r['stats'],
                'missing_by_source': {k: list(v) for k, v in r['missing_by_source'].items()},
            }
            for r in all_results
        ],
        'anomalies': {
            'year_to_year_drops': anomaly_result['anomalies']['year_to_year_drops'],
            'missing_years': anomaly_result['anomalies']['missing_years'][:100],  # 最初の100件のみ
        },
    }
    
    json_file = output_dir / f'fact_check_internal_{target_year or "all"}_{target_league or "all"}.json'
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(result_json, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 結果をJSON形式で保存しました: {json_file}")
    
    # CSV形式で保存（欠けている選手）
    for result in all_results:
        if result['missing_by_source']:
            for source_name, missing in result['missing_by_source'].items():
                csv_file = output_dir / f'missing_in_{source_name}_{result["year"]}_{result["league"]}.csv'
                with open(csv_file, 'w', encoding='utf-8-sig', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['player_id', 'year', 'league', 'source'])
                    for player_id in sorted(missing):
                        writer.writerow([player_id, result['year'], result['league'], source_name])
                print(f"✅ 欠けている選手をCSV形式で保存しました: {csv_file}")


if __name__ == '__main__':
    main()
