# AI 変更履歴 (AICHANGELOG.md)

## [2026-09-21] - raw.docx から raw.md への完全変換

### 作業概要
`raw_data/raw.docx` の内容を欠損・変形なくそのまま `raw_data/raw.md` へ Markdown 変換を実施。

### Before / After
- **Before:** `raw_data/raw.docx`（Word文書、バイナリ形式）のみが存在し、テキストや表データが直接扱えない状態。
- **After:** `raw_data/raw.md`（UTF-8、Markdown形式）を生成。
  - タイトル、見出し階層（H1, H2, H4）を正確に保持。
  - 全8カテゴリ・全208語の心情語表（6列テーブル）をすべて欠損なく変換。
  - 引用文献（14件）のハイパーリンクおよび本文・表中の上付き参照番号（`<sup>...</sup>`）を正確に再現。

### 影響範囲
- `raw_data/raw.md` の新規追加
- `Plan.md`, `AICHANGELOG.md` の新規追加

## [2026-09-21] - 心情語データの分類別CSV作成および考察レポート抽出

### 作業概要
`raw_data/raw.md` を解析し、全8カテゴリ・208語の心情語データを分類ごとのCSVファイルおよび全件統合CSVに構造化して出力。また、リスト以外の考察・分析・答案作成技術および引用文献を `raw_data/report.md` として抽出・保存。

### Before / After
- **Before:** `raw_data/raw.md` の中に単語テーブルと考察テキストが混在し、アプリケーション開発等での構造化利用が困難な状態。`raw_data/word-list` ディレクトリは空。
- **After:**
  - `raw_data/word-list/` に全8カテゴリの分類別CSV（各26語）と全語統合版 `all_words.csv`（全208語・カテゴリ列付与）を作成（UTF-8・BOMなし）。
  - テーブルセル内の上付き引用タグ（`<sup>...</sup>`）をクレンジングし、クリーンなテキストデータとして格納。
  - `raw_data/report.md` に単語テーブル以外の研究背景、全8カテゴリの分析・着眼点、記述答案作成における運用技術、引用文献一覧（14件）を再構成して保存。

### 影響範囲
- 新規作成:
  - `raw_data/word-list/01_恥・劣等感・気まずさ.csv`
  - `raw_data/word-list/02_誇り・自尊心・優越感.csv`
  - `raw_data/word-list/03_葛藤・戸惑い・もどかしさ.csv`
  - `raw_data/word-list/04_怒り・不満・反発.csv`
  - `raw_data/word-list/05_不安・恐れ・動揺.csv`
  - `raw_data/word-list/06_哀しみ・喪失感・後悔.csv`
  - `raw_data/word-list/07_他者への心情（羨望・嫉妬・同情・敬意など）.csv`
  - `raw_data/word-list/08_喜び・安堵・充実感.csv`
  - `raw_data/word-list/all_words.csv`
  - `raw_data/report.md`
- 更新:
  - `Plan.md`
  - `AICHANGELOG.md`

