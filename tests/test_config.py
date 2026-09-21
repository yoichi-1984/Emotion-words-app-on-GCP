"""tests/test_config.py

config.py の環境変数読み込み、DEV_MODE判定、ホワイトリスト検証、OAuth設定、GCPプロジェクトID取得のテスト。
"""

import os
from unittest.mock import patch

import pytest

import config


class TestConfigModule:
    """config モジュールの機能検証"""

    def test_is_dev_mode_delegation(self, monkeypatch):
        monkeypatch.setenv("DEV_MODE", "True")
        assert config.is_dev_mode() is True

        monkeypatch.setenv("DEV_MODE", "False")
        assert config.is_dev_mode() is False

    def test_get_allowed_emails_delegation(self, monkeypatch):
        monkeypatch.setenv("ALLOWED_EMAILS", "user1@example.com, user2@example.com")
        emails = config.get_allowed_emails()
        assert emails == ["user1@example.com", "user2@example.com"]

    def test_is_email_allowed_delegation(self, monkeypatch):
        monkeypatch.setenv("ALLOWED_EMAILS", "owner@example.com")
        assert config.is_email_allowed("owner@example.com") is True
        assert config.is_email_allowed("hacker@example.com") is False

    def test_get_oauth_config_delegation(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
        monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-client-secret")
        monkeypatch.setenv("REDIRECT_URI", "https://test.run.app/")
        cfg = config.get_oauth_config()
        assert cfg["client_id"] == "test-client-id"
        assert cfg["client_secret"] == "test-client-secret"
        assert cfg["redirect_uri"] == "https://test.run.app/"
        assert cfg["is_configured"] is True

    def test_get_gcp_project_id(self, monkeypatch):
        monkeypatch.setenv("GCP_PROJECT_ID", "my-kokugo-project")
        assert config.get_gcp_project_id() == "my-kokugo-project"

        monkeypatch.setenv("GCP_PROJECT_ID", ' "quoted-project" ')
        assert config.get_gcp_project_id() == "quoted-project"

        monkeypatch.delenv("GCP_PROJECT_ID", raising=False)
        assert config.get_gcp_project_id() is None
