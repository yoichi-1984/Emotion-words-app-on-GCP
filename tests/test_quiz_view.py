"""tests/test_quiz_view.py

views/quiz_view.py のセッション状態遷移、クイズ制御、および回答処理の単体テスト。
"""

from unittest.mock import MagicMock, patch
import pytest
import streamlit as st

from data_loader import WordItem
from db import DatabaseInterface, LocalJsonDB, WordStat
from quiz_logic import QuizQuestion
from views.quiz_view import (
    QUIZ_STATE_ANSWERED,
    QUIZ_STATE_ANSWERING,
    QUIZ_STATE_RESULT,
    QUIZ_STATE_SELECT,
    SUBMODE_CATEGORY,
    SUBMODE_RANDOM,
    SUBMODE_REVIEW,
    init_quiz_state,
    next_question,
    render_quiz_view,
    reset_to_select,
    start_quiz_session,
    submit_answer,
)


@pytest.fixture
def sample_words():
    """テスト用サンプル単語リスト (15語)"""
    words = []
    for i in range(1, 16):
        cat = "1. 恥・劣等感・気まずさ" if i <= 8 else "2. 怒り・不満・敵意"
        words.append(
            WordItem(
                no=i,
                category=cat,
                word=f"単語{i}",
                reading=f"たんご{i}",
                difficulty="並" if i % 2 == 0 else "高",
                meaning=f"意味{i}",
                example=f"例文{i}",
                tips=f"ポイント{i}",
            )
        )
    return words


@pytest.fixture
def mock_db():
    """DatabaseInterface のモック"""
    db = MagicMock(spec=DatabaseInterface)
    db.get_failed_words_stats.return_value = []
    return db


@pytest.fixture(autouse=True)
def clear_streamlit_session():
    """各テスト前に session_state をクリアする"""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    yield
    for key in list(st.session_state.keys()):
        del st.session_state[key]


def test_init_quiz_state():
    """init_quiz_state で正しく初期値が設定されることを検証"""
    init_quiz_state()
    assert st.session_state.quiz_state == QUIZ_STATE_SELECT
    assert st.session_state.quiz_config["mode"] == 1
    assert st.session_state.quiz_config["submode"] == SUBMODE_RANDOM
    assert st.session_state.quiz_questions == []
    assert st.session_state.current_q_index == 0
    assert st.session_state.current_selected_option is None
    assert st.session_state.session_results == []
    assert st.session_state.score == 0


def test_start_quiz_session_random(sample_words):
    """ランダムサブモードでクイズセッションを開始するテスト"""
    init_quiz_state()
    start_quiz_session(
        all_words=sample_words,
        mode=1,
        submode=SUBMODE_RANDOM,
        question_count=5,
    )

    assert st.session_state.quiz_state == QUIZ_STATE_ANSWERING
    assert st.session_state.quiz_config["mode"] == 1
    assert st.session_state.quiz_config["submode"] == SUBMODE_RANDOM
    assert len(st.session_state.quiz_questions) == 5
    assert st.session_state.current_q_index == 0
    assert st.session_state.score == 0
    assert st.session_state.session_results == []


def test_start_quiz_session_category(sample_words):
    """カテゴリ指定サブモードでクイズセッションを開始するテスト"""
    init_quiz_state()
    cat_target = "1. 恥・劣等感・気まずさ"
    start_quiz_session(
        all_words=sample_words,
        mode=2,
        submode=SUBMODE_CATEGORY,
        category_name=cat_target,
        question_count=5,
    )

    assert st.session_state.quiz_state == QUIZ_STATE_ANSWERING
    assert st.session_state.quiz_config["mode"] == 2
    assert st.session_state.quiz_config["category_name"] == cat_target
    assert len(st.session_state.quiz_questions) == 5
    for q in st.session_state.quiz_questions:
        assert q.target_word.category == cat_target


def test_start_quiz_session_review(sample_words):
    """苦手復習サブモードでクイズセッションを開始するテスト"""
    init_quiz_state()
    # 10語以上の間違えた単語を用意
    failed_words = sample_words[:12]
    start_quiz_session(
        all_words=sample_words,
        mode=1,
        submode=SUBMODE_REVIEW,
        failed_words=failed_words,
        question_count=10,
    )

    assert st.session_state.quiz_state == QUIZ_STATE_ANSWERING
    assert len(st.session_state.quiz_questions) == 10
    failed_nos = {w.no for w in failed_words}
    for q in st.session_state.quiz_questions:
        assert q.target_word.no in failed_nos


def test_start_quiz_session_invalid_submode(sample_words):
    """無効なサブモードを指定した場合に ValueError が発生することの検証"""
    init_quiz_state()
    with pytest.raises(ValueError, match="無効なサブモード"):
        start_quiz_session(
            all_words=sample_words,
            mode=1,
            submode="unknown_submode",
        )


def test_submit_answer_correct(mock_db, sample_words):
    """正解回答時の submit_answer の動作検証（スコア加算、DB記録、状態遷移）"""
    init_quiz_state()
    start_quiz_session(
        all_words=sample_words,
        mode=1,
        submode=SUBMODE_RANDOM,
        question_count=5,
    )

    current_q: QuizQuestion = st.session_state.quiz_questions[0]
    correct_ans = current_q.correct_answer

    # 正解を送信
    is_correct = submit_answer(
        db=mock_db,
        user_email="test@example.com",
        selected_option=correct_ans,
    )

    assert is_correct is True
    assert st.session_state.score == 1
    assert st.session_state.quiz_state == QUIZ_STATE_ANSWERED
    assert st.session_state.current_selected_option == correct_ans
    assert len(st.session_state.session_results) == 1

    res = st.session_state.session_results[0]
    assert res["is_correct"] is True
    assert res["target_word"] == current_q.target_word.word
    assert res["selected_option"] == correct_ans

    # DBに記録呼び出しされたことを検証
    mock_db.record_attempt.assert_called_once_with(
        email="test@example.com",
        word_no=current_q.target_word.no,
        word=current_q.target_word.word,
        category=current_q.target_word.category,
        is_correct=True,
    )


