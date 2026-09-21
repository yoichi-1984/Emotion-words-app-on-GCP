"""quiz_logic.py

中学受験 国語 心情語対策アプリケーションのクイズ出題・4択動的生成・正誤判定・統計更新ロジックモジュール。
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import random
from typing import Any, Dict, List, Optional, Tuple

from data_loader import WordItem


# 日本標準時 (JST: UTC+9)
JST = timezone(timedelta(hours=9))


@dataclass
class WordStat:
    """ユーザーの単語別学習履歴モデル

    Attributes:
        word_no: 単語No (1 〜 272)
        word: 心情語
        category: カテゴリ名
        total_attempts: 総出題回数
        incorrect_count: 不正解回数
        incorrect_rate: 不正解率 (incorrect_count / total_attempts, 小数点第3位まで四捨五入)
        has_ever_failed: 過去に1度でも間違えたか（一度Trueになると永続化）
        last_attempt_at: 最終回答日時 (JST ISO 8601文字列)
        last_result: 最終回答結果 ("correct" | "incorrect")
    """

    word_no: int
    word: str
    category: str
    total_attempts: int = 0
    incorrect_count: int = 0
    incorrect_rate: float = 0.0
    has_ever_failed: bool = False
    last_attempt_at: Optional[str] = None
    last_result: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換する。"""
        return asdict(self)


