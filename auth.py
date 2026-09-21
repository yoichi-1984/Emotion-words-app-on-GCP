"""auth.py

Google OAuth 2.0 Web フローおよび Gmail ホワイトリスト検証モジュール。
ローカル開発モード（DEV_MODE）と本番 Google OAuth 認証を切り替えて管理する。
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Tuple
import urllib.parse

import requests
import streamlit as st

logger = logging.getLogger(__name__)

# ==============================================================================
# Google OAuth 2.0 エンドポイント & 定数定義
# ==============================================================================
GOOGLE_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_ENDPOINT = "https://www.googleapis.com/oauth2/v2/userinfo"

DEFAULT_DEV_EMAIL = "local_dev@example.com"
SAMPLE_DEV_USERS = [
    "local_dev@example.com",
    "student_hanako@example.com",
    "student_taro@example.com",
]

OAUTH_SCOPES = ["openid", "email", "profile"]


# ==============================================================================
# 環境・設定ヘルパー関数
# ==============================================================================
def is_dev_mode() -> bool:
    """ローカル開発モード（DEV_MODE）が有効かどうかを判定する。

    Returns:
        bool: DEV_MODE 環境変数が True / 1 / t / yes の場合は True、それ以外は False。
    """
    dev_mode_env = os.getenv("DEV_MODE", "True").strip().lower()
    return dev_mode_env in ("true", "1", "t", "yes")


def get_allowed_emails() -> List[str]:
    """ホワイトリストに登録された許可メールアドレス一覧を取得する。

    大文字・小文字のブレを防止するため、すべて小文字に正規化して返す。

    Returns:
        List[str]: 正規化された許可メールアドレスのリスト
    """
    raw_emails = os.getenv("ALLOWED_EMAILS", "")
    if not raw_emails:
        return []
    return [e.strip().lower() for e in raw_emails.split(",") if e.strip()]


def is_email_allowed(email: str, allowed_emails: Optional[List[str]] = None) -> bool:
    """指定されたメールアドレスがホワイトリストに登録されているかを判定する。

    Args:
        email: 判定対象のメールアドレス
        allowed_emails: 許可アドレスリスト（省略時は get_allowed_emails() を使用）

    Returns:
        bool: 許可されている場合は True、それ以外は False
    """
    if not email:
        return False

    targets = allowed_emails if allowed_emails is not None else get_allowed_emails()
    if not targets:
        # ホワイトリストが未設定の場合は安全のため全拒否
        return False

    normalized_email = email.strip().lower()
    return normalized_email in targets


def get_oauth_config() -> Dict[str, Any]:
    """Google OAuth 2.0 連携に必要な環境変数を取得し、設定妥当性を検証する。

    Returns:
        Dict[str, Any]: OAuth設定辞書 (client_id, client_secret, redirect_uri, is_configured)
    """
    client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
    redirect_uri = os.getenv("REDIRECT_URI", "").strip()

    # プレースホルダーまたは空文字列でないことを検証
    placeholder_tokens = ("your-client-id", "your-client-secret", "your-cloud-run-url")
    is_valid = bool(
        client_id
        and client_secret
        and redirect_uri
        and not any(p in client_id or p in client_secret or p in redirect_uri for p in placeholder_tokens)
    )

    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "is_configured": is_valid,
    }


# ==============================================================================
# Google OAuth 2.0 Web フロー処理
# ==============================================================================
def get_google_auth_url(state: Optional[str] = None) -> Optional[str]:
    """Google OAuth 2.0 の認可画面 URL を生成する。

    Args:
        state: CSRF対策用のセッション固有ステート文字列（任意）

    Returns:
        Optional[str]: 認可用 URL。OAuth設定が無効な場合は None。
    """
    config = get_oauth_config()
    if not config["is_configured"]:
        return None

    params = {
        "client_id": config["client_id"],
        "redirect_uri": config["redirect_uri"],
        "response_type": "code",
        "scope": " ".join(OAUTH_SCOPES),
        "access_type": "online",
        "prompt": "select_account",
    }
    if state:
        params["state"] = state

    query_string = urllib.parse.urlencode(params)
    return f"{GOOGLE_AUTH_ENDPOINT}?{query_string}"


def exchange_code_for_token(code: str, config: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """認可コード（Authorization Code）をアクセストークンと交換する。

    Args:
        code: Google認可画面から返却された authorization code
        config: OAuth設定辞書（省略時は get_oauth_config() を使用）

    Returns:
        Optional[Dict[str, Any]]: トークンレスポンス辞書（access_token等）。失敗時は None。
    """
    cfg = config or get_oauth_config()
    if not cfg["is_configured"] or not code:
        logger.warning("OAuth設定が無効または認可コードが空です。")
        return None

    payload = {
        "code": code,
        "client_id": cfg["client_id"],
        "client_secret": cfg["client_secret"],
        "redirect_uri": cfg["redirect_uri"],
        "grant_type": "authorization_code",
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    try:
        response = requests.post(
            GOOGLE_TOKEN_ENDPOINT,
            data=payload,
            headers=headers,
            timeout=10,
        )
        if response.status_code == 200:
            return response.json()
        else:
            logger.error("トークン交換失敗: status=%s, body=%s", response.status_code, response.text)
            return None
    except requests.RequestException as e:
        logger.error("トークン交換通信エラー: %s", e)
        return None


def get_user_info_from_token(access_token: str) -> Optional[Dict[str, Any]]:
    """アクセストークンを用いて Google ユーザープロファイル（email等）を取得する。

    Args:
        access_token: 有効な Google OAuth 2.0 アクセストークン

    Returns:
        Optional[Dict[str, Any]]: ユーザープロファイル辞書（email, name, picture等）。失敗時は None。
    """
    if not access_token:
        return None

    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        response = requests.get(
            GOOGLE_USERINFO_ENDPOINT,
            headers=headers,
            timeout=10,
        )
        if response.status_code == 200:
            return response.json()
        else:
            logger.error("ユーザー情報取得失敗: status=%s, body=%s", response.status_code, response.text)
            return None
    except requests.RequestException as e:
        logger.error("ユーザー情報取得通信エラー: %s", e)
        return None


def process_oauth_callback() -> Optional[Dict[str, Any]]:
    """Streamlit の URL クエリパラメータを解析し、OAuth 2.0 の認可コードがあればユーザー情報を取得する。

    処理完了後、URL クエリパラメータを消去（clear）して多重実行を防止する。

    Returns:
        Optional[Dict[str, Any]]: 認証成功時はユーザー情報辞書（email含む）。
        認可コードがない場合や処理失敗時は None。
    """
    query_params = st.query_params

    # OAuth エラーの受信チェック
    if "error" in query_params:
        error_msg = query_params.get("error", "OAuth認証でエラーが発生しました。")
        logger.warning("OAuthエラー受信: %s", error_msg)
        st.session_state.auth_error = f"Googleログインが拒否または中断されました: {error_msg}"
        query_params.clear()
        return None

    # 認可コードの受信チェック
    code = query_params.get("code")
    if not code:
        return None

    # 認可コードをアクセストークンに交換
    token_data = exchange_code_for_token(code)
    # クエリパラメータは即座にクリアしてブラウザ再読み込み時の二重交換エラーを防ぐ
    query_params.clear()

    if not token_data or "access_token" not in token_data:
        st.session_state.auth_error = "認証トークンの取得に失敗しました。再度お試しください。"
        return None

    user_info = get_user_info_from_token(token_data["access_token"])
    if not user_info or "email" not in user_info:
        st.session_state.auth_error = "Googleユーザープロファイル（メールアドレス）の取得に失敗しました。"
        return None

    return user_info


# ==============================================================================
# 認証・認可状態操作関数
# ==============================================================================
def authenticate_user(email: str) -> Tuple[bool, str]:
    """メールアドレスのホワイトリスト照合を行い、セッション状態を更新する。

    Args:
        email: ログイン試行メールアドレス

    Returns:
        Tuple[bool, str]: (成功成否, メッセージ)
    """
    if not email:
        msg = "メールアドレスが取得できませんでした。"
        st.session_state.is_authenticated = False
        st.session_state.auth_error = msg
        return False, msg

    normalized_email = email.strip().lower()

    if is_email_allowed(normalized_email):
        st.session_state.is_authenticated = True
        st.session_state.user_email = normalized_email
        st.session_state.auth_error = None
        return True, "ログインに成功しました。"
    else:
        st.session_state.is_authenticated = False
        msg = f"アクセス権限がありません。お使いのアカウント（{normalized_email}）はホワイトリストに登録されていません。"
        st.session_state.auth_error = msg
        return False, msg


def logout_user() -> None:
    """ログアウトを実行し、セッション認証情報およびエラーを初期化する。"""
    st.session_state.is_authenticated = False
    st.session_state.user_email = ""
    st.session_state.auth_error = None
    st.session_state.current_view = "quiz"
    if hasattr(st, "query_params"):
        st.query_params.clear()
