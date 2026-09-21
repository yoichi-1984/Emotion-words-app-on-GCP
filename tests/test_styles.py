"""tests/test_styles.py

styles.py のカスタムCSS・カラー定数・UIコンポーネントHTML生成ヘルパーの検証テスト。
"""

from unittest.mock import MagicMock, patch
import pytest

import styles


class TestColorConstantsAndCSS:
    """カラー定数およびカスタムCSS文字列の整合性検証"""

    def test_color_constants(self):
        """カラー定数が期待通りのHEXコードで定義されていること"""
        assert styles.PRIMARY_COLOR.startswith("#")
        assert styles.PRIMARY_LIGHT.startswith("#")
        assert styles.SECONDARY_COLOR.startswith("#")
        assert styles.SUCCESS_COLOR.startswith("#")
        assert styles.ERROR_COLOR.startswith("#")
        assert styles.BG_COLOR.startswith("#")

        # 難易度別カラーの検証
        for diff in ["並", "中", "高"]:
            assert diff in styles.DIFF_COLORS
            assert "bg" in styles.DIFF_COLORS[diff]
            assert "text" in styles.DIFF_COLORS[diff]
            assert "border" in styles.DIFF_COLORS[diff]

    def test_custom_css_requirements(self):
        """CSS内に仕様書記載の必須セレクタとプロパティが含まれていること"""
        css = styles.get_custom_css()
        assert isinstance(css, str)
        assert css == styles.CUSTOM_CSS

        # ボタンのタップ領域拡大（52px, 12px丸角）
        assert "div.stButton > button" in css
        assert "min-height: 52px;" in css
        assert "border-radius: 12px;" in css

        # 4択ラジオボタンの押しやすさ向上
        assert 'div[role="radiogroup"] > label' in css
        assert 'div[role="radiogroup"] > label[data-checked="true"]' in css

        # 問題文カード
        assert ".question-card" in css
        assert "#81C784" in css

        # 判定バナー・バッジ・統計カード
        assert ".result-banner-correct" in css
        assert ".result-banner-incorrect" in css
        assert ".stat-card" in css
        assert ".badge" in css

    def test_apply_custom_styles(self):
        """apply_custom_styles が st.markdown を unsafe_allow_html=True で呼ぶこと"""
        with patch("streamlit.markdown") as mock_markdown:
            styles.apply_custom_styles()
            mock_markdown.assert_called_once()
            call_args, call_kwargs = mock_markdown.call_args
            assert "<style>" in call_args[0]
            assert styles.CUSTOM_CSS in call_args[0]
            assert call_kwargs.get("unsafe_allow_html") is True


class TestBadgeRendering:
    """render_badge の検証"""

    def test_render_diff_badges(self):
        """難易度バッジが適切なCSSクラスで出力されること"""
        badge_low = styles.render_badge("並", badge_type="diff_並")
        assert "badge-diff-low" in badge_low
        assert "並" in badge_low

        badge_mid = styles.render_badge("中", badge_type="diff_中")
        assert "badge-diff-mid" in badge_mid
        assert "中" in badge_mid

        badge_high = styles.render_badge("高", badge_type="diff_high")
        assert "badge-diff-high" in badge_high
        assert "高" in badge_high

    def test_render_category_and_default_badges(self):
        """カテゴリバッジとデフォルトバッジの出力"""
        badge_cat = styles.render_badge("喜び・安心", badge_type="category")
        assert "badge-category" in badge_cat
        assert "喜び・安心" in badge_cat

        badge_def = styles.render_badge("一般")
        assert "badge-outline" in badge_def

    def test_render_badge_html_escape(self):
        """悪意あるタグや特殊文字がエスケープされること"""
        badge = styles.render_badge("<script>alert('xss')</script>&")
        assert "<script>" not in badge
        assert "&lt;script&gt;" in badge
        assert "&amp;" in badge


