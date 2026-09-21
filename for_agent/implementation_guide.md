# 実装指示書（詳細設計・実装仕様書）：中学受験 国語 心情語対策アプリケーション

## 改訂履歴
| 日付 | 版 | 改訂内容 | 作成・改訂者 |
| :--- | :--- | :--- | :--- |
| 2026-09-21 | 1.0 | 初版作成（モジュール構成、状態遷移、UI・DB・出題詳細設計の策定） | AI Pair Programmer |
| 2026-09-21 | 1.1 | styles.py のUIコンポーネントヘルパー関数仕様（カード・バナー・バッジ・統計表示）の追記 | AI Pair Programmer |

---

## 1. 開発方針 & ディレクトリ構成

### 1.1 基本方針
* **Python 3.11+ / Streamlit 1.40+** を使用。
* モジュール分割により、UI表示、データアクセス、ビジネスロジック（クイズ生成・判定）、認証を明確に疎結合化する。
* **ローカル開発モード (`DEV_MODE=True`)** を備え、GCP設定前でも即座にUI・クイズ機能のローカル検証・単体テストが可能。

### 1.2 ディレクトリ構成
```
58_language-app/
├── .env.example               # 環境変数のサンプルファイル
├── .gitignore                 # .env, secrets.yaml, __pycache__, service_account.json を除外
├── Dockerfile                 # Cloud Run デプロイ用 Dockerfile
├── requirements.txt           # 依存ライブラリ一覧
├── app.py                     # メインエントリーポイント（認証・ルーティング・サイドバー）
├── config.py                  # 設定管理（環境変数読み込み、DEV_MODE判定、ホワイトリスト）
├── auth.py                    # 認証モジュール（Google OAuth 2.0 / ローカルモック認証）
├── db.py                      # DBアクセス抽象化（Firestore / ローカルJSONモック）
├── data_loader.py             # CSV読み込み & キャッシュ（all_words.csv）
├── quiz_logic.py              # クイズロジック（出題抽出、4択動的生成、正誤判定、統計計算）
├── styles.py                  # スマホ最適化カスタムCSS（パステルカラー、丸角、フォントサイズ）
├── views/                     # 画面コンポーネント
│   ├── __init__.py
│   ├── quiz_view.py           # クイズ画面（モード選択、1問1答、結果画面）
│   ├── review_view.py         # 苦手ノート画面（間違えた問題一覧・集計ソート）
│   └── dictionary_view.py     # 心情語辞典画面（全272語一覧・検索・詳細展開）
├── for_agent/                 # エージェント用仕様書・設計書
│   ├── requirements.md        # 要件定義書
│   └── implementation_guide.md# 本実装指示書
├── raw_data/
│   └── word-list/
│       └── all_words.csv      # 単語マスターデータ（全8分類・272語）
└── local_data/                # ローカル開発時のモックデータ保存先（.gitignore対象）
    └── mock_user_stats.json
```

---

## 2. データ構造・型定義

### 2.1 単語モデル (`data_loader.py`)
```python
from dataclasses import dataclass

@dataclass(frozen=True)
class WordItem:
    no: int                # 1 〜 272
    category: str          # 例: "1. 恥・劣等感・気まずさ"
    word: str              # 心情語（例: "気後れ"）
    reading: str           # 読み（例: "きおくれ"）
    difficulty: str        # 難易度（"並", "中", "高"）
    meaning: str           # 意味・ニュアンス
    example: str           # 入試物語文での代表的な場面・文脈例
    tips: str              # 小学生がつまずきやすい点・類語との識別ポイント
```

### 2.2 ユーザー学習履歴モデル (`db.py`)
```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class WordStat:
    word_no: int
    word: str
    category: str
    total_attempts: int = 0
    incorrect_count: int = 0
    incorrect_rate: float = 0.0     # incorrect_count / total_attempts
    has_ever_failed: bool = False   # 過去に1度でも間違えたか
    last_attempt_at: Optional[str] = None
    last_result: Optional[str] = None  # "correct" | "incorrect"
```

