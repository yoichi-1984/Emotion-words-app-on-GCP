"""tests/test_integration.py

アプリケーション全体の結合テスト（Integration Tests）
- py_compile による全モジュールの構文・インポート検証
- AppTest による Streamlit アプリケーションの E2E 起動・画面遷移・状態遷移検証
- クイズ出題 → 回答 → DB記録 → 苦手ノート反映 → 辞典連動の一連の学習サイクル結合検証
"""

import os
import py_compile
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest

from data_loader import load_words, WordItem
from db import LocalJsonDB, WordStat
from quiz_logic import (
    QuizQuestion,
    select_quiz_words,
    select_review_words,
    can_start_review_mode,
    create_quiz_question,
    build_quiz_session,
    evaluate_answer,
    update_word_stat,
    extract_failed_words,
)
from views.quiz_view import (
    QUIZ_STATE_SELECT,
    QUIZ_STATE_ANSWERING,
    QUIZ_STATE_ANSWERED,
    QUIZ_STATE_RESULT,
    SUBMODE_RANDOM,
    SUBMODE_CATEGORY,
    SUBMODE_REVIEW,
    start_quiz_session,
    submit_answer,
    next_question,
    reset_to_select,
)
from views.review_view import (
    build_review_items,
    filter_and_sort_review_items,
    SORT_INCORRECT_COUNT,
)
from views.dictionary_view import (
    filter_and_sort_dictionary_items,
    calculate_dictionary_summary,
    SORT_READING,
)

APP_PATH = str((Path(__file__).parent.parent / "app.py").resolve())


# ==============================================================================
# 1. 全Pythonファイルの構文・コンパイル検証
# ==============================================================================
class TestAllModulesCompilation:
    """全Pythonソースコードの構文・インポート結合チェック。"""

    def test_py_compile_all_source_files(self):
        """プロジェクト内のすべての主要 Python ファイルが構文エラーなくコンパイルできること。"""
        root_dir = Path(__file__).parent.parent
        target_files = [
            root_dir / "app.py",
            root_dir / "data_loader.py",
            root_dir / "db.py",
            root_dir / "quiz_logic.py",
            root_dir / "styles.py",
            root_dir / "views" / "__init__.py",
            root_dir / "views" / "quiz_view.py",
            root_dir / "views" / "review_view.py",
            root_dir / "views" / "dictionary_view.py",
        ]

        for file_path in target_files:
            assert file_path.exists(), f"対象ファイルが存在しません: {file_path}"
            compiled_path = py_compile.compile(str(file_path), doraise=True)
            assert compiled_path is not None, f"コンパイルに失敗しました: {file_path}"


# ==============================================================================
# 2. AppTest による Streamlit アプリケーション E2E 結合検証
# ==============================================================================
class TestAppTestE2E:
    """Streamlit AppTest を用いた画面遷移・認証・レンダリング結合テスト。"""

    def test_app_initial_load_in_dev_mode(self, monkeypatch):
        """DEV_MODE=True の場合、初期起動時に自動ログインされクイズ画面が表示されること。"""
        monkeypatch.setenv("DEV_MODE", "True")
        at = AppTest.from_file(APP_PATH)
        at.run()

        assert not at.exception, f"アプリ起動時に例外が発生しました: {at.exception}"
        assert at.session_state["is_authenticated"] is True
        assert at.session_state["current_view"] == "quiz"
        assert at.session_state["user_email"] == "local_dev@example.com"

        # クイズ画面のタイトルまたは見出しが存在すること
        title_texts = [t.value for t in at.title]
        assert any("心情語クイズ" in t for t in title_texts)

    def test_app_navigation_between_views(self, monkeypatch):
        """サイドバー操作により、クイズ → 苦手ノート → 心情語辞典への画面切り替えが正常に行われること。"""
        monkeypatch.setenv("DEV_MODE", "True")
        at = AppTest.from_file(APP_PATH)
        at.run()
        assert not at.exception

        # 1. 苦手ノート画面へ切り替え
        at.session_state["nav_radio"] = "📓 苦手ノート"
        at.session_state["current_view"] = "review"
        at.run()
        assert not at.exception
        assert at.session_state["current_view"] == "review"

        # 2. 心情語辞典画面へ切り替え
        at.session_state["nav_radio"] = "📚 心情語辞典"
        at.session_state["current_view"] = "dictionary"
        at.run()
        assert not at.exception
        assert at.session_state["current_view"] == "dictionary"

        # 3. 再びクイズ画面へ戻る
        at.session_state["nav_radio"] = "🎯 クイズ（学習モード）"
        at.session_state["current_view"] = "quiz"
        at.run()
        assert not at.exception
        assert at.session_state["current_view"] == "quiz"

    def test_app_logout_and_login_screen_rendering(self, monkeypatch):
        """ログアウト操作により未認証状態になり、ログイン画面がレンダリングされること。"""
        monkeypatch.setenv("DEV_MODE", "True")
        at = AppTest.from_file(APP_PATH)
        at.run()
        assert not at.exception
        assert at.session_state["is_authenticated"] is True

        # ログアウト状態を設定して再実行
        at.session_state["is_authenticated"] = False
        at.run()
        assert not at.exception
        assert at.session_state["is_authenticated"] is False

        # 開発ログイン用の要素が表示されていること
        info_texts = [info.value for info in at.info]
        assert any("ローカル開発モード" in text for text in info_texts)

    def test_app_production_mode_unauthenticated(self, monkeypatch):
        """DEV_MODE=False（本番認証モード）の場合、未認証ログイン画面が表示されること。"""
        monkeypatch.setenv("DEV_MODE", "False")
        at = AppTest.from_file(APP_PATH)
        at.run()
        assert not at.exception
        assert at.session_state["is_authenticated"] is False

        warning_texts = [w.value for w in at.warning]
        assert any("ログインが必要です" in text for text in warning_texts)


