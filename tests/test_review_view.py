"""tests/test_review_view.py

views/review_view.py の苦手単語集計、絞り込み・ソートロジック、および画面描画の単体テスト。
"""

from unittest.mock import MagicMock, patch
import pytest
import streamlit as st

from data_loader import WordItem
from db import DatabaseInterface, WordStat
from views.review_view import (
    SORT_CATEGORY,
    SORT_INCORRECT_COUNT,
    SORT_INCORRECT_RATE,
    SORT_RECENT_ATTEMPT,
    SORT_WORD_NO,
    ReviewItem,
    build_review_items,
    calculate_review_summary,
    filter_and_sort_review_items,
    format_attempt_time,
    render_review_view,
)


@pytest.fixture
def sample_words():
    """テスト用の単語マスターデータ (5語)"""
    return [
        WordItem(
            no=1,
            category="1. 恥・劣等感・気まずさ",
            word="気後れ",
            reading="きおくれ",
            difficulty="中",
            meaning="自信をなくして心がひるむこと。",
            example="大舞台を前にして気後れする。",
            tips="相手に圧倒されて引け目を感じる点に注目。",
        ),
        WordItem(
            no=2,
            category="1. 恥・劣等感・気まずさ",
            word="いたたまれない",
            reading="いたたまれない",
            difficulty="並",
            meaning="その場にじっとしていられないほど恥ずかしい・心苦しいこと。",
            example="自分のミスが原因でいたたまれなくなる。",
            tips="物理的に逃げ出したいほどの恥ずかしさや心苦しさ。",
        ),
        WordItem(
            no=3,
            category="2. 怒り・不満・敵意",
            word="憮然",
            reading="ぶぜん",
            difficulty="高",
            meaning="失望や不満で思い通りにならず、ぼう然とする・おもしろくない様子。",
            example="注意されて憮然とした表情を浮かべる。",
            tips="「怒っている」だけでなく「失望・落胆」のニュアンスを含む最頻出語。",
        ),
        WordItem(
            no=4,
            category="2. 怒り・不満・敵意",
            word="憤る",
            reading="いきどおる",
            difficulty="中",
            meaning="不正や理不尽なことに対して激しく怒ること。",
            example="不公平な扱いに強く憤る。",
            tips="社会的な理不尽や倫理的怒りに使われる。",
        ),
        WordItem(
            no=5,
            category="3. 喜び・安堵・感謝",
            word="胸をなでおろす",
            reading="むねをなでおろす",
            difficulty="並",
            meaning="心配や危機が去って安心すること。",
            example="無事合格を知って胸をなでおろす。",
            tips="緊張状態からの解放と安堵。",
        ),
    ]


@pytest.fixture
def sample_stats():
    """テスト用の学習履歴リスト"""
    return [
        WordStat(
            word_no=1,
            word="気後れ",
            category="1. 恥・劣等感・気まずさ",
            total_attempts=5,
            incorrect_count=3,
            incorrect_rate=0.6,
            has_ever_failed=True,
            last_attempt_at="2026-09-21T10:00:00+09:00",
            last_result="incorrect",
        ),
        WordStat(
            word_no=2,
            word="いたたまれない",
            category="1. 恥・劣等感・気まずさ",
            total_attempts=4,
            incorrect_count=1,
            incorrect_rate=0.25,
            has_ever_failed=True,
            last_attempt_at="2026-09-21T11:00:00+09:00",
            last_result="correct",
        ),
        WordStat(
            word_no=3,
            word="憮然",
            category="2. 怒り・不満・敵意",
            total_attempts=6,
            incorrect_count=5,
            incorrect_rate=0.833,
            has_ever_failed=True,
            last_attempt_at="2026-09-21T09:00:00+09:00",
            last_result="incorrect",
        ),
        WordStat(
            word_no=5,
            word="胸をなでおろす",
            category="3. 喜び・安堵・感謝",
            total_attempts=2,
            incorrect_count=0,
            incorrect_rate=0.0,
            has_ever_failed=False,  # 一度も間違えていない
            last_attempt_at="2026-09-21T08:00:00+09:00",
            last_result="correct",
        ),
    ]


@pytest.fixture
def mock_db():
    """DatabaseInterface のモック"""
    return MagicMock(spec=DatabaseInterface)


@pytest.fixture(autouse=True)
def clear_streamlit_session():
    """各テスト前後で session_state をクリアする"""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    yield
    for key in list(st.session_state.keys()):
        del st.session_state[key]


