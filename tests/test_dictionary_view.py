"""tests/test_dictionary_view.py

views/dictionary_view.py の集計サマリー、絞り込み・検索・ソートロジック、ページネーション、および画面描画の単体テスト。
"""

from unittest.mock import MagicMock, patch
import pytest

from data_loader import WordItem
from db import DatabaseInterface, WordStat
from views.dictionary_view import (
    DIFFICULTY_ALL,
    DIFFICULTY_HIGH,
    DIFFICULTY_LOW,
    DIFFICULTY_MID,
    SORT_CATEGORY,
    SORT_DIFFICULTY_ASC,
    SORT_DIFFICULTY_DESC,
    SORT_READING,
    SORT_WORD_NO,
    calculate_dictionary_summary,
    filter_and_sort_dictionary_items,
    paginate_items,
    render_dictionary_view,
)


@pytest.fixture
def sample_words():
    """テスト用の単語マスターデータ (6語)"""
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
        WordItem(
            no=6,
            category="3. 喜び・安堵・感謝",
            word="有頂天",
            reading="うちょうてん",
            difficulty="高",
            meaning="大喜びして夢中になり、我を忘れる様子。",
            example="褒められて有頂天になる。",
            tips="有頂天になりすぎて足元をすくわれる文脈頻出。",
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
            word_no=5,
            word="胸をなでおろす",
            category="3. 喜び・安堵・感謝",
            total_attempts=2,
            incorrect_count=0,
            incorrect_rate=0.0,
            has_ever_failed=False,
            last_attempt_at="2026-09-21T11:00:00+09:00",
            last_result="correct",
        ),
    ]


@pytest.fixture
def mock_db():
    """モックDB"""
    db = MagicMock(spec=DatabaseInterface)
    db.get_user_stats.return_value = {}
    return db


# ==============================================================================
# 1. calculate_dictionary_summary のテスト
# ==============================================================================
def test_calculate_dictionary_summary(sample_words):
    """サマリー統計の計算テスト"""
    summary = calculate_dictionary_summary(sample_words)

    assert summary["total_words"] == 6
    assert summary["diff_low"] == 2  # 並: いたたまれない, 胸をなでおろす
    assert summary["diff_mid"] == 2  # 中: 気後れ, 憤る
    assert summary["diff_high"] == 2  # 高: 憮然, 有頂天
    assert summary["categories_count"] == 3


def test_calculate_dictionary_summary_empty():
    """空リスト時のサマリー計算テスト"""
    summary = calculate_dictionary_summary([])

    assert summary["total_words"] == 0
    assert summary["diff_low"] == 0
    assert summary["diff_mid"] == 0
    assert summary["diff_high"] == 0
    assert summary["categories_count"] == 0


# ==============================================================================
# 2. フィルタリング機能のテスト
# ==============================================================================
def test_filter_by_category(sample_words):
    """カテゴリでの絞り込みテスト"""
    # 特定カテゴリ
    res1 = filter_and_sort_dictionary_items(
        sample_words, category="1. 恥・劣等感・気まずさ"
    )
    assert len(res1) == 2
    assert {w.no for w in res1} == {1, 2}

    # すべて
    res_all = filter_and_sort_dictionary_items(sample_words, category="すべて")
    assert len(res_all) == 6


def test_filter_by_difficulty(sample_words):
    """難易度での絞り込みテスト"""
    # 並
    res_low = filter_and_sort_dictionary_items(
        sample_words, difficulty=DIFFICULTY_LOW
    )
    assert len(res_low) == 2
    assert {w.no for w in res_low} == {2, 5}

    # 中
    res_mid = filter_and_sort_dictionary_items(
        sample_words, difficulty=DIFFICULTY_MID
    )
    assert len(res_mid) == 2
    assert {w.no for w in res_mid} == {1, 4}

    # 高
    res_high = filter_and_sort_dictionary_items(
        sample_words, difficulty=DIFFICULTY_HIGH
    )
    assert len(res_high) == 2
    assert {w.no for w in res_high} == {3, 6}

    # すべて
    res_all = filter_and_sort_dictionary_items(
        sample_words, difficulty=DIFFICULTY_ALL
    )
    assert len(res_all) == 6


