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

## [2026-09-21] - Web調査に基づく不足心情語の調査および充足（全272語へ拡充）

### 作業概要
大手進学塾（SAPIX『言葉ナビ』、四谷大塚『四科のまとめ』）や入試国語対策リソースを調査し、上位・難関校読解で頻出するが未収録だった重要心情語・慣用句を各カテゴリ8語ずつ（計64語）選定・執筆。全8分類CSVおよび統合CSV（`all_words.csv`）を各34語、合計272語へ拡充。

### Before / After
- **Before:** 各カテゴリ26語、合計208語。頻出重要語である「気まずい」「情けない」「自責の念」「気が進まない」「気が重い」「失望」「絶望」「畏敬の念」「心が躍る」「ほっとする」等が不足していた。
- **After:**
  - 各カテゴリに難関校必須の8語を追加し、各カテゴリ34語・合計272語へ均等拡充。
  - 全語に通し番号（1〜272）をカテゴリ順に再採番。
  - 各語に「読み」「意味・ニュアンス」「入試物語文での代表的な場面・文脈例」「小学生がつまずきやすい点・類語との識別ポイント」の全6カラムを精緻に完備。
  - バリデーションテストにより全272語の欠損なし・UTF-8（BOMなし）を確認。

### 影響範囲
- 更新:
  - `raw_data/word-list/01_恥・劣等感・気まずさ.csv` (26語 -> 34語)
  - `raw_data/word-list/02_誇り・自尊心・優越感.csv` (26語 -> 34語)
  - `raw_data/word-list/03_葛藤・戸惑い・もどかしさ.csv` (26語 -> 34語)
  - `raw_data/word-list/04_怒り・不満・反発.csv` (26語 -> 34語)
  - `raw_data/word-list/05_不安・恐れ・動揺.csv` (26語 -> 34語)
  - `raw_data/word-list/06_哀しみ・喪失感・後悔.csv` (26語 -> 34語)
  - `raw_data/word-list/07_他者への心情（羨望・嫉妬・同情・敬意など）.csv` (26語 -> 34語)
  - `raw_data/word-list/08_喜び・安堵・充実感.csv` (26語 -> 34語)
  - `raw_data/word-list/all_words.csv` (208語 -> 272語)
  - `Plan.md`
  - `AICHANGELOG.md`

## [2026-09-21] - 中学入試出題水準に基づく難易度（高・中・並）列の追加

### 作業概要
中学受験（国語・物語文読解および記述問題）における出題基準および大手進学塾（SAPIX『言葉ナビ』、四谷大塚『四科のまとめ』等）の語彙水準をWeb調査し、全272語に対して3段階の難易度（高・中・並）を判定・付与。分類別CSV（01〜08）および全語統合CSV（`all_words.csv`）の「読み」列直後に「難易度」列を追加。

### 難易度判定基準
- **並（基礎〜標準、69語・約25%）**: 小4〜小5基礎・偏差値〜50レベル。日常会話や平易な読書で自然に使われ、記述の前提となる基本感情語。
- **中（中堅〜上位校、116語・約43%）**: 小5後半〜小6入試頻出・偏差値50〜60レベル。塾テキスト最頻出で、合否を分ける重要心情語・慣用句。
- **高（難関〜最難関校、87語・約32%）**: 難関校長文記述・偏差値60〜レベル。小学生の実体験から遠い大人の屈折した心情、漢語・文語的表現に由来し差がつく高度な心情語。

### Before / After
- **Before:**
  - 分類別CSV（6列）: `No,心情語・慣用表現,読み,意味・ニュアンス,入試物語文での代表的な場面・文脈例,小学生がつまずきやすい点・類語との識別ポイント`
  - 統合版CSV（7列）: `No,カテゴリ,心情語・慣用表現,読み,意味・ニュアンス,入試物語文での代表的な場面・文脈例,小学生がつまずきやすい点・類語との識別ポイント`