---

## 3. クイズ出題 & 判定アルゴリズム (`quiz_logic.py`)

### 3.1 10問の選定ロジック
1. **通常モード（全カテゴリランダム / カテゴリ固定）**:
   - 対象母集団（全272語、または選択されたカテゴリの34語）から `random.sample(pool, 10)` で**重複なく10問**を抽出。
2. **苦手復習モード**:
   - ユーザーの学習履歴より `has_ever_failed == True` の単語一覧を取得。
   - **前提条件**: 間違えた問題が **10問以上** 存在すること。
     - 10問未満の場合はモード選択時に「間違えた問題が10問以上になると開放されます（現在: X問）」と表示し、開始不可とする。
   - 10問以上ある場合、該当する単語群から `random.sample(failed_words, 10)` で抽出。

### 3.2 4択動的生成ロジック
出題単語 $W_{target}$ に対し、以下の手順で4択肢を生成する：
1. **正解選択肢**:
   - モード1（心情語 → 意味）: $W_{target}.\text{meaning}$
   - モード2（意味 → 心情語）: $W_{target}.\text{word}$
2. **ダミー選択肢（3つ）**:
   - 全単語プールから $W_{target}$ を除外したリストから、`random.sample(remaining_words, 3)` で3語を選定。
   - 選ばれた3語の meaning（モード1）または word（モード2）をダミーとする。
3. **シャッフル & 正解インデックスの保持**:
   - 正解＋ダミー3つの計4つを `random.shuffle()` で並び替え。
   - 正解のインデックス（0〜3）または正解テキストを保持。

### 3.3 正誤判定 & 履歴更新
* ユーザーが選んだ選択肢と正解を照合。
* 正解（○）または不正解（×）を判定。
* **統計更新処理**:
  * `total_attempts += 1`
  * 不正解の場合: `incorrect_count += 1`, `has_ever_failed = True`
  * `incorrect_rate = round(incorrect_count / total_attempts, 3)`
  * `last_result = "correct" if is_correct else "incorrect"`
  * `last_attempt_at = 現在日時 (JST ISO 8601)`
  * DB（Firestore または ローカルJSON）へ即時保存。

---

## 4. 状態管理（Session State 設計）

`st.session_state` で管理するキー定義：

| キー名 | 型 | 初期値 / 説明 |
| :--- | :--- | :--- |
| `user_email` | `str` | ログイン中のユーザーメール（DEV_MODE時は `"local_dev@example.com"`） |
| `is_authenticated` | `bool` | 認証・認可が通っているか |
| `current_view` | `str` | `"quiz"` \| `"review"` \| `"dictionary"` |
| `quiz_state` | `str` | `"select"`（モード選択） \| `"answering"`（問題回答中） \| `"answered"`（判定・解説表示中） \| `"result"`（10問終了結果） |
| `quiz_config` | `dict` | `{"mode": 1 or 2, "submode": "random"|"category"|"review", "category_name": str}` |
| `quiz_questions` | `list[dict]` | 抽出された10問の単語データおよびシャッフルされた4択肢リスト |
| `current_q_index` | `int` | 現在の問題番号（0 〜 9） |
| `current_selected_option` | `str` \| `None` | 現在の問題でユーザーが選択中の選択肢 |
| `session_results` | `list[dict]` | 各問の正誤、ユーザーの回答、正解を蓄積するリスト |
| `score` | `int` | 今回のセッションの正解数（0 〜 10） |

---

## 5. UIコンポーネント & スタイリング仕様 (`styles.py`)

### 5.1 デザインテーマ
* **世界観**: 親しみやすく見やすい小学生向け学習アプリ。
* **カラーパレット**:
  * メインカラー（Primary）: `#2E7D32`（知的なフォレストグリーン） / `#E8F5E9`（パステルグリーン背景）
  * サブカラー（Secondary）: `#1976D2`（信頼感のあるブルー） / `#E3F2FD`（パステルブルー背景）
  * 正解カラー: `#2E7D32`（緑色、太字、チェックアイコン）
  * 不正解カラー: `#D32F2F`（赤色、太字、バツアイコン）
  * 背景色: `#FAFAFA`（目に優しいオフホワイト）

