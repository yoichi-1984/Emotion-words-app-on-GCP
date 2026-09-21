"""data_loader.py

単語マスターデータ (raw_data/word-list/all_words.csv) の読み込み、
データモデル (WordItem) の定義、および Streamlit キャッシュ関数を提供するモジュール。
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Union
import pandas as pd
import streamlit as st


@dataclass(frozen=True)
class WordItem:
    """心情語単語モデル

    Attributes:
        no: 単語通し番号 (1 〜 272)
        category: 分類カテゴリ名 (例: "1. 恥・劣等感・気まずさ")
        word: 心情語・慣用表現 (例: "気後れ")
        reading: 読み仮名 (例: "きおくれ")
        difficulty: 入試難易度 ("並", "中", "高")
        meaning: 意味・ニュアンス
        example: 入試物語文での代表的な場面・文脈例
        tips: 小学生がつまずきやすい点・類語との識別ポイント
    """

    no: int
    category: str
    word: str
    reading: str
    difficulty: str
    meaning: str
    example: str
    tips: str


# CSVのカラム名マッピング
COLUMN_MAPPING = {
    "No": "no",
    "カテゴリ": "category",
    "心情語・慣用表現": "word",
    "読み": "reading",
    "難易度": "difficulty",
    "意味・ニュアンス": "meaning",
    "入試物語文での代表的な場面・文脈例": "example",
    "小学生がつまずきやすい点・類語との識別ポイント": "tips",
}


def find_default_csv_path() -> Path:
    """単語マスターデータ CSV のデフォルトパスを探索して取得する。

    Returns:
        Path: 見つかった all_words.csv のパス

    Raises:
        FileNotFoundError: ファイルが見つからない場合
    """
    candidates = [
        Path(__file__).resolve().parent / "raw_data" / "word-list" / "all_words.csv",
        Path.cwd() / "raw_data" / "word-list" / "all_words.csv",
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError(
        f"単語マスターデータ (all_words.csv) が見つかりません。探索先: {[str(c) for c in candidates]}"
    )


def parse_csv_to_words(csv_path: Union[str, Path]) -> List[WordItem]:
    """CSVファイルを読み込み、WordItemのリストに変換する。

    Args:
        csv_path: CSVファイルのパス

    Returns:
        List[WordItem]: 単語アイテムのリスト
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"指定されたCSVファイルが存在しません: {path}")

    # UTF-8 (BOMあり/なし両対応のため utf-8-sig を指定)
    df = pd.read_csv(path, encoding="utf-8-sig")

    # 列名の空白除去
    df.columns = [c.strip() for c in df.columns]

    # 必要カラムの存在確認
    missing_columns = set(COLUMN_MAPPING.keys()) - set(df.columns)
    if missing_columns:
        raise ValueError(
            f"CSVファイルに必要な列が存在しません: {missing_columns} (存在列: {list(df.columns)})"
        )

    # 欠損値を空文字に補完
    df = df.fillna("")

    words: List[WordItem] = []
    for _, row in df.iterrows():
        try:
            no_val = int(row["No"])
        except (ValueError, TypeError):
            no_val = 0

        item = WordItem(
            no=no_val,
            category=str(row["カテゴリ"]).strip(),
            word=str(row["心情語・慣用表現"]).strip(),
            reading=str(row["読み"]).strip(),
            difficulty=str(row["難易度"]).strip(),
            meaning=str(row["意味・ニュアンス"]).strip(),
            example=str(row["入試物語文での代表的な場面・文脈例"]).strip(),
            tips=str(row["小学生がつまずきやすい点・類語との識別ポイント"]).strip(),
        )
        words.append(item)

    return words


@st.cache_data(show_spinner=False)
def load_words(csv_path: Optional[Union[str, Path]] = None) -> List[WordItem]:
    """単語マスターデータをロードしてキャッシュする。

    Streamlit の @st.cache_data により、2回目以降のアクセスを高速化。

    Args:
        csv_path: 明示的に指定する場合のCSVパス。Noneの場合はデフォルトパスを探索。

    Returns:
        List[WordItem]: 全単語リスト (全272語)
    """
    target_path = Path(csv_path) if csv_path is not None else find_default_csv_path()
    return parse_csv_to_words(target_path)


def get_categories(words: List[WordItem]) -> List[str]:
    """単語リストから重複を除いたカテゴリ一覧を順序を維持して返す。

    Args:
        words: 単語リスト

    Returns:
        List[str]: カテゴリ名のリスト
    """
    seen = set()
    categories = []
    for item in words:
        if item.category and item.category not in seen:
            seen.add(item.category)
            categories.append(item.category)
    return categories


def filter_by_category(words: List[WordItem], category: str) -> List[WordItem]:
    """指定されたカテゴリに合致する単語のみを抽出する。

    Args:
        words: 単語リスト
        category: 絞り込みたいカテゴリ名

    Returns:
        List[WordItem]: フィルタ後の単語リスト
    """
    return [w for w in words if w.category == category]


def filter_by_difficulty(words: List[WordItem], difficulty: str) -> List[WordItem]:
    """指定された難易度に合致する単語のみを抽出する。

    Args:
        words: 単語リスト
        difficulty: 難易度 ("並", "中", "高")

    Returns:
        List[WordItem]: フィルタ後の単語リスト
    """
    return [w for w in words if w.difficulty == difficulty]


def search_words(words: List[WordItem], keyword: str) -> List[WordItem]:
    """キーワードで単語リストを検索する（部分一致）。

    心情語、読み、意味、場面例、つまずきポイントのいずれかにマッチするものを抽出。

    Args:
        words: 単語リスト
        keyword: 検索キーワード

    Returns:
        List[WordItem]: 検索結果の単語リスト
    """
    if not keyword or not keyword.strip():
        return words

    kw = keyword.strip().lower()
    return [
        w
        for w in words
        if kw in w.word.lower()
        or kw in w.reading.lower()
        or kw in w.meaning.lower()
        or kw in w.example.lower()
        or kw in w.tips.lower()
        or kw in w.category.lower()
    ]
