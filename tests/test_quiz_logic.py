"""tests/test_quiz_logic.py

quiz_logic.py の出題サンプリング・4択動的生成・正誤判定・統計更新ロジック検証テスト。
"""

from datetime import datetime, timezone
import pytest

from data_loader import WordItem, load_words
from quiz_logic import (
    WordStat,
    QuizQuestion,
    get_current_jst_iso,
    select_quiz_words,
    can_start_review_mode,
    select_review_words,
    generate_quiz_options,
    create_quiz_question,
    build_quiz_session,
    evaluate_answer,
    update_word_stat,
    extract_failed_words,
)


@pytest.fixture(scope="module")
def all_words():
    """全272語の単語マスターデータをロードするフィクスチャ"""
    return load_words()


@pytest.fixture
def sample_word(all_words):
    """テスト用サンプル単語（第1問）"""
    return all_words[0]


class TestWordStatAndQuestionModels:
    """データ構造およびシリアライズのテスト"""

    def test_word_stat_to_dict(self):
        """WordStat の to_dict が仕様通りの辞書を生成すること"""
        stat = WordStat(
            word_no=1,
            word="気後れ",
            category="不安・恐れ",
            total_attempts=5,
            incorrect_count=2,
            incorrect_rate=0.4,
            has_ever_failed=True,
            last_attempt_at="2026-09-21T12:00:00+09:00",
            last_result="incorrect",
        )
        data = stat.to_dict()
        assert isinstance(data, dict)
        assert data["word_no"] == 1
        assert data["word"] == "気後れ"
        assert data["category"] == "不安・恐れ"
        assert data["total_attempts"] == 5
        assert data["incorrect_count"] == 2
        assert data["incorrect_rate"] == 0.4
        assert data["has_ever_failed"] is True
        assert data["last_attempt_at"] == "2026-09-21T12:00:00+09:00"
        assert data["last_result"] == "incorrect"

    def test_quiz_question_to_dict(self, sample_word):
        """QuizQuestion の to_dict がセッション管理に必要な全項目を保持すること"""
        question = QuizQuestion(
            target_word=sample_word,
            mode=1,
            question_text=sample_word.word,
            reading=sample_word.reading,
            options=["選択肢A", "選択肢B", "選択肢C", "選択肢D"],
            correct_answer="選択肢A",
            correct_index=0,
        )
        data = question.to_dict()
        assert isinstance(data, dict)
        assert data["target_word_no"] == sample_word.no
        assert data["target_word"] == sample_word.word
        assert data["category"] == sample_word.category
        assert data["mode"] == 1
        assert data["question_text"] == sample_word.word
        assert data["reading"] == sample_word.reading
        assert len(data["options"]) == 4
        assert data["correct_answer"] == "選択肢A"
        assert data["correct_index"] == 0
        assert data["meaning"] == sample_word.meaning
        assert data["example"] == sample_word.example
        assert data["tips"] == sample_word.tips
        assert data["difficulty"] == sample_word.difficulty

    def test_get_current_jst_iso(self):
        """現在日時の取得が JST (+09:00) の有効な ISO 8601 文字列であること"""
        iso_str = get_current_jst_iso()
        assert isinstance(iso_str, str)
        assert "+09:00" in iso_str
        parsed = datetime.fromisoformat(iso_str)
        assert parsed.tzinfo is not None
        # UTC+9 のオフセット確認
        assert parsed.utcoffset().total_seconds() == 9 * 3600


class TestQuizSelection:
    """問題選定および苦手復習モード抽出のテスト"""

    def test_select_quiz_words_default_count(self, all_words):
        """全単語プールからデフォルト10問が重複なく抽出されること"""
        selected = select_quiz_words(all_words)
        assert len(selected) == 10
        assert len({w.no for w in selected}) == 10
        for w in selected:
            assert isinstance(w, WordItem)

    def test_select_quiz_words_custom_count(self, all_words):
        """指定件数（例: 5問）が重複なく抽出されること"""
        selected = select_quiz_words(all_words, count=5)
        assert len(selected) == 5
        assert len({w.no for w in selected}) == 5

    def test_select_quiz_words_insufficient_pool(self, all_words):
        """要求件数がプール件数を超過した場合に ValueError が送出されること"""
        small_pool = all_words[:3]
        with pytest.raises(ValueError) as exc_info:
            select_quiz_words(small_pool, count=5)
        assert "要求件数 (5問) 未満です" in str(exc_info.value)

    def test_can_start_review_mode(self):
        """苦手復習モードの開始条件（10問以上）の判定テスト"""
        assert can_start_review_mode(0) is False
        assert can_start_review_mode(9) is False
        assert can_start_review_mode(10) is True
        assert can_start_review_mode(15) is True

    def test_select_review_words_success(self, all_words):
        """間違えた問題が10問以上ある場合に正常に10問抽出されること"""
        failed_words = all_words[:12]
        selected = select_review_words(failed_words, count=10)
        assert len(selected) == 10
        assert len({w.no for w in selected}) == 10
        for w in selected:
            assert w in failed_words

    def test_select_review_words_insufficient(self, all_words):
        """間違えた問題が10問未満の場合に ValueError が送出されること"""
        failed_words = all_words[:9]
        with pytest.raises(ValueError) as exc_info:
            select_review_words(failed_words, count=10)
        assert "間違えた問題が 10 問以上必要です" in str(exc_info.value)