### 5.2 スマートフォン最適化 CSS
```css
/* ボタンのタップ領域拡大（親指操作対応） */
div.stButton > button {
    border-radius: 12px;
    min-height: 52px;
    font-size: 16px;
    font-weight: bold;
    padding: 10px 16px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.08);
    transition: all 0.2s ease;
}

/* 4択ラジオボタンの押しやすさ向上 */
div[role="radiogroup"] > label {
    background-color: #FFFFFF;
    border: 2px solid #E0E0E0;
    border-radius: 12px;
    padding: 12px 16px;
    margin-bottom: 10px;
    display: flex;
    align-items: center;
}

/* 選択されたラジオボタンのハイライト */
div[role="radiogroup"] > label[data-checked="true"] {
    border-color: #4CAF50;
    background-color: #E8F5E9;
}

/* 問題文カード */
.question-card {
    background-color: #FFFFFF;
    border: 2px solid #81C784;
    border-radius: 16px;
    padding: 20px;
    margin-bottom: 20px;
    text-align: center;
    box-shadow: 0 4px 6px rgba(0,0,0,0.05);
}
```

### 5.3 UIヘルパー関数群 (`styles.py`)
* `apply_custom_styles()`: StreamlitアプリにカスタムCSSをインジェクト。
* `render_badge(text, badge_type)`: 難易度（並・中・高）やカテゴリ用バッジHTMLを生成。
* `render_question_card(content, label, subtext, category, difficulty)`: 問題文カードHTMLを生成。
* `render_result_banner(is_correct, correct_word, correct_meaning)`: 回答判定結果バナーHTMLを生成。
* `render_stat_card(label, value, subtext)`: 統計サマリーカードHTMLを生成。
* `render_word_detail_card(word, reading, category, difficulty, meaning, example, point)`: 辞典・苦手ノート用単語詳細カードHTMLを生成。
* `display_*`: 上記HTMLを `st.markdown(..., unsafe_allow_html=True)` で即時描画する各種表示ヘルパー。

### 5.4 各画面のUI仕様

#### 1. クイズ画面 (`views/quiz_view.py`)
* **モード選択画面**:
  * モード1（心情語 → 意味） / モード2（意味 → 心情語）の切り替え。
  * サブモード選択：
    * 全カテゴリランダム
    * カテゴリ固定（8分類からドロップダウン選択）
    * 苦手復習モード（10問未満の場合は無効化バッジとメッセージ表示）
  * 「クイズをスタート（全10問）」ボタン。
* **問題出題画面**:
  * プログレスバー（「第 3 / 10 問」）。
  * 問題文カード（モード1なら心情語、モード2なら意味）。
  * **ルビ（読み仮名）確認**: `st.popover("📖 読み方を確認")` でタップ時にふりがなを表示。
  * 4択ラジオボタン（未選択時は「回答する」ボタンを非活性または警告）。
  * 「回答する」ボタン。
* **回答・判定後画面**:
  * 大きな正解（⭕ 正解！）または不正解（❌ おしい！）のバナー。
  * 正解の選択肢を緑色枠で明示。
  * **解説表示**:
    * 「意味・ニュアンス」は常時表示。
    * `st.expander("💡 場面例 & つまずきポイントを開く")`: タップで文脈例と識別ポイントを展開。
  * 「次の問題へ ➔」ボタン（第10問目の後は「結果を見る ➔」）。
* **結果画面**:
  * 総合スコア（「10問中 8問正解！ たいへんよくできました💮」）。
  * 今回解いた10問の正誤一覧（単語、あなたの回答、正解）。
  * 「もう一度挑戦する」「トップに戻る」ボタン。

