"""config.py

中学受験 国語 心情語対策アプリケーションの設定管理モジュール。
環境変数の読み込み、DEV_MODE判定、Google OAuth設定、ホワイトリスト検証、GCPプロジェクト設定を提供する。
"""

import os
from typing import Any, Dict, List, Optional

import auth


def is_dev_mode() -> bool:
    """ローカル開発モード（DEV_MODE）が有効かどうかを判定する。"""
    return auth.is_dev_mode()


def get_allowed_emails() -> List[str]:
    """ホワイトリストに登録された許可メールアドレス一覧を取得する。"""
    return auth.get_allowed_emails()


def is_email_allowed(email: str, allowed_emails: Optional[List[str]] = None) -> bool:
    """指定されたメールアドレスがホワイトリストに登録されているかを判定する。"""
    return auth.is_email_allowed(email, allowed_emails=allowed_emails)


def get_oauth_config() -> Dict[str, Any]:
    """Google OAuth 2.0 連携に必要な環境変数を取得し、設定妥当性を検証する。"""
    return auth.get_oauth_config()


def get_gcp_project_id() -> Optional[str]:
    """GCP プロジェクトIDを取得する。

    Returns:
        Optional[str]: 設定されたプロジェクトID。未設定時は None。
    """
    raw_proj = os.getenv("GCP_PROJECT_ID", "").strip().strip('"\'')
    return raw_proj if raw_proj else None