- **After:**
  - 分類別CSV（7列）: `No,心情語・慣用表現,読み,難易度,意味・ニュアンス,入試物語文での代表的な場面・文脈例,小学生がつまずきやすい点・類語との識別ポイント`
  - 統合版CSV（8列）: `No,カテゴリ,心情語・慣用表現,読み,難易度,意味・ニュアンス,入試物語文での代表的な場面・文脈例,小学生がつまずきやすい点・類語との識別ポイント`
  - 自動テストスクリプトにより、全272語の欠損なし・難易度値の正当性（高・中・並）・分類別と統合版の整合性・UTF-8（BOMなし）を検証済み。

### 影響範囲
- 更新:
  - `raw_data/word-list/01_恥・劣等感・気まずさ.csv`
  - `raw_data/word-list/02_誇り・自尊心・優越感.csv`
  - `raw_data/word-list/03_葛藤・戸惑い・もどかしさ.csv`
  - `raw_data/word-list/04_怒り・不満・反発.csv`
  - `raw_data/word-list/05_不安・恐れ・動揺.csv`
  - `raw_data/word-list/06_哀しみ・喪失感・後悔.csv`
  - `raw_data/word-list/07_他者への心情（羨望・嫉妬・同情・敬意など）.csv`
  - `raw_data/word-list/08_喜び・安堵・充実感.csv`
  - `raw_data/word-list/all_words.csv`
  - `Plan.md`
  - `AICHANGELOG.md`

## [2026-09-21] - アプリケーション要件定義書の策定および合意形成

### 作業概要
ユーザーへのヒアリングおよびディスカッションに基づき、中学受験国語・心情語対策アプリケーションの要件定義書を作成。技術スタック（Streamlit / Cloud Run / Cloud Firestore / Google OAuth 2.0）、データモデル、画面設計、クイズ出題ロジック（4択動的生成）、セキュリティ・運用方針を策定し、`for_agent/requirements.md` としてドキュメント化。

### Before / After
- **Before:** アプリケーションの仕様・技術構成・画面設計が未確定の構想段階。`for_agent/` ディレクトリが存在しない状態。
- **After:**
  - `for_agent/requirements.md`（要件定義書初版）を作成・保存。
  - フロントエンドに Streamlit、DBに Cloud Firestore、認証に Google OAuth 2.0（Gmailホワイトリスト方式）、ホスティングに Cloud Run を選定。
  - クイズ仕様（2モード、全カテゴリからのダミー動的生成、10問セッション、ルビ確認、解説トグル、苦手ノート、心情語辞典）を確定。
  - 全272語・最大5名の家族利用における Firestore 容量・無料枠内運用の妥当性を検証・確認。

### 影響範囲
- 新規作成:
  - `for_agent/requirements.md`
- 更新:
  - `Plan.md`
  - `AICHANGELOG.md`

## [2026-09-21] - 実装指示書（詳細設計・実装仕様書）の策定

### 作業概要
ユーザーからの詳細決定事項（苦手復習モードの10問以上開放条件、回答確定ボタン方式、GCPコンソールでのデータ管理、DEV_MODEによるローカルモック検証、小学生向けパステルUI）を網羅した実装指示書（詳細設計・実装仕様書）を作成。モジュール構成、状態遷移、データ型、出題・判定アルゴリズム、スマホ最適化CSS、DBインターフェース、テスト計画を策定し、`for_agent/implementation_guide.md` としてドキュメント化。

### Before / After
- **Before:** 要件定義書（ハイレベルな仕様）のみが存在し、具体的なコード設計（モジュール分割、状態変数、データ型、CSS詳細）が未定義な状態。
- **After:**
  - `for_agent/implementation_guide.md` を作成。
  - ディレクトリ構成、`WordItem` / `WordStat` / `QuizSession` の型定義、`quiz_logic.py` の出題・4択動的生成・判定アルゴリズムを詳細化。
  - `st.session_state` のキースキーマおよび画面遷移フローを確定。
  - スマホ最適化CSS（パステルカラー、親指タップ対応のmin-height:52pxボタン）を設計。
  - `DEV_MODE=True` によるローカルモックDB（JSON）/モック認証設計により、GCP未設定環境でも即座に動作検証可能な体制を確立。
  - `for_agent/requirements.md` を1.1版に改訂し、詳細決定事項と同期。