class TestQuizOptionsGeneration:
    """4択動的生成アルゴリズムのテスト"""

    def test_generate_options_mode1_meaning(self, sample_word, all_words):
        """モード1（心情語 → 意味）の4択生成テスト"""
        options, correct_answer, correct_index = generate_quiz_options(
            target_word=sample_word,
            all_words=all_words,
            mode=1,
            dummy_count=3,
        )
        # 4つの選択肢が存在すること
        assert len(options) == 4
        # 4つの選択肢に重複がないこと
        assert len(set(options)) == 4
        # 正解は対象単語の意味であること
        assert correct_answer == sample_word.meaning
        # correct_index が options の中での正解インデックスと一致すること
        assert options[correct_index] == correct_answer

        # ダミー3つは正解と一致せず、他の単語の意味であること
        dummies = [opt for i, opt in enumerate(options) if i != correct_index]
        assert len(dummies) == 3
        for d in dummies:
            assert d != correct_answer

    def test_generate_options_mode2_word(self, sample_word, all_words):
        """モード2（意味 → 心情語）の4択生成テスト"""
        options, correct_answer, correct_index = generate_quiz_options(
            target_word=sample_word,
            all_words=all_words,
            mode=2,
            dummy_count=3,
        )
        # 4つの選択肢が存在すること
        assert len(options) == 4
        # 4つの選択肢に重複がないこと
        assert len(set(options)) == 4
        # 正解は対象単語の心情語名であること
        assert correct_answer == sample_word.word
        # correct_index が options の中での正解インデックスと一致すること
        assert options[correct_index] == correct_answer

        # ダミー3つは正解と一致せず、他の単語の心情語名であること
        dummies = [opt for i, opt in enumerate(options) if i != correct_index]
        assert len(dummies) == 3
        for d in dummies:
            assert d != correct_answer

    def test_generate_options_shuffle_distribution(self, sample_word, all_words):
        """4択生成時に正解の位置（correct_index: 0〜3）がランダムに分散すること"""
        indices = set()
        # 50回実行して全インデックス (0, 1, 2, 3) が網羅されることを確認
        for _ in range(50):
            _, _, idx = generate_quiz_options(sample_word, all_words, mode=1)
            indices.add(idx)
        assert indices == {0, 1, 2, 3}

    def test_generate_options_invalid_mode(self, sample_word, all_words):
        """不正なモード番号を指定した場合に ValueError が送出されること"""
        with pytest.raises(ValueError) as exc_info:
            generate_quiz_options(sample_word, all_words, mode=99)
        assert "無効な出題モードです" in str(exc_info.value)

    def test_generate_options_insufficient_candidates(self, sample_word):
        """単語数が不足してダミーが3つ生成できない場合に ValueError が送出されること"""
        tiny_pool = [sample_word]
        with pytest.raises(ValueError) as exc_info:
            generate_quiz_options(sample_word, tiny_pool, mode=1, dummy_count=3)
        assert "ダミー選択肢の候補数が不足しています" in str(exc_info.value)


class TestQuizQuestionAndSession:
    """QuizQuestion 構築およびセッション構築のテスト"""

    def test_create_quiz_question_mode1(self, sample_word, all_words):
        """モード1の問題オブジェクト生成テスト"""
        q = create_quiz_question(sample_word, all_words, mode=1)
        assert q.target_word == sample_word
        assert q.mode == 1
        assert q.question_text == sample_word.word
        assert q.reading == sample_word.reading
        assert q.correct_answer == sample_word.meaning
        assert len(q.options) == 4
        assert q.options[q.correct_index] == q.correct_answer

    def test_create_quiz_question_mode2(self, sample_word, all_words):
        """モード2の問題オブジェクト生成テスト"""
        q = create_quiz_question(sample_word, all_words, mode=2)
        assert q.target_word == sample_word
        assert q.mode == 2
        assert q.question_text == sample_word.meaning
        assert q.reading == sample_word.reading
        assert q.correct_answer == sample_word.word
        assert len(q.options) == 4
        assert q.options[q.correct_index] == q.correct_answer

    def test_build_quiz_session(self, all_words):
        """10問の選定リストから10問の QuizQuestion が正しく構築されること"""
        selected = select_quiz_words(all_words, count=10)
        session_questions = build_quiz_session(selected, all_words, mode=1)
        assert len(session_questions) == 10
        for i, q in enumerate(session_questions):
            assert isinstance(q, QuizQuestion)
            assert q.target_word == selected[i]
            assert len(q.options) == 4
            assert q.correct_answer in q.options


