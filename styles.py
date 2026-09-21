"""styles.py

中学受験 国語 心情語対策アプリケーション
スマートフォン最適化カスタムCSS、パステルカラーテーマ、およびUIコンポーネントヘルパー。
"""

from __future__ import annotations

import html
from typing import Any
import streamlit as st

# ==============================================================================
# カラーパレット定数（Color Palette Constants）
# ==============================================================================
# メインカラー: 知的なフォレストグリーン
PRIMARY_COLOR = "#2E7D32"
PRIMARY_LIGHT = "#E8F5E9"
PRIMARY_DARK = "#1B5E20"

# サブカラー: 信頼感のあるブルー
SECONDARY_COLOR = "#1976D2"
SECONDARY_LIGHT = "#E3F2FD"
SECONDARY_DARK = "#0D47A1"

# 正解・不正解カラー
SUCCESS_COLOR = "#2E7D32"
SUCCESS_BG = "#E8F5E9"
ERROR_COLOR = "#D32F2F"
ERROR_BG = "#FFEBEE"

# 背景・ニュートラルカラー
BG_COLOR = "#FAFAFA"
CARD_BG = "#FFFFFF"
TEXT_COLOR = "#212121"
TEXT_MUTED = "#616161"
BORDER_COLOR = "#E0E0E0"

# 難易度別カラー
DIFF_COLORS = {
    "並": {"bg": "#E8F5E9", "text": "#2E7D32", "border": "#A5D6A7"},
    "中": {"bg": "#FFF8E1", "text": "#E65100", "border": "#FFE082"},
    "高": {"bg": "#FFEBEE", "text": "#C62828", "border": "#FFCDD2"},
}