def test_search_query(sample_words):
    """キーワード検索機能のテスト（単語名、読み、意味、例文、ヒント）"""
    # 単語名で検索
    res_word = filter_and_sort_dictionary_items(sample_words, search_query="気後れ")
    assert len(res_word) == 1
    assert res_word[0].word == "気後れ"

    # 読み仮名で検索
    res_reading = filter_and_sort_dictionary_items(
        sample_words, search_query="うちょうてん"
    )
    assert len(res_reading) == 1
    assert res_reading[0].word == "有頂天"

    # 意味で検索
    res_meaning = filter_and_sort_dictionary_items(
        sample_words, search_query="心がひるむ"
    )
    assert len(res_meaning) == 1
    assert res_meaning[0].word == "気後れ"

    # 例文で検索
    res_example = filter_and_sort_dictionary_items(
        sample_words, search_query="不公平な扱い"
    )
    assert len(res_example) == 1
    assert res_example[0].word == "憤る"

    # つまずきポイント（ヒント）で検索
    res_tips = filter_and_sort_dictionary_items(
        sample_words, search_query="足元をすくわれる"
    )
    assert len(res_tips) == 1
    assert res_tips[0].word == "有頂天"

    # 前後空白・大文字小文字対応
    res_trim = filter_and_sort_dictionary_items(
        sample_words, search_query="  気後れ  "
    )
    assert len(res_trim) == 1

    # 一致なし
    res_none = filter_and_sort_dictionary_items(
        sample_words, search_query="存在しない語句"
    )
    assert len(res_none) == 0


def test_combined_filters_and_search(sample_words):
    """複合絞り込み（カテゴリ + 難易度 + 検索）のテスト"""
    res = filter_and_sort_dictionary_items(
        sample_words,
        category="2. 怒り・不満・敵意",
        difficulty="中",
        search_query="憤る",
    )
    assert len(res) == 1
    assert res[0].word == "憤る"

    # 難易度不一致でヒットしないケース
    res_miss = filter_and_sort_dictionary_items(
        sample_words,
        category="2. 怒り・不満・敵意",
        difficulty="高",
        search_query="憤る",
    )
    assert len(res_miss) == 0


# ==============================================================================
# 3. ソート機能のテスト
# ==============================================================================
def test_sort_reading(sample_words):
    """50音順ソートのテスト"""
    # reading:
    # 2: いたたまれない
    # 4: いきどおる -> 'いきどおる' < 'いたたまれない'
    # 6: うちょうてん
    # 1: きおくれ
    # 3: ぶぜん
    # 5: むねをなでおろす
    sorted_words = filter_and_sort_dictionary_items(
        sample_words, sort_by=SORT_READING
    )
    readings = [w.reading for w in sorted_words]
    assert readings == [
        "いきどおる",
        "いたたまれない",
        "うちょうてん",
        "きおくれ",
        "ぶぜん",
        "むねをなでおろす",
    ]


def test_sort_word_no(sample_words):
    """単語番号順ソートのテスト"""
    sorted_words = filter_and_sort_dictionary_items(
        sample_words, sort_by=SORT_WORD_NO
    )
    assert [w.no for w in sorted_words] == [1, 2, 3, 4, 5, 6]


def test_sort_category(sample_words):
    """カテゴリ順ソートのテスト"""
    sorted_words = filter_and_sort_dictionary_items(
        sample_words, sort_by=SORT_CATEGORY
    )
    assert [w.no for w in sorted_words] == [1, 2, 3, 4, 5, 6]


def test_sort_difficulty_asc(sample_words):
    """難易度昇順（並→中→高）ソートのテスト"""
    sorted_words = filter_and_sort_dictionary_items(
        sample_words, sort_by=SORT_DIFFICULTY_ASC
    )
    diffs = [w.difficulty for w in sorted_words]
    assert diffs == ["並", "並", "中", "中", "高", "高"]
    # 同難易度内は単語番号順
    assert [w.no for w in sorted_words if w.difficulty == "並"] == [2, 5]
    assert [w.no for w in sorted_words if w.difficulty == "中"] == [1, 4]
    assert [w.no for w in sorted_words if w.difficulty == "高"] == [3, 6]


