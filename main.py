import pandas as pd
import glob
import numpy as np
import os
import sys
from tqdm import tqdm
import time
from IPython.display import display

def check_data_files(directory="../data"):
    """必要なキーワードを含むファイルが存在するかチェックする"""
    required_keywords = ["ボイラ", "構外", "油", "太陽光", "電力", "ガス"]
    
    if not os.path.exists(directory):
        print(f"エラー: ディレクトリ '{directory}' が見つかりません。")
        return False, ["すべてのファイル（ディレクトリなし）"]

    files = os.listdir(directory)
    missing_keywords = []

    print(f"--- ファイル確認開始: {directory} ---")
    for keyword in tqdm(required_keywords, desc="チェック中"):
        found = any(keyword in filename for filename in files)
        if not found:
            print(f"警告: '{keyword}' を含むファイルが存在しません。")
            missing_keywords.append(keyword)
    
    if not missing_keywords:
        print("OK: すべてのキーワードに一致するファイルが見つかりました。")
    print("-----------------------------------")
    return len(missing_keywords) == 0, missing_keywords

def main():
    directory = "../data"
    result_dir = "../result"
    
    # 1. ファイルチェック
    all_files_exist, missing = check_data_files(directory)

    if not all_files_exist:
        print(f"\n【忠告】以下のキーワードを含むファイルが不足しています:")
        for m in missing:
            print(f"  - {m}")
        
        choice = input("\n不足しているファイルがありますが、集計処理を続けますか？ [y/N]: ").strip().lower()
        if choice != 'y':
            print("処理を中断しました。")
            sys.exit()

    # 2. ファイルリストの取得
    files = glob.glob(os.path.join(directory, "*.csv")) + glob.glob(os.path.join(directory, "*.xls*"))
    if not files:
        print("処理対象のファイルが見つかりませんでした。")
        return

    merged_df = None

    print('\n--- データ読み込み・マージ実行中 ---')
    for filepath in tqdm(files, desc="ファイル処理"):
        file_full_name = os.path.basename(filepath)
        file_name = os.path.splitext(file_full_name)[0]
        
        # 「構外」が含まれる場合は1行読み飛ばす設定
        skip_rows = 1 if "構外" in file_full_name else 0
        
        try:
            # --- 読み込み処理 ---
            if filepath.endswith('.csv'):
                try:
                    df = pd.read_csv(filepath, sep=None, engine='python', encoding='UTF-16', skiprows=skip_rows)
                except:
                    df = pd.read_csv(filepath, sep=None, engine='python', encoding='utf-8-sig', skiprows=skip_rows)
            else:
                df = pd.read_excel(filepath, skiprows=skip_rows)
            
            # --- クリーニング ---
            # 列名のタブ・改行・「実績」・前後の空白を除去
            df.columns = [str(col).replace('実績', '').replace('\t', '').replace('\n', '').strip() for col in df.columns]
            
            if not all(col in df.columns for col in ['年', '月']):
                print(f"  ！ スキップ（'年' '月'不足）: {file_full_name}")
                continue

            # 「ファイル名 @ 項目名」にリネーム
            df = df.rename(columns=lambda x: f"{file_name}@{x}" if x not in ['年', '月'] else x)
            
            # --- マージ ---
            if merged_df is None:
                merged_df = df
            else:
                # 型を文字列に揃えてマージ（不一致防止）
                df['年'] = df['年'].astype(str)
                df['月'] = df['月'].astype(str)
                merged_df['年'] = merged_df['年'].astype(str)
                merged_df['月'] = merged_df['月'].astype(str)
                merged_df = pd.merge(merged_df, df, on=['年', '月'], how='outer')
                
        except Exception as e:
            print(f"  × エラー（{file_full_name}）: {e}")
            continue

    # 3. 集計・整形処理
    if merged_df is not None:
        # 数値ソート
        merged_df['年'] = pd.to_numeric(merged_df['年'], errors='coerce')
        merged_df['月'] = pd.to_numeric(merged_df['月'], errors='coerce')
        merged_df = merged_df.sort_values(['年', '月']).reset_index(drop=True)
        
        # 転置してマルチインデックス化
        final_df = merged_df.set_index(['年', '月']).T
        new_index = final_df.index.str.split('@', expand=True)
        new_index.names = ['ファイル名', '項目名']
        final_df.index = new_index
        
        # ファイル名でソート
        final_df = final_df.sort_index(level='ファイル名')

        print("\n--- グループ化されたデータ ---")
        display(final_df)

        # 4. 保存処理
        print('\nデータ保存中...')
        if not os.path.exists(result_dir):
            os.makedirs(result_dir)
            
        for _ in tqdm(range(5), desc="書き込み"):
            time.sleep(0.2)

        output_path = os.path.join(result_dir, 'summaryData.csv')
        final_df.to_csv(output_path, encoding='cp932')

        print(f'保存完了: {output_path}')
        time.sleep(1)
        print('こちら処理完了後、自動で閉じます（3秒後）')
        time.sleep(3)
    else:
        print("マージ可能なデータがありませんでした。")

if __name__ == "__main__":
    main()