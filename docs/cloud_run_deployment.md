# Google Cloud Run デプロイ＆運用マニュアル

中学受験 国語 心情語対策アプリケーションの Google Cloud Run へのデプロイ手順書および運用マニュアルです。

---

## 1. システム構成・コスト仕様

* **ホスティング**: Google Cloud Run（完全マネージド型サーバーレスコンテナ）
* **リージョン**: `asia-northeast1`（東京）
* **データベース**: Google Cloud Firestore（Nativeモード、東京リージョン）
* **認証方式**: Google OAuth 2.0（事前許可 Gmail アドレスのみアクセス可能なホワイトリスト方式）
* **運用コスト**:
  * Cloud Run: `min-instances=0`（アクセスがないときはインスタンス数ゼロ、コールドスタート時に自動起動）
  * Firestore: 無料枠内（月間 1GB 保存、1日あたり 50,000回 読取 / 20,000回 書込）
  * **月額目安**: 個人・ご家族での利用であれば **月額ほぼ 0 円** で運用可能。

---

## 2. 前提条件と準備状況

本プロジェクト（`kokugo-emotion-words`）では、以下の準備が完了しています：

1. **GCP プロジェクト**: `kokugo-emotion-words`（プロジェクト番号: `353453856897`）
2. **Cloud Firestore データベース**: `projects/kokugo-emotion-words/databases/(default)`（Native モード、`asia-northeast1`、稼働中）
3. **必要な GCP API**:
   * `run.googleapis.com` (Cloud Run Admin API)
   * `cloudbuild.googleapis.com` (Cloud Build API)
   * `firestore.googleapis.com` (Cloud Firestore API)
   * `artifactregistry.googleapis.com` (Artifact Registry API)
4. **OAuth 2.0 クライアント認証情報**:
   * `env/gcp.env` に登録済み（クライアントID、クライアントシークレット、ホワイトリストメールアドレス）

---

## 3. デプロイ手順

### 方法 A: デプロイスクリプトを実行する（推奨）

リポジトリルートに配置された `deploy.ps1`（Windows）または `deploy.sh`（macOS / Linux / Cloud Shell）を実行します。

#### Windows (PowerShell)
```powershell
# ドライラン（コマンド確認のみ）
.\deploy.ps1 -DryRun

# 実際のデプロイ実行
.\deploy.ps1
```

#### macOS / Linux / Cloud Shell (Bash)
```bash
chmod +x deploy.sh
./deploy.sh
```

---

### 方法 B: `gcloud` コマンドで手動デプロイする

```powershell
cmd /c gcloud run deploy kokugo-emotion-words `
  --source . `
  --project kokugo-emotion-words `
  --region asia-northeast1 `
  --platform managed `
  --allow-unauthenticated `
  --min-instances 0 `
  --max-instances 2 `
  --memory 512Mi `
  --cpu 1 `
  --set-env-vars DEV_MODE=False,GCP_PROJECT_ID=kokugo-emotion-words,GOOGLE_CLIENT_ID="[クライアントID]",GOOGLE_CLIENT_SECRET="[シークレット]",ALLOWED_EMAILS="youichirou.uka@gmail.com,asacoccocco@gmail.com,souichirou.uka@gmail.com,souichirou.uka.1111@gmail.com",REDIRECT_URI="http://localhost:8501/"
```

> **※注意**: 初回デプロイ時はまだ Cloud Run の本番 URL が確定していないため、デプロイ完了後に発行された本番 URL で `REDIRECT_URI` を更新します（後述）。

---

## 4. デプロイ後の重要設定（Google OAuth 2.0 連携）

Cloud Run にデプロイされると、以下のようなサービス URL が発行されます：
`https://kokugo-emotion-words-xxxxxx-an.a.run.app`

### ステップ 1: GCP Console でリダイレクト URI を追加
1. [Google Cloud Console - 認証情報](https://console.cloud.google.com/apis/credentials?project=kokugo-emotion-words) を開く。
2. 作成済みの **OAuth 2.0 クライアント ID** をクリックして編集画面を開く。
3. **[承認済みの JavaScript 生成元]** に追加：
   * `https://kokugo-emotion-words-xxxxxx-an.a.run.app`
4. **[承認済みのリダイレクト URI]** に追加：
   * `https://kokugo-emotion-words-xxxxxx-an.a.run.app/` （末尾スラッシュを含める）
5. **[保存]** をクリック。

### ステップ 2: Cloud Run サービスの環境変数 `REDIRECT_URI` を更新
`deploy.ps1` を実行した場合は自動的に更新されます。手動で行う場合は以下を実行します：

```powershell
cmd /c gcloud run services update kokugo-emotion-words `
  --project kokugo-emotion-words `
  --region asia-northeast1 `
  --update-env-vars "REDIRECT_URI=https://kokugo-emotion-words-xxxxxx-an.a.run.app/"
```

また、ローカルの `env/gcp.env` の `REDIRECT_URI` も同様に更新しておくと安心です。

---

## 5. 動作確認と確認ポイント

1. ブラウザで `https://kokugo-emotion-words-xxxxxx-an.a.run.app` にアクセス。
2. **ログイン画面の確認**:
   * Google ログインボタンが表示されていること。
3. **ホワイトリスト認証の確認**:
   * `ALLOWED_EMAILS` に含まれる Gmail アドレスでログイン ➔ クイズトップ画面が表示されること。
   * 含まれないアドレスでログイン ➔ 「アクセス権限がありません」と表示されること。
4. **Firestore 永続化の確認**:
   * クイズを数問回答後、苦手ノート画面や Firestore コンソールで `users/{email}/stats/{word_no}` にデータが保存されていることを確認。

---

## 6. 運用・保守コマンド

### ログの確認 (Cloud Logging)
```powershell
# リアルタイムログストリーム
cmd /c gcloud run services logs tail kokugo-emotion-words --project kokugo-emotion-words --region asia-northeast1
```

### サービスの削除（必要時）
```powershell
cmd /c gcloud run services delete kokugo-emotion-words --project kokugo-emotion-words --region asia-northeast1 --quiet
```
