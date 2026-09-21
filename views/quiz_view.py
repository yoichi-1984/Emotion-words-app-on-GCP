"""views/quiz_view.py

中学受験 国語 心情語対策アプリケーション
クイズ学習画面ビュー（モード選択、1問1答、ルビ確認、解説トグル、結果画面）。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import streamlit as st

from data_loader import WordItem
from db import DatabaseInterface, WordStat
from quiz_logic import (
    QuizQuestion,
    build_quiz_session,
    can_start_review_mode,
    evaluate_answer,
    extract_failed_words,
    select_quiz_words,
    select_review_words,
)
from styles import (
    display_question_card,
    display_result_banner,
    display_stat_card,
    display_word_detail_card,
    render_badge,
)

# ==============================================================================
# 画面ステート定数
# ==============================================================================
QUIZ_STATE_SELECT = "select"
QUIZ_STATE_ANSWERING = "answering"
QUIZ_STATE_ANSWERED = "answered"
QUIZ_STATE_RESULT = "result"

# サブモード定数
SUBMODE_RANDOM = "random"
SUBMODE_CATEGORY = "category"
SUBMODE_REVIEW = "review"


# ==============================================================================
# セッション状態管理関数
# ==============================================================================
def init_quiz_state() -> None:
    """クイズ画面用のセッションステートを初期化する。"""
    if "quiz_state" not in st.session_state:
        st.session_state.quiz_state = QUIZ_STATE_SELECT

    if "quiz_config" not in st.session_state:
        st.session_state.quiz_config = {
            "mode": 1,
            "submode": SUBMODE_RANDOM,
            "category_name": "",
        }

    if "quiz_questions" not in st.session_state:
        st.session_state.quiz_questions = []

    if "current_q_index" not in st.session_state:
        st.session_state.current_q_index = 0

    if "current_selected_option" not in st.session_state:
        st.session_state.current_selected_option = None

    if "session_results" not in st.session_state:
        st.session_state.session_results = []

    if "score" not in st.session_state:
        st.session_state.score = 0


def start_quiz_session(
    all_words: List[WordItem],
    mode: int,
    submode: str,
    category_name: str = "",
    failed_words: Optional[List[WordItem]] = None,
    question_count: int = 10,
) -> None:
    """指定された設定でクイズセッションを開始し、セッションステートをセットアップする。

    Args:
        all_words: 全単語リスト
        mode: 出題モード (1: 心情語 → 意味, 2: 意味 → 心情語)
        submode: サブモード ("random" | "category" | "review")
        category_name: カテゴリ固定時のカテゴリ名
        failed_words: 苦手復習モード用の間違えた単語リスト
        question_count: 出題件数（デフォルト10）
    """
    if failed_words is None:
        failed_words = []

    if submode == SUBMODE_RANDOM:
        pool = all_words
        selected = select_quiz_words(pool, count=question_count)
    elif submode == SUBMODE_CATEGORY:
        pool = [w for w in all_words if w.category == category_name]
        selected = select_quiz_words(pool, count=question_count)
    elif submode == SUBMODE_REVIEW:
        selected = select_review_words(failed_words, count=question_count)
    else:
        raise ValueError(f"無効なサブモードです: {submode}")

    questions = build_quiz_session(selected_words=selected, all_words=all_words, mode=mode)

    st.session_state.quiz_config = {
        "mode": mode,
        "submode": submode,
        "category_name": category_name,
    }
    st.session_state.quiz_questions = questions
    st.session_state.current_q_index = 0
    st.session_state.current_selected_option = None
    st.session_state.session_results = []
    st.session_state.score = 0
    st.session_state.quiz_state = QUIZ_STATE_ANSWERING


def submit_answer(
    db: DatabaseInterface,
    user_email: str,
    selected_option: str,
) -> bool:
    """ユーザーの回答を判定し、DBおよびセッション結果に記録する。

    Args:
        db: データベースクライアント
        user_email: ユーザーメールアドレス
        selected_option: ユーザーが選択した回答テキスト

    Returns:
        bool: 正解なら True, 不正解なら False
    """
    q_index = st.session_state.current_q_index
    questions: List[QuizQuestion] = st.session_state.quiz_questions
    current_q = questions[q_index]

    is_correct = evaluate_answer(selected_option, current_q.correct_answer)

    # DBに学習結果を記録
    db.record_attempt(
        email=user_email,
        word_no=current_q.target_word.no,
        word=current_q.target_word.word,
        category=current_q.target_word.category,
        is_correct=is_correct,
    )

    if is_correct:
        st.session_state.score += 1

    # セッション結果リストに追加
    result_entry = {
        "question_no": q_index + 1,
        "target_word_no": current_q.target_word.no,
        "target_word": current_q.target_word.word,
        "reading": current_q.reading,
        "category": current_q.target_word.category,
        "difficulty": current_q.target_word.difficulty,
        "mode": current_q.mode,
        "question_text": current_q.question_text,
        "selected_option": selected_option,
        "correct_answer": current_q.correct_answer,
        "is_correct": is_correct,
        "meaning": current_q.target_word.meaning,
        "example": current_q.target_word.example,
        "tips": current_q.target_word.tips,
        "options": current_q.options,
    }
    st.session_state.session_results.append(result_entry)
    st.session_state.current_selected_option = selected_option
    st.session_state.quiz_state = QUIZ_STATE_ANSWERED

    return is_correct


def next_question() -> None:
    """次の問題へ進む、または全問終了時に結果画面へ遷移する。"""
    q_index = st.session_state.current_q_index
    total = len(st.session_state.quiz_questions)

    if q_index + 1 < total:
        st.session_state.current_q_index = q_index + 1
        st.session_state.current_selected_option = None
        st.session_state.quiz_state = QUIZ_STATE_ANSWERING
    else:
        st.session_state.quiz_state = QUIZ_STATE_RESULT


def reset_to_select() -> None:
    """モード選択画面に戻る。"""
    st.session_state.quiz_state = QUIZ_STATE_SELECT
    st.session_state.current_selected_option = None


# ==============================================================================
# UI画面描画コンポーネント
# ==============================================================================
def render_quiz_view(
    db: DatabaseInterface,
    user_email: str,
    all_words: List[WordItem],
) -> None:
    """クイズ画面のメイン描画関数。

    セッション状態に応じて、モード選択・出題・判定解説・結果画面を描画する。

    Args:
        db: データベースクライアント
        user_email: ログイン中のユーザーメール
        all_words: 単語マスターデータリスト
    """
    init_quiz_state()

    state = st.session_state.quiz_state

    if state == QUIZ_STATE_SELECT:
        _render_select_screen(db=db, user_email=user_email, all_words=all_words)
    elif state == QUIZ_STATE_ANSWERING:
        _render_answering_screen(db=db, user_email=user_email)
    elif state == QUIZ_STATE_ANSWERED:
        _render_answered_screen()
    elif state == QUIZ_STATE_RESULT:
        _render_result_screen(db=db, user_email=user_email, all_words=all_words)
    else:
        # 想定外の状態の場合はモード選択へリセット
        st.session_state.quiz_state = QUIZ_STATE_SELECT
        st.rerun()


def _render_select_screen(
    db: DatabaseInterface,
    user_email: str,
    all_words: List[WordItem],
) -> None:
    """1. モード選択画面を描画する。"""
    st.title("🎯 心情語クイズ（全10問）")
    st.write("出題形式と出題範囲を選んで、クイズをスタートしましょう！")

    # 苦手単語の取得
    failed_stats = db.get_failed_words_stats(user_email)
    failed_words = extract_failed_words(all_words, failed_stats)
    review_available = can_start_review_mode(len(failed_words), min_required=10)

    # 1. 出題形式（基本モード）
    st.subheader("1. 出題形式")
    mode_options = {
        "モード1: 心情語 ➔ 意味（言葉の意味を答える）": 1,
        "モード2: 意味 ➔ 心情語（意味に合う言葉を答える）": 2,
    }
    selected_mode_label = st.radio(
        "問題の出題形式を選択:",
        options=list(mode_options.keys()),
        index=0,
        key="select_mode_radio",
    )
    mode = mode_options[selected_mode_label]

    # 2. 出題範囲（サブモード）
    st.subheader("2. 出題範囲")
    submode_display_names = {
        SUBMODE_RANDOM: "🎲 全カテゴリからランダム（全272語から出題）",
        SUBMODE_CATEGORY: "📂 カテゴリを指定（8つの感情カテゴリから選択）",
        SUBMODE_REVIEW: f"🔥 苦手復習モード（間違えた問題から出題 / 現在: {len(failed_words)}問）",
    }

    submode_choice = st.radio(
        "出題する範囲を選択:",
        options=[SUBMODE_RANDOM, SUBMODE_CATEGORY, SUBMODE_REVIEW],
        format_func=lambda s: submode_display_names[s],
        index=0,
        key="select_submode_radio",
    )

    category_name = ""
    start_disabled = False

    if submode_choice == SUBMODE_CATEGORY:
        # カテゴリ一覧の取得（出現順序を維持）
        unique_categories: List[str] = []
        for w in all_words:
            if w.category not in unique_categories:
                unique_categories.append(w.category)

        category_name = st.selectbox(
            "特訓するカテゴリを選択してください:",
            options=unique_categories,
            key="select_category_box",
        )

    elif submode_choice == SUBMODE_REVIEW:
        if not review_available:
            st.info(
                f"💡 **苦手復習モードは準備中です**\n\n"
                f"過去に間違えた問題が **10問以上** 蓄積されると開放されます。（現在: **{len(failed_words)} / 10問**）\n\n"
                f"通常のクイズに挑戦して、苦手な語句を見つけましょう！"
            )
            start_disabled = True
        else:
            st.success(
                f"🔥 **苦手復習モードが開放されています！**\n\n"
                f"過去に間違えた **{len(failed_words)}問** の中からランダムに10問出題されます。"
            )

    st.write("")
    if st.button(
        "クイズをスタート（全10問） ➔",
        type="primary",
        disabled=start_disabled,
        use_container_width=True,
        key="btn_start_quiz",
    ):
        start_quiz_session(
            all_words=all_words,
            mode=mode,
            submode=submode_choice,
            category_name=category_name,
            failed_words=failed_words,
            question_count=10,
        )
        st.rerun()


def _render_answering_screen(
    db: DatabaseInterface,
    user_email: str,
) -> None:
    """2. 1問1答 出題・回答画面を描画する。"""
    questions: List[QuizQuestion] = st.session_state.quiz_questions
    idx = st.session_state.current_q_index
    total = len(questions)

    if idx >= total or not questions:
        st.session_state.quiz_state = QUIZ_STATE_SELECT
        st.rerun()
        return

    current_q = questions[idx]

    # プログレスバー & 問題番号表示
    progress_val = float(idx) / float(total)
    st.progress(progress_val)
    st.caption(f"第 {idx + 1} / {total} 問")

    # 問題カードの表示
    if current_q.mode == 1:
        display_question_card(
            content=current_q.target_word.word,
            label="この心情語の意味として最も適切なものを選ぼう",
            category=current_q.target_word.category,
            difficulty=current_q.target_word.difficulty,
        )
    else:
        display_question_card(
            content=current_q.target_word.meaning,
            label="この意味に最も合致する心情語を選ぼう",
            category=current_q.target_word.category,
            difficulty=current_q.target_word.difficulty,
        )

    # ルビ（読み仮名）確認機能（タップで展開）
    with st.popover("📖 読み方（ふりがな）を確認する"):
        st.markdown(f"**心情語**: **{current_q.target_word.word}**")
        st.markdown(f"**読み仮名**: **{current_q.reading}**")
        st.markdown(f"**難易度**: {current_q.target_word.difficulty}")
        st.markdown(f"**カテゴリ**: {current_q.target_word.category}")

    st.write("")

    # 4択ラジオボタン（初期状態は未選択）
    selected_option = st.radio(
        "選択肢（4つの中から1つ選んでください）:",
        options=current_q.options,
        index=None,
        key=f"quiz_radio_q_{idx}",
    )

    st.write("")

    # 回答するボタン
    if st.button("回答する ➔", type="primary", use_container_width=True, key=f"btn_submit_q_{idx}"):
        if selected_option is None:
            st.warning("⚠️ 選択肢を1つ選んでから回答してください。")
        else:
            submit_answer(db=db, user_email=user_email, selected_option=selected_option)
            st.rerun()


def _render_answered_screen() -> None:
    """3. 判定・解説画面を描画する。"""
    questions: List[QuizQuestion] = st.session_state.quiz_questions
    idx = st.session_state.current_q_index
    total = len(questions)
    results = st.session_state.session_results

    if not results or idx >= total:
        st.session_state.quiz_state = QUIZ_STATE_SELECT
        st.rerun()
        return

    current_q = questions[idx]
    last_result = results[-1]
    is_correct = last_result["is_correct"]

    # プログレスバー
    progress_val = float(idx + 1) / float(total)
    st.progress(progress_val)
    st.caption(f"第 {idx + 1} / {total} 問（回答済み）")

    # 判定結果バナー
    display_result_banner(
        is_correct=is_correct,
        correct_word=current_q.target_word.word,
        correct_meaning=current_q.target_word.meaning,
    )

    # 選択肢の正誤レビュー
    st.markdown("##### 選択肢の確認")
    for opt in current_q.options:
        if opt == current_q.correct_answer:
            st.success(f"⭕ **【正解】** {opt}")
        elif opt == last_result["selected_option"] and not is_correct:
            st.error(f"❌ **【あなたの回答】** {opt}")
        else:
            st.markdown(f"・ {opt}")

    st.write("")

    # 解説表示（意味は常時表示）
    st.markdown("#### 📖 意味・ニュアンス")
    st.info(
        f"**【{current_q.target_word.word}】**（{current_q.reading}）\n\n"
        f"**意味**: {current_q.target_word.meaning}"
    )

    # 文脈例・つまずきポイント（トグル・expander）
    with st.expander("💡 物語文での場面例 & つまずきポイントを開く", expanded=True):
        st.markdown(
            f"**📖 入試物語文での代表的な場面例:**\n\n"
            f"{current_q.target_word.example}"
        )
        st.markdown(
            f"**💡 小学生がつまずきやすい点・識別ポイント:**\n\n"
            f"{current_q.target_word.tips}"
        )

    st.write("")

    # 次へ進むボタン
    is_last = (idx + 1 >= total)
    next_label = "結果を見る ➔" if is_last else "次の問題へ ➔"

    if st.button(next_label, type="primary", use_container_width=True, key=f"btn_next_q_{idx}"):
        next_question()
        st.rerun()


def _render_result_screen(
    db: DatabaseInterface,
    user_email: str,
    all_words: List[WordItem],
) -> None:
    """4. 10問終了後の結果画面を描画する。"""
    st.title("📊 学習結果サマリー")

    score = st.session_state.score
    total = len(st.session_state.quiz_questions)
    rate = int((score / total) * 100) if total > 0 else 0
    results: List[Dict[str, Any]] = st.session_state.session_results

    # 評価メッセージ & 演出
    if score == total:
        st.balloons()
        st.success(f"🎉 **満点！完璧です！全{total}問正解！💮**")
    elif score >= 8:
        st.balloons()
        st.success(f"👏 **たいへんよくできました！合格点クリアです！（{score}/{total}問正解）**")
    elif score >= 5:
        st.info(f"💪 **あと一歩！間違えた問題を復習して完全定着を目指そう！（{score}/{total}問正解）**")
    else:
        st.warning(f"📚 **おつかれさまでした！「苦手ノート」で間違えた言葉を確認しましょう。（{score}/{total}問正解）**")

    # サマリーカード
    col1, col2 = st.columns(2)
    with col1:
        display_stat_card("正解数", f"{score} / {total} 問")
    with col2:
        display_stat_card("正解率", f"{rate}%")

    st.write("")
    st.subheader("📝 今回解いた問題の一覧")

    # 各問の振り返り
    for r in results:
        icon = "⭕" if r["is_correct"] else "❌"
        cat_badge = render_badge(r["category"], badge_type="category")
        diff_badge = render_badge(f"難易度: {r['difficulty']}", badge_type=f"diff_{r['difficulty']}")

        with st.expander(
            f"{icon} 第 {r['question_no']} 問: 【{r['target_word']}】（{r['reading']}） {cat_badge} {diff_badge}"
        ):
            if not r["is_correct"]:
                st.error(f"❌ あなたの回答: {r['selected_option']}")
                st.success(f"⭕ 正解: {r['correct_answer']}")
            else:
                st.success(f"⭕ あなたの回答（正解）: {r['correct_answer']}")

            st.markdown(f"**意味**: {r['meaning']}")
            st.markdown(f"**場面例**: {r['example']}")
            st.markdown(f"**つまずきポイント**: {r['tips']}")

    st.write("")

    # ナビゲーションボタン
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🔄 同じ条件でもう一度解く", use_container_width=True, key="btn_retry_same"):
            cfg = st.session_state.quiz_config
            failed_stats = db.get_failed_words_stats(user_email)
            failed_words = extract_failed_words(all_words, failed_stats)

            start_quiz_session(
                all_words=all_words,
                mode=cfg["mode"],
                submode=cfg["submode"],
                category_name=cfg["category_name"],
                failed_words=failed_words,
                question_count=total,
            )
            st.rerun()

    with col_btn2:
        if st.button("🏠 モード選択に戻る", type="primary", use_container_width=True, key="btn_return_select"):
            reset_to_select()
            st.rerun()
