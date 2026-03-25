#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
compute_metrics_pitching_all_seasons.py

Record_pitching.csv に記載された指標を計算して、全シーズンの pitching_YYYY_(PL|CL)_from_master.csv を
計算済みCSVとして出力するスクリプト（Phase 2）

入力: _data/master_csv__import_1950_2024/ （デフォルト）
出力: _data/master_csv_calculated/
元CSVは絶対に上書きしない（破壊的変更禁止）

計算指標: ERA, K-BB%, WHIP, K%, BB%, WPCT（算出可能な場合）
"""
import csv
import glob
import math
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# WindowsでのUnicode出力対応
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def normalize_column_name(col_name: str) -> str:
    """列名を正規化（BOM除去、全角スペース除去、前後空白strip）"""
    if not col_name:
        return col_name
    col_name = col_name.lstrip('\ufeff')
    col_name = col_name.replace('\u3000', ' ')
    col_name = col_name.strip()
    col_name = re.sub(r'\s+', ' ', col_name)
    return col_name


def load_csv_with_encoding(csv_path: Path) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """CSVを読み込む（文字コード自動判定）"""
    for encoding in ['utf-8-sig', 'utf-8', 'shift_jis', 'cp932']:
        try:
            with open(csv_path, 'r', encoding=encoding) as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames
                if not fieldnames:
                    return [], {}
                column_mapping = {}
                normalized_fieldnames = []
                for orig in fieldnames:
                    norm = normalize_column_name(orig)
                    column_mapping[orig] = norm
                    normalized_fieldnames.append(norm)
                data = []
                for row in reader:
                    nr = {column_mapping.get(k, k): row.get(k, '') for k in fieldnames}
                    data.append(nr)
                return data, column_mapping
        except (UnicodeDecodeError, FileNotFoundError):
            continue
    raise ValueError(f"Failed to read {csv_path}")


def safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    if value is None or value == '' or (isinstance(value, str) and value.strip() == ''):
        return default
    try:
        s = str(value).strip().replace(',', '')
        if s in ('-', '－', 'nan', 'NaN', 'NAN'):
            return default
        val = float(s)
        if math.isnan(val) or math.isinf(val):
            return default
        return val
    except (ValueError, TypeError):
        return default


def get_val(row: Dict[str, Any], keys: List[str], default: float = 0.0) -> float:
    """行から指定キーの値を取得"""
    for k in keys:
        if k in row:
            v = safe_float(row[k])
            if v is not None:
                return v
    return default


def extract_metrics_from_record(record_path: Path) -> List[str]:
    """Record_pitching.csv から指標リストを抽出"""
    for enc in ['utf-8-sig', 'utf-8', 'shift_jis', 'cp932']:
        try:
            with open(record_path, 'r', encoding=enc) as f:
                line = f.readline().rstrip('\r\n')
            if not line:
                return []
            metrics = [m.strip().lstrip('\ufeff') for m in line.split(',') if m.strip()]
            return [m for m in metrics if m.lower() not in ('id', 'name', 'label', 'desc', 'description', '単位', '備考', 'unit', 'note', 'memo')]
        except (UnicodeDecodeError, FileNotFoundError):
            continue
    return []


def parse_pitching_filename(filename: str) -> Optional[Tuple[int, str]]:
    """pitching_YYYY_LL_from_master.csv から (year, league) をパース"""
    m = re.match(r'^pitching_(\d{4})_(PL|CL)_from_master\.csv$', filename)
    if m:
        return (int(m.group(1)), m.group(2))
    return None


def find_pitching_csv_files(data_dir: Path, year: Optional[int] = None, league: Optional[str] = None) -> List[Tuple[Path, int, str]]:
    """投手CSVファイルを列挙"""
    results = []
    for p in data_dir.glob('pitching_*_*_from_master.csv'):
        parsed = parse_pitching_filename(p.name)
        if parsed:
            y, ll = parsed
            if year is not None and y != year:
                continue
            if league is not None and ll != league:
                continue
            results.append((p, y, ll))
    return sorted(results, key=lambda x: (x[1], x[2]))


# 計算が必要な指標
CALCULATED = {'ERA', 'K-BB%', 'WHIP', 'K%', 'BB%', 'WPCT'}


def ip_baseball_to_decimal(ip: float) -> float:
    """野球表記の投球回（.1=1/3, .2=2/3）を十進数に変換。ERA/WHIP 計算用"""
    if ip <= 0:
        return ip
    whole = int(ip)
    frac = ip - whole
    if abs(frac - 0.1) < 0.05:  # .1 = 1アウト = 1/3
        return whole + 1/3
    if abs(frac - 0.2) < 0.05:  # .2 = 2アウト = 2/3
        return whole + 2/3
    return ip


def compute_pitching_metrics(row: Dict[str, Any]) -> Dict[str, Any]:
    """派生指標を計算して row に追加。計算値は常に優先（上書き）"""
    out = row.copy()
    ip_raw = get_val(row, ['IP', '投球回'], 0)
    ip = ip_baseball_to_decimal(ip_raw)  # 野球表記 .1/.2 を十進に変換
    bf = get_val(row, ['BF', '打者'], 0)
    er = get_val(row, ['ER', '自責点'], 0)
    h = get_val(row, ['H', '安打'], 0)
    bb = get_val(row, ['BB', '与四球', '四球'], 0)
    so = get_val(row, ['SO', '奪三振', '三振'], 0)
    w = get_val(row, ['W', '勝利'], 0)
    l_val = get_val(row, ['L', '敗北'], 0)

    # ERA = (ER×9)/IP
    if ip > 0:
        out['ERA'] = round((er * 9) / ip, 2)

    # WHIP = (BB+H)/IP
    if ip > 0:
        out['WHIP'] = round((bb + h) / ip, 2)

    # K% = SO/BF×100
    if bf > 0:
        out['K%'] = round((so / bf) * 100, 1)

    # BB% = BB/BF×100
    if bf > 0:
        out['BB%'] = round((bb / bf) * 100, 1)

    # K-BB% = (SO−BB)/BF×100
    if bf > 0:
        out['K-BB%'] = round(((so - bb) / bf) * 100, 1)

    # WPCT = W/(W+L)
    if (w + l_val) > 0:
        out['WPCT'] = round(w / (w + l_val), 3)

    return out


def process_pitching_csv(
    input_path: Path,
    output_path: Path,
    target_metrics: List[str],
    dry_run: bool = False,
    overwrite: bool = False
) -> bool:
    """投手CSVを処理して計算済みCSVを出力"""
    if not input_path.exists():
        print(f"   ❌ 入力が見つかりません: {input_path}")
        return False

    if output_path.exists() and not overwrite and not dry_run:
        print(f"   ⚠️ 既存ファイルのためスキップ: {output_path.name} （--overwrite で上書き可）")
        return False

    try:
        data, _ = load_csv_with_encoding(input_path)
    except Exception as e:
        print(f"   ❌ 読み込みエラー: {e}")
        return False

    if not data:
        print(f"   ⚠️ データが空です: {input_path}")
        return False

    processed = [compute_pitching_metrics(row) for row in data]

    if dry_run:
        print(f"   [DRY-RUN] 処理済み: {len(processed)}行")
        return True

    output_path.parent.mkdir(parents=True, exist_ok=True)
    all_keys: Set[str] = set()
    for row in processed:
        all_keys.update(row.keys())

    # 列順: 識別列 → Record_pitching.csv の指標順 → その他
    id_cols = ['year', 'league', 'team', 'player_id', 'player_name_ja', 'player_name_en']
    metrics_ordered = [m for m in target_metrics if m in all_keys]
    other_cols = sorted(all_keys - set(id_cols) - set(metrics_ordered))
    fieldnames = [c for c in id_cols if c in all_keys]
    fieldnames.extend(metrics_ordered)
    fieldnames.extend(other_cols)

    try:
        with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(processed)
        return True
    except Exception as e:
        print(f"   ❌ 書き込みエラー: {e}")
        return False


def main():
    import argparse
    parser = argparse.ArgumentParser(description='投手指標計算（Phase 2）')
    parser.add_argument('--year', type=int, help='年度でフィルタ')
    parser.add_argument('--league', choices=['PL', 'CL'], help='リーグでフィルタ')
    parser.add_argument('--dry-run', action='store_true', help='書き込みなし')
    parser.add_argument('--overwrite', action='store_true', help='既存を上書き')
    parser.add_argument('--input-dir', type=str, default='_data/master_csv__import_1950_2024', help='入力ディレクトリ')
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent
    input_dir = project_root / args.input_dir if not Path(args.input_dir).is_absolute() else Path(args.input_dir)
    output_dir = project_root / '_data' / 'master_csv_calculated'
    record_path = project_root / 'Record_pitching.csv'

    if not record_path.exists():
        print(f"❌ Record_pitching.csv が見つかりません: {record_path}")
        return 1

    target_metrics = extract_metrics_from_record(record_path)
    if not target_metrics:
        print("❌ 指標リストの抽出に失敗しました")
        return 1

    print(f"Record_pitching.csv: {len(target_metrics)}指標")
    print(f"入力: {input_dir}")
    print(f"出力: {output_dir}")
    print(f"モード: {'DRY-RUN' if args.dry_run else '通常'}")
    if args.overwrite:
        print("上書き: 有効")

    if not input_dir.exists():
        print(f"❌ 入力ディレクトリが存在しません: {input_dir}")
        return 1

    files = find_pitching_csv_files(input_dir, args.year, args.league)
    if not files:
        print("❌ 対象の投手CSVが見つかりません")
        return 1

    print(f"\n対象ファイル: {len(files)}件")

    ok = 0
    skip = 0
    fail = 0
    for inp, year, league in files:
        out_name = f"pitching_{year}_{league}_from_master.csv"
        out_path = output_dir / out_name
        print(f"\n📝 {inp.name}")
        success = process_pitching_csv(inp, out_path, target_metrics, args.dry_run, args.overwrite)
        if success:
            if not args.dry_run and out_path.exists():
                ok += 1
                print(f"   ✅ {out_path}")
            else:
                ok += 1
        else:
            if out_path.exists() and not args.overwrite:
                skip += 1
            else:
                fail += 1

    print(f"\n{'='*50}")
    print(f"サマリ: 成功 {ok} / スキップ {skip} / 失敗 {fail} / 合計 {len(files)}")
    return 0 if fail == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