# ==============================================================================
# 1. build_review_items のテスト
# ==============================================================================
def test_build_review_items(sample_stats, sample_words):
    """has_ever_failed が True の単語のみが正しく ReviewItem に結合されることを検証"""
    items = build_review_items(sample_stats, sample_words)
    # word_no 1, 2, 3 のみ抽出される（5は has_ever_failed=False）
    assert len(items) == 3
    word_nos = [item.word_no for item in items]
    assert word_nos == [1, 2, 3]

    item1 = items[0]
    assert item1.word == "気後れ"
    assert item1.reading == "きおくれ"
    assert item1.category == "1. 恥・劣等感・気まずさ"
    assert item1.difficulty == "中"
    assert item1.meaning == "自信をなくして心がひるむこと。"
    assert item1.example == "大舞台を前にして気後れする。"
    assert item1.tips == "相手に圧倒されて引け目を感じる点に注目。"
    assert item1.total_attempts == 5
    assert item1.incorrect_count == 3
    assert item1.incorrect_rate == 0.6
    assert item1.has_ever_failed is True
    assert item1.last_result == "incorrect"


def test_build_review_items_missing_word(sample_words):
    """マスターデータに存在しない単語番号はスキップされることを検証"""
    stats = [
        WordStat(
            word_no=999,
            word="存在しない単語",
            category="未分類",
            has_ever_failed=True,
        )
    ]
    items = build_review_items(stats, sample_words)
    assert items == []


# ==============================================================================
# 2. calculate_review_summary のテスト
# ==============================================================================
def test_calculate_review_summary_empty():
    """アイテムが空の場合のサマリー計算を検証"""
    summary = calculate_review_summary([])
    assert summary["failed_words_count"] == 0
    assert summary["total_attempts"] == 0
    assert summary["total_incorrect"] == 0
    assert summary["overall_incorrect_rate"] == 0.0


def test_calculate_review_summary(sample_stats, sample_words):
    """複数アイテムがある場合のサマリー計算を検証"""
    items = build_review_items(sample_stats, sample_words)
    summary = calculate_review_summary(items)

    # 抽出されたアイテム:
    # 1: attempts=5, incorrect=3
    # 2: attempts=4, incorrect=1
    # 3: attempts=6, incorrect=5
    # total_attempts = 15, total_incorrect = 9, rate = 9/15 = 60.0%
    assert summary["failed_words_count"] == 3
    assert summary["total_attempts"] == 15
    assert summary["total_incorrect"] == 9
    assert summary["overall_incorrect_rate"] == 60.0


# ==============================================================================
# 3. filter_and_sort_review_items のテスト
# ==============================================================================
def test_filter_by_category(sample_stats, sample_words):
    """カテゴリでの絞り込みを検証"""
    items = build_review_items(sample_stats, sample_words)

    filtered_cat1 = filter_and_sort_review_items(
        items, category_filter="1. 恥・劣等感・気まずさ"
    )
    assert len(filtered_cat1) == 2
    assert {i.word_no for i in filtered_cat1} == {1, 2}

    filtered_cat2 = filter_and_sort_review_items(
        items, category_filter="2. 怒り・不満・敵意"
    )
    assert len(filtered_cat2) == 1
    assert filtered_cat2[0].word_no == 3

    filtered_all = filter_and_sort_review_items(items, category_filter="すべて")
    assert len(filtered_all) == 3


def test_filter_by_search_query(sample_stats, sample_words):
    """検索キーワードによる絞り込み（単語、読み、意味）を検証"""
    items = build_review_items(sample_stats, sample_words)

    # 単語名で検索
    res_word = filter_and_sort_review_items(items, search_query="憮然")
    assert len(res_word) == 1
    assert res_word[0].word == "憮然"

    # 読み仮名で検索
    res_reading = filter_and_sort_review_items(items, search_query="きおくれ")
    assert len(res_reading) == 1
    assert res_reading[0].word == "気後れ"

    # 意味で検索
    res_meaning = filter_and_sort_review_items(items, search_query="心苦しい")
    assert len(res_meaning) == 1
    assert res_meaning[0].word == "いたたまれない"

    # 該当なし
    res_none = filter_and_sort_review_items(items, search_query="存在しないキーワード")
    assert len(res_none) == 0