def test_submit_answer_incorrect(mock_db, sample_words):
    """不正解回答時の submit_answer の動作検証（スコア維持、DB記録、状態遷移）"""
    init_quiz_state()
    start_quiz_session(
        all_words=sample_words,
        mode=1,
        submode=SUBMODE_RANDOM,
        question_count=5,
    )

    current_q: QuizQuestion = st.session_state.quiz_questions[0]
    # ダミー（誤答）選択肢を特定
    wrong_ans = [opt for opt in current_q.options if opt != current_q.correct_answer][0]

    # 誤答を送信
    is_correct = submit_answer(
        db=mock_db,
        user_email="test@example.com",
        selected_option=wrong_ans,
    )

    assert is_correct is False
    assert st.session_state.score == 0
    assert st.session_state.quiz_state == QUIZ_STATE_ANSWERED
    assert st.session_state.current_selected_option == wrong_ans
    assert len(st.session_state.session_results) == 1

    res = st.session_state.session_results[0]
    assert res["is_correct"] is False
    assert res["selected_option"] == wrong_ans

    # DBに記録呼び出しされたことを検証
    mock_db.record_attempt.assert_called_once_with(
        email="test@example.com",
        word_no=current_q.target_word.no,
        word=current_q.target_word.word,
        category=current_q.target_word.category,
        is_correct=False,
    )


def test_next_question_and_result_transition(sample_words):
    """next_question での次問遷移と最終問題後の結果画面遷移を検証"""
    init_quiz_state()
    start_quiz_session(
        all_words=sample_words,
        mode=1,
        submode=SUBMODE_RANDOM,
        question_count=2,
    )

    # 1問目回答済みとする
    st.session_state.quiz_state = QUIZ_STATE_ANSWERED
    st.session_state.current_selected_option = "dummy"

    # 次の問題へ遷移
    next_question()
    assert st.session_state.current_q_index == 1
    assert st.session_state.current_selected_option is None
    assert st.session_state.quiz_state == QUIZ_STATE_ANSWERING

    # 2問目（最終問）回答済みとする
    st.session_state.quiz_state = QUIZ_STATE_ANSWERED
    st.session_state.current_selected_option = "dummy2"

    # 最終問題後の次へ（結果画面へ遷移）
    next_question()
    assert st.session_state.quiz_state == QUIZ_STATE_RESULT


def test_reset_to_select():
    """reset_to_select でモード選択画面にリセットされることを検証"""
    init_quiz_state()
    st.session_state.quiz_state = QUIZ_STATE_RESULT
    st.session_state.current_selected_option = "selected"

    reset_to_select()
    assert st.session_state.quiz_state == QUIZ_STATE_SELECT
    assert st.session_state.current_selected_option is None


@patch("streamlit.rerun")
def test_render_quiz_view_select_screen(mock_rerun, mock_db, sample_words):
    """render_quiz_view で初期画面（モード選択）がエラーなく描画されることを検証"""
    # StreamlitのUI関数をモック
    render_quiz_view(db=mock_db, user_email="test@example.com", all_words=sample_words)
    assert st.session_state.quiz_state == QUIZ_STATE_SELECT


@patch("streamlit.rerun")
def test_render_quiz_view_answering_screen(mock_rerun, mock_db, sample_words):
    """render_quiz_view で問題出題画面がエラーなく描画されることを検証"""
    start_quiz_session(
        all_words=sample_words,
        mode=1,
        submode=SUBMODE_RANDOM,
        question_count=5,
    )
    render_quiz_view(db=mock_db, user_email="test@example.com", all_words=sample_words)
    assert st.session_state.quiz_state == QUIZ_STATE_ANSWERING


@patch("streamlit.rerun")
def test_render_quiz_view_answered_screen(mock_rerun, mock_db, sample_words):
    """render_quiz_view で回答・判定画面がエラーなく描画されることを検証"""
    start_quiz_session(
        all_words=sample_words,
        mode=1,
        submode=SUBMODE_RANDOM,
        question_count=5,
    )
    # 1問目を回答
    current_q = st.session_state.quiz_questions[0]
    submit_answer(mock_db, "test@example.com", current_q.correct_answer)

    render_quiz_view(db=mock_db, user_email="test@example.com", all_words=sample_words)
    assert st.session_state.quiz_state == QUIZ_STATE_ANSWERED


@patch("streamlit.balloons")
@patch("streamlit.rerun")
def test_render_quiz_view_result_screen(mock_rerun, mock_balloons, mock_db, sample_words):
    """render_quiz_view で結果画面がエラーなく描画されることを検証"""
    start_quiz_session(
        all_words=sample_words,
        mode=1,
        submode=SUBMODE_RANDOM,
        question_count=2,
    )
    # 2問回答して結果画面にする
    for _ in range(2):
        q = st.session_state.quiz_questions[st.session_state.current_q_index]
        submit_answer(mock_db, "test@example.com", q.correct_answer)
        next_question()

    assert st.session_state.quiz_state == QUIZ_STATE_RESULT
    render_quiz_view(db=mock_db, user_email="test@example.com", all_words=sample_words)
    assert st.session_state.score == 2