# ==============================================================================
# 3. 学習サイクル結合シナリオテスト（データ・ロジック・DB・ビュー連動）
# ==============================================================================
class TestLearningFlowIntegration:
    """実マスターデータとDBを用いた出題・採点・苦手記録・辞典連動の結合シナリオ。"""

    @pytest.fixture
    def real_words(self):
        """実CSVデータ（全272語）をロード。"""
        words = load_words()
        assert len(words) == 272
        return words

    @pytest.fixture
    def temp_db(self, tmp_path):
        """一時ファイルを用いた LocalJsonDB インスタンス。"""
        db_file = tmp_path / "test_user_stats.json"
        return LocalJsonDB(filepath=db_file)

    def test_full_quiz_to_review_flow(self, real_words, temp_db):
        """クイズ出題から回答、DB記録、苦手ノートへの反映シナリオ。

        1. 実データから10問抽出してセッション用の問題を構築
        2. 1〜4問目は正解、5〜10問目は不正解として回答をDBに記録
        3. 苦手ノート（review_view ロジック）に6件が反映されることを検証
        """
        user_email = "student_test@example.com"

        # 1. 10問ランダム抽出および問題生成
        selected_words = select_quiz_words(real_words, count=10)
        assert len(selected_words) == 10
        questions = build_quiz_session(selected_words, real_words, mode=1)
        assert len(questions) == 10

        # 2. 回答をシミュレート（1〜4問目正解、5〜10問目不正解）
        for idx, q in enumerate(questions):
            if idx < 4:
                # 正解を選択
                selected_option = q.correct_answer
                is_correct = evaluate_answer(selected_option, q.correct_answer)
                assert is_correct is True
            else:
                # 不正解を選択（正解以外の選択肢）
                wrong_options = [opt for opt in q.options if opt != q.correct_answer]
                selected_option = wrong_options[0]
                is_correct = evaluate_answer(selected_option, q.correct_answer)
                assert is_correct is False

            # 3. DBへ記録
            stat = temp_db.record_attempt(
                email=user_email,
                word_no=q.target_word.no,
                word=q.target_word.word,
                category=q.target_word.category,
                is_correct=is_correct,
            )
            assert stat.total_attempts == 1
            if is_correct:
                assert stat.incorrect_count == 0
                assert stat.has_ever_failed is False
            else:
                assert stat.incorrect_count == 1
                assert stat.has_ever_failed is True

        # 4. DB内のステータス検証
        user_stats = temp_db.get_user_stats(user_email)
        attempted_stats = [s for s in user_stats.values() if s.total_attempts > 0]
        assert len(attempted_stats) == 10

        failed_stats = temp_db.get_failed_words_stats(user_email)
        assert len(failed_stats) == 6
        for stat in failed_stats:
            assert stat.has_ever_failed is True
            assert stat.incorrect_count >= 1

        # 5. 苦手ノート（review_view）フィルタ・ソートロジックとの結合検証
        review_items = build_review_items(stats=failed_stats, all_words=real_words)
        assert len(review_items) == 6

        filtered_items = filter_and_sort_review_items(
            items=review_items,
            sort_by=SORT_INCORRECT_COUNT,
            category_filter="すべて",
            search_query="",
        )
        assert len(filtered_items) == 6
        # 不正解回数の多い順にソートされていること
        assert all(item.incorrect_count >= 1 for item in filtered_items)

    def test_failed_review_mode_unlock_flow(self, real_words, temp_db):
        """苦手復習モードの開放（10問以上）と出題結合シナリオ。

        1. 不正解が9問の段階では苦手復習モードは開放されない
        2. 10問目の不正解を記録するとモードが開放される
        3. 苦手復習モードで10問出題を生成し、すべて過去の苦手語であることを確認
        """
        user_email = "student_review_test@example.com"

        # 最初の9単語に不正解を記録
        first_9_words = real_words[:9]
        for w in first_9_words:
            temp_db.record_attempt(
                email=user_email,
                word_no=w.no,
                word=w.word,
                category=w.category,
                is_correct=False,
            )

        failed_stats_9 = temp_db.get_failed_words_stats(user_email)
        assert len(failed_stats_9) == 9
        assert can_start_review_mode(len(failed_stats_9), min_required=10) is False

        # 9問の状態で苦手復習モードの単語抽出を呼び出すと ValueError が送出されること
        failed_word_items_9 = extract_failed_words(real_words, failed_stats_9)
        assert len(failed_word_items_9) == 9
        with pytest.raises(ValueError, match="10 問以上必要"):
            select_review_words(failed_word_items_9, count=10)

        # 10問目の不正解を記録
        word_10 = real_words[9]
        temp_db.record_attempt(
            email=user_email,
            word_no=word_10.no,
            word=word_10.word,
            category=word_10.category,
            is_correct=False,
        )

        failed_stats_10 = temp_db.get_failed_words_stats(user_email)
        assert len(failed_stats_10) == 10
        assert can_start_review_mode(len(failed_stats_10), min_required=10) is True

        # 苦手復習モードで単語抽出 & 出題生成
        failed_word_items_10 = extract_failed_words(real_words, failed_stats_10)
        review_words = select_review_words(failed_word_items_10, count=10)
        assert len(review_words) == 10

        review_session = build_quiz_session(review_words, real_words, mode=1)
        assert len(review_session) == 10

        # 出題された問題の単語番号がすべて過去の苦手語10件に含まれていること
        failed_nos = {stat.word_no for stat in failed_stats_10}
        session_nos = {q.target_word.no for q in review_session}
        assert session_nos == failed_nos

    def test_quiz_results_reflected_in_dictionary(self, real_words, temp_db):
        """クイズ結果が心情語辞典（dictionary_view）の検索・表示ロジックと正常に連動することの検証。"""
        user_email = "dict_user@example.com"

        # 特定の単語（No.1）に対して学習履歴を記録（1回目不正解、2回目不正解、3回目正解）
        w1 = real_words[0]
        temp_db.record_attempt(user_email, w1.no, w1.word, w1.category, is_correct=False)
        temp_db.record_attempt(user_email, w1.no, w1.word, w1.category, is_correct=False)
        temp_db.record_attempt(user_email, w1.no, w1.word, w1.category, is_correct=True)

        # 辞典サマリーの計算
        summary = calculate_dictionary_summary(real_words)
        assert summary["total_words"] == 272
        assert summary["diff_low"] == 69
        assert summary["diff_mid"] == 116
        assert summary["diff_high"] == 87

        # 辞典検索（単語名検索で対象単語が含まれること）
        filtered = filter_and_sort_dictionary_items(
            words=real_words,
            category="すべて",
            difficulty="すべて",
            search_query=w1.word,
            sort_by=SORT_READING,
        )
        assert len(filtered) >= 1
        assert any(w.no == w1.no for w in filtered)

        # DBから統計を取得して辞典での表示ステータスを確認
        user_stats = temp_db.get_user_stats(user_email)
        w1_stat = user_stats.get(w1.no)
        assert w1_stat is not None
        assert w1_stat.total_attempts == 3
        assert w1_stat.incorrect_count == 2
        assert w1_stat.last_result == "correct"
        assert w1_stat.has_ever_failed is True

    def test_user_stats_reset_flow(self, real_words, temp_db):
        """学習履歴リセット機能により、蓄積された履歴がすべて正常にクリアされることの検証。"""
        user_email = "reset_test@example.com"

        # 5問の履歴を記録
        for w in real_words[:5]:
            temp_db.record_attempt(user_email, w.no, w.word, w.category, is_correct=False)

        stats_before = temp_db.get_user_stats(user_email)
        attempted_before = [s for s in stats_before.values() if s.total_attempts > 0]
        assert len(attempted_before) == 5
        assert len(temp_db.get_failed_words_stats(user_email)) == 5

        # 履歴をリセット
        temp_db.reset_user_stats(user_email)

        # リセット後の確認
        stats_after = temp_db.get_user_stats(user_email)
        attempted_after = [s for s in stats_after.values() if s.total_attempts > 0]
        assert len(attempted_after) == 0
        assert len(temp_db.get_failed_words_stats(user_email)) == 0
