#!/usr/bin/env python3
"""2025年のCSVファイルのIsoPとIsoDを再計算するスクリプト"""
import csv
import math
import sys
from pathlib import Path

def safe_float(value, default=None):
    """安全にfloatに変換（Noneを返すことも可能）"""
    if value is None or value == '':
        return default
    try:
        val = float(value)
        if math.isnan(val) or math.isinf(val):
            return default
        return val
    except (ValueError, TypeError):
        return default

def calculate_isop_isod(row):
    """IsoPとIsoDを計算"""
    # SLGを取得または計算
    slg = safe_float(row.get('SLG') or row.get('長打率'))
    if slg is None:
        # SLGを計算（TB / AB）
        tb = safe_float(row.get('TB') or row.get('塁打'), 0)
        ab = safe_float(row.get('AB') or row.get('打数'), 0)
        if ab > 0:
            slg = tb / ab
    
    # AVGを取得または計算
    avg = safe_float(row.get('AVG') or row.get('打率'))
    if avg is None:
        # AVGを計算（H / AB）
        h = safe_float(row.get('H') or row.get('安打'), 0)
        ab = safe_float(row.get('AB') or row.get('打数'), 0)
        if ab > 0:
            avg = h / ab
    
    # OBPを取得または計算
    obp = safe_float(row.get('OBP') or row.get('出塁率'))
    if obp is None:
        # OBPを計算（(H + BB + HBP) / (AB + BB + HBP + SF)）
        h = safe_float(row.get('H') or row.get('安打'), 0)
        bb = safe_float(row.get('BB') or row.get('四球'), 0)
        hbp = safe_float(row.get('HBP') or row.get('死球'), 0)
        ab = safe_float(row.get('AB') or row.get('打数'), 0)
        sf = safe_float(row.get('SF') or row.get('犠飛'), 0)
        denominator = ab + bb + hbp + sf
        if denominator > 0:
            obp = (h + bb + hbp) / denominator
    
    # IsoPとIsoDを計算
    isop = None
    isod = None
    if slg is not None and avg is not None:
        isop = slg - avg
    if obp is not None and avg is not None:
        isod = obp - avg
    
    return isop, isod, slg, avg, obp

def fix_csv_file(csv_path):
    """CSVファイルのIsoPとIsoDを修正"""
    print(f"処理中: {csv_path}")
    
    if not csv_path.exists():
        print(f"⚠️  ファイルが見つかりません: {csv_path}")
        return False
    
    # CSVを読み込み
    rows = []
    fieldnames = None
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            rows.append(row)
    
    if not fieldnames:
        print(f"❌ ヘッダーが見つかりません: {csv_path}")
        return False
    
    # IsoPとIsoDを再計算
    updated_count = 0
    for row in rows:
        isop, isod, slg, avg, obp = calculate_isop_isod(row)
        
        # IsoPを更新
        if isop is not None:
            row['IsoP'] = f"{isop:.6f}".rstrip('0').rstrip('.')
            updated_count += 1
        
        # IsoDを更新
        if isod is not None:
            row['IsoD'] = f"{isod:.6f}".rstrip('0').rstrip('.')
            updated_count += 1
        
        # SLG, AVG, OBPも更新（空の場合）
        if slg is not None and slg > 0:
            if not row.get('SLG') or row.get('SLG') == '':
                row['SLG'] = f"{slg:.3f}".rstrip('0').rstrip('.')
            if not row.get('長打率') or row.get('長打率') == '':
                row['長打率'] = f"{slg:.3f}".rstrip('0').rstrip('.')
        
        if avg is not None and avg > 0:
            if not row.get('AVG') or row.get('AVG') == '':
                row['AVG'] = f"{avg:.3f}".rstrip('0').rstrip('.')
            if not row.get('打率') or row.get('打率') == '':
                row['打率'] = f"{avg:.3f}".rstrip('0').rstrip('.')
        
        if obp is not None and obp > 0:
            if not row.get('OBP') or row.get('OBP') == '':
                row['OBP'] = f"{obp:.3f}".rstrip('0').rstrip('.')
            if not row.get('出塁率') or row.get('出塁率') == '':
                row['出塁率'] = f"{obp:.3f}".rstrip('0').rstrip('.')
    
    # CSVを書き込み
    with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"✅ 完了: {csv_path} ({updated_count}行更新)")
    return True

if __name__ == '__main__':
    # スクリプトのディレクトリを基準にパスを設定
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir
    print(f"Script directory: {script_dir}")
    print(f"Project root: {project_root}")
    
    # 2025年のCSVファイルを処理
    csv_files = [
        project_root / '_data' / 'master_csv_calculated' / 'batting_2025_PL_from_master.csv',
        project_root / '_data' / 'master_csv_calculated' / 'batting_2025_CL_from_master.csv',
    ]
    
    success_count = 0
    for csv_path in csv_files:
        if fix_csv_file(csv_path):
            success_count += 1
    
    if success_count > 0:
        print(f"\n✅ {success_count}個のCSVファイルを更新しました")
        sys.exit(0)
    else:
        print("\n❌ CSVファイルの更新に失敗しました")
        sys.exit(1)
