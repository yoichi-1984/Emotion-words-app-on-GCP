"""views/dictionary_view.py

中学受験 国語 心情語対策アプリケーション
心情語辞典画面ビュー（全272語の検索・カテゴリ/難易度フィルタ・50音順ソート・ページネーション・詳細展開表示）。
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple
import streamlit as st

from data_loader import WordItem
from db import DatabaseInterface, WordStat
from styles import (
    display_stat_card,
    display_word_detail_card,
    render_badge,
)
from views.review_view import format_attempt_time

# ==============================================================================
# ソートオプション定数
# ==============================================================================
SORT_READING = "50音順（あいうえお順）"
SORT_WORD_NO = "単語番号順（No.1〜272）"
SORT_CATEGORY = "カテゴリ順"
SORT_DIFFICULTY_ASC = "難易度順（並→中→高）"
SORT_DIFFICULTY_DESC = "難易度順（高→中→並）"

SORT_OPTIONS = [
    SORT_READING,
    SORT_WORD_NO,
    SORT_CATEGORY,
    SORT_DIFFICULTY_ASC,
    SORT_DIFFICULTY_DESC,
]

# 難易度フィルタ定数
DIFFICULTY_ALL = "すべて"
DIFFICULTY_LOW = "並"
DIFFICULTY_MID = "中"
DIFFICULTY_HIGH = "高"

DIFFICULTY_OPTIONS = [
    DIFFICULTY_ALL,
    DIFFICULTY_LOW,
    DIFFICULTY_MID,
    DIFFICULTY_HIGH,
]

# 難易度ソート用重み付け
DIFF_RANK = {
    "並": 1,
    "中": 2,
    "高": 3,
}

# 1ページあたりの表示件数オプション
PAGE_SIZE_OPTIONS = [20, 50, 100, "すべて"]


# ==============================================================================
# ロジック・ヘルパー関数（ビジネスロジック層）
# ==============================================================================
def calculate_dictionary_summary(words: List[WordItem]) -> Dict[str, Any]:
    """単語リストからサマリー統計（総語数、難易度別語数、カテゴリ数）を計算する。

    Args:
        words: 単語マスターデータのリスト

    Returns:
        Dict[str, Any]: 集計サマリー情報
    """
    total_words = len(words)
    diff_low = sum(1 for w in words if w.difficulty == DIFFICULTY_LOW)
    diff_mid = sum(1 for w in words if w.difficulty == DIFFICULTY_MID)
    diff_high = sum(1 for w in words if w.difficulty == DIFFICULTY_HIGH)
    categories_count = len({w.category for w in words})

    return {
        "total_words": total_words,
        "diff_low": diff_low,
        "diff_mid": diff_mid,
        "diff_high": diff_high,
        "categories_count": categories_count,
    }


def filter_and_sort_dictionary_items(
    words: List[WordItem],
    category: str = "すべて",
    difficulty: str = DIFFICULTY_ALL,
    search_query: str = "",
    sort_by: str = SORT_READING,
) -> List[WordItem]:
    """単語リストを指定された条件で絞り込み、ソートする。

    Args:
        words: 絞り込み前の単語アイテムリスト
        category: 絞り込みカテゴリ ("すべて" またはカテゴリ名)
        difficulty: 絞り込み難易度 ("すべて", "並", "中", "高")
        search_query: 単語名・読み・意味・例文・ヒントの検索文字列
        sort_by: 並び替え順

    Returns:
        List[WordItem]: 絞り込み・ソート後の単語アイテムリスト
    """
    filtered = list(words)

    # 1. カテゴリ絞り込み
    if category and category != "すべて":
        filtered = [w for w in filtered if w.category == category]

    # 2. 難易度絞り込み
    if difficulty and difficulty != DIFFICULTY_ALL:
        filtered = [w for w in filtered if w.difficulty == difficulty]

    # 3. キーワード検索（単語、読み、意味、場面例、つまずきポイント）
    query = search_query.strip().lower()
    if query:
        filtered = [
            w
            for w in filtered
            if query in w.word.lower()
            or query in w.reading.lower()
            or query in w.meaning.lower()
            or query in w.example.lower()
            or query in w.tips.lower()
        ]

    # 4. ソート処理
    if sort_by == SORT_READING:
        # 50音順（読み昇順 -> 単語番号昇順）
        filtered.sort(key=lambda w: (w.reading, w.no))
    elif sort_by == SORT_WORD_NO:
        # 単語番号昇順
        filtered.sort(key=lambda w: w.no)
    elif sort_by == SORT_CATEGORY:
        # カテゴリ昇順 -> 単語番号昇順
        filtered.sort(key=lambda w: (w.category, w.no))
    elif sort_by == SORT_DIFFICULTY_ASC:
        # 難易度並→中→高 -> 単語番号昇順
        filtered.sort(key=lambda w: (DIFF_RANK.get(w.difficulty, 99), w.no))
    elif sort_by == SORT_DIFFICULTY_DESC:
        # 難易度高→中→並 -> 単語番号昇順
        filtered.sort(key=lambda w: (-DIFF_RANK.get(w.difficulty, 0), w.no))

    return filtered


def paginate_items(
    items: List[WordItem],
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[WordItem], int]:
    """単語リストを指定ページとページサイズでスライスし、対象アイテムと総ページ数を返す。

    Args:
        items: 単語リスト
        page: ページ番号（1始まり）
        page_size: 1ページあたりの件数（0以下の場合は全件返却）

    Returns:
        Tuple[List[WordItem], int]: (指定ページのアイテムリスト, 総ページ数)
    """
    if not items:
        return [], 1

    if page_size <= 0:
        return items, 1

    total_pages = max(1, (len(items) + page_size - 1) // page_size)
    actual_page = max(1, min(page, total_pages))

    start_idx = (actual_page - 1) * page_size
    end_idx = start_idx + page_size

    return items[start_idx:end_idx], total_pages


# ==============================================================================
# UIレンダリングコンポーネント（View層）
# ==============================================================================
def render_dictionary_view(
    all_words: List[WordItem],
    db: Optional[DatabaseInterface] = None,
    user_email: Optional[str] = None,
) -> None:
    """心情語辞典画面を描画するメイン関数。

    全272語の検索・閲覧、カテゴリ・難易度フィルタ、50音順等のソート、および単語詳細表示を提供する。

    Args:
        all_words: 全単語マスターデータリスト
        db: データベースクライアント（任意、学習状況表示用）
        user_email: ログイン中のユーザーメールアドレス（任意、学習状況表示用）
    """
    st.title("📚 心情語辞典（全272語）")
    st.write(
        "中学入試の物語文で頻出する最重要心情語・慣用表現（全272語）の辞典です。"
        "五十音順やカテゴリ、難易度で自由に調べたり、意味やつまずきポイントを確認できます。"
    )

    # 1. 単語マスターデータが空の場合
    if not all_words:
        st.info("現在、登録されている単語データはありません。")
        return

    # 2. 全体サマリーカードの描画
    summary = calculate_dictionary_summary(all_words)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        display_stat_card("収録語数", f"{summary['total_words']} 語", f"全{summary['categories_count']}分類")
    with col2:
        display_stat_card("並レベル", f"{summary['diff_low']} 語", "標準・基本語")
    with col3:
        display_stat_card("中レベル", f"{summary['diff_mid']} 語", "頻出・重要語")
    with col4:
        display_stat_card("高レベル", f"{summary['diff_high']} 語", "難関・差がつく語")

    st.write("")

    # 3. 検索バーと表示件数
    col_search, col_pagesize = st.columns([3, 1])
    with col_search:
        search_query = st.text_input(
            "🔍 単語・読み・意味で検索",
            value="",
            placeholder="例: 気後れ、きおくれ、自信がない、引け目 ...",
            key="dict_search_input",
        )
    with col_pagesize:
        selected_page_size = st.selectbox(
            "📄 1ページの件数",
            options=PAGE_SIZE_OPTIONS,
            index=0,
            key="dict_page_size_select",
        )

    # 4. 絞り込み・ソートコントロール
    categories = sorted(list({w.category for w in all_words}))
    category_options = ["すべて"] + categories

    col_cat, col_diff, col_sort = st.columns(3)
    with col_cat:
        selected_category = st.selectbox(
            "📂 カテゴリ",
            options=category_options,
            index=0,
            key="dict_category_select",
        )
    with col_diff:
        selected_difficulty = st.selectbox(
            "⭐ 難易度",
            options=DIFFICULTY_OPTIONS,
            index=0,
            key="dict_difficulty_select",
        )
    with col_sort:
        selected_sort = st.selectbox(
            "↕ 並び替え",
            options=SORT_OPTIONS,
            index=0,
            key="dict_sort_select",
        )

    # 5. フィルタ・ソート適用
    filtered_words = filter_and_sort_dictionary_items(
        words=all_words,
        category=selected_category,
        difficulty=selected_difficulty,
        search_query=search_query,
        sort_by=selected_sort,
    )

    st.caption(
        f"表示中: **{len(filtered_words)} 語**（全 {len(all_words)} 語中）"
    )

    # 該当なしの場合
    if not filtered_words:
        st.warning("条件に一致する単語は見つかりませんでした。検索キーワードや絞り込み条件を変更してください。")
        return

    # 6. ページネーション計算
    if selected_page_size == "すべて":
        page_size_int = 0
        total_pages = 1
        current_page = 1
    else:
        page_size_int = int(selected_page_size)
        total_pages = max(1, math.ceil(len(filtered_words) / page_size_int))
        if total_pages > 1:
            col_page_sel, col_page_info = st.columns([2, 2])
            with col_page_sel:
                current_page = st.selectbox(
                    "ページ切替",
                    options=list(range(1, total_pages + 1)),
                    index=0,
                    format_func=lambda p: f"ページ {p} / {total_pages}",
                    key="dict_page_select",
                )
            with col_page_info:
                start_num = (current_page - 1) * page_size_int + 1
                end_num = min(current_page * page_size_int, len(filtered_words))
                st.caption(f"{start_num} 〜 {end_num} 件目を表示中")
        else:
            current_page = 1

    paged_words, _ = paginate_items(
        items=filtered_words,
        page=current_page,
        page_size=page_size_int,
    )

    # 7. ユーザー学習状況の取得（任意）
    stats_map: Dict[int, WordStat] = {}
    if db is not None and user_email:
        try:
            stats_map = db.get_user_stats(user_email)
        except Exception:
            stats_map = {}

    st.write("")

    # 8. 単語カード一覧の描画（アコーディオン展開式）
    for item in paged_words:
        stat = stats_map.get(item.no)

        # ヘッダータイトルの作成
        stat_suffix = ""
        if stat:
            if stat.has_ever_failed:
                stat_suffix = f" [✕ 苦手: ミス{stat.incorrect_count}回]"
            elif stat.total_attempts > 0:
                stat_suffix = f" [○ 正解: {stat.total_attempts}回]"

        header_title = (
            f"【No.{item.no} {item.word}】（{item.reading}） "
            f"[{item.difficulty}] {stat_suffix}"
        )

        with st.expander(header_title, expanded=False):
            # 学習履歴が存在する場合は状況バーを表示
            if stat and stat.total_attempts > 0:
                col_st1, col_st2 = st.columns([3, 2])
                with col_st1:
                    st.caption(
                        f"📊 あなたの学習記録: 出題 {stat.total_attempts}回 / "
                        f"不正解 {stat.incorrect_count}回 (ミス率 {int(stat.incorrect_rate * 100)}%)"
                    )
                with col_st2:
                    attempt_str = format_attempt_time(stat.last_attempt_at)
                    last_icon = "🟢 正解" if stat.last_result == "correct" else "🔴 不正解"
                    st.caption(f"直近: {last_icon} | 最終出題: {attempt_str}")

            # 単語詳細カード（意味、場面例、つまずきポイント）
            display_word_detail_card(
                word=item.word,
                reading=item.reading,
                category=item.category,
                difficulty=item.difficulty,
                meaning=item.meaning,
                example=item.example,
                point=item.tips,
            )