### 影響範囲
- 新規作成:
  - `for_agent/implementation_guide.md`
- 更新:
  - `for_agent/requirements.md`
  - `Plan.md`
  - `AICHANGELOG.md`

## [2026-09-21] - ループエンジニアリング基盤の配備およびタスク詳細化

### 作業概要
`old/loop.txt` のループエンジニアリング原則に基づき、開発自律化のための環境基盤を配備。リポジトリルートにプロジェクトルールおよび検証コマンドを定義した `AGENTS.md` を作成。また、`.agents/skills/` 配下に `/plan`, `/loop-step`, `/review` の3つのSkill（コマンド定義）を配備。既存の `Plan.md` を `old/Plan_phase1.md` にバックアップした上で、1タスク＝1実装＋1検証で完結するきめ細かいタスクリストへ再構成。

### Before / After
- **Before:**
  - `AGENTS.md` および `.agents/skills/` が存在せず、自律ループ用スラッシュコマンドが未整備。
  - `Plan.md` のタスク粒度が大きく、1イテレーションでの検証単位が曖昧。
  - `old/` にフェーズ1時点の計画書バックアップがない状態。
- **After:**
  - `AGENTS.md`（Streamlit / pytest / py_compile によるGround Truth検証定義）を新規作成。
  - `.agents/skills/plan/SKILL.md`（/plan コマンド定義）を作成。
  - `.agents/skills/loop-step/SKILL.md`（/loop-step コマンド定義）を作成。
  - `.agents/skills/review/SKILL.md`（/review コマンド定義）を作成。
  - `old/Plan_phase1.md` に旧計画書を退避・保存。
  - `Plan.md` を17の具体的ステップにブレイクダウンし、フェーズ2（実装ループ）へ即時移行可能な状態に更新。

### 影響範囲
- 新規作成:
  - `AGENTS.md`
  - `.agents/skills/plan/SKILL.md`
  - `.agents/skills/loop-step/SKILL.md`
  - `.agents/skills/review/SKILL.md`
  - `old/Plan_phase1.md`
- 更新:
  - `Plan.md`
  - `AICHANGELOG.md`

## [2026-09-21] - requirements.txt の作成および仮想環境依存パッケージの整備

### 作業概要
アプリケーション実行・テストに必要な依存ライブラリ一覧（Streamlit, pandas, pytest, python-dotenv, google-cloud-firestore, google-auth, google-auth-oauthlib, requests）を定義した `requirements.txt` を新規作成。仮想環境 `env` に全パッケージをインストールし、正常なインポートを検証。

### Before / After
- **Before:** `requirements.txt` が未作成で、仮想環境 `env` には `pip` のみが存在する状態。
- **After:**
  - `requirements.txt` を作成（Streamlit 1.40+, pandas 2.0+, pytest 8.0+, google-cloud-firestore, OAuth 関連パッケージを定義）。
  - `pip install -r requirements.txt` を実行し、全依存関係を仮想環境に正常導入完了。
  - Pythonスクリプトによる各モジュールのインポート検証（Exit Code 0）を確認済み。

### 影響範囲
- 新規作成:
  - `requirements.txt`
- 更新:
  - `Plan.md`
  - `AICHANGELOG.md`

## [2026-09-21] - .env.example の作成および .gitignore の更新

### 作業概要
アプリケーション設定用の環境変数テンプレートファイル `.env.example` を新規作成し、ローカル開発用モックデータ保存ディレクトリ（`local_data/`）およびサービスアカウントキー・クレデンシャルファイルを Git 管理から除外するよう `.gitignore` を更新。

### Before / After
- **Before:**
  - `.env.example` が存在せず、必要な環境変数の形式（DEV_MODE, Google OAuth, Firestore 設定）が明示されていない。
  - `.gitignore` にローカルモックデータ用ディレクトリ `local_data/` やサービスアカウントキー（`*service_account*.json`, `credentials.json`, `secrets.yaml`）の除外設定が明示的に記載されていない。