def test_sort_incorrect_count(sample_stats, sample_words):
    """不正解回数が多い順ソートを検証"""
    items = build_review_items(sample_stats, sample_words)
    # incorrect: 3番(5回), 1番(3回), 2番(1回)
    sorted_items = filter_and_sort_review_items(items, sort_by=SORT_INCORRECT_COUNT)
    assert [i.word_no for i in sorted_items] == [3, 1, 2]


def test_sort_incorrect_rate(sample_stats, sample_words):
    """不正解率が高い順ソートを検証"""
    items = build_review_items(sample_stats, sample_words)
    # rate: 3番(0.833), 1番(0.6), 2番(0.25)
    sorted_items = filter_and_sort_review_items(items, sort_by=SORT_INCORRECT_RATE)
    assert [i.word_no for i in sorted_items] == [3, 1, 2]


def test_sort_word_no(sample_stats, sample_words):
    """単語番号順ソートを検証"""
    items = build_review_items(sample_stats, sample_words)
    sorted_items = filter_and_sort_review_items(items, sort_by=SORT_WORD_NO)
    assert [i.word_no for i in sorted_items] == [1, 2, 3]


def test_sort_category(sample_stats, sample_words):
    """カテゴリ順ソートを検証"""
    items = build_review_items(sample_stats, sample_words)
    sorted_items = filter_and_sort_review_items(items, sort_by=SORT_CATEGORY)
    # カテゴリ 1 (No.1, 2) -> カテゴリ 2 (No.3)
    assert [i.word_no for i in sorted_items] == [1, 2, 3]


def test_sort_recent_attempt(sample_stats, sample_words):
    """最近解いた順ソートを検証"""
    items = build_review_items(sample_stats, sample_words)
    # last_attempt: 2番(11:00), 1番(10:00), 3番(09:00)
    sorted_items = filter_and_sort_review_items(items, sort_by=SORT_RECENT_ATTEMPT)
    assert [i.word_no for i in sorted_items] == [2, 1, 3]


# ==============================================================================
# 4. format_attempt_time のテスト
# ==============================================================================
def test_format_attempt_time():
    """日時フォーマット関数のテスト"""
    assert format_attempt_time("2026-09-21T10:30:00+09:00") == "2026/09/21 10:30"
    assert format_attempt_time(None) == "未回答"
    assert format_attempt_time("") == "未回答"


# ==============================================================================
# 5. render_review_view の描画テスト
# ==============================================================================
def test_render_review_view_empty(mock_db, sample_words):
    """苦手単語が0件のときの描画テスト"""
    mock_db.get_failed_words_stats.return_value = []

    with patch("streamlit.info") as mock_info:
        render_review_view(mock_db, "user@example.com", sample_words)
        assert mock_info.called
        assert "現在、苦手ノートに登録されている単語はありません" in mock_info.call_args[0][0]


def test_render_review_view_less_than_10(mock_db, sample_words, sample_stats):
    """苦手単語が10件未満のときの描画テスト（復習モード未開放メッセージ）"""
    mock_db.get_failed_words_stats.return_value = sample_stats

    with patch("streamlit.info") as mock_info, patch("streamlit.success") as mock_success:
        render_review_view(mock_db, "user@example.com", sample_words)
        # 10問未満なので info が呼ばれ、successは呼ばれない
        assert any("苦手復習モードの開放条件" in call[0][0] for call in mock_info.call_args_list)
        assert not mock_success.called


def test_render_review_view_10_or_more(mock_db, sample_words):
    """苦手単語が10件以上のときの描画テスト（復習モード開放メッセージ）"""
    # 10個の失敗データを作成
    ten_stats = []
    ten_words = []
    for i in range(1, 12):
        ten_stats.append(
            WordStat(
                word_no=i,
                word=f"単語{i}",
                category="1. 恥・劣等感・気まずさ",
                total_attempts=2,
                incorrect_count=1,
                incorrect_rate=0.5,
                has_ever_failed=True,
            )
        )
        ten_words.append(
            WordItem(
                no=i,
                category="1. 恥・劣等感・気まずさ",
                word=f"単語{i}",
                reading=f"たんご{i}",
                difficulty="並",
                meaning=f"意味{i}",
                example=f"例文{i}",
                tips=f"ヒント{i}",
            )
        )

    mock_db.get_failed_words_stats.return_value = ten_stats

    with patch("streamlit.success") as mock_success:
        render_review_view(mock_db, "user@example.com", ten_words)
        assert mock_success.called
        assert "苦手語句が10語以上蓄積されています" in mock_success.call_args[0][0]
