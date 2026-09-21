# 中学受験 国語 心情語対策アプリケーション (Emotion Words App)

中学入試（物語文・心情説明記述対策）で問われる重要心情語（全8カテゴリ・272語）を効率的にマスターするための Streamlit 学習アプリケーションです。

---

## 🌟 主な機能

1. **🎯 4択クイズ（学習モード）**:
   * **通常モード**: 全272語からランダムに10問出題。ふりがな・意味・場面例・つまずきやすいポイントの解説つき。
   * **苦手復習モード**: 過去に間違えた問題から優先的に10問を抽出して出題。
2. **📓 苦手ノート**:
   * 間違えたことのある単語の一覧、誤答回数、誤答率、最終回答結果を整理して確認。
3. **📚 心情語辞典**:
   * 全272語の横断検索、カテゴリ絞り込み、難易度（並・中・高）フィルタ、詳細カード展開。
4. **🔒 Google OAuth 2.0 & 家族ホワイトリスト認証**:
   * 事前登録された Gmail アドレスのみログイン可能。ご家族ごとの学習データを分離保存。

---

## 🚀 ローカル起動方法

```bash
# 仮想環境の有効化 (Windows)
.\env\Scripts\activate

# 依存パッケージのインストール
pip install -r requirements.txt

# ローカル開発サーバーの起動 (DEV_MODE=True で自動ログイン)
streamlit run app.py
```

ブラウザで `http://localhost:8501` にアクセスして利用します。

---

## ☁️ Google Cloud Run デプロイ

Google Cloud Run（`min-instances=0`）と Cloud Firestore の無料枠を活用し、**月額ほぼ 0 円** で運用可能です。

### デプロイスクリプトの実行
```powershell
# Windows (PowerShell)
.\deploy.ps1

# ドライラン（コマンド確認のみ）
.\deploy.ps1 -DryRun
```

```bash
# macOS / Linux / Cloud Shell (Bash)
chmod +x deploy.sh
./deploy.sh
```

詳細な設定手順や GCP Console でのリダイレクト URI 設定については、[docs/cloud_run_deployment.md](docs/cloud_run_deployment.md) を参照してください。

---

## 🧪 テスト実行

```bash
pytest
```
