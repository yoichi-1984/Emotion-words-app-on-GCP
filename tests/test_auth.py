"""tests/test_auth.py

auth.py の単体テスト。
Google OAuth 2.0 Webフロー、Gmailホワイトリスト判定、環境変数判定、
コールバック処理、およびセッション認証状態更新を包括的に検証する。
"""

import os
from unittest.mock import MagicMock, patch
import pytest
import requests
import streamlit as st

from auth import (
    authenticate_user,
    exchange_code_for_token,
    get_allowed_emails,
    get_google_auth_url,
    get_oauth_config,
    get_user_info_from_token,
    is_dev_mode,
    is_email_allowed,
    logout_user,
    process_oauth_callback,
)


@pytest.fixture(autouse=True)
def clear_streamlit_session():
    """各テスト前後に session_state および query_params を初期化する。"""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    if hasattr(st, "query_params"):
        st.query_params.clear()
    yield
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    if hasattr(st, "query_params"):
        st.query_params.clear()


# ==============================================================================
# 環境変数・ホワイトリストのテスト
# ==============================================================================
def test_is_dev_mode():
    """DEV_MODE 環境変数の各パターンの判定を検証"""
    with patch.dict(os.environ, {"DEV_MODE": "True"}):
        assert is_dev_mode() is True

    with patch.dict(os.environ, {"DEV_MODE": "true"}):
        assert is_dev_mode() is True

    with patch.dict(os.environ, {"DEV_MODE": "1"}):
        assert is_dev_mode() is True

    with patch.dict(os.environ, {"DEV_MODE": "yes"}):
        assert is_dev_mode() is True

    with patch.dict(os.environ, {"DEV_MODE": "False"}):
        assert is_dev_mode() is False

    with patch.dict(os.environ, {"DEV_MODE": "0"}):
        assert is_dev_mode() is False

    with patch.dict(os.environ, {"DEV_MODE": "no"}):
        assert is_dev_mode() is False

    # 未設定時はデフォルト True
    with patch.dict(os.environ, {}, clear=True):
        assert is_dev_mode() is True


def test_get_allowed_emails():
    """ALLOWED_EMAILS の小文字正規化とパースを検証"""
    with patch.dict(
        os.environ,
        {"ALLOWED_EMAILS": " User1@Gmail.Com, USER2@GMAIL.COM , user3@example.com "},
    ):
        emails = get_allowed_emails()
        assert emails == ["user1@gmail.com", "user2@gmail.com", "user3@example.com"]

    with patch.dict(os.environ, {"ALLOWED_EMAILS": ""}):
        assert get_allowed_emails() == []


def test_is_email_allowed():
    """is_email_allowed のホワイトリスト照合を検証"""
    whitelist = ["allowed1@gmail.com", "allowed2@gmail.com"]

    # 許可リスト内のアドレス（大文字混じり・トリム考慮）
    assert is_email_allowed("allowed1@gmail.com", whitelist) is True
    assert is_email_allowed(" Allowed1@GMAIL.COM ", whitelist) is True
    assert is_email_allowed("allowed2@gmail.com", whitelist) is True

    # 許可リスト外のアドレス
    assert is_email_allowed("stranger@gmail.com", whitelist) is False
    assert is_email_allowed("", whitelist) is False
    assert is_email_allowed(None, whitelist) is False

    # ホワイトリスト空の場合は拒否
    assert is_email_allowed("allowed1@gmail.com", []) is False


# ==============================================================================
# OAuth 設定と認可 URL 生成のテスト
# ==============================================================================
def test_get_oauth_config_valid():
    """正常なOAuth環境変数設定の取得検証"""
    env_vars = {
        "GOOGLE_CLIENT_ID": "actual-client-id-12345.apps.googleusercontent.com",
        "GOOGLE_CLIENT_SECRET": "actual-secret-67890",
        "REDIRECT_URI": "https://app-url.run.app/",
    }
    with patch.dict(os.environ, env_vars):
        cfg = get_oauth_config()
        assert cfg["is_configured"] is True
        assert cfg["client_id"] == env_vars["GOOGLE_CLIENT_ID"]
        assert cfg["client_secret"] == env_vars["GOOGLE_CLIENT_SECRET"]
        assert cfg["redirect_uri"] == env_vars["REDIRECT_URI"]


def test_get_oauth_config_invalid_placeholders():
    """プレースホルダーや未設定時の検証"""
    env_vars = {
        "GOOGLE_CLIENT_ID": "your-client-id.apps.googleusercontent.com",
        "GOOGLE_CLIENT_SECRET": "your-client-secret",
        "REDIRECT_URI": "https://your-cloud-run-url.run.app/",
    }
    with patch.dict(os.environ, env_vars):
        cfg = get_oauth_config()
        assert cfg["is_configured"] is False

    with patch.dict(os.environ, {}, clear=True):
        cfg = get_oauth_config()
        assert cfg["is_configured"] is False


def test_get_google_auth_url():
    """認可 URL 生成の検証"""
    valid_env = {
        "GOOGLE_CLIENT_ID": "test-client-id",
        "GOOGLE_CLIENT_SECRET": "test-client-secret",
        "REDIRECT_URI": "https://example.com/oauth2callback",
    }
    with patch.dict(os.environ, valid_env):
        url = get_google_auth_url(state="test_state_123")
        assert url is not None
        assert url.startswith("https://accounts.google.com/o/oauth2/v2/auth?")
        assert "client_id=test-client-id" in url
        assert "redirect_uri=https%3A%2F%2Fexample.com%2Foauth2callback" in url
        assert "response_type=code" in url
        assert "state=test_state_123" in url
        assert "prompt=select_account" in url

    # 設定無効時は None
    with patch.dict(os.environ, {}, clear=True):
        assert get_google_auth_url() is None


