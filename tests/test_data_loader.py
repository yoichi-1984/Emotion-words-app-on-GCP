"""tests/test_data_loader.py

data_loader.py の単体テストおよび all_words.csv のデータ整合性検証。
"""

from pathlib import Path
import tempfile
import pytest

from data_loader import (
    WordItem,
    find_default_csv_path,
    parse_csv_to_words,
    load_words,
    get_categories,
    filter_by_category,
    filter_by_difficulty,
    search_words,
)


@pytest.fixture(scope="module")
def all_words():
    """全単語データをロードするフィクスチャ"""
    return load_words()


class TestDataLoaderIntegrity:
    """単語マスターデータ (all_words.csv) の完全性・整合性テスト"""

    def test_default_csv_path_exists(self):
        """デフォルトCSVパスが実在すること"""
        csv_path = find_default_csv_path()
        assert csv_path.exists()
        assert csv_path.name == "all_words.csv"

    def test_total_word_count(self, all_words):
        """全272語が過不足なくロードされること"""
        assert len(all_words) == 272

    def test_word_numbers_sequential(self, all_words):
        """Noが1から272まで重複なく連番であること"""
        numbers = [w.no for w in all_words]
        assert len(numbers) == 272
        assert numbers == list(range(1, 273))

    def test_no_empty_or_whitespace_fields(self, all_words):
        """すべての単語において必須フィールドが空文字や空白のみでないこと"""
        for w in all_words:
            assert isinstance(w, WordItem)
            assert w.no > 0, f"不正なNo: {w}"
            assert w.category.strip() != "", f"空のカテゴリ: {w}"
            assert w.word.strip() != "", f"空の心情語: {w}"
            assert w.reading.strip() != "", f"空の読み: {w}"
            assert w.difficulty.strip() in {"並", "中", "高"}, f"不正な難易度: {w}"
            assert w.meaning.strip() != "", f"空の意味: {w}"
            assert w.example.strip() != "", f"空の文脈例: {w}"
            assert w.tips.strip() != "", f"空のつまずきポイント: {w}"

    def test_categories_count_and_distribution(self, all_words):
        """全8カテゴリが存在し、各カテゴリにちょうど34語ずつ配分されていること"""
        categories = get_categories(all_words)
        assert len(categories) == 8, f"カテゴリ数が8ではありません: {len(categories)}"

        for cat in categories:
            cat_words = filter_by_category(all_words, cat)
            assert len(cat_words) == 34, f"カテゴリ '{cat}' の単語数が34語ではありません (現在: {len(cat_words)}語)"

    def test_difficulty_distribution(self, all_words):
        """難易度が「並」「中」「高」のいずれかに分類され、合計が272語であること"""
        easy = filter_by_difficulty(all_words, "並")
        medium = filter_by_difficulty(all_words, "中")
        hard = filter_by_difficulty(all_words, "高")

        assert len(easy) > 0
        assert len(medium) > 0
        assert len(hard) > 0
        assert len(easy) + len(medium) + len(hard) == 272


class TestDataLoaderFunctions:
    """data_loader.py のユーティリティ関数の動作テスト"""

    def test_filter_by_category(self, all_words):
        """カテゴリによる絞り込み機能のテスト"""
        categories = get_categories(all_words)
        first_cat = categories[0]
        filtered = filter_by_category(all_words, first_cat)
        assert len(filtered) == 34
        assert all(w.category == first_cat for w in filtered)

        # 存在しないカテゴリ
        empty = filter_by_category(all_words, "存在しないカテゴリ")
        assert len(empty) == 0

    def test_filter_by_difficulty(self, all_words):
        """難易度による絞り込み機能のテスト"""
        for diff in ["並", "中", "高"]:
            filtered = filter_by_difficulty(all_words, diff)
            assert len(filtered) > 0
            assert all(w.difficulty == diff for w in filtered)

        # 存在しない難易度
        assert len(filter_by_difficulty(all_words, "超高")) == 0

    def test_search_words_empty_or_whitespace(self, all_words):
        """空文字や空白文字での検索時は全件が返ること"""
        assert len(search_words(all_words, "")) == 272
        assert len(search_words(all_words, "   ")) == 272

    def test_search_words_by_word(self, all_words):
        """心情語名による検索"""
        results = search_words(all_words, "気後れ")
        assert len(results) >= 1
        assert any(w.word == "気後れ" for w in results)

    def test_search_words_by_reading(self, all_words):
        """読み仮名による検索"""
        results = search_words(all_words, "きおくれ")
        assert len(results) >= 1
        assert any("きおくれ" in w.reading for w in results)

    def test_search_words_by_meaning(self, all_words):
        """意味キーワードによる検索"""
        results = search_words(all_words, "劣等感")
        assert len(results) >= 1
        assert any("劣等感" in w.meaning or "劣等感" in w.category for w in results)

    def test_search_words_no_match(self, all_words):
        """マッチしないキーワードの検索結果が空リストであること"""
        results = search_words(all_words, "xyz_non_existent_keyword_999")
        assert len(results) == 0


class TestDataLoaderErrorHandling:
    """例外処理・異常系のテスト"""

    def test_parse_csv_file_not_found(self):
        """存在しないパスを指定したときに FileNotFoundError が発生すること"""
        with pytest.raises(FileNotFoundError):
            parse_csv_to_words(Path("non_existent_dir/dummy.csv"))

    def test_parse_csv_missing_columns(self):
        """必須列が欠けているCSVを指定したときに ValueError が発生すること"""
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8-sig", delete=False, suffix=".csv") as f:
            f.write("No,カテゴリ,心情語・慣用表現\n1,カテゴリA,単語A\n")
            temp_path = Path(f.name)

        try:
            with pytest.raises(ValueError) as exc_info:
                parse_csv_to_words(temp_path)
            assert "必要な列が存在しません" in str(exc_info.value)
        finally:
            if temp_path.exists():
                temp_path.unlink()