def test_sort_difficulty_desc(sample_words):
    """難易度降順（高→中→並）ソートのテスト"""
    sorted_words = filter_and_sort_dictionary_items(
        sample_words, sort_by=SORT_DIFFICULTY_DESC
    )
    diffs = [w.difficulty for w in sorted_words]
    assert diffs == ["高", "高", "中", "中", "並", "並"]
    # 同難易度内は単語番号順
    assert [w.no for w in sorted_words if w.difficulty == "高"] == [3, 6]
    assert [w.no for w in sorted_words if w.difficulty == "中"] == [1, 4]
    assert [w.no for w in sorted_words if w.difficulty == "並"] == [2, 5]


# ==============================================================================
# 4. ページネーションのテスト
# ==============================================================================
def test_paginate_items(sample_words):
    """ページネーションの正常系テスト"""
    # 6件を1ページあたり2件で分割 -> 計3ページ
    page1, total1 = paginate_items(sample_words, page=1, page_size=2)
    assert total1 == 3
    assert [w.no for w in page1] == [1, 2]

    page2, total2 = paginate_items(sample_words, page=2, page_size=2)
    assert total2 == 3
    assert [w.no for w in page2] == [3, 4]

    page3, total3 = paginate_items(sample_words, page=3, page_size=2)
    assert total3 == 3
    assert [w.no for w in page3] == [5, 6]


def test_paginate_items_bounds(sample_words):
    """ページ番号の境界値テスト（範囲外の自動補正）"""
    # 範囲外の大きなページ番号 -> 最終ページが返る
    page_over, total = paginate_items(sample_words, page=99, page_size=2)
    assert total == 3
    assert [w.no for w in page_over] == [5, 6]

    # 0以下のページ番号 -> 第1ページが返る
    page_under, total = paginate_items(sample_words, page=0, page_size=2)
    assert total == 3
    assert [w.no for w in page_under] == [1, 2]


def test_paginate_items_all(sample_words):
    """全件表示（page_size <= 0）のテスト"""
    items, total = paginate_items(sample_words, page=1, page_size=0)
    assert total == 1
    assert len(items) == 6


def test_paginate_items_empty():
    """空リストに対するページネーションテスト"""
    items, total = paginate_items([], page=1, page_size=20)
    assert total == 1
    assert items == []


# ==============================================================================
# 5. render_dictionary_view の描画テスト
# ==============================================================================
def test_render_dictionary_view_empty():
    """単語マスターデータが空のときの描画テスト"""
    with patch("streamlit.info") as mock_info:
        render_dictionary_view([])
        assert mock_info.called
        assert "現在、登録されている単語データはありません" in mock_info.call_args[0][0]


def test_render_dictionary_view_normal(sample_words):
    """通常の辞典画面描画テスト"""
    with patch("streamlit.title") as mock_title, \
         patch("streamlit.expander") as mock_expander, \
         patch("views.dictionary_view.display_word_detail_card") as mock_detail:
        render_dictionary_view(sample_words)

        assert mock_title.called
        assert "心情語辞典" in mock_title.call_args[0][0]
        # 6件の単語に対して expander が呼び出される
        assert mock_expander.call_count == 6
        assert mock_detail.call_count == 6


def test_render_dictionary_view_with_db_stats(sample_words, sample_stats, mock_db):
    """ユーザー学習履歴を含む辞典画面描画テスト"""
    mock_db.get_user_stats.return_value = {s.word_no: s for s in sample_stats}

    with patch("streamlit.title") as mock_title, \
         patch("streamlit.expander") as mock_expander, \
         patch("views.dictionary_view.display_word_detail_card") as mock_detail:
        render_dictionary_view(sample_words, db=mock_db, user_email="test@example.com")

        assert mock_title.called
        assert mock_expander.call_count == 6
        assert mock_detail.call_count == 6

        # 苦手単語(No.1)と正解単語(No.5)のタイトル接尾辞を確認
        expander_titles = [call[0][0] for call in mock_expander.call_args_list]
        assert any("【No.1 気後れ】" in t and "✕ 苦手" in t for t in expander_titles)
        assert any("【No.5 胸をなでおろす】" in t and "○ 正解" in t for t in expander_titles)


def test_render_dictionary_view_no_search_results(sample_words):
    """検索該当なし時の警告表示テスト"""
    with patch("views.dictionary_view.filter_and_sort_dictionary_items", return_value=[]), \
         patch("streamlit.warning") as mock_warning:
        render_dictionary_view(sample_words)

        assert mock_warning.called
        assert "条件に一致する単語は見つかりませんでした" in mock_warning.call_args[0][0]
