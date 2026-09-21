"""app.py

中学受験 国語 心情語対策アプリケーション
メインエントリーポイント（ページ初期化、認証ルーティング、サイドバーナビゲーション、画面切り替え）。
"""

from __future__ import annotations

import os
from typing import List, Optional
import streamlit as st

# 環境変数の読み込み (.env または env/gcp.env があれば自動ロード)
try:
    from dotenv import load_dotenv

    load_dotenv()
    if os.path.exists("env/gcp.env"):
        load_dotenv("env/gcp.env")
except ImportError:
    pass

from auth import (
    authenticate_user,
    get_allowed_emails,
    get_google_auth_url,
    is_dev_mode,
    logout_user,
    process_oauth_callback,
)
from data_loader import WordItem, load_words
from db import DatabaseInterface, get_db
from styles import apply_custom_styles, render_badge
from views.dictionary_view import render_dictionary_view
from views.quiz_view import render_quiz_view
from views.review_view import render_review_view

# ==============================================================================
# 定数定義
# ==============================================================================
VIEW_QUIZ = "quiz"
VIEW_REVIEW = "review"
VIEW_DICTIONARY = "dictionary"

NAV_OPTIONS = [
    {"key": VIEW_QUIZ, "label": "🎯 クイズ（学習モード）"},
    {"key": VIEW_REVIEW, "label": "📓 苦手ノート"},
    {"key": VIEW_DICTIONARY, "label": "📚 心情語辞典"},
]

DEFAULT_DEV_EMAIL = "local_dev@example.com"
SAMPLE_DEV_USERS = [
    "local_dev@example.com",
    "student_hanako@example.com",
    "student_taro@example.com",
]


# ==============================================================================
# セッション状態管理関数
# ==============================================================================
def init_app_session_state() -> None:
    """アプリケーション全体のセッション状態を初期化する。"""
    if "is_authenticated" not in st.session_state:
        # DEV_MODE の場合は初期状態で自動認証
        st.session_state.is_authenticated = is_dev_mode()

    if "user_email" not in st.session_state:
        st.session_state.user_email = DEFAULT_DEV_EMAIL

    if "auth_error" not in st.session_state:
        st.session_state.auth_error = None

    if "current_view" not in st.session_state:
        st.session_state.current_view = VIEW_QUIZ

    # 本番モードかつ未認証の場合、OAuthコールバックの検証を実施
    if not is_dev_mode() and not st.session_state.is_authenticated:
        user_info = process_oauth_callback()
        if user_info and "email" in user_info:
            authenticate_user(user_info["email"])


def switch_view(view_key: str) -> None:
    """表示画面を切り替える。

    Args:
        view_key: 切り替え先画面キー ('quiz' | 'review' | 'dictionary')
    """
    valid_keys = {item["key"] for item in NAV_OPTIONS}
    if view_key in valid_keys:
        st.session_state.current_view = view_key


def logout() -> None:
    """ログアウト処理を実行し、セッション状態をリセットする。"""
    logout_user()
    st.session_state.current_view = VIEW_QUIZ


def login_as_dev_user(email: str) -> None:
    """開発用アカウントでログインする。

    Args:
        email: ログインするメールアドレス
    """
    st.session_state.user_email = email
    st.session_state.is_authenticated = True
    st.session_state.auth_error = None


# ==============================================================================
# UIコンポーネント: ログイン画面
# ==============================================================================
def render_login_screen() -> None:
    """未認証時のログイン画面を描画する。"""
    st.title("📖 中学受験 心情語マスター")
    st.write("中学受験国語（物語文）で合否を分ける重要心情語（全272語）の学習アプリです。")

    # 認証エラー（ホワイトリスト外、認可エラー等）が存在する場合は表示
    auth_error = st.session_state.get("auth_error")
    if auth_error:
        st.error(auth_error)

    dev_mode = is_dev_mode()

    if dev_mode:
        st.info("🛠️ **ローカル開発モード (DEV_MODE) で動作中**")
        st.markdown(
            """
            ローカル環境でのテスト用に、Google OAuth 認証をバイパスして即座にログイン可能です。
            使用する開発アカウントを選択または入力してください。
            """
        )

        selected_user = st.selectbox(
            "テストユーザーを選択:",
            options=SAMPLE_DEV_USERS,
            index=0,
            key="dev_login_user_select",
        )

        custom_user = st.text_input(
            "または任意のメールアドレスを入力:",
            value="",
            placeholder="custom_user@example.com",
            key="dev_login_custom_user",
        )

        final_email = custom_user.strip() if custom_user.strip() else selected_user

        if st.button("🚀 開発モードでログイン", type="primary", use_container_width=True):
            login_as_dev_user(final_email)
            st.rerun()

    else:
        # 本番モード (DEV_MODE=False) の場合: Google OAuth 2.0 Web フロー
        st.warning("🔒 **ログインが必要です**")
        st.write("このアプリケーションは事前登録されたご家族の Google アカウントでのみご利用いただけます。")

        auth_url = get_google_auth_url()
        if auth_url:
            st.link_button(
                "🔑 Google アカウントでログイン",
                auth_url,
                type="primary",
                use_container_width=True,
            )
        else:
            st.warning(
                "⚠️ Google OAuth の設定（GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET / REDIRECT_URI）"
                "が不完全です。.env または環境変数の設定を確認してください。"
            )


