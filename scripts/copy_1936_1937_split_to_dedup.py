#!/usr/bin/env python3
"""
copy_1936_1937_split_to_dedup.py

1936/1937年の分割済みファイルを yearly_from_master_dedup フォルダにコピーし、
必要に応じて既存の年単位ファイルを削除する
"""

import csv
import shutil
from pathlib import Path
from typing import List, Dict, Any


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


def main():
    # パス設定
    base_path = Path(r"C:\Users\short\OneDrive\ドキュメント\デスクトップ\npb_batting")
    source_dir = base_path / "data" / "batting" / "jbl"
    target_dir = base_path / "data" / "batting" / "yearly_from_master_dedup"
    
    # ソースファイル
    source_files = {
        '1936_spring': source_dir / "batting_1936S_from_individual.csv",
        '1936_fall': source_dir / "batting_1936A_from_individual.csv",
        '1937_spring': source_dir / "batting_1937S_from_individual.csv",
        '1937_fall': source_dir / "batting_1937A_from_individual.csv",
    }
    
    # ターゲットファイル名
    target_files = {
        '1936_spring': target_dir / "batting_1936_spring_PRE.csv",
        '1936_fall': target_dir / "batting_1936_fall_PRE.csv",
        '1937_spring': target_dir / "batting_1937_spring_PRE.csv",
        '1937_fall': target_dir / "batting_1937_fall_PRE.csv",
    }
    
    # 削除対象（既存の年単位ファイル）
    files_to_delete = [
        target_dir / "batting_1936_PRE_from_master.csv",
        target_dir / "batting_1937_PRE_from_master.csv",
    ]
    
    print("=" * 80)
    print("1936/1937年 分割ファイルを yearly_from_master_dedup にコピー")
    print("=" * 80)
    
    # ソースファイルの存在確認
    print("\n[確認] ソースファイルの確認:")
    all_exist = True
    for key, source_path in source_files.items():
        if source_path.exists():
            data = load_csv_with_encoding(source_path)
            print(f"  {source_path.name}: {len(data)}行 -> OK")
        else:
            print(f"  {source_path.name}: 見つかりません -> NG")
            all_exist = False
    
    if not all_exist:
        print("\n[エラー] 一部のソースファイルが見つかりません。処理を中断します。")
        return 1
    
    # ターゲットディレクトリの確認
    print(f"\n[確認] ターゲットディレクトリ: {target_dir}")
    if not target_dir.exists():
        target_dir.mkdir(parents=True, exist_ok=True)
        print("  ディレクトリを作成しました")
    else:
        print("  既に存在します")
    
    # 既存ファイルの確認
    print("\n[確認] 既存の年単位ファイル:")
    for file_path in files_to_delete:
        if file_path.exists():
            data = load_csv_with_encoding(file_path)
            print(f"  {file_path.name}: {len(data)}行 -> 削除予定")
        else:
            print(f"  {file_path.name}: 存在しません")
    
    # ファイルをコピー
    print("\n[実行] ファイルをコピー中...")
    copied_files = []
    
    for key, source_path in source_files.items():
        target_path = target_files[key]
        
        try:
            # CSVを読み込んで再保存（文字コードを統一）
            data = load_csv_with_encoding(source_path)
            
            # 列名を取得
            if data:
                fieldnames = list(data[0].keys())
                save_csv(data, target_path, fieldnames=fieldnames)
                copied_files.append(target_path)
            else:
                print(f"[警告] {source_path.name} は空です")
        
        except Exception as e:
            print(f"[エラー] {source_path.name} のコピーに失敗: {e}")
            import traceback
            traceback.print_exc()
            return 1
    
    # 既存の年単位ファイルを削除
    print("\n[実行] 既存の年単位ファイルを削除中...")
    deleted_files = []
    
    for file_path in files_to_delete:
        if file_path.exists():
            try:
                file_path.unlink()
                deleted_files.append(file_path)
                print(f"[削除] {file_path.name}")
            except Exception as e:
                print(f"[警告] {file_path.name} の削除に失敗: {e}")
        else:
            print(f"[スキップ] {file_path.name} は存在しないため削除をスキップ")
    
    # 結果サマリー
    print("\n" + "=" * 80)
    print("処理完了")
    print("=" * 80)
    print(f"\n[コピーしたファイル] {len(copied_files)}件")
    for f in copied_files:
        print(f"  {f.name}")
    
    print(f"\n[削除したファイル] {len(deleted_files)}件")
    for f in deleted_files:
        print(f"  {f.name}")
    
    print(f"\n[確認] ターゲットディレクトリの内容を確認してください: {target_dir}")
    
    return 0


if __name__ == '__main__':
    exit(main())





