class TestQuestionCardRendering:
    """render_question_card の検証"""

    def test_render_basic_question_card(self):
        """基本項目のカードHTML生成"""
        html_out = styles.render_question_card(
            content="気が置けない",
            label="この言葉の意味を選ぼう",
            subtext="中学入試頻出の心情語です",
        )
        assert 'class="question-card"' in html_out
        assert "気が置けない" in html_out
        assert "この言葉の意味を選ぼう" in html_out
        assert "中学入試頻出の心情語です" in html_out

    def test_render_question_card_with_badges(self):
        """カテゴリと難易度バッジを含むカードHTML生成"""
        html_out = styles.render_question_card(
            content="テスト単語",
            category="不安・恐れ",
            difficulty="高",
        )
        assert "不安・恐れ" in html_out
        assert "難易度: 高" in html_out
        assert "badge-diff-high" in html_out
        assert "badge-category" in html_out

    def test_render_question_card_escaping(self):
        """カード内容がHTMLエスケープされること"""
        html_out = styles.render_question_card(
            content="<img src=x onerror=alert(1)>",
            label="<label>",
            subtext="<sub>",
        )
        assert "<img src=x" not in html_out
        assert "&lt;img src=x" in html_out
        assert "&lt;label&gt;" in html_out
        assert "&lt;sub&gt;" in html_out


class TestResultBannerRendering:
    """render_result_banner の検証"""

    def test_render_correct_banner(self):
        """正解時のバナー出力"""
        banner = styles.render_result_banner(is_correct=True)
        assert "result-banner-correct" in banner
        assert "⭕ 正解！" in banner
        assert "すばらしい" in banner

    def test_render_incorrect_banner_without_detail(self):
        """詳細なしの不正解バナー出力"""
        banner = styles.render_result_banner(is_correct=False)
        assert "result-banner-incorrect" in banner
        assert "❌ おしい！" in banner
        assert "苦手ノート" in banner

    def test_render_incorrect_banner_with_detail(self):
        """正解単語・正解意味付きの不正解バナー出力"""
        banner = styles.render_result_banner(
            is_correct=False,
            correct_word="気後れ",
            correct_meaning="相手の勢いに圧倒されて、心がひるむこと。",
        )
        assert "result-banner-incorrect" in banner
        assert "気後れ" in banner
        assert "相手の勢いに圧倒されて、心がひるむこと。" in banner


class TestStatAndWordDetailRendering:
    """render_stat_card および render_word_detail_card の検証"""

    def test_render_stat_card(self):
        """統計サマリーカードの出力"""
        card = styles.render_stat_card(
            label="苦手語句数",
            value="15語",
            subtext="全272語中",
        )
        assert "stat-card" in card
        assert "苦手語句数" in card
        assert "15語" in card
        assert "全272語中" in card

    def test_render_word_detail_card(self):
        """単語詳細カードの出力"""
        card = styles.render_word_detail_card(
            word="憮然",
            reading="ぶぜん",
            category="怒り・不満",
            difficulty="高",
            meaning="失望や不満のために、ぼんやりとしたり不機嫌になったりする様子。",
            example="期待していた結果が出ず、憮然として席を立った。",
            point="「ぶぜんとする」を単に怒っていると誤解しやすい。",
        )
        assert "word-detail-card" in card
        assert "憮然" in card
        assert "ぶぜん" in card
        assert "怒り・不満" in card
        assert "難易度: 高" in card
        assert "失望や不満のために" in card
        assert "物語文での場面例" in card
        assert "つまずきポイント・識別" in card


class TestDisplayHelpers:
    """Streamlit描画ヘルパー（display_*）の検証"""

    def test_display_helpers_call_st_markdown(self):
        """各描画ヘルパーが st.markdown(..., unsafe_allow_html=True) を呼ぶこと"""
        with patch("streamlit.markdown") as mock_markdown:
            styles.display_question_card("単語")
            assert mock_markdown.call_count == 1
            assert mock_markdown.call_args[1].get("unsafe_allow_html") is True

            styles.display_result_banner(True)
            assert mock_markdown.call_count == 2
            assert mock_markdown.call_args[1].get("unsafe_allow_html") is True

            styles.display_stat_card("ラベル", "値")
            assert mock_markdown.call_count == 3
            assert mock_markdown.call_args[1].get("unsafe_allow_html") is True

            styles.display_word_detail_card(
                word="テスト",
                reading="てすと",
                category="喜び",
                difficulty="並",
                meaning="意味",
            )
            assert mock_markdown.call_count == 4
            assert mock_markdown.call_args[1].get("unsafe_allow_html") is True
