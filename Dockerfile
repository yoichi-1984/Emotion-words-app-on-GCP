# ==============================================================================
# Google Cloud Run 用 Dockerfile
# 中学受験 国語 心情語対策アプリケーション (Streamlit)
# ==============================================================================

# 公式 Python 3.11 スリムイメージ（軽量かつ高セキュリティ）
FROM python:3.11-slim

# 環境変数の設定
# - PYTHONUNBUFFERED: ログをバッファリングせず即時出力（Cloud Logging でリアルタイム確認）
# - PYTHONDONTWRITEBYTECODE: コンテナ内での .pyc 一時ファイル生成を抑制
# - PORT: Cloud Run 標準のポート 8080
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

WORKDIR /app

# ヘルスチェック用 curl のインストールと apt キャッシュの削除
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 依存パッケージ定義のコピーとインストール（キャッシュ効率化）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションソースコードおよびマスターデータのコピー
COPY . .

# Cloud Run 標準ポート（8080）の公開
EXPOSE 8080

# コンテナヘルスチェック（Streamlit 内部の _stcore/health エンドポイントを利用）
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl --fail http://localhost:${PORT:-8080}/_stcore/health || exit 1

# Cloud Run 起動コマンド
# 動的に Cloud Run から割り当てられる PORT 環境変数（デフォルト8080）を反映
ENTRYPOINT ["sh", "-c", "exec streamlit run app.py --server.port=${PORT:-8080} --server.address=0.0.0.0 --server.enableCORS=false --server.enableXsrfProtection=false --server.headless=true"]
