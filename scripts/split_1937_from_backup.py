#!/usr/bin/env python3
"""
split_1937_from_backup.py

バックアップファイル（dedup前）から1937年を春秋に分割する
"""

import csv
from pathlib import Path
from typing import List, Dict, Any, Optional
from collections import defaultdict


def load_csv_with_encoding(csv_path: Path) -> List[Dict[str, Any]]:
    """CSVファイルを読み込む（文字コード自動判定）"""
    encodings = ['utf-8-sig', 'utf-8', 'shift_jis', 'cp932']
    for encoding in encodings:
        try:
            with open(csv_path, 'r', encoding=encoding) as f:
                reader = csv.DictReader(f)
                return list(reader)
        except (UnicodeDecodeError, FileNotFoundError):
            continue
    raise ValueError(f"Failed to read {csv_path} with any encoding")


def save_csv(data: List[Dict[str, Any]], output_path: Path, fieldnames: List[str] = None):
    """CSVファイルを保存"""
    if not data:
        print(f"[警告] {output_path.name} に書き込むデータがありません")
        return
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    if fieldnames is None:
        fieldnames = list(data[0].keys())
    
    with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(data)
    
    print(f"[完了] 保存: {output_path} ({len(data)}行)")


def determine_season_from_url(row: Dict[str, Any], url_columns: List[str]) -> Optional[str]:
    """URL列から春秋を判定"""
    for col in url_columns:
        url = str(row.get(col, '')).strip().lower()
        spring_keywords = ['spring', '春', '前半', '1st', '1937春', '1937s', 'spring1937']
        fall_keywords = ['fall', 'autumn', '秋', '後半', '2nd', '1937秋', '1937a', 'fall1937']
        
        if any(keyword in url for keyword in spring_keywords):
            return 'spring'
        elif any(keyword in url for keyword in fall_keywords):
            return 'fall'
    
    return None


