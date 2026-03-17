"""
Tests for color harmony scoring.
"""

from app.utils.colors import color_harmony_score


class TestColorHarmony:
    def test_all_same_color_group(self):
        score = color_harmony_score(["black", "white", "gray", "beige"])
        assert score == 1.0

    def test_monochromatic_with_neutral(self):
        score = color_harmony_score(["navy", "blue", "white"])
        assert score >= 0.9

    def test_complementary_colors(self):
        score = color_harmony_score(["red", "navy"])
        assert score >= 0.8

    def test_high_variety_lower_score(self):
        score = color_harmony_score(["red", "blue", "green", "purple"])
        assert score < 0.8

    def test_empty_colors(self):
        score = color_harmony_score([])
        assert score == 1.0

    def test_single_color(self):
        score = color_harmony_score(["black"])
        assert score == 1.0

    def test_unknown_colors(self):
        score = color_harmony_score(["chartreuse", "cerulean"])
        assert 0 <= score <= 1

    def test_all_neutrals(self):
        score = color_harmony_score(["black", "white", "gray", "cream"])
        assert score == 1.0
