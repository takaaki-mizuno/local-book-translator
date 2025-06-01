#!/usr/bin/env python3
"""
HTMLで書かれた英語のテキストを、Markdownに変換し、日本語に翻訳するツール

使用例:
    python main.py input.html output.md
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from bs4 import BeautifulSoup
from markdownify import markdownify as md
import re

# mlx_lm API をimport
from mlx_lm import load, generate


def html_to_markdown(html_content: str) -> str:
    """
    HTMLコンテンツをMarkdownに変換する
    
    Args:
        html_content: 変換するHTMLコンテンツ
        
    Returns:
        変換されたMarkdownテキスト
    """
    # BeautifulSoupでHTMLをパース
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # readable-textクラスの要素のみを抽出（章節のコンテンツ）
    content_elements = soup.find_all(class_='readable-text')
    
    if not content_elements:
        # readable-textクラスがない場合は全体を使用
        content_elements = [soup]
    
    # 各要素をMarkdownに変換
    markdown_parts = []
    for element in content_elements:
        # markdownifyを使用してHTMLをMarkdownに変換
        markdown_text = md(str(element), heading_style="ATX")
        if markdown_text.strip():
            markdown_parts.append(markdown_text.strip())
    
    # 結合して最終的なMarkdownを作成
    full_markdown = '\n\n'.join(markdown_parts)
    
    # 余分な空行を削除し、整形
    full_markdown = re.sub(r'\n{3,}', '\n\n', full_markdown)
    
    return full_markdown


def translate_with_mlx_lm(text: str, model_name: str = "mlx-community/plamo-2-translate", 
                         model=None, tokenizer=None) -> str:
    """
    mlx_lmを使用して英語テキストを日本語に翻訳する
    
    Args:
        text: 翻訳する英語テキスト
        model_name: 使用するモデル名
        model: 既にロード済みのモデル（None の場合は新規ロード）
        tokenizer: 既にロード済みのトークナイザー（None の場合は新規ロード）
        
    Returns:
        翻訳された日本語テキスト
    """
    try:
        # モデルとトークナイザーがまだロードされていない場合
        if model is None or tokenizer is None:
            print(f"モデルをロード中: {model_name}")
            # plamo系モデルはtrust_remote_code=Trueが必要
            if "plamo" in model_name.lower():
                model, tokenizer = load(
                    model_name,
                    tokenizer_config={"trust_remote_code": True}
                )
            else:
                model, tokenizer = load(model_name)
        
        # plamo-2-translate用の正しい翻訳プロンプト形式
        if "plamo" in model_name.lower() and "translate" in model_name.lower():
            # plamo-2-translateの公式プロンプト形式を使用
            translation_prompt = f'''<|plamo:op|>dataset
translation
<|plamo:op|>input lang=English
{text}
<|plamo:op|>output lang=Japanese writingStyle=polite
'''
        else:
            # 他のモデルの場合
            translation_prompt = f"Translate the following English text to Japanese:\n\n{text}\n\nJapanese translation:"
        
        # 翻訳を実行（plamo-2-translate用のパラメータ設定）
        if "plamo" in model_name.lower() and "translate" in model_name.lower():
            translated_text = generate(
                model, 
                tokenizer, 
                prompt=translation_prompt,
                max_tokens=1024,
                verbose=False
            )
        else:
            translated_text = generate(
                model, 
                tokenizer, 
                prompt=translation_prompt,
                max_tokens=200,
                verbose=False
            )
        
        # plamo-2-translateの出力から翻訳結果のみを抽出
        if "plamo" in model_name.lower() and "translate" in model_name.lower():
            # プロンプト部分を除去して翻訳結果のみを抽出
            # プロンプト全体を除去して翻訳結果のみを取得
            if translation_prompt in translated_text:
                # プロンプト部分を完全に除去
                result = translated_text.replace(translation_prompt, "").strip()
            else:
                result = translated_text.strip()
            
            # <|plamo:op|> タグが含まれている場合は、最初の出現位置で切断
            if "<|plamo:op|>" in result:
                result = result.split("<|plamo:op|>")[0].strip()
            
            # 空の結果の場合は元のテキストを返す
            if not result:
                return text
                
            return result
        elif "Japanese translation:" in translated_text:
            # 他のモデルの場合
            parts = translated_text.split("Japanese translation:")
            if len(parts) > 1:
                result = parts[-1].strip()
                lines = result.split('\n')
                clean_lines = []
                for line in lines:
                    line = line.strip()
                    if line:
                        clean_lines.append(line)
                    else:
                        break
                return '\n'.join(clean_lines)
        
        return translated_text.strip()
        
    except Exception as e:
        print(f"翻訳中にエラーが発生しました: {e}", file=sys.stderr)
        return text  # 翻訳に失敗した場合は元のテキストを返す


def translate_markdown_chunks(markdown_content: str, output_file_path: str, model_name: str = "mlx-community/plamo-2-translate", 
                            chunk_size: int = 1000, start_line: int = 1) -> str:
    """
    Markdownコンテンツを小さなチャンクに分割して翻訳し、進行中にファイルに保存する
    
    Args:
        markdown_content: 翻訳するMarkdownコンテンツ
        output_file_path: 出力ファイルのパス
        model_name: 使用するモデル名
        chunk_size: 一度に翻訳する文字数
        start_line: 翻訳を開始する段落番号
        
    Returns:
        翻訳されたMarkdownコンテンツ
    """
    # モデルとトークナイザーを一度だけロード
    print(f"モデルをロード中: {model_name}")
    try:
        # plamo系モデルはtrust_remote_code=Trueが必要
        if "plamo" in model_name.lower():
            model, tokenizer = load(
                model_name,
                tokenizer_config={"trust_remote_code": True}
            )
        else:
            model, tokenizer = load(model_name)
        print("モデルのロードが完了しました")
    except Exception as e:
        print(f"モデルのロードに失敗しました: {e}", file=sys.stderr)
        return markdown_content
    
    # 段落単位で分割
    paragraphs = markdown_content.split('\n\n')
    total_paragraphs = len(paragraphs)
    print(f"全体で {total_paragraphs} 段落が見つかりました")
    print(f"段落 {start_line} から翻訳を開始します")
    
    # 出力ファイルを初期化（開始行が1の場合のみ）
    output_path = Path(output_file_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    if start_line == 1:
        # 最初から開始する場合はファイルを空にする
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("")
    
    translated_paragraphs = []
    current_chunk = ""
    chunk_count = 0
    paragraph_count = 0
    
    for paragraph in paragraphs:
        paragraph_count += 1
        
        # 開始行より前の段落はスキップ
        if paragraph_count < start_line:
            continue
        
        # 現在のチャンクに段落を追加すると制限を超える場合
        if len(current_chunk) + len(paragraph) > chunk_size and current_chunk:
            # 現在のチャンクを翻訳
            chunk_count += 1
            
            print(f"\n{'='*80}")
            print(f"翻訳中... (チャンク {chunk_count}, 段落 {paragraph_count-1}, 長さ: {len(current_chunk)}文字)")
            print(f"{'='*80}")
            print("【翻訳前】:")
            print(current_chunk)
            print(f"{'-'*80}")
            
            translated_chunk = translate_with_mlx_lm(current_chunk, model_name, model, tokenizer)
            translated_paragraphs.append(translated_chunk)
            
            print("【翻訳後】:")
            print(translated_chunk)
            print(f"{'='*80}")
            
            # 翻訳完了後すぐにファイルに追記保存
            with open(output_path, 'a', encoding='utf-8') as f:
                if start_line == 1 and chunk_count == 1:
                    # 最初から開始で最初のチャンクの場合
                    f.write(translated_chunk)
                else:
                    # 2番目以降のチャンクまたは途中から開始の場合は改行を追加
                    f.write('\n\n' + translated_chunk)
            print(f"チャンク {chunk_count} を保存しました")
            
            current_chunk = paragraph
        else:
            # チャンクに段落を追加
            if current_chunk:
                current_chunk += "\n\n" + paragraph
            else:
                current_chunk = paragraph
    
    # 最後のチャンクを翻訳
    if current_chunk:
        chunk_count += 1
        
        print(f"\n{'='*80}")
        print(f"翻訳中... (最終チャンク {chunk_count}, 段落 {paragraph_count}, 長さ: {len(current_chunk)}文字)")
        print(f"{'='*80}")
        print("【翻訳前】:")
        print(current_chunk)
        print(f"{'-'*80}")
        
        translated_chunk = translate_with_mlx_lm(current_chunk, model_name, model, tokenizer)
        translated_paragraphs.append(translated_chunk)
        
        print("【翻訳後】:")
        print(translated_chunk)
        print(f"{'='*80}")
        
        # 最後のチャンクも保存
        with open(output_path, 'a', encoding='utf-8') as f:
            if start_line == 1 and chunk_count == 1:
                # 最初から開始で唯一のチャンクの場合
                f.write(translated_chunk)
            else:
                # 最後のチャンクまたは途中から開始の場合は改行を追加
                f.write('\n\n' + translated_chunk)
        print(f"最終チャンク {chunk_count} を保存しました")
    
    return '\n\n'.join(translated_paragraphs)


def main() -> None:
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="HTMLで書かれた英語のテキストをMarkdownに変換し、日本語に翻訳します"
    )
    parser.add_argument(
        "input_file",
        type=str,
        help="入力HTMLファイルのパス"
    )
    parser.add_argument(
        "output_file", 
        type=str,
        help="出力Markdownファイルのパス"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="mlx-community/plamo-2-translate",
        help="使用する翻訳モデル (デフォルト: mlx-community/plamo-2-translate)"
    )
    parser.add_argument(
        "--no-translate",
        action="store_true",
        help="翻訳をスキップし、Markdown変換のみを行う"
    )
    parser.add_argument(
        "--start-line",
        type=int,
        default=1,
        help="翻訳を開始する段落番号 (デフォルト: 1)"
    )
    
    args = parser.parse_args()
    
    # 入力ファイルの存在確認
    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"エラー: 入力ファイル '{args.input_file}' が見つかりません", file=sys.stderr)
        sys.exit(1)
    
    try:
        # HTMLファイルを読み込み
        print(f"HTMLファイルを読み込み中: {args.input_file}")
        with open(input_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # HTMLからMarkdownに変換
        print("HTMLをMarkdownに変換中...")
        markdown_content = html_to_markdown(html_content)
        
        if args.no_translate:
            # 翻訳をスキップ
            final_content = markdown_content
            print("翻訳をスキップしました")
            
            # 出力ファイルに保存
            output_path = Path(args.output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(final_content)
            
            print(f"完了! 結果を保存しました: {args.output_file}")
        else:
            # 日本語に翻訳（この過程でファイルに順次保存される）
            print("英語から日本語に翻訳中...")
            final_content = translate_markdown_chunks(markdown_content, args.output_file, args.model, args.start_line)
            
            print(f"完了! 翻訳結果を保存しました: {args.output_file}")
        
    except Exception as e:
        print(f"エラーが発生しました: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
