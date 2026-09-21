"""tests/test_db.py

db.py の学習履歴モデル (WordStat)、データベースインターフェース (DatabaseInterface)、
およびローカルモックDB (LocalJsonDB, get_db) の読み書き・整合性検証テスト。
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import json
import os
from pathlib import Path
import pytest

from data_loader import WordItem, load_words
from db import (
    DatabaseInterface,
    LocalJsonDB,
    WordStat,
    get_current_jst_iso,
    get_db,
)


@pytest.fixture(scope="module")
def all_words():
    """全272語の単語マスターデータをロードするフィクスチャ"""
    return load_words()


@pytest.fixture
def temp_db_path(tmp_path):
    """テスト専用の一時JSONファイルパスを提供するフィクスチャ"""
    return tmp_path / "test_user_stats.json"


@pytest.fixture
def sample_word(all_words):
    """テスト用サンプル単語（第1問）"""
    return all_words[0]


class TestWordStatModel:
    """WordStat データモデルおよびシリアライズのテスト"""

    def test_word_stat_defaults(self):
        """WordStat の初期値が仕様通りであること"""
        stat = WordStat(word_no=10, word="あきらめる", category="悲しみ・諦め")
        assert stat.word_no == 10
        assert stat.word == "あきらめる"
        assert stat.category == "悲しみ・諦め"
        assert stat.total_attempts == 0
        assert stat.incorrect_count == 0
        assert stat.incorrect_rate == 0.0
        assert stat.has_ever_failed is False
        assert stat.last_attempt_at is None
        assert stat.last_result is None

    def test_word_stat_to_dict(self):
        """WordStat の to_dict が仕様通りの辞書を生成すること"""
        stat = WordStat(
            word_no=1,
            word="気後れ",
            category="不安・恐れ",
            total_attempts=4,
            incorrect_count=1,
            incorrect_rate=0.25,
            has_ever_failed=True,
            last_attempt_at="2026-09-21T12:00:00+09:00",
            last_result="correct",
        )
        data = stat.to_dict()
        assert isinstance(data, dict)
        assert data["word_no"] == 1
        assert data["word"] == "気後れ"
        assert data["category"] == "不安・恐れ"
        assert data["total_attempts"] == 4
        assert data["incorrect_count"] == 1
        assert data["incorrect_rate"] == 0.25
        assert data["has_ever_failed"] is True
        assert data["last_attempt_at"] == "2026-09-21T12:00:00+09:00"
        assert data["last_result"] == "correct"

    def test_word_stat_from_dict_complete(self):
        """完全な辞書データから WordStat インスタンスが正しく復元されること"""
        data = {
            "word_no": 5,
            "word": "いたたまれない",
            "category": "不安・恐れ",
            "total_attempts": 3,
            "incorrect_count": 2,
            "incorrect_rate": 0.667,
            "has_ever_failed": True,
            "last_attempt_at": "2026-09-21T12:30:00+09:00",
            "last_result": "incorrect",
        }
        stat = WordStat.from_dict(data)
        assert stat.word_no == 5
        assert stat.word == "いたたまれない"
        assert stat.category == "不安・恐れ"
        assert stat.total_attempts == 3
        assert stat.incorrect_count == 2
        assert stat.incorrect_rate == 0.667
        assert stat.has_ever_failed is True
        assert stat.last_attempt_at == "2026-09-21T12:30:00+09:00"
        assert stat.last_result == "incorrect"

    def test_word_stat_from_dict_with_defaults(self):
        """オプショナルなキーが欠けている場合でもデフォルト値で復元されること"""
        data = {
            "word_no": "8",
            "word": "途方に暮れる",
            "category": "悲しみ・諦め",
        }
        stat = WordStat.from_dict(data)
        assert stat.word_no == 8
        assert stat.word == "途方に暮れる"
        assert stat.category == "悲しみ・諦め"
        assert stat.total_attempts == 0
        assert stat.incorrect_count == 0
        assert stat.incorrect_rate == 0.0
        assert stat.has_ever_failed is False
        assert stat.last_attempt_at is None
        assert stat.last_result is None

    def test_get_current_jst_iso(self):
        """現在時刻が JST (+09:00) の有効な ISO 8601 文字列であること"""
        iso_str = get_current_jst_iso()
        assert "+09:00" in iso_str
        parsed = datetime.fromisoformat(iso_str)
        assert parsed.utcoffset().total_seconds() == 9 * 3600


class TestLocalJsonDBInitialization:
    """LocalJsonDB のファイル生成・初期化・エラーハンドリングのテスト"""

    def test_ensure_file_and_directory_creation(self, tmp_path):
        """未作成のディレクトリ・ファイルパスを指定した場合、自動生成されること"""
        nested_dir = tmp_path / "sub" / "data"
        db_file = nested_dir / "stats.json"
        assert not nested_dir.exists()
        assert not db_file.exists()

        db = LocalJsonDB(filepath=db_file)
        assert nested_dir.exists()
        assert db_file.exists()

        # ファイル内容が初期状態 {"users": {}} であること
        with open(db_file, "r", encoding="utf-8") as f:
            content = json.load(f)
        assert content == {"users": {}}

    def test_preserve_existing_file(self, temp_db_path):
        """既に存在する有効なJSONファイルの内容が上書きされず保持されること"""
        initial_data = {
            "users": {
                "test@example.com": {
                    "email": "test@example.com",
                    "last_login_at": "2026-09-21T09:00:00+09:00",
                    "stats": {},
                }
            }
        }
        with open(temp_db_path, "w", encoding="utf-8") as f:
            json.dump(initial_data, f, ensure_ascii=False)

        db = LocalJsonDB(filepath=temp_db_path)
        stats = db.get_user_stats("test@example.com")
        assert len(stats) == 272  # マスター全件ロード可能

        with open(temp_db_path, "r", encoding="utf-8") as f:
            saved = json.load(f)
        assert "test@example.com" in saved["users"]

    def test_read_corrupt_json_fallback(self, temp_db_path):
        """ファイルが不正なJSON（破損ファイル）の場合でもクラッシュせず空辞書として扱われること"""
        with open(temp_db_path, "w", encoding="utf-8") as f:
            f.write("INVALID JSON CONTENT {{{")

        db = LocalJsonDB(filepath=temp_db_path)
        stats = db.get_user_stats("test@example.com")
        # 例外を起こさずデフォルト統計（全272件）を返すこと
        assert len(stats) == 272


class TestLocalJsonDBGetStats:
    """LocalJsonDB.get_user_stats の動作テスト"""

    def test_get_user_stats_new_user(self, temp_db_path, all_words):
        """未学習ユーザーの場合、全272語のデフォルト WordStat が辞書で返されること"""
        db = LocalJsonDB(filepath=temp_db_path)
        stats = db.get_user_stats("new_user@example.com")

        assert len(stats) == len(all_words)
        assert len(stats) == 272

        for w in all_words:
            assert w.no in stats
            stat = stats[w.no]
            assert isinstance(stat, WordStat)
            assert stat.word_no == w.no
            assert stat.word == w.word
            assert stat.category == w.category
            assert stat.total_attempts == 0
            assert stat.incorrect_count == 0
            assert stat.incorrect_rate == 0.0
            assert stat.has_ever_failed is False
            assert stat.last_attempt_at is None
            assert stat.last_result is None

    def test_get_user_stats_merged_with_history(self, temp_db_path, sample_word, all_words):
        """学習履歴がある場合、該当単語は更新された値、他はデフォルト値でマージされること"""
        db = LocalJsonDB(filepath=temp_db_path)
        db.record_attempt(
            email="learner@example.com",
            word_no=sample_word.no,
            word=sample_word.word,
            category=sample_word.category,
            is_correct=False,
            timestamp="2026-09-21T10:00:00+09:00",
        )

        stats = db.get_user_stats("learner@example.com")
        assert len(stats) == len(all_words)

        # 解答済み単語の確認
        learned_stat = stats[sample_word.no]
        assert learned_stat.total_attempts == 1
        assert learned_stat.incorrect_count == 1
        assert learned_stat.incorrect_rate == 1.0
        assert learned_stat.has_ever_failed is True
        assert learned_stat.last_result == "incorrect"
        assert learned_stat.last_attempt_at == "2026-09-21T10:00:00+09:00"

        # 未解答の単語（第2問以降）の確認
        other_word = all_words[1]
        other_stat = stats[other_word.no]
        assert other_stat.total_attempts == 0
        assert other_stat.has_ever_failed is False

    def test_custom_words_loader(self, temp_db_path):
        """カスタムの単語ローダー関数を指定できること"""
        custom_words = [
            WordItem(
                no=999,
                word="特別語",
                reading="とくべつご",
                category="テスト",
                meaning="意味",
                example="用例",
                tips="解説",
                difficulty="並",
            )
        ]
        db = LocalJsonDB(filepath=temp_db_path, words_loader=lambda: custom_words)
        stats = db.get_user_stats("user@example.com")
        assert len(stats) == 1
        assert 999 in stats
        assert stats[999].word == "特別語"


class TestLocalJsonDBRecordAttempt:
    """LocalJsonDB.record_attempt の記録・計算・永続化テスト"""

    def test_record_attempt_first_correct(self, temp_db_path, sample_word):
        """初回正解時の統計更新"""
        db = LocalJsonDB(filepath=temp_db_path)
        stat = db.record_attempt(
            email="student@example.com",
            word_no=sample_word.no,
            word=sample_word.word,
            category=sample_word.category,
            is_correct=True,
            timestamp="2026-09-21T11:00:00+09:00",
        )

        assert stat.word_no == sample_word.no
        assert stat.word == sample_word.word
        assert stat.category == sample_word.category
        assert stat.total_attempts == 1
        assert stat.incorrect_count == 0
        assert stat.incorrect_rate == 0.0
        assert stat.has_ever_failed is False
        assert stat.last_result == "correct"
        assert stat.last_attempt_at == "2026-09-21T11:00:00+09:00"

    def test_record_attempt_first_incorrect(self, temp_db_path, sample_word):
        """初回不正解時の統計更新"""
        db = LocalJsonDB(filepath=temp_db_path)
        stat = db.record_attempt(
            email="student@example.com",
            word_no=sample_word.no,
            word=sample_word.word,
            category=sample_word.category,
            is_correct=False,
            timestamp="2026-09-21T11:05:00+09:00",
        )

        assert stat.total_attempts == 1
        assert stat.incorrect_count == 1
        assert stat.incorrect_rate == 1.0
        assert stat.has_ever_failed is True
        assert stat.last_result == "incorrect"
        assert stat.last_attempt_at == "2026-09-21T11:05:00+09:00"

    def test_record_attempt_cumulative_and_rounding(self, temp_db_path, sample_word):
        """複数回答時の累積と不正解率（四捨五入小数点第3位）の検証"""
        db = LocalJsonDB(filepath=temp_db_path)
        email = "student@example.com"

        # 1回目: 不正解 (1/1 = 1.0)
        s1 = db.record_attempt(email, sample_word.no, sample_word.word, sample_word.category, False)
        assert s1.total_attempts == 1
        assert s1.incorrect_count == 1
        assert s1.incorrect_rate == 1.0

        # 2回目: 正解 (1/2 = 0.5)
        s2 = db.record_attempt(email, sample_word.no, sample_word.word, sample_word.category, True)
        assert s2.total_attempts == 2
        assert s2.incorrect_count == 1
        assert s2.incorrect_rate == 0.5
        assert s2.has_ever_failed is True  # 過去不正解フラグが保持される

        # 3回目: 正解 (1/3 = 0.333)
        s3 = db.record_attempt(email, sample_word.no, sample_word.word, sample_word.category, True)
        assert s3.total_attempts == 3
        assert s3.incorrect_count == 1
        assert s3.incorrect_rate == 0.333
        assert s3.has_ever_failed is True
        assert s3.last_result == "correct"

    def test_record_attempt_default_timestamp(self, temp_db_path, sample_word):
        """timestamp 引数未指定時に JST の現在時刻が設定されること"""
        db = LocalJsonDB(filepath=temp_db_path)
        stat = db.record_attempt(
            email="student@example.com",
            word_no=sample_word.no,
            word=sample_word.word,
            category=sample_word.category,
            is_correct=True,
        )
        assert stat.last_attempt_at is not None
        assert "+09:00" in stat.last_attempt_at

    def test_record_attempt_file_persistence(self, temp_db_path, sample_word):
        """記録結果がファイルに永続化され、新規DBインスタンスでも正しく復元されること"""
        db1 = LocalJsonDB(filepath=temp_db_path)
        db1.record_attempt(
            email="persist_user@example.com",
            word_no=sample_word.no,
            word=sample_word.word,
            category=sample_word.category,
            is_correct=False,
            timestamp="2026-09-21T12:00:00+09:00",
        )

        # 別のDBインスタンスを作成
        db2 = LocalJsonDB(filepath=temp_db_path)
        stats = db2.get_user_stats("persist_user@example.com")
        saved_stat = stats[sample_word.no]

        assert saved_stat.total_attempts == 1
        assert saved_stat.incorrect_count == 1
        assert saved_stat.has_ever_failed is True
        assert saved_stat.last_attempt_at == "2026-09-21T12:00:00+09:00"


class TestLocalJsonDBGetFailedWords:
    """LocalJsonDB.get_failed_words_stats の動作テスト"""

    def test_get_failed_words_stats_empty(self, temp_db_path):
        """学習履歴がない、または不正解がない場合は空リストが返ること"""
        db = LocalJsonDB(filepath=temp_db_path)
        assert db.get_failed_words_stats("user@example.com") == []

        # 正解のみの場合
        db.record_attempt("user@example.com", 1, "単語1", "カテゴリ1", True)
        assert db.get_failed_words_stats("user@example.com") == []

    def test_get_failed_words_stats_filtering_and_sorting(self, temp_db_path, all_words):
        """不正解歴のある単語のみが単語No順（昇順）で抽出されること"""
        db = LocalJsonDB(filepath=temp_db_path)
        email = "test@example.com"

        w10 = all_words[9]   # word_no = 10
        w2 = all_words[1]    # word_no = 2
        w5 = all_words[4]    # word_no = 5
        w1 = all_words[0]    # word_no = 1

        # w10: 不正解
        db.record_attempt(email, w10.no, w10.word, w10.category, False)
        # w2: 不正解
        db.record_attempt(email, w2.no, w2.word, w2.category, False)
        # w5: 正解のみ
        db.record_attempt(email, w5.no, w5.word, w5.category, True)
        # w1: 不正解ののちに正解
        db.record_attempt(email, w1.no, w1.word, w1.category, False)
        db.record_attempt(email, w1.no, w1.word, w1.category, True)

        failed_stats = db.get_failed_words_stats(email)
        # 不正解歴があるのは w1, w2, w10 の3語
        assert len(failed_stats) == 3
        # word_no 順でソートされていること (1, 2, 10)
        assert [s.word_no for s in failed_stats] == [w1.no, w2.no, w10.no]
        for s in failed_stats:
            assert s.has_ever_failed is True

    def test_get_failed_words_user_isolation(self, temp_db_path, all_words):
        """複数ユーザーの間違えた単語が互いに干渉しないこと"""
        db = LocalJsonDB(filepath=temp_db_path)
        w1 = all_words[0]
        w2 = all_words[1]

        # ユーザーAは w1 を間違える
        db.record_attempt("user_a@example.com", w1.no, w1.word, w1.category, False)
        # ユーザーBは w2 を間違える
        db.record_attempt("user_b@example.com", w2.no, w2.word, w2.category, False)

        failed_a = db.get_failed_words_stats("user_a@example.com")
        failed_b = db.get_failed_words_stats("user_b@example.com")

        assert len(failed_a) == 1
        assert failed_a[0].word_no == w1.no

        assert len(failed_b) == 1
        assert failed_b[0].word_no == w2.no


class TestLocalJsonDBReset:
    """LocalJsonDB.reset_user_stats の動作テスト"""

    def test_reset_user_stats(self, temp_db_path, sample_word):
        """リセット後にユーザー統計がクリアされ、初期状態に戻ること"""
        db = LocalJsonDB(filepath=temp_db_path)
        email = "reset_user@example.com"

        # 回答履歴を作成
        db.record_attempt(email, sample_word.no, sample_word.word, sample_word.category, False)
        assert len(db.get_failed_words_stats(email)) == 1

        # リセット実行
        db.reset_user_stats(email)

        # 間違えた単語が0件になること
        assert db.get_failed_words_stats(email) == []

        # 全単語統計が初期値に戻ること
        stats = db.get_user_stats(email)
        assert stats[sample_word.no].total_attempts == 0
        assert stats[sample_word.no].has_ever_failed is False

    def test_reset_user_stats_isolation(self, temp_db_path, sample_word):
        """ユーザーAをリセットしてもユーザーBのデータは維持されること"""
        db = LocalJsonDB(filepath=temp_db_path)
        db.record_attempt("user_a@example.com", sample_word.no, sample_word.word, sample_word.category, False)
        db.record_attempt("user_b@example.com", sample_word.no, sample_word.word, sample_word.category, False)

        db.reset_user_stats("user_a@example.com")

        assert db.get_failed_words_stats("user_a@example.com") == []
        assert len(db.get_failed_words_stats("user_b@example.com")) == 1


class TestGetDBFactory:
    """get_db ファクトリ関数の動作テスト"""

    def test_get_db_dev_mode_true(self, temp_db_path):
        """dev_mode=True で LocalJsonDB のインスタンスが返されること"""
        db = get_db(dev_mode=True, json_path=temp_db_path)
        assert isinstance(db, DatabaseInterface)
        assert isinstance(db, LocalJsonDB)
        assert db.filepath == temp_db_path

    def test_get_db_with_env_var(self, monkeypatch, temp_db_path):
        """環境変数 DEV_MODE に応じてインスタンスが生成されること"""
        monkeypatch.setenv("DEV_MODE", "True")
        db = get_db(dev_mode=None, json_path=temp_db_path)
        assert isinstance(db, LocalJsonDB)

        # DEV_MODE=False (現フェーズでは LocalJsonDB フォールバック)
        monkeypatch.setenv("DEV_MODE", "False")
        db_prod = get_db(dev_mode=None, json_path=temp_db_path)
        assert isinstance(db_prod, DatabaseInterface)


class TestConcurrencySafety:
    """スレッド並行書き込み時の整合性テスト"""

    def test_concurrent_record_attempts(self, temp_db_path, all_words):
        """マルチスレッドから同時に異なる単語を記録してもデータが破損しないこと"""
        db = LocalJsonDB(filepath=temp_db_path)
        email = "thread_test@example.com"
        target_words = all_words[:20]

        def record(w: WordItem):
            db.record_attempt(
                email=email,
                word_no=w.no,
                word=w.word,
                category=w.category,
                is_correct=False,
            )

        with ThreadPoolExecutor(max_workers=5) as executor:
            list(executor.map(record, target_words))

        failed_stats = db.get_failed_words_stats(email)
        assert len(failed_stats) == 20
        # 単語No順にソートされていること
        assert [s.word_no for s in failed_stats] == [w.no for w in target_words]
