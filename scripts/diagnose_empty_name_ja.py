#!/usr/bin/env python3
"""
player_name_jaが空の選手の原因を診断する

使用方法:
    python scripts/diagnose_empty_name_ja.py <player_id> [year] [league]
    
例:
    python scripts/diagnose_empty_name_ja.py 21423824 1988 CL
"""
import csv
import sys
from pathlib import Path
from typing import Dict, List, Optional

# プロジェクトルート
script_dir = Path(__file__).parent
project_root = script_dir.parent

def load_csv_dict(csv_path: Path) -> List[Dict]:
    """CSVファイルを読み込んで辞書のリストを返す"""
    if not csv_path.exists():
        return []
    
    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            return list(reader)
    except Exception as e:
        print(f"❌ CSV読み込みエラー ({csv_path}): {e}", file=sys.stderr)
        return []

def find_in_csv(csv_path: Path, player_id: str, key_col: str = 'player_id') -> List[Dict]:
    """CSVファイルからplayer_idで検索"""
    rows = load_csv_dict(csv_path)
    return [row for row in rows if row.get(key_col, '').strip() == player_id.strip()]

def check_stage2(player_id: str) -> Dict:
    """段階2: player_id_name_kana_official.csv をチェック"""
    csv_path = project_root / 'output' / 'master' / 'player_id_name_kana_official.csv'
    rows = find_in_csv(csv_path, player_id)
    
    result = {
        'found': len(rows) > 0,
        'rows': rows,
        'has_name_ja': any(row.get('name_ja', '').strip() for row in rows),
        'http_status': rows[0].get('http_status', '') if rows else '',
        'outcome': rows[0].get('outcome', '') if rows else '',
    }
    
    return result

def check_stage3(player_id: str) -> Dict:
    """段階3: player_id_to_roman_full.csv をチェック"""
    csv_path = project_root / 'output' / 'master' / 'player_id_to_roman_full.csv'
    rows = find_in_csv(csv_path, player_id)
    
    result = {
        'found': len(rows) > 0,
        'rows': rows,
        'name_ja': rows[0].get('name_ja', '').strip() if rows else '',
    }
    
    return result

def check_stage0_5(player_id: str, year: Optional[int] = None, league: Optional[str] = None) -> Dict:
    """段階0/5: 元CSVと適用後CSVをチェック"""
    # 元CSV（master_csv）
    original_csvs = []
    if year and league:
        original_csvs.append(project_root / '_data' / 'master_csv' / f'batting_{year}_{league}_from_master.csv')
    else:
        # 全CSVを検索
        for csv_file in (project_root / '_data' / 'master_csv').glob('batting_*_from_master.csv'):
            original_csvs.append(csv_file)
    
    # 適用後CSV（master_csv_calculated）
    applied_csvs = []
    if year and league:
        applied_csvs.append(project_root / '_data' / 'master_csv_calculated' / f'batting_{year}_{league}_from_master.csv')
    else:
        for csv_file in (project_root / '_data' / 'master_csv_calculated').glob('batting_*_from_master.csv'):
            applied_csvs.append(csv_file)
    
    original_rows = []
    applied_rows = []
    
    for csv_path in original_csvs:
        rows = find_in_csv(csv_path, player_id)
        if rows:
            original_rows.extend(rows)
    
    for csv_path in applied_csvs:
        rows = find_in_csv(csv_path, player_id)
        if rows:
            applied_rows.extend(rows)
    
    result = {
        'original_found': len(original_rows) > 0,
        'applied_found': len(applied_rows) > 0,
        'original_name_ja': original_rows[0].get('player_name_ja', '').strip() if original_rows else '',
        'applied_name_ja': applied_rows[0].get('player_name_ja', '').strip() if applied_rows else '',
        'original_rows': original_rows,
        'applied_rows': applied_rows,
    }
    
    return result

