"""tests/test_deployment.py

Dockerfile, .dockerignore, .streamlit/config.toml, およびデプロイスクリプトの妥当性を検証するテスト。
Cloud Run 要件（ポート8080、ベースイメージ、ヘルスチェック、機密情報の除外設定等）を網羅する。
"""

from pathlib import Path
import re
import pytest

from auth import get_allowed_emails, get_oauth_config, is_dev_mode
from db import FirestoreDB, LocalJsonDB, get_db


def test_dockerfile_configuration():
    """Dockerfile の構成と Cloud Run 要件の整合性を検証"""
    dockerfile_path = Path("Dockerfile")
    assert dockerfile_path.exists(), "Dockerfile が存在しません"

    content = dockerfile_path.read_text(encoding="utf-8")

    # ベースイメージ
    assert "FROM python:3.11-slim" in content, "ベースイメージは python:3.11-slim である必要があります"

    # ポート設定
    assert "EXPOSE 8080" in content, "Cloud Run 標準ポート 8080 が公開されていません"
    assert "PORT=8080" in content, "PORT=8080 環境変数が設定されていません"

    # ヘルスチェック
    assert "HEALTHCHECK" in content, "HEALTHCHECK が定義されていません"
    assert "_stcore/health" in content, "Streamlit のヘルスチェックエンドポイントが指定されていません"

    # 起動コマンド
    assert "streamlit run app.py" in content, "Streamlit 起動コマンドが指定されていません"
    assert "--server.address=0.0.0.0" in content, "0.0.0.0 バインドが指定されていません"
    assert "--server.enableCORS=false" in content, "CORS 無効化設定が必要です"
    assert "--server.enableXsrfProtection=false" in content, "XSRF 無効化設定が必要です"


def test_dockerignore_configuration():
    """.dockerignore による不要ファイル・機密情報の除外設定を検証"""
    dockerignore_path = Path(".dockerignore")
    assert dockerignore_path.exists(), ".dockerignore が存在しません"

    content = dockerignore_path.read_text(encoding="utf-8")
    ignored_patterns = [line.strip() for line in content.splitlines() if line.strip() and not line.startswith("#")]

    # 機密情報・環境変数
    assert ".env" in ignored_patterns, ".env が除外されていません"
    assert "*.env" in ignored_patterns, "*.env が除外されていません"
    assert "local_data/" in ignored_patterns, "local_data/ が除外されていません"
    assert "credentials.json" in ignored_patterns, "credentials.json が除外されていません"

    # Git および一時ファイル
    assert ".git" in ignored_patterns, ".git が除外されていません"
    assert "tests/" in ignored_patterns, "tests/ が除外されていません"
    assert ".pytest_cache/" in ignored_patterns, ".pytest_cache/ が除外されていません"

    # 仮想環境
    assert any("env" in p for p in ignored_patterns), "仮想環境ディレクトリが除外されていません"

    # 単語マスターCSV（all_words.csv）自体は除外されていないこと
    assert "all_words.csv" not in ignored_patterns, "all_words.csv が誤って除外されています"


def test_streamlit_config_toml():
    """.streamlit/config.toml の構成を検証"""
    config_path = Path(".streamlit/config.toml")
    assert config_path.exists(), ".streamlit/config.toml が存在しません"

    content = config_path.read_text(encoding="utf-8")

    assert "port = 8080" in content, "ポート 8080 が指定されていません"
    assert "headless = true" in content, "headless = true が指定されていません"
    assert "address = \"0.0.0.0\"" in content, "address = 0.0.0.0 が指定されていません"
    assert "gatherUsageStats = false" in content, "gatherUsageStats = false が指定されていません"


def test_deploy_scripts_exist_and_valid():
    """deploy.ps1 および deploy.sh の存在と主要設定値を検証"""
    ps1_path = Path("deploy.ps1")
    sh_path = Path("deploy.sh")

    assert ps1_path.exists(), "deploy.ps1 が存在しません"
    assert sh_path.exists(), "deploy.sh が存在しません"

    ps1_content = ps1_path.read_text(encoding="utf-8")
    sh_content = sh_path.read_text(encoding="utf-8")

    # プロジェクト名とリージョン
    assert "kokugo-emotion-words" in ps1_content
    assert "asia-northeast1" in ps1_content
    assert "--min-instances" in ps1_content

    assert "kokugo-emotion-words" in sh_content
    assert "asia-northeast1" in sh_content
    assert "--min-instances" in sh_content


def test_auth_and_db_quote_and_empty_handling(monkeypatch):
    """auth.py および db.py が引用符付き環境変数や空文字 DEV_MODE を適切に処理することを検証"""
    # 1. DEV_MODE が空文字の場合は安全に True（開発モード）と判定
    monkeypatch.setenv("DEV_MODE", "")
    assert is_dev_mode() is True

    # 2. 引用符付きのメールアドレスとクライアントIDの処理
    monkeypatch.setenv("ALLOWED_EMAILS", ' "test1@gmail.com" , \'test2@gmail.com\' ')
    allowed = get_allowed_emails()
    assert allowed == ["test1@gmail.com", "test2@gmail.com"]

    monkeypatch.setenv("GOOGLE_CLIENT_ID", ' "custom-client-id" ')
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", " 'custom-secret' ")
    monkeypatch.setenv("REDIRECT_URI", ' "https://example.run.app/" ')

    cfg = get_oauth_config()
    assert cfg["client_id"] == "custom-client-id"
    assert cfg["client_secret"] == "custom-secret"
    assert cfg["redirect_uri"] == "https://example.run.app/"
    assert cfg["is_configured"] is True

    # 3. db.get_db が DEV_MODE="" のときに LocalJsonDB を返すこと
    monkeypatch.setenv("DEV_MODE", "")
    db_instance = get_db(dev_mode=None)
    assert isinstance(db_instance, LocalJsonDB)

    # 4. db.FirestoreDB が引用符付き GCP_PROJECT_ID をクリーンに取得すること
    monkeypatch.setenv("GCP_PROJECT_ID", ' "kokugo-emotion-words" ')
    firestore_db = FirestoreDB(project_id=None, client="mock_client")
    assert firestore_db.project_id == "kokugo-emotion-words"