- **After:**
  - `.env.example` を作成し、`DEV_MODE=True`、Google OAuth 関連設定、`ALLOWED_EMAILS`、`GCP_PROJECT_ID` などの環境変数定義を明記。
  - `.gitignore` に `local_data/`、`*service_account*.json`、`credentials.json`、`secrets.yaml` の除外設定を追記。

### 影響範囲
- 新規作成:
  - `.env.example`
- 更新:
  - `.gitignore`
  - `Plan.md`
  - `AICHANGELOG.md`

## [2026-09-21] - data_loader.py の実装（WordItem 定義、all_words.csv 読み込み、キャッシュ関数）

### 作業概要
心情語データモデル `WordItem` の定義、全272語の単語マスターデータ (`all_words.csv`) の読み込み・検証、Streamlit の高速キャッシュ関数 (`@st.cache_data`)、およびカテゴリ別フィルタ・難易度別フィルタ・全文検索を行うユーティリティ関数を備えた `data_loader.py` を新規作成。

### Before / After
- **Before:**
  - 単語データをPythonコードから安全・構造的に読み込むためのモジュールが存在しなかった。
- **After:**
  - `data_loader.py` を作成。
  - `WordItem`（frozen dataclass）を定義し、型安全なデータ構造を提供。
  - `find_default_csv_path()` により実行ディレクトリに依存せず柔軟に `all_words.csv` を探索。
  - `parse_csv_to_words()` により `utf-8-sig` でCSVを安全にパースし、NaNの除去・型変換を実施。
  - `@st.cache_data` を付与した `load_words()` により、Streamlit アプリ実行時の高速キャッシュを実現。
  - `get_categories()`, `filter_by_category()`, `filter_by_difficulty()`, `search_words()` などの便利関数を提供。
  - `python -m py_compile data_loader.py` による構文検証、および全272語・8カテゴリ正常読み込みのアサーション検証に合格（Exit Code 0）。

### 影響範囲
- 新規作成:
  - `data_loader.py`
- 更新:
  - `Plan.md`
  - `AICHANGELOG.md`

## [2026-09-21] - tests/test_data_loader.py の作成と pytest による単語データ整合性検証

### 作業概要
`data_loader.py` の単体テストおよび `all_words.csv`（全272語）のデータ整合性を自動検証する `tests/test_data_loader.py` を作成し、pytest を用いて15項目の全テストをパス（Exit Code 0）することを確認。

### Before / After
- **Before:**
  - `tests/` ディレクトリが存在せず、単語データや `data_loader.py` の動作検証が手動実行のみであった。
- **After:**
  - `tests/` パッケージおよび `tests/test_data_loader.py` を作成。
  - 以下の検証項目を網羅した15件のテストケースを実装：
    1. CSVデフォルトパスの実在確認
    2. 全272語の過不足ない読み込み確認
    3. No 1〜272の連番・重複なし確認
    4. 必須項目（カテゴリ、語、読み、難易度、意味、文脈例、つまずきポイント）の非空・完全性検証
    5. 全8カテゴリの存在および各カテゴリ34語の均等配分検証
    6. 難易度（並・中・高）の完全網羅検証
    7. カテゴリ別フィルタ・難易度別フィルタの正常動作
    8. 語名・読み仮名・意味キーワードによる部分一致検索の動作
    9. 存在しないファイルパス時の FileNotFoundError 送出検証
    10. 必須列不足CSV時の ValueError 送出検証
  - `pytest -v tests/test_data_loader.py` を実行し、全15件が正常終了（Exit Code 0）。

### 影響範囲
- 新規作成:
  - `tests/__init__.py`
  - `tests/test_data_loader.py`
- 更新:
  - `Plan.md`
  - `AICHANGELOG.md`

## [2026-09-21] - quiz_logic.py の実装（4択動的生成、10問サンプリング、正誤判定ロジック）

### 作業概要
クイズ機能のコアロジックを担う `quiz_logic.py` を新規作成。1問1答形式での出題単語選定（通常モード10問サンプリング、苦手復習モードの10問開放条件・サンプリング）、4択動的生成（正解＋ダミー3つのランダム抽出とシャッフル）、正誤判定、および単語学習履歴（`WordStat`）の更新・JST ISO 8601タイムスタンプ付与ロジックを実装。