# ==============================================================================
# カスタムCSS定義（Custom CSS）
# ==============================================================================
CUSTOM_CSS = """
/* 全体ベーススタイル */
html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, "Hiragino Kaku Gothic ProN", "Yu Gothic", sans-serif;
    color: #212121;
}

/* スマホ最適化: Streamlitメインコンテナの余白調整 */
.block-container {
    padding-top: 1.2rem;
    padding-bottom: 3rem;
    padding-left: 0.8rem;
    padding-right: 0.8rem;
    max-width: 760px;
}

/* ボタンのタップ領域拡大（親指操作対応） */
div.stButton > button {
    border-radius: 12px;
    min-height: 52px;
    font-size: 16px;
    font-weight: bold;
    padding: 10px 16px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.08);
    transition: all 0.2s ease;
    border: 1px solid #D1D5DB;
    width: 100%;
}

div.stButton > button:hover {
    box-shadow: 0 4px 8px rgba(0,0,0,0.12);
    transform: translateY(-1px);
}

div.stButton > button:active {
    transform: translateY(1px);
    box-shadow: 0 1px 2px rgba(0,0,0,0.08);
}

/* プライマリボタン（決定・回答・開始） */
div.stButton > button[kind="primary"] {
    background-color: #2E7D32;
    color: #FFFFFF;
    border: none;
}

div.stButton > button[kind="primary"]:hover {
    background-color: #1B5E20;
    color: #FFFFFF;
}

/* 4択ラジオボタンの押しやすさ向上 */
div[role="radiogroup"] {
    display: flex;
    flex-direction: column;
    gap: 10px;
}

div[role="radiogroup"] > label {
    background-color: #FFFFFF;
    border: 2px solid #E0E0E0;
    border-radius: 12px;
    padding: 12px 16px;
    margin-bottom: 0px !important;
    display: flex;
    align-items: center;
    cursor: pointer;
    transition: all 0.2s ease;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}

div[role="radiogroup"] > label:hover {
    border-color: #81C784;
    background-color: #F9FBE7;
}

/* 選択されたラジオボタンのハイライト */
div[role="radiogroup"] > label[data-checked="true"] {
    border-color: #4CAF50 !important;
    background-color: #E8F5E9 !important;
    font-weight: bold;
}

/* 問題文カード */
.question-card {
    background-color: #FFFFFF;
    border: 2px solid #81C784;
    border-radius: 16px;
    padding: 24px 20px;
    margin-top: 10px;
    margin-bottom: 20px;
    text-align: center;
    box-shadow: 0 4px 6px rgba(0,0,0,0.05);
}

.question-card .question-label {
    font-size: 13px;
    color: #558B2F;
    font-weight: 600;
    letter-spacing: 0.5px;
    margin-bottom: 8px;
}

.question-card .question-text {
    font-size: 26px;
    font-weight: 800;
    color: #1B5E20;
    line-height: 1.4;
    margin: 8px 0;
}

.question-card .question-sub {
    font-size: 14px;
    color: #616161;
    margin-top: 6px;
}

/* 回答判定結果バナー */
.result-banner {
    border-radius: 14px;
    padding: 16px 20px;
    margin: 16px 0;
    text-align: center;
}

.result-banner-correct {
    background-color: #E8F5E9;
    border: 2px solid #2E7D32;
    color: #1B5E20;
}

.result-banner-correct .banner-title {
    font-size: 22px;
    font-weight: 800;
    margin-bottom: 4px;
}

.result-banner-incorrect {
    background-color: #FFEBEE;
    border: 2px solid #D32F2F;
    color: #C62828;
}

.result-banner-incorrect .banner-title {
    font-size: 22px;
    font-weight: 800;
    margin-bottom: 4px;
}

/* 単語・情報バッジ */
.badge {
    display: inline-block;
    padding: 4px 10px;
    border-radius: 9999px;
    font-size: 12px;
    font-weight: 700;
    line-height: 1.2;
    margin: 2px 4px;
    text-align: center;
}

.badge-diff-low {
    background-color: #E8F5E9;
    color: #2E7D32;
    border: 1px solid #A5D6A7;
}

.badge-diff-mid {
    background-color: #FFF8E1;
    color: #E65100;
    border: 1px solid #FFE082;
}

.badge-diff-high {
    background-color: #FFEBEE;
    color: #C62828;
    border: 1px solid #FFCDD2;
}

.badge-category {
    background-color: #E3F2FD;
    color: #1565C0;
    border: 1px solid #90CAF9;
}

.badge-outline {
    background-color: #FFFFFF;
    color: #616161;
    border: 1px solid #BDBDBD;
}

/* 統計サマリーカード */
.stat-card {
    background-color: #FFFFFF;
    border: 1px solid #E0E0E0;
    border-radius: 12px;
    padding: 16px 12px;
    text-align: center;
    box-shadow: 0 2px 4px rgba(0,0,0,0.04);
}

.stat-card .stat-value {
    font-size: 28px;
    font-weight: 800;
    color: #2E7D32;
    line-height: 1.2;
}

.stat-card .stat-label {
    font-size: 12px;
    color: #757575;
    margin-top: 4px;
    font-weight: 600;
}

.stat-card .stat-subtext {
    font-size: 11px;
    color: #9E9E9E;
    margin-top: 2px;
}

/* 単語詳細カード（辞典・苦手ノート用） */
.word-detail-card {
    background-color: #FFFFFF;
    border: 1px solid #E0E0E0;
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 12px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}

.word-detail-header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 8px;
}

.word-detail-title {
    font-size: 20px;
    font-weight: 800;
    color: #212121;
}

.word-detail-reading {
    font-size: 13px;
    color: #757575;
    margin-left: 8px;
}

.word-detail-meaning {
    font-size: 15px;
    color: #333333;
    line-height: 1.5;
    margin: 8px 0;
}

.word-detail-box {
    background-color: #F8F9FA;
    border-left: 4px solid #81C784;
    border-radius: 4px;
    padding: 10px 12px;
    margin-top: 8px;
    font-size: 13px;
    line-height: 1.5;
}

.word-detail-box-label {
    font-weight: 700;
    color: #2E7D32;
    margin-bottom: 4px;
}
"""


# ==============================================================================
# UIレンダリング関数（UI Rendering Helpers）
# ==============================================================================
def apply_custom_styles() -> None:
    """StreamlitアプリにカスタムCSSをインジェクトする。"""
    st.markdown(f"<style>{CUSTOM_CSS}</style>", unsafe_allow_html=True)


