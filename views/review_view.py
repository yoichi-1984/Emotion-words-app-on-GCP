"""views/review_view.py

中学受験 国語 心情語対策アプリケーション
苦手ノート画面ビュー（間違えた問題一覧、統計サマリー、ソート・絞り込み、詳細展開表示）。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
import streamlit as st

from data_loader import WordItem
from db import DatabaseInterface, WordStat
from quiz_logic import can_start_review_mode
from styles import (
    display_stat_card,
    display_word_detail_card,
    render_badge,
)

# ==============================================================================
# ソートオプション定数
# ==============================================================================
SORT_INCORRECT_COUNT = "不正解回数が多い順"
SORT_INCORRECT_RATE = "不正解率が高い順"
SORT_WORD_NO = "単語番号順"
SORT_CATEGORY = "カテゴリ順"
SORT_RECENT_ATTEMPT = "最近解いた順"

SORT_OPTIONS = [
    SORT_INCORRECT_COUNT,
    SORT_INCORRECT_RATE,
    SORT_WORD_NO,
    SORT_CATEGORY,
    SORT_RECENT_ATTEMPT,
]


# ==============================================================================
# データモデル
# ==============================================================================
@dataclass(frozen=True)
class ReviewItem:
    """苦手ノート表示用の統合データモデル（WordStat と WordItem の結合）

    Attributes:
        stat: 単語別学習履歴
        word_item: 単語マスターデータ
    """

    stat: WordStat
    word_item: WordItem

    @property
    def word_no(self) -> int:
        return self.stat.word_no

    @property
    def word(self) -> str:
        return self.word_item.word

    @property
    def reading(self) -> str:
        return self.word_item.reading

    @property
    def category(self) -> str:
        return self.word_item.category

    @property
    def difficulty(self) -> str:
        return self.word_item.difficulty

    @property
    def meaning(self) -> str:
        return self.word_item.meaning

    @property
    def example(self) -> str:
        return self.word_item.example

    @property
    def tips(self) -> str:
        return self.word_item.tips

    @property
    def total_attempts(self) -> int:
        return self.stat.total_attempts

    @property
    def incorrect_count(self) -> int:
        return self.stat.incorrect_count

    @property
    def incorrect_rate(self) -> float:
        return self.stat.incorrect_rate

    @property
    def has_ever_failed(self) -> bool:
        return self.stat.has_ever_failed

    @property
    def last_attempt_at(self) -> Optional[str]:
        return self.stat.last_attempt_at

    @property
    def last_result(self) -> Optional[str]:
        return self.stat.last_result


# ==============================================================================
# ロジック・ヘルパー関数（ビジネスロジック層）
# ==============================================================================
def build_review_items(
    stats: List[WordStat],
    all_words: List[WordItem],
) -> List[ReviewItem]:
    """過去に間違えたことのある単語統計とマスターデータを結合して ReviewItem のリストを生成する。

    Args:
        stats: 単語別学習履歴リスト
        all_words: 全単語マスターデータリスト

    Returns:
        List[ReviewItem]: 苦手単語アイテムのリスト
    """
    words_map = {w.no: w for w in all_words}
    review_items = []

    for stat in stats:
        if stat.has_ever_failed and stat.word_no in words_map:
            review_items.append(ReviewItem(stat=stat, word_item=words_map[stat.word_no]))

    return review_items


def calculate_review_summary(items: List[ReviewItem]) -> Dict[str, Any]:
    """苦手単語群からサマリー統計（語数、総出題数、総不正解数、総合不正解率）を計算する。

    Args:
        items: 苦手単語アイテムのリスト

    Returns:
        Dict[str, Any]: 集計サマリー情報
    """
    failed_words_count = len(items)
    total_attempts = sum(item.total_attempts for item in items)
    total_incorrect = sum(item.incorrect_count for item in items)

    overall_incorrect_rate = (
        round((total_incorrect / total_attempts) * 100, 1) if total_attempts > 0 else 0.0
    )

    return {
        "failed_words_count": failed_words_count,
        "total_attempts": total_attempts,
        "total_incorrect": total_incorrect,
        "overall_incorrect_rate": overall_incorrect_rate,
    }


def filter_and_sort_review_items(
    items: List[ReviewItem],
    sort_by: str = SORT_INCORRECT_COUNT,
    category_filter: str = "すべて",
    search_query: str = "",
) -> List[ReviewItem]:
    """苦手単語リストを指定条件で絞り込み、ソートする。

    Args:
        items: 絞り込み前の単語アイテムリスト
        sort_by: 並び順
        category_filter: 絞り込みカテゴリ ("すべて" またはカテゴリ名)
        search_query: 単語名・読み・意味の検索文字列

    Returns:
        List[ReviewItem]: 絞り込み・ソート後の単語アイテムリスト
    """
    filtered = list(items)

    # 1. カテゴリ絞り込み
    if category_filter and category_filter != "すべて":
        filtered = [item for item in filtered if item.category == category_filter]

    # 2. キーワード検索（単語、読み、意味）
    query = search_query.strip().lower()
    if query:
        filtered = [
            item
            for item in filtered
            if query in item.word.lower()
            or query in item.reading.lower()
            or query in item.meaning.lower()
        ]

    # 3. ソート処理
    if sort_by == SORT_INCORRECT_COUNT:
        # 不正解回数降順 -> 不正解率降順 -> 単語番号昇順
        filtered.sort(key=lambda x: (-x.incorrect_count, -x.incorrect_rate, x.word_no))
    elif sort_by == SORT_INCORRECT_RATE:
        # 不正解率降順 -> 不正解回数降順 -> 単語番号昇順
        filtered.sort(key=lambda x: (-x.incorrect_rate, -x.incorrect_count, x.word_no))
    elif sort_by == SORT_WORD_NO:
        # 単語番号昇順
        filtered.sort(key=lambda x: x.word_no)
    elif sort_by == SORT_CATEGORY:
        # カテゴリ昇順 -> 単語番号昇順
        filtered.sort(key=lambda x: (x.category, x.word_no))
    elif sort_by == SORT_RECENT_ATTEMPT:
        # 直近解いた日時降順（Noneは末尾） -> 単語番号昇順
        filtered.sort(key=lambda x: (x.last_attempt_at or "", x.word_no), reverse=True)

    return filtered


def format_attempt_time(iso_str: Optional[str]) -> str:
    """ISO 8601 形式の日時文字列を見やすい日時にフォーマットする。

    Args:
        iso_str: ISO 8601 文字列

    Returns:
        str: フォーマットされた日時文字列 (例: "2026/09/21 12:34")
    """
    if not iso_str:
        return "未回答"
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime("%Y/%m/%d %H:%M")
    except Exception:
        # ISOパース不可の場合は先頭16文字程度を返す
        return iso_str[:16].replace("T", " ")


# ==============================================================================
# UIレンダリングコンポーネント（View層）
# ==============================================================================
def render_review_view(
    db: DatabaseInterface,
    user_email: str,
    all_words: List[WordItem],
) -> None:
    """苦手ノート画面を描画するメイン関数。

    過去に間違えた問題の一覧、サマリー統計、ソート・絞り込み、および単語詳細を表示する。

    Args:
        db: データベースクライアント
        user_email: ログイン中のユーザーメールアドレス
        all_words: 全単語マスターデータリスト
    """
    st.title("📓 苦手ノート（間違えた問題一覧）")
    st.write(
        "これまでのクイズで間違えたことのある単語が自動で記録されます。"
        "意味や場面例、つまずきポイントを反復確認して、完全定着を目指しましょう！"
    )

    # 1. データ取得と結合
    stats = db.get_failed_words_stats(user_email)
    review_items = build_review_items(stats, all_words)

    # 2. 苦手単語が0件の場合（エンプティステート）
    if not review_items:
        st.info(
            "🎉 **現在、苦手ノートに登録されている単語はありません！**\n\n"
            "クイズを解いていくと、間違えた問題がここに自動的に記録されます。\n"
            "左上のメニューから「クイズ（学習モード）」に挑戦してみましょう！"
        )
        return

    # 3. サマリー統計カードの描画
    summary = calculate_review_summary(review_items)
    col1, col2, col3 = st.columns(3)
    with col1:
        display_stat_card("苦手語句数", f"{summary['failed_words_count']} 語", "過去に間違えた単語")
    with col2:
        display_stat_card("総出題回数", f"{summary['total_attempts']} 回", "苦手単語の累積出題")
    with col3:
        display_stat_card("総合不正解率", f"{summary['overall_incorrect_rate']}%", "苦手単語のミス率")

    st.write("")

    # 4. 苦手復習モードに関するインフォメーション
    can_review = can_start_review_mode(len(review_items), min_required=10)
    if can_review:
        st.success(
            "🎯 **苦手語句が10語以上蓄積されています！**\n\n"
            "クイズ画面の「苦手復習モード」で、間違えた問題だけを集中特訓できます。"
        )
    else:
        st.info(
            f"💡 **苦手復習モードの開放条件**: 間違えた単語が **10語** 以上蓄積されると、"
            f"クイズ画面で「苦手復習モード」がプレイ可能になります（現在 **{len(review_items)} / 10** 語）。"
        )

    st.write("")
    st.subheader("📋 苦手単語一覧")

    # 5. 検索および絞り込みコントロール
    search_query = st.text_input(
        "🔍 単語・読み・意味で検索",
        value="",
        placeholder="例: 気後れ、きおくれ、自信がない ...",
        key="review_search_input",
    )

    # カテゴリ一覧の抽出
    categories = sorted(list({w.category for w in all_words}))
    category_options = ["すべて"] + categories

    col_filter, col_sort = st.columns(2)
    with col_filter:
        selected_category = st.selectbox(
            "📂 カテゴリで絞り込み",
            options=category_options,
            index=0,
            key="review_category_select",
        )
    with col_sort:
        selected_sort = st.selectbox(
            "↕ 並び替え（ソート）",
            options=SORT_OPTIONS,
            index=0,
            key="review_sort_select",
        )

    # 6. フィルタ・ソート適用
    displayed_items = filter_and_sort_review_items(
        items=review_items,
        sort_by=selected_sort,
        category_filter=selected_category,
        search_query=search_query,
    )

    st.caption(
        f"表示中: **{len(displayed_items)} 語**（全苦手語句: {len(review_items)} 語）"
    )

    # 該当なしの場合
    if not displayed_items:
        st.warning("条件に一致する単語は見つかりませんでした。検索条件を変更してください。")
        return

    # 7. 単語カード一覧（アコーディオン表示）
    for item in displayed_items:
        # 直近結果に応じたインジケータアイコン
        last_icon = "🟢 直近:正解" if item.last_result == "correct" else "🔴 直近:不正解"
        rate_percent = int(item.incorrect_rate * 100)

        cat_badge = render_badge(item.category, badge_type="category")
        diff_badge = render_badge(f"難易度: {item.difficulty}", badge_type=f"diff_{item.difficulty}")

        header_title = (
            f"【No.{item.word_no} {item.word}】（{item.reading}） "
            f"— ✕ 不正解: {item.incorrect_count}回 / {item.total_attempts}回 ({rate_percent}%)"
        )

        with st.expander(header_title, expanded=False):
            # ヘッダー情報（バッジ + 最終学習状況）
            col_badges, col_status = st.columns([3, 2])
            with col_badges:
                st.markdown(f"{cat_badge} {diff_badge}", unsafe_allow_html=True)
            with col_status:
                attempt_str = format_attempt_time(item.last_attempt_at)
                st.caption(f"{last_icon} | 最終出題: {attempt_str}")

            # 単語詳細カード（意味、物語文場面例、つまずきポイント）
            display_word_detail_card(
                word=item.word,
                reading=item.reading,
                category=item.category,
                difficulty=item.difficulty,
                meaning=item.meaning,
                example=item.example,
                point=item.tips,
            )