### Before / After
- **Before:**
  - クイズ出題、選択肢の動的生成、正誤判定および統計更新を管理するロジックが存在しなかった。
- **After:**
  - `quiz_logic.py` を新規作成。
  - `WordStat` データモデル（出題回数、不正解回数、不正解率、過去不正解フラグ等）および `QuizQuestion` データモデル（4択、正解インデックス、辞書変換対応）を定義。
  - `select_quiz_words()`: 単語プールから重複なく10問サンプリング。
  - `can_start_review_mode()` / `select_review_words()`: 間違えた問題が10問以上ある場合のみ開始できるガード条件と抽出ロジックを実装。
  - `generate_quiz_options()`: モード1（心情語→意味）およびモード2（意味→心情語）に応じた4択動的生成・シャッフル・正解インデックス特定を実装。
  - `create_quiz_question()` / `build_quiz_session()`: 1問単位および10問セッション単位のクイズ問題構築を提供。
  - `evaluate_answer()`: 選択肢と正解の一致判定。
  - `update_word_stat()`: 回答結果に応じた出題回数・不正解回数・不正解率（四捨五入）・最終結果・JSTタイムスタンプの安全な更新ロジックを実装。
  - `extract_failed_words()`: 統計情報から間違えたことのある単語アイテムを抽出する補助関数を実装。
  - `py_compile` による構文チェックおよびスモークテストに合格（Exit Code 0）。

### 影響範囲
- 新規作成:
  - `quiz_logic.py`
- 更新:
  - `Plan.md`
  - `AICHANGELOG.md`

## [2026-09-21] - tests/test_quiz_logic.py の作成と pytest による出題・4択動的生成ロジック検証

### 作業概要
`quiz_logic.py` の各機能（データモデル、出題サンプリング、苦手復習モード開放条件、4択動的生成・シャッフル、正誤判定、統計更新、苦手単語抽出）を検証する単体テストスイート `tests/test_quiz_logic.py` を作成。pytest を実行し、全40件（既存15件＋新規25件）のテストがすべて合格（Exit Code 0）することを確認。

### Before / After
- **Before:**
  - `quiz_logic.py` の実装に対する自動単体テストが存在せず、ランダムサンプリングや4択動的生成（正解・ダミー重複防止、シャッフル分布）、統計更新の永続性等の回帰検証が自動化されていなかった。
- **After:**
  - `tests/test_quiz_logic.py` を新規作成（計25テストケース）。
  - 主な検証項目：
    1. `WordStat.to_dict()` および `QuizQuestion.to_dict()` のデータ保持とシリアライズ完全性
    2. `get_current_jst_iso()` による JST (+09:00) タイムスタンプ取得
    3. `select_quiz_words()` の重複なしサンプリングおよび要素不足時の例外発生
    4. `can_start_review_mode()` および `select_review_words()` の10問未満ガード条件
    5. モード1（心情語→意味）およびモード2（意味→心情語）の4択動的生成（正解が必ず1つ、ダミー3つと重複なし、正解インデックス一致）
    6. 4択シャッフルにおける正解配置（0〜3）のランダム分布検証
    7. 不正なモードやダミー不足時の例外処理
    8. `create_quiz_question()` / `build_quiz_session()` による問題構築
    9. `evaluate_answer()` による完全一致・前後の余白トリム照合
    10. `update_word_stat()` による初回正解・初回不正解・過去不正解フラグ永続化・不正解率四捨五入（0.333など）の計算精度
    11. `extract_failed_words()` による間違えた単語のマスター順抽出
  - `pytest` を実行し、全40テスト（`test_data_loader.py`: 15件, `test_quiz_logic.py`: 25件）が100%成功（Exit Code 0）。

### 影響範囲
- 新規作成:
  - `tests/test_quiz_logic.py`
- 更新:
  - `Plan.md`
  - `AICHANGELOG.md`

## [2026-09-21] - db.py の実装（DatabaseInterface、WordStat 定義、LocalJsonDB モック実装）

