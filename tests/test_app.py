"""tests/test_app.py

app.py のセッション状態管理、環境変数判定、ルーティング、およびUIコンポーネントの単体テスト。
"""

import os
from unittest.mock import MagicMock, patch
import pytest
import streamlit as st

from app import (
    DEFAULT_DEV_EMAIL,
    NAV_OPTIONS,
    VIEW_DICTIONARY,
    VIEW_QUIZ,
    VIEW_REVIEW,
    get_allowed_emails,
    init_app_session_state,
    is_dev_mode,
    login_as_dev_user,
    logout,
    render_login_screen,
    render_main_content,
    render_sidebar,
    switch_view,
)
from data_loader import WordItem
from db import DatabaseInterface


@pytest.fixture(autouse=True)
def clear_streamlit_session():
    """各テスト前後に session_state をクリアする。"""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    yield
    for key in list(st.session_state.keys()):
        del st.session_state[key]


@pytest.fixture
def sample_words():
    """テスト用サンプル単語リスト"""
    return [
        WordItem(
            no=1,
            category="1. 恥・劣等感・気まずさ",
            word="気後れ",
            reading="きおくれ",
            difficulty="中",
            meaning="相手の勢いに圧倒されて気が引けること。",
            example="強豪校との試合で気後れする。",
            tips="「気後れ」と「物怖じ」のニュアンスの違いを押さえましょう。",
        )
    ]


@pytest.fixture
def mock_db():
    """DatabaseInterface のモック"""
    db = MagicMock(spec=DatabaseInterface)
    db.get_failed_words_stats.return_value = []
    return db


def test_is_dev_mode():
    """DEV_MODE 環境変数の各パターンの判定を検証"""
    with patch.dict(os.environ, {"DEV_MODE": "True"}):
        assert is_dev_mode() is True

    with patch.dict(os.environ, {"DEV_MODE": "true"}):
        assert is_dev_mode() is True

    with patch.dict(os.environ, {"DEV_MODE": "1"}):
        assert is_dev_mode() is True

    with patch.dict(os.environ, {"DEV_MODE": "False"}):
        assert is_dev_mode() is False

    with patch.dict(os.environ, {"DEV_MODE": "0"}):
        assert is_dev_mode() is False

    with patch.dict(os.environ, {"DEV_MODE": "no"}):
        assert is_dev_mode() is False


def test_get_allowed_emails():
    """ALLOWED_EMAILS 環境変数のパースを検証"""
    with patch.dict(os.environ, {"ALLOWED_EMAILS": "user1@gmail.com, user2@gmail.com, "}):
        emails = get_allowed_emails()
        assert emails == ["user1@gmail.com", "user2@gmail.com"]

    with patch.dict(os.environ, {"ALLOWED_EMAILS": ""}):
        assert get_allowed_emails() == []


def test_init_app_session_state_dev_mode_true():
    """DEV_MODE=True 時の初期セッション状態を検証"""
    with patch("app.is_dev_mode", return_value=True):
        init_app_session_state()

        assert st.session_state.is_authenticated is True
        assert st.session_state.user_email == DEFAULT_DEV_EMAIL
        assert st.session_state.current_view == VIEW_QUIZ


def test_init_app_session_state_dev_mode_false():
    """DEV_MODE=False 時の初期セッション状態を検証"""
    with patch("app.is_dev_mode", return_value=False):
        init_app_session_state()

        assert st.session_state.is_authenticated is False
        assert st.session_state.user_email == DEFAULT_DEV_EMAIL
        assert st.session_state.current_view == VIEW_QUIZ


def test_switch_view():
    """画面切り替え関数の動作を検証"""
    init_app_session_state()

    switch_view(VIEW_REVIEW)
    assert st.session_state.current_view == VIEW_REVIEW

    switch_view(VIEW_DICTIONARY)
    assert st.session_state.current_view == VIEW_DICTIONARY

    # 不正なキーは無視される
    switch_view("invalid_view")
    assert st.session_state.current_view == VIEW_DICTIONARY


def test_logout():
    """ログアウト処理で認証フラグとビューがリセットされることを検証"""
    st.session_state.is_authenticated = True
    st.session_state.current_view = VIEW_REVIEW

    logout()

    assert st.session_state.is_authenticated is False
    assert st.session_state.current_view == VIEW_QUIZ


def test_login_as_dev_user():
    """開発ユーザーでのログイン処理を検証"""
    st.session_state.is_authenticated = False
    st.session_state.user_email = ""

    login_as_dev_user("test_student@example.com")

    assert st.session_state.is_authenticated is True
    assert st.session_state.user_email == "test_student@example.com"


@patch("app.render_quiz_view")
def test_render_main_content_quiz(mock_render_quiz, mock_db, sample_words):
    """current_view == VIEW_QUIZ 時に render_quiz_view が呼び出されることを検証"""
    st.session_state.current_view = VIEW_QUIZ

    render_main_content(mock_db, "test@example.com", sample_words)
    mock_render_quiz.assert_called_once_with(
        db=mock_db,
        user_email="test@example.com",
        all_words=sample_words,
    )


@patch("app.render_review_view")
def test_render_main_content_review(mock_render_review, mock_db, sample_words):
    """current_view == VIEW_REVIEW 時に render_review_view が呼び出されることを検証"""
    st.session_state.current_view = VIEW_REVIEW

    render_main_content(mock_db, "test@example.com", sample_words)
    mock_render_review.assert_called_once_with(
        db=mock_db,
        user_email="test@example.com",
        all_words=sample_words,
    )


@patch("app.render_dictionary_view")
def test_render_main_content_dictionary(mock_render_dict, mock_db, sample_words):
    """current_view == VIEW_DICTIONARY 時に render_dictionary_view が呼び出されることを検証"""
    st.session_state.current_view = VIEW_DICTIONARY

    render_main_content(mock_db, "test@example.com", sample_words)
    mock_render_dict.assert_called_once_with(
        all_words=sample_words,
        db=mock_db,
        user_email="test@example.com",
    )


@patch("app.switch_view")
@patch("streamlit.rerun")
def test_render_main_content_invalid_fallback(mock_rerun, mock_switch_view, mock_db, sample_words):
    """想定外の current_view 時に VIEW_QUIZ へフォールバックすることを検証"""
    st.session_state.current_view = "unknown_view"

    render_main_content(mock_db, "test@example.com", sample_words)
    mock_switch_view.assert_called_once_with(VIEW_QUIZ)
    mock_rerun.assert_called_once()


@patch("streamlit.rerun")
def test_render_login_screen_dev(mock_rerun):
    """DEV_MODE=True 時のログイン画面描画とログインボタン押下の検証"""
    with patch("app.is_dev_mode", return_value=True):
        render_login_screen()


def test_render_sidebar(mock_db):
    """サイドバー描画がエラーなく実行されることを検証"""
    st.session_state.current_view = VIEW_QUIZ
    with patch("app.is_dev_mode", return_value=True):
        render_sidebar(mock_db, "test@example.com")