def get_custom_css() -> str:
    """定義されているカスタムCSS文字列を返す。"""
    return CUSTOM_CSS


def render_badge(text: str, badge_type: str = "default") -> str:
    """バッジのHTMLスニペットを生成する。

    Args:
        text: 表示テキスト
        badge_type: 'diff_並', 'diff_中', 'diff_高', 'diff_low', 'diff_mid',
                    'diff_high', 'category', または 'default'

    Returns:
        バッジのHTML文字列
    """
    safe_text = html.escape(str(text))
    cls_map = {
        "diff_並": "badge-diff-low",
        "diff_中": "badge-diff-mid",
        "diff_高": "badge-diff-high",
        "diff_low": "badge-diff-low",
        "diff_mid": "badge-diff-mid",
        "diff_high": "badge-diff-high",
        "category": "badge-category",
    }
    css_class = cls_map.get(badge_type, "badge-outline")
    return f'<span class="badge {css_class}">{safe_text}</span>'


def render_question_card(
    content: str,
    label: str = "問題",
    subtext: str = "",
    category: str = "",
    difficulty: str = "",
) -> str:
    """問題文表示用のカードHTMLを生成する。

    Args:
        content: 問題本文（心情語または意味）
        label: ヘッダーラベル（例: "この言葉の意味を選ぼう"）
        subtext: サブテキスト（任意）
        category: カテゴリ名（任意）
        difficulty: 難易度（並/中/高、任意）

    Returns:
        カードHTML文字列
    """
    badges = []
    if category:
        badges.append(render_badge(category, badge_type="category"))
    if difficulty:
        badges.append(render_badge(f"難易度: {difficulty}", badge_type=f"diff_{difficulty}"))

    badges_html = f'<div style="margin-bottom: 8px;">{" ".join(badges)}</div>' if badges else ""
    sub_div = f'<div class="question-sub">{html.escape(subtext)}</div>' if subtext else ""

    return (
        f'<div class="question-card">\n'
        f"    {badges_html}\n"
        f'    <div class="question-label">{html.escape(label)}</div>\n'
        f'    <div class="question-text">{html.escape(content)}</div>\n'
        f"    {sub_div}\n"
        f"</div>"
    )


def render_result_banner(
    is_correct: bool,
    correct_word: str = "",
    correct_meaning: str = "",
) -> str:
    """回答判定結果バナーHTMLを生成する。

    Args:
        is_correct: 正解か否か
        correct_word: 正解の心情語（任意）
        correct_meaning: 正解の意味（任意）

    Returns:
        バナーHTML文字列
    """
    if is_correct:
        return (
            '<div class="result-banner result-banner-correct">\n'
            '    <div class="banner-title">⭕ 正解！</div>\n'
            "    <div>すばらしい！その調子で進みましょう。</div>\n"
            "</div>"
        )
    else:
        detail_html = ""
        if correct_word and correct_meaning:
            detail_html = (
                f'    <div style="margin-top: 6px; font-size: 14px;">'
                f"正解は「<strong>{html.escape(correct_word)}</strong>」: "
                f"{html.escape(correct_meaning)}</div>\n"
            )
        elif correct_word:
            detail_html = (
                f'    <div style="margin-top: 6px; font-size: 14px;">'
                f"正解は「<strong>{html.escape(correct_word)}</strong>」です。</div>\n"
            )

        return (
            f'<div class="result-banner result-banner-incorrect">\n'
            f'    <div class="banner-title">❌ おしい！</div>\n'
            f"    <div>間違えた問題は「苦手ノート」に保存されます。復習しましょう！</div>\n"
            f"{detail_html}"
            f"</div>"
        )