class TestAnswerEvaluation:
    """正誤判定関数のテスト"""

    def test_evaluate_answer_correct(self):
        """完全一致および前後の空白を含む場合の一致判定"""
        assert evaluate_answer("気後れ", "気後れ") is True
        assert evaluate_answer(" 気後れ ", "気後れ") is True
        assert evaluate_answer("気後れ", " 気後れ\n") is True

    def test_evaluate_answer_incorrect(self):
        """不一致判定"""
        assert evaluate_answer("気後れ", "いたたまれない") is False
        assert evaluate_answer("", "気後れ") is False


class TestStatUpdates:
    """学習統計（WordStat）更新および苦手単語抽出のテスト"""

    def test_update_word_stat_initial_correct(self, sample_word):
        """初回回答で正解した場合の統計更新"""
        stat = update_word_stat(
            current_stat=None,
            word=sample_word,
            is_correct=True,
            timestamp="2026-09-21T12:00:00+09:00",
        )
        assert stat.word_no == sample_word.no
        assert stat.word == sample_word.word
        assert stat.category == sample_word.category
        assert stat.total_attempts == 1
        assert stat.incorrect_count == 0
        assert stat.incorrect_rate == 0.0
        assert stat.has_ever_failed is False
        assert stat.last_result == "correct"
        assert stat.last_attempt_at == "2026-09-21T12:00:00+09:00"

    def test_update_word_stat_initial_incorrect(self, sample_word):
        """初回回答で不正解だった場合の統計更新"""
        stat = update_word_stat(
            current_stat=None,
            word=sample_word,
            is_correct=False,
            timestamp="2026-09-21T12:00:00+09:00",
        )
        assert stat.total_attempts == 1
        assert stat.incorrect_count == 1
        assert stat.incorrect_rate == 1.0
        assert stat.has_ever_failed is True
        assert stat.last_result == "incorrect"
        assert stat.last_attempt_at == "2026-09-21T12:00:00+09:00"

    def test_update_word_stat_failed_persistence(self, sample_word):
        """過去に不正解（has_ever_failed=True）の場合、次回以降正解してもフラグが保持されること"""
        # 初回: 不正解
        stat = update_word_stat(None, sample_word, is_correct=False)
        assert stat.has_ever_failed is True
        assert stat.total_attempts == 1
        assert stat.incorrect_count == 1

        # 2回目: 正解
        stat = update_word_stat(stat, sample_word, is_correct=True)
        assert stat.has_ever_failed is True
        assert stat.total_attempts == 2
        assert stat.incorrect_count == 1
        assert stat.incorrect_rate == 0.5
        assert stat.last_result == "correct"

    def test_update_word_stat_rate_rounding(self, sample_word):
        """不正解率の四捨五入（小数点第3位まで）計算テスト"""
        # 3回中1回不正解 -> 1/3 = 0.3333... -> 0.333
        stat = None
        for is_correct in [False, True, True]:
            stat = update_word_stat(stat, sample_word, is_correct=is_correct)
        assert stat.total_attempts == 3
        assert stat.incorrect_count == 1
        assert stat.incorrect_rate == 0.333

    def test_update_word_stat_default_timestamp(self, sample_word):
        """timestamp を省略した場合に現在時刻 (JST) が自動設定されること"""
        stat = update_word_stat(None, sample_word, is_correct=True)
        assert stat.last_attempt_at is not None
        assert "+09:00" in stat.last_attempt_at

    def test_extract_failed_words(self, all_words):
        """has_ever_failed == True の単語のみがマスター順で抽出されること"""
        w1, w2, w3, w4 = all_words[0], all_words[1], all_words[2], all_words[3]
        stats = [
            WordStat(word_no=w2.no, word=w2.word, category=w2.category, has_ever_failed=True),
            WordStat(word_no=w4.no, word=w4.word, category=w4.category, has_ever_failed=True),
            WordStat(word_no=w1.no, word=w1.word, category=w1.category, has_ever_failed=False),
            WordStat(word_no=w3.no, word=w3.word, category=w3.category, has_ever_failed=False),
        ]
        failed_list = extract_failed_words(all_words, stats)
        assert len(failed_list) == 2
        # マスター順（w2, w4 の順）
        assert failed_list[0].no == w2.no
        assert failed_list[1].no == w4.no
