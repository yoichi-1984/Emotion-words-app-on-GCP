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
