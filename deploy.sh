#!/usr/bin/env bash
# ==============================================================================
# Google Cloud Run への自動デプロイスクリプト (Bash)
# ==============================================================================
set -euo pipefail

PROJECT_ID="${1:-kokugo-emotion-words}"
REGION="${2:-asia-northeast1}"
SERVICE_NAME="${3:-kokugo-emotion-words}"

echo "=========================================================="
echo " 中学受験 国語 心情語対策アプリ - Cloud Run デプロイツール "
echo "=========================================================="

ENV_FILE=""
if [ -f "env/gcp.env" ]; then
    ENV_FILE="env/gcp.env"
elif [ -f ".env" ]; then
    ENV_FILE=".env"
fi

if [ -n "$ENV_FILE" ]; then
    echo "[INFO] 設定ファイルを読み込み中: $ENV_FILE"
    # set -a で export して source
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
fi

PROJECT_ID="${GCP_PROJECT_ID:-$PROJECT_ID}"
CLIENT_ID="${GOOGLE_CLIENT_ID:-}"
CLIENT_SECRET="${GOOGLE_CLIENT_SECRET:-}"
ALLOWED_EMAILS="${ALLOWED_EMAILS:-}"
REDIRECT_URI="${REDIRECT_URI:-http://localhost:8501/}"

# 空白・クォートのトリム
CLIENT_ID=$(echo "$CLIENT_ID" | sed -e 's/^[ "]*//' -e 's/[ "]*$//')
CLIENT_SECRET=$(echo "$CLIENT_SECRET" | sed -e 's/^[ "]*//' -e 's/[ "]*$//')

echo ""
echo "【設定パラメータ】"
echo "  Project ID      : $PROJECT_ID"
echo "  Region          : $REGION"
echo "  Service Name    : $SERVICE_NAME"
echo "  Allowed Emails  : $ALLOWED_EMAILS"
echo "  Current Redirect: $REDIRECT_URI"
echo ""

if [ -z "$CLIENT_ID" ] || [ -z "$CLIENT_SECRET" ] || [ -z "$ALLOWED_EMAILS" ]; then
    echo "[ERROR] 必要な環境変数 (GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, ALLOWED_EMAILS) が不足しています。"
    exit 1
fi

IMAGE_TAG="gcr.io/$PROJECT_ID/$SERVICE_NAME:latest"
TMP_ENV_FILE="local_data/cloudrun_env.yaml"
mkdir -p local_data
cat <<EOF > "$TMP_ENV_FILE"
DEV_MODE: "False"
GCP_PROJECT_ID: "$PROJECT_ID"
GOOGLE_CLIENT_ID: "$CLIENT_ID"
GOOGLE_CLIENT_SECRET: "$CLIENT_SECRET"
ALLOWED_EMAILS: "$ALLOWED_EMAILS"
REDIRECT_URI: "$REDIRECT_URI"
EOF

echo "[STEP 1] Cloud Build によるイメージビルド中 ($IMAGE_TAG)..."
gcloud builds submit --tag "$IMAGE_TAG" --project "$PROJECT_ID"

echo ""
echo "[STEP 2] Cloud Run へコンテナ配備中..."
gcloud run deploy "$SERVICE_NAME" \
    --image "$IMAGE_TAG" \
    --project "$PROJECT_ID" \
    --region "$REGION" \
    --platform managed \
    --allow-unauthenticated \
    --min-instances 0 \
    --max-instances 2 \
    --memory 512Mi \
    --cpu 1 \
    --env-vars-file "$TMP_ENV_FILE"


SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" --project "$PROJECT_ID" --region "$REGION" --format "value(status.url)")

echo ""
echo "=========================================================="
echo " 🎉 Cloud Run デプロイが正常に完了しました！"
echo " サービス URL: $SERVICE_URL"
echo "=========================================================="
echo ""
echo "【重要: 次の手順（Google OAuth 2.0 連携設定）】"
echo "1. Google Cloud Console の [APIとサービス] > [認証情報] を開く:"
echo "   https://console.cloud.google.com/apis/credentials?project=$PROJECT_ID"
echo "2. OAuth 2.0 クライアント ID を選択"
echo "3. [承認済みのリダイレクト URI] に以下を追加:"
echo "   $SERVICE_URL/"
echo "4. [承認済みの JavaScript 生成元] に以下を追加:"
echo "   $SERVICE_URL"
echo ""

if [ "$REDIRECT_URI" != "$SERVICE_URL/" ] && [ "$REDIRECT_URI" != "$SERVICE_URL" ]; then
    echo "[INFO] Cloud Run サービスの REDIRECT_URI を最新 URL ($SERVICE_URL/) に自動更新します..."
    gcloud run services update "$SERVICE_NAME" --project "$PROJECT_ID" --region "$REGION" --update-env-vars "REDIRECT_URI=$SERVICE_URL/"
    echo "[OK] REDIRECT_URI を $SERVICE_URL/ に更新しました。"
fi

echo ""
echo "デプロイ完了: $SERVICE_URL"
