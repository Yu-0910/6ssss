#!/usr/bin/env python3
"""
正規化処理のテストスクリプト
既存のJSONファイルに対して正規化処理を実行して検証
"""

import json
import hashlib
from pathlib import Path

# 指標分類の定義（build_rankings_2025_PL_full.py からコピー）
METRICS_REQUIRE_QUALIFYING_PA_BY_NAME = {
    "OPS", "打率", "出塁率", "長打率", "IsoP", "IsoD",
    "BB%", "K%", "BB/K",
    "RC", "XR", "BABIP",
    "SecA", "TA", "NOI", "GPA"
}

METRICS_NO_QUALIFYING_PA_BY_NAME = {
    "安打", "本塁打", "打点", "試合", "打席", "打数",
    "単打", "二塁打", "三塁打", "得点",
    "四球", "敬遠", "死球", "三振", "塁打",
    "盗塁", "盗塁死", "犠打", "犠飛", "併殺打"
}

def sanitize_filename(metric: str) -> str:
    """ファイル名用に指標名をサニタイズ"""
    if not metric:
        return metric
    file_metric = metric.strip()
    file_metric = file_metric.replace('/', '-').replace('\\', '-')
    forbidden_chars = [':', '*', '?', '"', '<', '>', '|']
    for char in forbidden_chars:
        file_metric = file_metric.replace(char, '_')
    file_metric = file_metric.rstrip('.')
    return file_metric

def calculate_file_hash(file_path: Path) -> str:
    """ファイルのハッシュを計算"""
    with open(file_path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()

def main():
    output_dir = Path('public/data/rankings/2025/PL')
    
    # Record.csvから指標名を取得
    record_csv = Path('Record.csv')
    if not record_csv.exists():
        record_csv = Path('_data/master_csv/Record.csv')
    
    if not record_csv.exists():
        print(f"❌ Record.csvが見つかりません")
        return 1
    
    with open(record_csv, 'r', encoding='utf-8-sig') as f:
        first_line = f.readline().strip()
        metrics = [m.strip() for m in first_line.split(',') if m.strip()]
    
    print(f"📊 抽出された指標数: {len(metrics)}")
    print(f"   指標: {', '.join(metrics[:10])}...")
    print(f"\n📋 Aグループ定義: {sorted(METRICS_REQUIRE_QUALIFYING_PA_BY_NAME)}")
    print(f"\n📋 Bグループ定義: {sorted(METRICS_NO_QUALIFYING_PA_BY_NAME)}")
    
    # 各指標の状態を確認
    print("\n" + "="*60)
    print("🔍 既存JSONファイルの状態確認...")
    
    a_group_found = []
    b_group_found = []
    a_group_missing = []
    b_group_missing = []
    
    for metric in metrics:
        file_metric = sanitize_filename(metric)
        json_path = output_dir / f"{file_metric}.json"
        json_all_path = output_dir / f"{file_metric}_all.json"
        
        is_a_group = metric in METRICS_REQUIRE_QUALIFYING_PA_BY_NAME
        is_b_group = metric in METRICS_NO_QUALIFYING_PA_BY_NAME
        
        if not is_a_group and not is_b_group:
            print(f"   ⚠️  {metric}: A/Bグループのどちらにも分類されていません")
            continue
        
        if not json_path.exists():
            if is_a_group:
                a_group_missing.append(metric)
            else:
                b_group_missing.append(metric)
            continue
        
        if not json_all_path.exists():
            if is_a_group:
                a_group_missing.append(metric)
            else:
                b_group_missing.append(metric)
            continue
        
        # ファイルのハッシュを計算
        json_hash = calculate_file_hash(json_path)
        json_all_hash = calculate_file_hash(json_all_path)
        
        if is_a_group:
            a_group_found.append((metric, json_hash == json_all_hash))
            if json_hash == json_all_hash:
                print(f"   ⚠️  {metric} (A): json と all が一致しています（正規化が必要？）")
        else:
            b_group_found.append((metric, json_hash == json_all_hash))
            if json_hash != json_all_hash:
                print(f"   ❌ {metric} (B): json と all が一致していません（正規化が必要）")
            else:
                print(f"   ✅ {metric} (B): json と all が一致しています（正規化済み）")
    
    print(f"\n📊 結果:")
    print(f"   Aグループ: {len(a_group_found)}件（一致={sum(1 for _, match in a_group_found if match)}件）")
    print(f"   Bグループ: {len(b_group_found)}件（一致={sum(1 for _, match in b_group_found if match)}件）")
    
    if a_group_missing:
        print(f"\n⚠️  Aグループでファイルが見つからない指標: {a_group_missing}")
    if b_group_missing:
        print(f"\n⚠️  Bグループでファイルが見つからない指標: {b_group_missing}")
    
    return 0

if __name__ == '__main__':
    exit(main())


