#### 2. 苦手ノート画面 (`views/review_view.py`)
* 過去に1回でも間違えた単語（`has_ever_failed == True`）の一覧表示。
* サマリーカード: 「苦手語句数: ○語」「総出題数: ○回」「総不正解率: ○%」。
* ソート切り替え: 「不正解回数が多い順」「不正解率が高い順」「単語番号順」。
* 各単語のアコーディオンを開くと、読み・難易度・意味・場面例・つまずきポイントを完全確認可能。

#### 3. 心情語辞典画面 (`views/dictionary_view.py`)
* 全272語の検索・閲覧。
* フィルタ: カテゴリ（全8種）、難易度（並・中・高）。
* 検索バー（単語名、読み、意味の全文検索）。
* 単語カード一覧。タップで詳細（意味、場面例、つまずきポイント）を展開。

---

## 6. バックエンド・DBアクセス設計 (`db.py`)

### 6.1 インターフェース定義
```python
class DatabaseInterface:
    def get_user_stats(self, email: str) -> dict[int, WordStat]:
        """全単語のユーザー統計を取得（未出題単語はデフォルト値）"""
        pass

    def record_attempt(self, email: str, word_no: int, word: str, category: str, is_correct: bool):
        """1問の回答結果を保存・更新"""
        pass

    def get_failed_words_stats(self, email: str) -> list[WordStat]:
        """過去に一度でも間違えた単語一覧を取得"""
        pass
```

### 6.2 ローカルモック実装 (`LocalJsonDB`)
* `local_data/mock_user_stats.json` にJSON形式で読み書き。
* GCP認証なしでローカル完全動作を担保。

### 6.3 Firestore実装 (`FirestoreDB`)
* `google-cloud-firestore` を使用。
* コレクション: `users/{email}/stats/{word_no}`。
* トランザクションまたはアトミックインクリメント（`firestore.Increment`）を用いて、同時書き込みにも耐えうる設計。

---

## 7. 認証 & セキュリティ仕様 (`auth.py`, `config.py`)

1. **ローカル開発モード (`DEV_MODE=True`)**:
   * Googleログインをバイパスし、擬似ユーザー `dev_user@example.com` で自動ログイン。
2. **本番モード (`DEV_MODE=False`)**:
   * Google OAuth 2.0 Webフロー。
   * Googleの認可エンドポイントにリダイレクト ➔ 認証コードをコールバックで受け取りトークン交換 ➔ ユーザーのメールアドレス取得。
   * **ホワイトリスト検証**:
     * `.env` の `ALLOWED_EMAILS`（カンマ区切り）に該当アドレスが存在するか確認。
     * 未許可アドレスの場合はエラーメッセージ画面を表示し、セッション破棄。

---

## 8. デプロイ・環境構築仕様

### 8.1 必要な環境変数 (`.env`)
```env
# アプリ動作モード (True: ローカル開発, False: 本番)
DEV_MODE=True

# GCP / OAuth 設定
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
REDIRECT_URI=https://your-cloud-run-url.run.app/

# ホワイトリスト（カンマ区切り）
ALLOWED_EMAILS=owner@gmail.com,family1@gmail.com

# Firestore 設定
GCP_PROJECT_ID=your-gcp-project-id
```

### 8.2 Cloud Run 用 Dockerfile 仕様
* ベースイメージ: `python:3.11-slim`
* ポート: 8080（Cloud Run標準）
* 起動コマンド: `streamlit run app.py --server.port=8080 --server.address=0.0.0.0 --server.enableCORS=false --server.enableXsrfProtection=false`

---

## 9. テスト & 検証計画

1. **単体テスト (`tests/test_quiz_logic.py`)**:
   * `all_words.csv` の読み込み検証（全272語、欠損値なし）。
   * 4択生成ロジックの検証（正解が必ず1つ含まれること、ダミー3つが重複しないこと）。
   * 正誤判定および統計計算（正解率計算）の検証。
   * 苦手復習モードの10問未満ガード条件の検証。
2. **ローカルUI動作確認**:
   * `DEV_MODE=True` で `streamlit run app.py` を実行。
   * モード1 / モード2 で10問回答し、結果画面、苦手ノート、辞典画面への遷移を検証。