# ==============================================================================
# トークン交換・ユーザープロファイル取得のテスト
# ==============================================================================
@patch("requests.post")
def test_exchange_code_for_token_success(mock_post):
    """認可コードからトークンへの交換成功"""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "access_token": "mock_access_token",
        "expires_in": 3600,
        "token_type": "Bearer",
    }
    mock_post.return_value = mock_resp

    config = {
        "client_id": "test_id",
        "client_secret": "test_sec",
        "redirect_uri": "https://test.app",
        "is_configured": True,
    }
    res = exchange_code_for_token("valid_code_123", config=config)
    assert res is not None
    assert res["access_token"] == "mock_access_token"
    mock_post.assert_called_once()


@patch("requests.post")
def test_exchange_code_for_token_failure(mock_post):
    """認可コード交換失敗（400エラーまたは例外発生）"""
    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.text = "invalid_grant"
    mock_post.return_value = mock_resp

    config = {
        "client_id": "test_id",
        "client_secret": "test_sec",
        "redirect_uri": "https://test.app",
        "is_configured": True,
    }
    assert exchange_code_for_token("bad_code", config=config) is None

    # 通信例外発生時
    mock_post.side_effect = requests.RequestException("Connection error")
    assert exchange_code_for_token("code_error", config=config) is None


def test_exchange_code_for_token_invalid_config():
    """設定が無効またはコードが空の場合は None"""
    assert exchange_code_for_token("", config={"is_configured": True}) is None
    assert exchange_code_for_token("code", config={"is_configured": False}) is None


@patch("requests.get")
def test_get_user_info_from_token_success(mock_get):
    """アクセストークンによるユーザー情報取得成功"""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "email": "student@gmail.com",
        "name": "Hanako Yamada",
        "picture": "https://lh3.googleusercontent.com/photo.jpg",
    }
    mock_get.return_value = mock_resp

    user_info = get_user_info_from_token("valid_token")
    assert user_info is not None
    assert user_info["email"] == "student@gmail.com"
    assert user_info["name"] == "Hanako Yamada"


@patch("requests.get")
def test_get_user_info_from_token_failure(mock_get):
    """ユーザー情報取得失敗（401エラーまたは例外）"""
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_get.return_value = mock_resp

    assert get_user_info_from_token("invalid_token") is None

    mock_get.side_effect = requests.RequestException("Timeout")
    assert get_user_info_from_token("timeout_token") is None

    # トークンが空
    assert get_user_info_from_token("") is None


# ==============================================================================
# コールバック処理および認証ハンドリングのテスト
# ==============================================================================
def test_process_oauth_callback_with_error():
    """URLパラメータに error が含まれる場合"""
    st.query_params["error"] = "access_denied"

    result = process_oauth_callback()
    assert result is None
    assert "access_denied" in st.session_state.auth_error
    assert "error" not in st.query_params


def test_process_oauth_callback_no_params():
    """URLパラメータに何も無い場合"""
    assert process_oauth_callback() is None


@patch("auth.exchange_code_for_token")
@patch("auth.get_user_info_from_token")
def test_process_oauth_callback_success(mock_get_info, mock_exchange):
    """OAuthコールバック受信時の正常なトークン交換とユーザー情報取得"""
    st.query_params["code"] = "auth_code_xyz"

    mock_exchange.return_value = {"access_token": "token_123"}
    mock_get_info.return_value = {"email": "family@gmail.com", "name": "Family"}

    user_info = process_oauth_callback()
    assert user_info == {"email": "family@gmail.com", "name": "Family"}
    assert "code" not in st.query_params


@patch("auth.exchange_code_for_token", return_value=None)
def test_process_oauth_callback_token_fail(mock_exchange):
    """トークン交換失敗時のエラーハンドリング"""
    st.query_params["code"] = "invalid_code"

    result = process_oauth_callback()
    assert result is None
    assert "認証トークンの取得に失敗しました" in st.session_state.auth_error
    assert "code" not in st.query_params


def test_authenticate_user_allowed():
    """ホワイトリスト許可アカウントの認証成功"""
    with patch("auth.get_allowed_emails", return_value=["allowed@gmail.com"]):
        success, msg = authenticate_user("Allowed@Gmail.COM")
        assert success is True
        assert st.session_state.is_authenticated is True
        assert st.session_state.user_email == "allowed@gmail.com"
        assert st.session_state.auth_error is None


def test_authenticate_user_denied():
    """ホワイトリスト未登録アカウントの認証拒否"""
    with patch("auth.get_allowed_emails", return_value=["allowed@gmail.com"]):
        success, msg = authenticate_user("unknown@gmail.com")
        assert success is False
        assert st.session_state.is_authenticated is False
        assert "アクセス権限がありません" in msg
        assert "アクセス権限がありません" in st.session_state.auth_error


def test_authenticate_user_empty():
    """空メールアドレスでの認証試行"""
    success, msg = authenticate_user("")
    assert success is False
    assert st.session_state.is_authenticated is False
    assert "メールアドレスが取得できませんでした" in msg


def test_logout_user():
    """ログアウト処理でセッション状態が初期化されることを検証"""
    st.session_state.is_authenticated = True
    st.session_state.user_email = "test@gmail.com"
    st.session_state.auth_error = "some error"
    st.session_state.current_view = "review"
    st.query_params["code"] = "xyz"

    logout_user()

    assert st.session_state.is_authenticated is False
    assert st.session_state.user_email == ""
    assert st.session_state.auth_error is None
    assert st.session_state.current_view == "quiz"
    assert "code" not in st.query_params