@dataclass
class QuizQuestion:
    """1問分のクイズ出題データモデル

    Attributes:
        target_word: 出題対象の単語
        mode: 出題モード (1: 心情語 → 意味, 2: 意味 → 心情語)
        question_text: 画面に提示される問題文（mode 1: 心情語, mode 2: 意味）
        reading: 読み仮名（mode 1 でのルビ確認用）
        options: シャッフルされた4つの選択肢
        correct_answer: 正解の文字列
        correct_index: 正解の選択肢インデックス (0 〜 3)
    """

    target_word: WordItem
    mode: int
    question_text: str
    reading: str
    options: List[str]
    correct_answer: str
    correct_index: int

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換する（Streamlitのセッションステート保存用）。"""
        return {
            "target_word_no": self.target_word.no,
            "target_word": self.target_word.word,
            "category": self.target_word.category,
            "mode": self.mode,
            "question_text": self.question_text,
            "reading": self.reading,
            "options": list(self.options),
            "correct_answer": self.correct_answer,
            "correct_index": self.correct_index,
            "meaning": self.target_word.meaning,
            "example": self.target_word.example,
            "tips": self.target_word.tips,
            "difficulty": self.target_word.difficulty,
        }


def get_current_jst_iso() -> str:
    """現在の日時を JST (UTC+9) の ISO 8601 形式文字列で取得する。

    Returns:
        str: 例 "2026-09-21T12:00:00+09:00"
    """
    return datetime.now(JST).isoformat()


def select_quiz_words(pool: List[WordItem], count: int = 10) -> List[WordItem]:
    """対象の単語プールから重複なく指定件数（デフォルト10問）をランダム抽出する。

    Args:
        pool: 出題候補の単語リスト
        count: 抽出件数 (デフォルト 10)

    Returns:
        List[WordItem]: 抽出された単語リスト

    Raises:
        ValueError: 単語プールの件数が指定件数未満の場合
    """
    if len(pool) < count:
        raise ValueError(
            f"出題可能単語数 ({len(pool)}問) が要求件数 ({count}問) 未満です。"
        )
    return random.sample(pool, count)


def can_start_review_mode(failed_words_count: int, min_required: int = 10) -> bool:
    """苦手復習モードが開始可能かどうかを判定する。

    過去に間違えた問題が min_required 問以上蓄積されている場合に True を返す。

    Args:
        failed_words_count: 間違えた問題の件数
        min_required: 必要な最小問題数 (デフォルト 10)

    Returns:
        bool: 開始可能な場合 True
    """
    return failed_words_count >= min_required


def select_review_words(failed_words: List[WordItem], count: int = 10) -> List[WordItem]:
    """苦手復習モード用に、過去に間違えた問題群から重複なく指定件数を抽出する。

    Args:
        failed_words: 過去に間違えた履歴のある単語リスト
        count: 抽出件数 (デフォルト 10)

    Returns:
        List[WordItem]: 抽出された単語リスト

    Raises:
        ValueError: 間違えた問題が指定件数未満の場合
    """
    if not can_start_review_mode(len(failed_words), min_required=count):
        raise ValueError(
            f"間違えた問題が {count} 問以上必要です（現在: {len(failed_words)} 問）。"
        )
    return random.sample(failed_words, count)


def generate_quiz_options(
    target_word: WordItem,
    all_words: List[WordItem],
    mode: int = 1,
    dummy_count: int = 3,
) -> Tuple[List[str], str, int]:
    """出題単語に対して正解1つとダミー3つの計4つの選択肢を動的生成し、シャッフルして返す。

    Args:
        target_word: 出題対象の単語
        all_words: 全単語リスト（ダミー選択肢の抽出元）
        mode: 出題モード (1: 心情語 → 意味, 2: 意味 → 心情語)
        dummy_count: ダミー選択肢の数 (デフォルト 3)

    Returns:
        Tuple[List[str], str, int]:
            - options: シャッフルされた4つの選択肢リスト
            - correct_answer: 正解のテキスト
            - correct_index: options における正解のインデックス (0 〜 3)

    Raises:
        ValueError: mode が 1 または 2 以外の場合、またはダミー候補が不足している場合
    """
    if mode == 1:
        correct_answer = target_word.meaning
        # 正解と同じ意味および同一単語を除外してダミー候補を作成
        candidate_words = [
            w for w in all_words if w.no != target_word.no and w.meaning != correct_answer
        ]
        # 意味文字列の一意性を確保
        unique_dummy_meanings = list({w.meaning for w in candidate_words})
        if len(unique_dummy_meanings) < dummy_count:
            raise ValueError("ダミー選択肢の候補数が不足しています。")
        dummy_options = random.sample(unique_dummy_meanings, dummy_count)

    elif mode == 2:
        correct_answer = target_word.word
        # 正解と同じ単語を除外してダミー候補を作成
        candidate_words = [
            w for w in all_words if w.no != target_word.no and w.word != correct_answer
        ]
        unique_dummy_words = list({w.word for w in candidate_words})
        if len(unique_dummy_words) < dummy_count:
            raise ValueError("ダミー選択肢の候補数が不足しています。")
        dummy_options = random.sample(unique_dummy_words, dummy_count)

    else:
        raise ValueError(f"無効な出題モードです: {mode} (1 または 2 を指定してください)")

    # 4択を作成してシャッフル
    options = [correct_answer] + dummy_options
    random.shuffle(options)
    correct_index = options.index(correct_answer)

    return options, correct_answer, correct_index


def create_quiz_question(
    target_word: WordItem,
    all_words: List[WordItem],
    mode: int = 1,
) -> QuizQuestion:
    """単一の出題単語から QuizQuestion オブジェクトを構築する。

    Args:
        target_word: 出題対象の単語
        all_words: 全単語リスト
        mode: 出題モード (1: 心情語 → 意味, 2: 意味 → 心情語)

    Returns:
        QuizQuestion: クイズ問題オブジェクト
    """
    options, correct_answer, correct_index = generate_quiz_options(
        target_word=target_word,
        all_words=all_words,
        mode=mode,
    )

    if mode == 1:
        question_text = target_word.word
        reading = target_word.reading
    else:
        question_text = target_word.meaning
        reading = target_word.reading

    return QuizQuestion(
        target_word=target_word,
        mode=mode,
        question_text=question_text,
        reading=reading,
        options=options,
        correct_answer=correct_answer,
        correct_index=correct_index,
    )


def build_quiz_session(
    selected_words: List[WordItem],
    all_words: List[WordItem],
    mode: int = 1,
) -> List[QuizQuestion]:
    """選定された単語群（10問）からクイズセッション用の一連の問題を構築する。

    Args:
        selected_words: 出題する10問の単語リスト
        all_words: 全単語リスト
        mode: 出題モード (1: 心情語 → 意味, 2: 意味 → 心情語)

    Returns:
        List[QuizQuestion]: 10問のクイズ問題リスト
    """
    return [
        create_quiz_question(target_word=w, all_words=all_words, mode=mode)
        for w in selected_words
    ]


def evaluate_answer(selected_option: str, correct_answer: str) -> bool:
    """ユーザーが選択した選択肢が正解と一致するかを判定する。

    Args:
        selected_option: ユーザーの選択したテキスト
        correct_answer: 正解テキスト

    Returns:
        bool: 一致していれば True, 不一致なら False
    """
    return selected_option.strip() == correct_answer.strip()


def update_word_stat(
    current_stat: Optional[WordStat],
    word: WordItem,
    is_correct: bool,
    timestamp: Optional[str] = None,
) -> WordStat:
    """回答結果に基づいて WordStat（単語別学習統計）を更新する。

    - total_attempts を +1
    - 不正解の場合は incorrect_count を +1、has_ever_failed を True に更新
    - incorrect_rate を計算 (小数点第3位まで四捨五入)
    - last_result を "correct" または "incorrect" に更新
    - last_attempt_at を JST ISO 8601 文字列で記録

    Args:
        current_stat: 現在の単語統計（未回答の場合は None）
        word: 回答対象の単語
        is_correct: 正解したか否か
        timestamp: 明示的な記録日時（None の場合は現在時刻 JST）

    Returns:
        WordStat: 更新後の統計データ
    """
    if current_stat is None:
        stat = WordStat(
            word_no=word.no,
            word=word.word,
            category=word.category,
            total_attempts=0,
            incorrect_count=0,
            incorrect_rate=0.0,
            has_ever_failed=False,
        )
    else:
        # 既存インスタンスのコピーまたは更新
        stat = WordStat(
            word_no=current_stat.word_no,
            word=current_stat.word,
            category=current_stat.category,
            total_attempts=current_stat.total_attempts,
            incorrect_count=current_stat.incorrect_count,
            incorrect_rate=current_stat.incorrect_rate,
            has_ever_failed=current_stat.has_ever_failed,
            last_attempt_at=current_stat.last_attempt_at,
            last_result=current_stat.last_result,
        )

    stat.total_attempts += 1
    if not is_correct:
        stat.incorrect_count += 1
        stat.has_ever_failed = True

    stat.incorrect_rate = round(stat.incorrect_count / stat.total_attempts, 3)
    stat.last_result = "correct" if is_correct else "incorrect"
    stat.last_attempt_at = timestamp if timestamp is not None else get_current_jst_iso()

    return stat


def extract_failed_words(
    all_words: List[WordItem],
    stats: List[WordStat],
) -> List[WordItem]:
    """ユーザーの学習統計から過去に間違えた問題（has_ever_failed == True）の単語リストを抽出する。

    Args:
        all_words: 全単語リスト
        stats: ユーザーの学習統計リスト

    Returns:
        List[WordItem]: 間違えたことのある単語リスト（マスター順）
    """
    failed_word_nos = {s.word_no for s in stats if s.has_ever_failed}
    return [w for w in all_words if w.no in failed_word_nos]