def render_stat_card(label: str, value: Any, subtext: str = "") -> str:
    """統計サマリーカードのHTMLスニペットを生成する。

    Args:
        label: 指標名（例: "苦手語句数"）
        value: 指標値（例: "12語", 85% 等）
        subtext: 補足説明（任意）

    Returns:
        カードHTML文字列
    """
    safe_label = html.escape(str(label))
    safe_val = html.escape(str(value))
    sub_div = f'<div class="stat-subtext">{html.escape(subtext)}</div>' if subtext else ""

    return (
        f'<div class="stat-card">\n'
        f'    <div class="stat-value">{safe_val}</div>\n'
        f'    <div class="stat-label">{safe_label}</div>\n'
        f"    {sub_div}\n"
        f"</div>"
    )


def render_word_detail_card(
    word: str,
    reading: str,
    category: str,
    difficulty: str,
    meaning: str,
    example: str = "",
    point: str = "",
) -> str:
    """辞典や苦手ノート用の単語詳細カードHTMLを生成する。

    Args:
        word: 心情語
        reading: 読み仮名
        category: カテゴリ
        difficulty: 難易度（並/中/高）
        meaning: 意味
        example: 代表的な場面例（任意）
        point: つまずきポイント（任意）

    Returns:
        カードHTML文字列
    """
    cat_badge = render_badge(category, badge_type="category")
    diff_badge = render_badge(f"難易度: {difficulty}", badge_type=f"diff_{difficulty}")

    example_box = ""
    if example:
        example_box = (
            f'    <div class="word-detail-box">\n'
            f'        <div class="word-detail-box-label">📖 物語文での場面例</div>\n'
            f"        <div>{html.escape(example)}</div>\n"
            f"    </div>\n"
        )

    point_box = ""
    if point:
        point_box = (
            f'    <div class="word-detail-box" style="border-left-color: #FFA726;">\n'
            f'        <div class="word-detail-box-label" style="color: #E65100;">💡 つまずきポイント・識別</div>\n'
            f"        <div>{html.escape(point)}</div>\n"
            f"    </div>\n"
        )

    return (
        f'<div class="word-detail-card">\n'
        f'    <div class="word-detail-header">\n'
        f"        <div>\n"
        f'            <span class="word-detail-title">{html.escape(word)}</span>\n'
        f'            <span class="word-detail-reading">（{html.escape(reading)}）</span>\n'
        f"        </div>\n"
        f"        <div>{cat_badge} {diff_badge}</div>\n"
        f"    </div>\n"
        f'    <div class="word-detail-meaning">{html.escape(meaning)}</div>\n'
        f"{example_box}"
        f"{point_box}"
        f"</div>"
    )


# ==============================================================================
# Streamlit直接描画ヘルパー（Streamlit Direct Display Helpers）
# ==============================================================================
def display_question_card(
    content: str,
    label: str = "問題",
    subtext: str = "",
    category: str = "",
    difficulty: str = "",
) -> None:
    """問題文カードをStreamlit画面に直接描画する。"""
    st.markdown(
        render_question_card(
            content=content,
            label=label,
            subtext=subtext,
            category=category,
            difficulty=difficulty,
        ),
        unsafe_allow_html=True,
    )


def display_result_banner(
    is_correct: bool,
    correct_word: str = "",
    correct_meaning: str = "",
) -> None:
    """回答判定結果バナーをStreamlit画面に直接描画する。"""
    st.markdown(
        render_result_banner(
            is_correct=is_correct,
            correct_word=correct_word,
            correct_meaning=correct_meaning,
        ),
        unsafe_allow_html=True,
    )


def display_stat_card(label: str, value: Any, subtext: str = "") -> None:
    """統計サマリーカードをStreamlit画面に直接描画する。"""
    st.markdown(render_stat_card(label=label, value=value, subtext=subtext), unsafe_allow_html=True)


def display_word_detail_card(
    word: str,
    reading: str,
    category: str,
    difficulty: str,
    meaning: str,
    example: str = "",
    point: str = "",
) -> None:
    """単語詳細カードをStreamlit画面に直接描画する。"""
    st.markdown(
        render_word_detail_card(
            word=word,
            reading=reading,
            category=category,
            difficulty=difficulty,
            meaning=meaning,
            example=example,
            point=point,
        ),
        unsafe_allow_html=True,
    )
