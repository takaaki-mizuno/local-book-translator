# Local Book Translator

HTMLで書かれた英語のテキストを、Markdownに変換し、日本語に翻訳するツールです。

## 機能

- HTMLからMarkdownへの変換
- [mlx-lm](https://github.com/ml-explore/mlx-lm)を使用した英語から日本語への翻訳
- `plamo-2-translate`モデルによる高品質な翻訳
- コマンドライン引数による簡単な操作

## 必要な環境

- macOS（Apple Silicon推奨）
- Python 3.12.1以上
- uv（パッケージ管理）

## インストール

```bash
git clone <repository-url>
cd local-book-translator
uv sync
```

## 使用方法

### 基本的な使用法

```bash
# HTMLをMarkdownに変換し、日本語に翻訳
uv run python main.py input.html output.md

# 例: chapter_06.htmlを翻訳
uv run python main.py source/chapter_06.html output/chapter_06_ja.md
```

### オプション

```bash
# 翻訳をスキップしてMarkdown変換のみ実行
uv run python main.py input.html output.md --no-translate

# 別の翻訳モデルを指定
uv run python main.py input.html output.md --model your-model-name

# ヘルプを表示
uv run python main.py --help
```

## 技術仕様

- **HTMLパーサー**: BeautifulSoup4
- **Markdown変換**: markdownify
- **翻訳モデル**: mlx-community/plamo-2-translate
- **翻訳エンジン**: mlx-lm

## 特徴

- `readable-text`クラスの要素を自動検出して本文のみを抽出
- 大きなファイルは自動的にチャンクに分割して翻訳
- 翻訳時のメタデータを自動除去してクリーンな出力
- エラーハンドリングとタイムアウト機能

## サンプル

入力（HTML）:
```html
<div class="readable-text">
    <h2>Getting feedback</h2>
    <p>Let's be honest: when you ask your peers to review something...</p>
</div>
```

出力（Markdown、日本語）:
```markdown
## フィードバックを得る

率直に言おう：同僚にコードや文章のレビューを依頼するとき...
```

## ライセンス

MIT License
