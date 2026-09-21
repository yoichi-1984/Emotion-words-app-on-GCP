"""db.py

中学受験 国語 心情語対策アプリケーションのデータベースアクセス層モジュール。
ユーザー学習履歴モデル (WordStat)、抽象インターフェース (DatabaseInterface)、
およびローカルJSONモック実装 (LocalJsonDB) を提供する。
"""

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import threading
from typing import Any, Callable, Dict, List, Optional, Union

from data_loader import WordItem, load_words

# 日本標準時 (JST: UTC+9)
JST = timezone(timedelta(hours=9))


def get_current_jst_iso() -> str:
    """現在の日時を JST (UTC+9) の ISO 8601 形式文字列で取得する。"""
    return datetime.now(JST).isoformat()


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

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WordStat":
        """辞書データから WordStat インスタンスを生成する。"""
        return cls(
            word_no=int(data["word_no"]),
            word=str(data["word"]),
            category=str(data["category"]),
            total_attempts=int(data.get("total_attempts", 0)),
            incorrect_count=int(data.get("incorrect_count", 0)),
            incorrect_rate=float(data.get("incorrect_rate", 0.0)),
            has_ever_failed=bool(data.get("has_ever_failed", False)),
            last_attempt_at=data.get("last_attempt_at"),
            last_result=data.get("last_result"),
        )


class DatabaseInterface(ABC):
    """データベースアクセスの共通インターフェース"""

    @abstractmethod
    def get_user_stats(self, email: str) -> Dict[int, WordStat]:
        """指定ユーザーの全単語統計を取得する。
        未出題の単語もデフォルト値の WordStat で埋めた辞書 {word_no: WordStat} を返す。
        """
        pass

    @abstractmethod
    def record_attempt(
        self,
        email: str,
        word_no: int,
        word: str,
        category: str,
        is_correct: bool,
        timestamp: Optional[str] = None,
    ) -> WordStat:
        """1問の回答結果を保存・更新し、更新後の WordStat を返す。"""
        pass

    @abstractmethod
    def get_failed_words_stats(self, email: str) -> List[WordStat]:
        """過去に一度でも間違えた（has_ever_failed == True）単語統計のリストを取得する。"""
        pass

    @abstractmethod
    def reset_user_stats(self, email: str) -> None:
        """指定ユーザーの統計履歴をリセット（初期化）する。"""
        pass