### 作業概要
`for_agent/implementation_guide.md` および `for_agent/requirements.md` の仕様に基づき、データベースアクセス抽象化層 `db.py` を新規実装。学習履歴モデル `WordStat`、抽象インターフェース `DatabaseInterface`、およびローカル環境での完全動作を保証する `LocalJsonDB` モック実装を作成。また、ファクトリ関数 `get_db()` を提供し、`quiz_logic.py` とのモデル統一を行った。

### Before / After
- **Before:**
  - データベースアクセス層が存在せず、学習履歴（出題回数・不正解回数・正解率・直近結果等）の永続化インターフェースが未定義。
  - `WordStat` モデルが `quiz_logic.py` 内に暫定的に定義されており、DB層とのモデル共有がなされていなかった。
- **After:**
  - `db.py` を新規実装：
    - `WordStat`: 単語別学習履歴モデル（`to_dict()`, `from_dict()` 完備）。
    - `DatabaseInterface`: 抽象基底クラス（`get_user_stats`, `record_attempt`, `get_failed_words_stats`, `reset_user_stats`）。
    - `LocalJsonDB`: `local_data/mock_user_stats.json` にUTF-8・インデント付きで安全に保存するモックDB。スレッドセーフ（`threading.Lock`）かつ自動ディレクトリ生成対応。全272語の未出題単語もデフォルト値で補完して返却。
    - `get_db()`: 環境変数 `DEV_MODE` に応じて適切な DB インスタンスを返すファクトリ関数。
  - `quiz_logic.py` 内の重複定義を解消し、`db.py` の `WordStat`, `JST`, `get_current_jst_iso` をインポート・再エクスポートする構造に統一。
  - `python -m py_compile db.py quiz_logic.py` および `pytest`（全40テスト）がすべて正常終了（Exit Code 0）。

### 影響範囲
- 新規作成:
  - `db.py`
- 更新:
  - `quiz_logic.py`
## [2026-09-21] - tests/test_db.py の作成と pytest によるローカルモックDB読み書き検証

### 作業概要
`db.py` の学習履歴モデル（`WordStat`）、インターフェース（`DatabaseInterface`）、ローカルJSONモック実装（`LocalJsonDB`）、およびファクトリ関数（`get_db`）を対象とする単体テストスイート `tests/test_db.py` を新規作成。全24テストケースを実装し、pytest による全テスト（計64件）の正常終了（Exit Code 0）を確認。

### Before / After
- **Before:**
  - `db.py` の単体テストが存在せず、`LocalJsonDB` のファイル自動生成・JSON読み書き・データマージ・回答履歴更新・不正解フラグ永続化・ユーザーデータリセット・マルチスレッド並行書き込みの堅牢性が自動テストで検証されていなかった。
- **After:**
  - `tests/test_db.py` を新規作成（計24テストケース）。
  - 主な検証項目：
    1. `WordStat` の初期値、`to_dict()` および `from_dict()` の相互変換・型変換・デフォルト補完
    2. JSTタイムスタンプ文字列のフォーマット検証
    3. `LocalJsonDB` の初期化時におけるディレクトリ・ファイル自動生成、初期データ構造、破損JSON時のフォールバック処理
    4. `get_user_stats` による全272語のデフォルト値補完および学習履歴のマージ
    5. `record_attempt` による正解・不正解時の統計更新（回数、不正解率の四捨五入、過去不正解フラグの不可逆的保持）
    6. 別DBインスタンスによるJSONファイル永続化・再読み込みの整合性
    7. `get_failed_words_stats` による間違えた単語の抽出・No順ソート・ユーザー間分離
    8. `reset_user_stats` による特定ユーザーの学習履歴リセットと他ユーザーデータの不干渉
    9. `get_db` ファクトリ関数（引数指定、環境変数 `DEV_MODE` 連動）の動作
    10. `ThreadPoolExecutor` を用いた並行書き込み時のスレッドセーフティ
  - `pytest` を実行し、全64テスト（`test_data_loader.py`: 15件, `test_db.py`: 24件, `test_quiz_logic.py`: 25件）が100%成功（Exit Code 0）。

### 影響範囲
- 新規作成:
  - `tests/test_db.py`
- 更新:
  - `AICHANGELOG.md`
  - `Plan.md`
