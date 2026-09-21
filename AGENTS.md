# AGENTS.md

## 1. プロジェクト概要 & 技術スタック
- **プロジェクト名称**: 中学受験 国語 心情語対策アプリケーション（Streamlit）
- **Framework**: Streamlit (1.40+)
- **Language**: Python 3.11+ (venv: `env`)
- **Package Manager**: pip
- **Database**: Google Cloud Firestore (本番) / ローカルJSONモック (開発)
- **Auth**: Google OAuth 2.0 (Gmailホワイトリスト方式) / ローカルモック認証 (開発)
- **Hosting**: Google Cloud Run

## 2. 検証コマンド (Verification Ground Truth)
エージェントはコード作成・修正後、以下のコマンドを実行して正常終了（Exit Code 0）を必ず確認すること。
- **構文・インポートチェック**:
  `python -m py_compile app.py` （修正した各 `.py` ファイルに対しても実行可能）
- **単体テスト**:
  `pytest` （`tests/` 配下にテストコードが存在する場合）

## 3. 参照ディレクトリ・正本定義
- **仕様書正本**: `for_agent/` 配下のすべての `.md` ファイル
  - [requirements.md](file:///c:/Users/youic/Documents/Myproject/58_language-app/for_agent/requirements.md): 要件定義書
  - [implementation_guide.md](file:///c:/Users/youic/Documents/Myproject/58_language-app/for_agent/implementation_guide.md): 実装指示書・詳細設計書
- **進捗管理**: [Plan.md](file:///c:/Users/youic/Documents/Myproject/58_language-app/Plan.md)
- **変更ログ**: [AICHANGELOG.md](file:///c:/Users/youic/Documents/Myproject/58_language-app/AICHANGELOG.md)
- **単語マスターデータ**: `raw_data/word-list/all_words.csv`

## 4. 自律実装ルール
- 1回のイテレーションで処理する未完了タスクは **必ず1つ** とする。
- 実装後は検証コマンド（構文チェックまたは pytest）を実行し、エラーがないことを確認してから完了とする。
- タスク完了後は `AICHANGELOG.md` に追記、`Plan.md` を `- [x]` に更新し、Git コミットを作成する。