class LocalJsonDB(DatabaseInterface):
    """ローカルJSONファイルを用いたモックDB実装"""

    DEFAULT_PATH = Path("local_data") / "mock_user_stats.json"

    def __init__(
        self,
        filepath: Optional[Union[str, Path]] = None,
        words_loader: Optional[Callable[[], List[WordItem]]] = None,
    ) -> None:
        """LocalJsonDB を初期化する。

        Args:
            filepath: 保存先JSONファイルのパス（未指定時は local_data/mock_user_stats.json）
            words_loader: 単語マスターデータ取得関数（未指定時は data_loader.load_words）
        """
        self.filepath = Path(filepath) if filepath is not None else self.DEFAULT_PATH
        self.words_loader = words_loader or load_words
        self._lock = threading.Lock()
        self._ensure_file_exists()

    def _ensure_file_exists(self) -> None:
        """ファイルおよび親ディレクトリの存在を確認・生成する。"""
        with self._lock:
            if not self.filepath.parent.exists():
                self.filepath.parent.mkdir(parents=True, exist_ok=True)
            if not self.filepath.exists():
                self._write_raw({"users": {}})

    def _read_raw(self) -> Dict[str, Any]:
        """JSONファイルから生データを読み込む（ロック内部で使用）。"""
        if not self.filepath.exists():
            return {"users": {}}
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {"users": {}}

    def _write_raw(self, data: Dict[str, Any]) -> None:
        """JSONファイルに生データを書き込む（ロック内部で使用）。"""
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_user_stats(self, email: str) -> Dict[int, WordStat]:
        """指定ユーザーの全単語統計を取得する。
        単語マスターに基づき、全272語のデフォルト辞書に保存済みデータをマージして返す。
        """
        all_words = self.words_loader()
        stats_dict: Dict[int, WordStat] = {}

        # 1. 全単語のデフォルト統計を初期化
        for w in all_words:
            stats_dict[w.no] = WordStat(
                word_no=w.no,
                word=w.word,
                category=w.category,
                total_attempts=0,
                incorrect_count=0,
                incorrect_rate=0.0,
                has_ever_failed=False,
                last_attempt_at=None,
                last_result=None,
            )

        # 2. 保存されているユーザー統計を上書きマージ
        with self._lock:
            raw_data = self._read_raw()
            user_data = raw_data.get("users", {}).get(email, {})
            user_stats = user_data.get("stats", {})

            for word_no_str, stat_dict in user_stats.items():
                try:
                    word_no = int(word_no_str)
                    stat = WordStat.from_dict(stat_dict)
                    stats_dict[word_no] = stat
                except (ValueError, KeyError):
                    continue

        return stats_dict

    def record_attempt(
        self,
        email: str,
        word_no: int,
        word: str,
        category: str,
        is_correct: bool,
        timestamp: Optional[str] = None,
    ) -> WordStat:
        """1問の回答結果を保存・更新し、更新後の WordStat を返す。"""
        record_time = timestamp or get_current_jst_iso()

        with self._lock:
            data = self._read_raw()
            if "users" not in data:
                data["users"] = {}
            if email not in data["users"]:
                data["users"][email] = {
                    "email": email,
                    "last_login_at": record_time,
                    "stats": {},
                }

            user_entry = data["users"][email]
            stats_map = user_entry.setdefault("stats", {})
            word_no_str = str(word_no)

            if word_no_str in stats_map:
                current_stat = WordStat.from_dict(stats_map[word_no_str])
            else:
                current_stat = WordStat(
                    word_no=word_no,
                    word=word,
                    category=category,
                    total_attempts=0,
                    incorrect_count=0,
                    incorrect_rate=0.0,
                    has_ever_failed=False,
                )

            # 統計値の更新
            current_stat.total_attempts += 1
            if not is_correct:
                current_stat.incorrect_count += 1
                current_stat.has_ever_failed = True

            current_stat.incorrect_rate = round(
                current_stat.incorrect_count / current_stat.total_attempts, 3
            )
            current_stat.last_result = "correct" if is_correct else "incorrect"
            current_stat.last_attempt_at = record_time

            # 保存
            stats_map[word_no_str] = current_stat.to_dict()
            self._write_raw(data)

            return current_stat

    def get_failed_words_stats(self, email: str) -> List[WordStat]:
        """過去に一度でも間違えた（has_ever_failed == True）単語統計のリストを取得する。
        単語No順でソートして返す。
        """
        with self._lock:
            data = self._read_raw()
            user_data = data.get("users", {}).get(email, {})
            user_stats = user_data.get("stats", {})

            failed_stats: List[WordStat] = []
            for stat_dict in user_stats.values():
                try:
                    stat = WordStat.from_dict(stat_dict)
                    if stat.has_ever_failed:
                        failed_stats.append(stat)
                except (ValueError, KeyError):
                    continue

            failed_stats.sort(key=lambda s: s.word_no)
            return failed_stats

    def reset_user_stats(self, email: str) -> None:
        """指定ユーザーの統計履歴をリセット（初期化）する。"""
        with self._lock:
            data = self._read_raw()
            if "users" in data and email in data["users"]:
                data["users"][email]["stats"] = {}
                self._write_raw(data)


def get_db(
    dev_mode: Optional[bool] = None,
    json_path: Optional[Union[str, Path]] = None,
) -> DatabaseInterface:
    """環境設定に応じた DatabaseInterface インスタンスを生成・返却するファクトリ関数。

    Args:
        dev_mode: True の場合 LocalJsonDB。None の場合は環境変数 DEV_MODE を参照。
        json_path: LocalJsonDB を利用する場合のカスタムファイルパス。

    Returns:
        DatabaseInterface: DBアクセスクライアント
    """
    if dev_mode is None:
        dev_mode_env = os.getenv("DEV_MODE", "True").lower()
        dev_mode = dev_mode_env in ("true", "1", "t", "yes")

    if dev_mode:
        return LocalJsonDB(filepath=json_path)

    # 本番モード (DEV_MODE=False) の場合:
    # Phase 2 タスク16で FirestoreDB が追加された際に切り替え可能とする。
    # 現時点では LocalJsonDB をフォールバック利用。
    return LocalJsonDB(filepath=json_path)
