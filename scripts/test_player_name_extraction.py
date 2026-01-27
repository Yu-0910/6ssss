#!/usr/bin/env python3
"""
テストスクリプト: 選手名の抽出ロジックをテスト
"""

import re
from pathlib import Path
from typing import Optional
from bs4 import BeautifulSoup

def find_japanese_name(html: str) -> Optional[str]:
    """HTMLから選手名（日本語）を探す"""
    if not html:
        return None
    
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        # id="pc_v_name" の中の日本語名
        pc_v_name_li = soup.find('li', id='pc_v_name')
        if pc_v_name_li:
            name_text = pc_v_name_li.get_text().strip()
            if name_text and 2 <= len(name_text) <= 50:
                return name_text
        
        # フォールバック: div#pc_v_name の中を探す
        pc_v_name_div = soup.find('div', id='pc_v_name')
        if pc_v_name_div:
            # div内のテキストを取得
            name_text = pc_v_name_div.get_text().strip()
            # 最初のli要素のテキストを取得
            first_li = pc_v_name_div.find('li')
            if first_li:
                name_text = first_li.get_text().strip()
            if name_text and 2 <= len(name_text) <= 50:
                return name_text
    except Exception as e:
        print(f"Error in find_japanese_name: {e}")
        pass
    
    return None

# テスト用: キャッシュから読み込む
if __name__ == '__main__':
    from pathlib import Path
    
    player_id = '3305153'  # 山﨑　伊織
    html_path = Path(f'output/html_cache/players/{player_id}.html')
    
    print(f"Testing player_id: {player_id}")
    print(f"HTML cache path: {html_path}")
    
    if not html_path.exists():
        print("HTML cache not found")
        exit(1)
    
    try:
        html = html_path.read_text(encoding='utf-8')
        name = find_japanese_name(html)
        print(f"Extracted name: {name}")
        
        # HTML構造を確認
        soup = BeautifulSoup(html, 'html.parser')
        pc_v_name_li = soup.find('li', id='pc_v_name')
        pc_v_name_div = soup.find('div', id='pc_v_name')
        
        print(f"\nHTML Structure:")
        print(f"  li#pc_v_name found: {pc_v_name_li is not None}")
        if pc_v_name_li:
            print(f"  li#pc_v_name text: {repr(pc_v_name_li.get_text()[:100])}")
        
        print(f"  div#pc_v_name found: {pc_v_name_div is not None}")
        if pc_v_name_div:
            print(f"  div#pc_v_name HTML (first 300 chars): {str(pc_v_name_div)[:300]}")
            ul = pc_v_name_div.find('ul')
            if ul:
                lis = ul.find_all('li')
                print(f"  ul found, li count: {len(lis)}")
                for i, li in enumerate(lis[:5]):
                    print(f"    li[{i}]: id={li.get('id')}, text={repr(li.get_text()[:50])}")
            else:
                # ulがない場合、div内の直接のテキストを確認
                print(f"  div#pc_v_name direct text: {repr(pc_v_name_div.get_text()[:100])}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