def diagnose(player_id: str, year: Optional[int] = None, league: Optional[str] = None) -> Dict:
    """診断を実行"""
    print(f"\n{'='*60}")
    print(f"=== player_name_jaが空の原因診断 ===")
    print(f"{'='*60}\n")
    print(f"対象player_id: {player_id}")
    if year and league:
        print(f"対象年度・リーグ: {year}年 {league}リーグ")
    print()
    
    # 段階2のチェック
    print("📖 段階2: player_id_name_kana_official.csv をチェック中...")
    stage2 = check_stage2(player_id)
    
    if not stage2['found']:
        print(f"  ❌ player_id {player_id} が見つかりません")
        return {'cause': 'NOT_FOUND', 'stage': 2}
    
    print(f"  ✅ {len(stage2['rows'])}行見つかりました")
    print(f"  - http_status: {stage2['http_status']}")
    print(f"  - outcome: {stage2['outcome']}")
    print(f"  - name_jaが存在: {stage2['has_name_ja']}")
    
    if len(stage2['rows']) > 1:
        print(f"  ⚠️ 同一player_idで複数行存在します")
        for i, row in enumerate(stage2['rows'], 1):
            print(f"    行{i}: name_ja='{row.get('name_ja', '')}', name_kana='{row.get('name_kana', '')}', roman_official='{row.get('roman_official', '')}'")
    
    # 原因Bの判定
    if stage2['http_status'] != '200' or stage2['outcome'] in ['FAILED', 'ERROR', 'NO_DATA']:
        print(f"\n  🔍 原因B（取得失敗）の可能性が高い")
        print(f"     - http_statusが200以外、またはoutcomeが失敗系")
        cause_b = True
    elif not stage2['has_name_ja'] and stage2['http_status'] == '200':
        print(f"\n  🔍 原因B（パース失敗）の可能性が高い")
        print(f"     - http_status=200なのにname_jaが空")
        cause_b = True
    else:
        cause_b = False
    
    # 段階3のチェック
    print(f"\n📖 段階3: player_id_to_roman_full.csv をチェック中...")
    stage3 = check_stage3(player_id)
    
    if not stage3['found']:
        print(f"  ❌ player_id {player_id} が見つかりません")
    else:
        print(f"  ✅ 見つかりました")
        print(f"  - name_ja: '{stage3['name_ja']}'")
        
        # 原因Cの判定
        if stage2['has_name_ja'] and not stage3['name_ja']:
            print(f"\n  🔍 原因C（段階3の選択ロジック）の可能性が高い")
            print(f"     - 段階2にはname_jaがあるのに、段階3で空になっている")
            cause_c = True
        else:
            cause_c = False
    
    # 段階0/5のチェック
    print(f"\n📖 段階0/5: 元CSVと適用後CSVをチェック中...")
    stage05 = check_stage0_5(player_id, year, league)
    
    if stage05['original_found']:
        print(f"  ✅ 元CSVで見つかりました")
        print(f"  - player_name_ja: '{stage05['original_name_ja']}'")
    else:
        print(f"  ⚠️ 元CSVで見つかりませんでした")
    
    if stage05['applied_found']:
        print(f"  ✅ 適用後CSVで見つかりました")
        print(f"  - player_name_ja: '{stage05['applied_name_ja']}'")
    else:
        print(f"  ⚠️ 適用後CSVで見つかりませんでした")
    
    # 原因Aの判定
    if stage05['original_found'] and stage05['applied_found']:
        if stage05['original_name_ja'] and not stage05['applied_name_ja']:
            print(f"\n  🔍 原因A（段階5の上書き事故）の可能性が高い")
            print(f"     - 元CSVにはplayer_name_jaがあるのに、適用後に空になっている")
            cause_a = True
        else:
            cause_a = False
    else:
        cause_a = False
    
    # 判定結果
    print(f"\n{'='*60}")
    print(f"=== 判定結果 ===")
    print(f"{'='*60}\n")
    
    causes = []
    if cause_a:
        causes.append('A')
    if cause_b:
        causes.append('B')
    if cause_c:
        causes.append('C')
    
    if not causes:
        print("  ⚠️ 明確な原因を特定できませんでした")
        print("  - 追加の調査が必要です")
    else:
        print(f"  🔍 原因候補: {', '.join(causes)}")
        if 'A' in causes:
            print(f"     - A: 段階5（apply_roman_to_master_csvs.py）が空のname_jaで上書き")
        if 'B' in causes:
            print(f"     - B: 段階2で取得/パース失敗")
        if 'C' in causes:
            print(f"     - C: 段階3の選択ロジックで空の行を採用")
    
    return {
        'cause': causes[0] if causes else 'UNKNOWN',
        'causes': causes,
        'stage2': stage2,
        'stage3': stage3,
        'stage05': stage05,
    }

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("使用方法: python scripts/diagnose_empty_name_ja.py <player_id> [year] [league]")
        print("例: python scripts/diagnose_empty_name_ja.py 21423824 1988 CL")
        sys.exit(1)
    
    player_id = sys.argv[1]
    year = int(sys.argv[2]) if len(sys.argv) > 2 else None
    league = sys.argv[3] if len(sys.argv) > 3 else None
    
    result = diagnose(player_id, year, league)
    
    # 原因Aの場合の修正案
    if 'A' in result.get('causes', []):
        print(f"\n{'='*60}")
        print(f"=== 原因Aの場合の修正案 ===")
        print(f"{'='*60}\n")
        print("apply_roman_to_master_csvs.py を修正:")
        print("  - player_name_jaを上書きする際、空の場合は元の値を維持")
        print("  - 例: if name_ja and name_ja.strip(): row['player_name_ja'] = name_ja")
    
    sys.exit(0)




