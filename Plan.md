# 進捗管理計画書 (Plan.md)

## 中学受験 国語 心情語対策アプリケーション

### フェーズ1: 仕様策定 & データ整備（完了）
- [x] 原本Wordドキュメント（raw_data/raw.docx）の完全なMarkdown化（raw_data/raw.md）
- [x] 心情語データ（全8カテゴリ・208語）の構造化データ整備
- [x] Web調査に基づく不足語の調査・充足（全8カテゴリ各8語追加、計64語追加・全272語へ拡充）
- [x] 中学入試出題基準・塾基準に基づく難易度（高・中・並）の付与（全8分類CSV＋統合CSV、計272語）
- [x] 要件定義の策定および仕様書作成（for_agent/requirements.md）
- [x] 実装指示書の策定（for_agent/implementation_guide.md）
- [x] ループエンジニアリング基盤の配備（AGENTS.md, .agents/skills/）

### フェーズ2: アプリケーション実装ループ（Phase 2: Coding Loop）
- [ ] 01. requirements.txt の作成（Streamlit, pytest 等）および仮想環境依存パッケージの整備
- [ ] 02. .env.example の作成および .gitignore の更新（.env, local_data/ 等の機密・一時ファイル除外）
- [ ] 03. data_loader.py の実装（WordItem 定義、all_words.csv 読み込み、キャッシュ関数）
- [ ] 04. tests/test_data_loader.py の作成と pytest による単語データ整合性検証
- [ ] 05. quiz_logic.py の実装（4択動的生成、10問サンプリング、正誤判定ロジック）
- [ ] 06. tests/test_quiz_logic.py の作成と pytest による出題・4択動的生成ロジック検証
- [ ] 07. db.py の実装（DatabaseInterface、WordStat 定義、LocalJsonDB モック実装）
- [ ] 08. tests/test_db.py の作成と pytest によるローカルモックDB読み書き検証
- [ ] 09. styles.py の実装（パステルカラー、スマホ最適化ボタンスタイル、カスタムCSS）
- [ ] 10. views/quiz_view.py の実装（モード選択、1問1答、ルビ確認、解説トグル、結果画面）
- [ ] 11. views/review_view.py の実装（苦手ノート画面・間違えた問題一覧・集計ソート表示）
- [ ] 12. views/dictionary_view.py の実装（心情語辞典画面・全272語検索・フィルタ・詳細展開）
- [ ] 13. app.py の実装（サイドバー開閉ナビゲーション、セッション状態管理、ローカルモック認証）
- [ ] 14. アプリケーション全体のローカル結合検証（py_compile および pytest）
- [ ] 15. auth.py の実装（Google OAuth 2.0 Webフロー & Gmailホワイトリスト検証）
- [ ] 16. db.py への FirestoreDB 実装の追加（Cloud Firestore 連携）
- [ ] 17. Dockerfile の作成および Cloud Run デプロイ設定の整備

### フェーズ3: 検品・同期（Phase 3: Review & Sync）
- [ ] 全機能の回帰テスト実行・仕様書（for_agent/）との完全同期点検