def split_1937_from_backup(source_path: Path, output_dir: Path):
    """バックアップファイルから1937年を春秋に分割"""
    print(f"\n[読み込み] {source_path.name}")
    data = load_csv_with_encoding(source_path)
    print(f"  全行数: {len(data)}行")
    
    # year列を探す
    year_column = None
    for col in data[0].keys():
        if 'year' in col.lower():
            year_column = col
            break
    
    if not year_column:
        raise ValueError("year列が見つかりません")
    
    # player_id列を探す
    player_id_column = None
    for col in ['player_id', 'playerId', 'id', '選手ID']:
        if col in data[0].keys():
            player_id_column = col
            break
    
    if not player_id_column:
        raise ValueError("player_id列が見つかりません")
    
    # 1937年のデータをフィルタ
    filtered_data = []
    for row in data:
        year_val = str(row.get(year_column, '')).strip()
        if year_val == '1937' or year_val.startswith('1937'):
            filtered_data.append(row)
    
    print(f"  1937年フィルタ後: {len(filtered_data)}行")
    
    # URL列を探す
    url_columns = []
    for col in data[0].keys():
        if 'url' in col.lower() or 'source' in col.lower() or 'page' in col.lower():
            url_columns.append(col)
    
    # player_id + year で重複を検出
    key_to_rows = defaultdict(list)
    for row in filtered_data:
        player_id = str(row.get(player_id_column, '')).strip()
        year_val = str(row.get(year_column, '')).strip()
        key = (player_id, year_val)
        key_to_rows[key].append(row)
    
    # 重複があるキーを抽出
    duplicates = {k: rows for k, rows in key_to_rows.items() if len(rows) > 1}
    print(f"  重複キー数: {len(duplicates)}件")
    
    spring_data = []
    fall_data = []
    single_data = []  # 重複がない行
    
    # 重複がある行を処理（2行なら春秋の可能性が高い）
    processed_keys = set()
    for key, rows in duplicates.items():
        if len(rows) == 2:
            # 2行なら春秋の可能性が高い
            row1, row2 = rows
            
            # URLから判定を試みる
            season1 = determine_season_from_url(row1, url_columns) if url_columns else None
            season2 = determine_season_from_url(row2, url_columns) if url_columns else None
            
            if season1 or season2:
                if season1 == 'spring' or season2 == 'fall':
                    spring_data.append(row1 if season1 == 'spring' else row2)
                    fall_data.append(row2 if season1 == 'spring' else row1)
                elif season1 == 'fall' or season2 == 'spring':
                    fall_data.append(row1 if season1 == 'fall' else row2)
                    spring_data.append(row2 if season1 == 'fall' else row1)
                else:
                    # どちらか一方しか判定できない場合
                    if season1 == 'spring':
                        spring_data.append(row1)
                        fall_data.append(row2)
                    elif season1 == 'fall':
                        fall_data.append(row1)
                        spring_data.append(row2)
                    elif season2 == 'spring':
                        spring_data.append(row2)
                        fall_data.append(row1)
                    elif season2 == 'fall':
                        fall_data.append(row2)
                        spring_data.append(row1)
                    else:
                        # 判定できない場合は最初の行を春、2番目を秋として扱う
                        spring_data.append(row1)
                        fall_data.append(row2)
            else:
                # URLから判定できない場合、最初の行を春、2番目を秋として扱う
                spring_data.append(row1)
                fall_data.append(row2)
            
            processed_keys.add(key)
        else:
            # 2行以外はそのまま処理
            for row in rows:
                single_data.append(row)
            processed_keys.add(key)
    
    # 重複がない行を処理
    for key, rows in key_to_rows.items():
        if key not in processed_keys:
            single_data.append(rows[0])
    
    print(f"\n[分割結果]")
    print(f"  春: {len(spring_data)}行")
    print(f"  秋: {len(fall_data)}行")
    print(f"  単一（重複なし）: {len(single_data)}行")
    print(f"  合計: {len(spring_data) + len(fall_data) + len(single_data)}行")
    
    # 単一データを春と秋に振り分ける（どちらかに含める）
    # ここでは、単一データを春に含める（後で手動で確認・調整が必要な可能性がある）
    if single_data:
        print(f"\n[注意] 重複がない行が{len(single_data)}行あります。")
        print(f"  これらは春のデータとして含めます（後で確認してください）")
        spring_data.extend(single_data)
    
    # 保存
    fieldnames = list(data[0].keys())
    
    spring_path = output_dir / "batting_1937_spring_PRE.csv"
    save_csv(spring_data, spring_path, fieldnames=fieldnames)
    
    fall_path = output_dir / "batting_1937_fall_PRE.csv"
    save_csv(fall_data, fall_path, fieldnames=fieldnames)
    
    return {
        'spring': spring_data,
        'fall': fall_data,
        'single': single_data
    }


def main():
    base_path = Path(r"C:\Users\short\OneDrive\ドキュメント\デスクトップ\npb_batting")
    
    # バックアップファイル（最新のものを使用）
    backup_path = base_path / "data" / "batting" / "backups" / "20251222_014659" / "yearly_from_master" / "batting_1937_PRE_from_master.csv"
    
    # 出力先
    output_dir = base_path / "data" / "batting" / "yearly_from_master_dedup"
    
    print("=" * 80)
    print("1937年データをバックアップから分割")
    print("=" * 80)
    
    if not backup_path.exists():
        print(f"[エラー] バックアップファイルが見つかりません: {backup_path}")
        return 1
    
    try:
        result = split_1937_from_backup(backup_path, output_dir)
        
        print("\n" + "=" * 80)
        print("処理完了")
        print("=" * 80)
        print(f"\n[結果]")
        print(f"  春: {len(result['spring'])}行")
        print(f"  秋: {len(result['fall'])}行")
        if result['single']:
            print(f"  単一データ: {len(result['single'])}行（春に含めました）")
        print(f"\n[確認] 出力先: {output_dir}")
        print(f"  既存のファイルが上書きされました。")
        
    except Exception as e:
        print(f"\n[エラー] 処理中にエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())





