# ==============================================================================
# UIコンポーネント: サイドバーナビゲーション
# ==============================================================================
def render_sidebar(db: DatabaseInterface, user_email: str) -> None:
    """サイドバーナビゲーションおよびユーザー操作部を描画する。

    Args:
        db: データベースクライアント
        user_email: ログイン中のユーザーメール
    """
    with st.sidebar:
        # 1. アプリロゴ & タイトル
        st.markdown("### 📖 心情語マスター")
        st.caption("中学受験 国語・重要心情語272")

        # 2. ユーザー情報バナー
        dev_mode = is_dev_mode()
        badge_type = "diff_low" if dev_mode else "category"
        badge_label = "開発モード" if dev_mode else "認証済み"
        badge_html = render_badge(badge_label, badge_type)

        st.markdown(
            f"""
            <div style="background-color: #F5F5F5; border-radius: 8px; padding: 10px; margin-bottom: 12px; font-size: 13px;">
                <div style="color: #616161; font-size: 11px;">ログイン中アカウント</div>
                <div style="font-weight: bold; color: #212121; word-break: break-all;">{user_email}</div>
                <div style="margin-top: 4px;">{badge_html}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("---")

        # 3. 画面ナビゲーションメニュー
        st.markdown("**メニュー**")
        labels = [item["label"] for item in NAV_OPTIONS]
        keys = [item["key"] for item in NAV_OPTIONS]

        current_key = st.session_state.get("current_view", VIEW_QUIZ)
        current_index = keys.index(current_key) if current_key in keys else 0

        selected_label = st.radio(
            "画面切り替え",
            options=labels,
            index=current_index,
            label_visibility="collapsed",
            key="nav_radio",
        )

        selected_key = keys[labels.index(selected_label)]
        if selected_key != current_key:
            switch_view(selected_key)
            st.rerun()

        st.markdown("---")

        # 4. 開発者ツール (DEV_MODE時のみ表示)
        if dev_mode:
            with st.expander("🛠️ 開発者ツール (DEV_MODE)", expanded=False):
                st.caption("アカウント切り替え")
                switch_email = st.selectbox(
                    "ユーザー切り替え:",
                    options=SAMPLE_DEV_USERS,
                    index=SAMPLE_DEV_USERS.index(user_email) if user_email in SAMPLE_DEV_USERS else 0,
                    key="dev_switch_user_select",
                )
                if switch_email != user_email:
                    if st.button("切替を実行", key="btn_apply_user_switch"):
                        login_as_dev_user(switch_email)
                        st.rerun()

                st.markdown("---")
                st.caption("学習履歴リセット")
                if st.button("⚠️ このユーザーの履歴を初期化", key="btn_reset_stats", type="secondary"):
                    db.reset_user_stats(user_email)
                    st.success(f"{user_email} の履歴を初期化しました。")
                    st.rerun()

        # 5. ログアウトボタン
        if st.button("🚪 ログアウト", use_container_width=True, key="btn_logout"):
            logout()
            st.rerun()


# ==============================================================================
# メインルーティングコンポーネント
# ==============================================================================
def render_main_content(
    db: DatabaseInterface,
    user_email: str,
    all_words: List[WordItem],
) -> None:
    """現在の current_view に応じたメイン画面コンポーネントを呼び出す。

    Args:
        db: データベースクライアント
        user_email: ログイン中のユーザーメール
        all_words: 単語マスターデータリスト
    """
    current_view = st.session_state.get("current_view", VIEW_QUIZ)

    if current_view == VIEW_QUIZ:
        render_quiz_view(db=db, user_email=user_email, all_words=all_words)
    elif current_view == VIEW_REVIEW:
        render_review_view(db=db, user_email=user_email, all_words=all_words)
    elif current_view == VIEW_DICTIONARY:
        render_dictionary_view(all_words=all_words, db=db, user_email=user_email)
    else:
        # 想定外のビューの場合はクイズ画面へフォールバック
        switch_view(VIEW_QUIZ)
        st.rerun()


# ==============================================================================
# メインエントリーポイント
# ==============================================================================
def main() -> None:
    """Streamlit アプリケーションのエントリーポイント。"""
    # 1. ページ初期設定（Streamlitコマンドの先頭で実行）
    st.set_page_config(
        page_title="中学受験 心情語マスター",
        page_icon="📖",
        layout="centered",
        initial_sidebar_state="auto",
    )

    # 2. スマホ最適化カスタムCSSの適用
    apply_custom_styles()

    # 3. アプリセッション状態の初期化
    init_app_session_state()

    # 4. 単語マスターデータおよびDBクライアントの読み込み
    all_words = load_words()
    db = get_db()

    # 5. 認証状態に応じたルーティング
    if not st.session_state.is_authenticated:
        render_login_screen()
        return

    user_email = st.session_state.user_email

    # 6. サイドバー描画
    render_sidebar(db=db, user_email=user_email)

    # 7. メイン画面描画
    render_main_content(db=db, user_email=user_email, all_words=all_words)


if __name__ == "__main__":
    main()
