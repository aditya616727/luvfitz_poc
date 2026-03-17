"""
Color harmony utilities for outfit scoring.
"""

# Color wheel groups – items in the same group are harmonious
COLOR_GROUPS = {
    "neutral": ["black", "white", "gray", "grey", "beige", "cream", "tan", "khaki", "ivory", "charcoal", "taupe"],
    "warm": ["red", "orange", "yellow", "gold", "coral", "salmon", "peach", "rust", "burgundy", "maroon", "wine"],
    "cool": ["blue", "navy", "teal", "cyan", "turquoise", "aqua", "indigo"],
    "earth": ["brown", "olive", "green", "forest", "sage", "moss", "army"],
    "pastel": ["pink", "lavender", "lilac", "mint", "baby blue", "light pink", "blush", "mauve", "periwinkle"],
    "bold": ["purple", "magenta", "fuchsia", "neon", "electric", "hot pink", "bright"],
}


def _classify_color(color: str) -> str | None:
    color_lower = color.lower() if color else ""
    for group, colors in COLOR_GROUPS.items():
        if any(c in color_lower for c in colors):
            return group
    return None


def color_harmony_score(colors: list[str]) -> float:
    """
    Score from 0 to 1 indicating how well colours go together.
    Neutrals go with everything; same group = great; mixed = okay.
    """
    groups = [_classify_color(c) for c in colors if c]
    groups = [g for g in groups if g is not None]

    if len(groups) <= 1:
        return 1.0

    neutral_count = groups.count("neutral")
    non_neutral = [g for g in groups if g != "neutral"]

    if not non_neutral:
        return 1.0  # all neutrals

    unique_non_neutral = set(non_neutral)

    if len(unique_non_neutral) == 1:
        return 1.0  # monochromatic + neutrals

    # Complementary pairs that work well
    good_pairs = {
        frozenset({"warm", "cool"}),
        frozenset({"earth", "warm"}),
        frozenset({"pastel", "neutral"}),
        frozenset({"cool", "earth"}),
    }

    if len(unique_non_neutral) == 2 and frozenset(unique_non_neutral) in good_pairs:
        return 0.85

    # The more variety, the lower the score
    score = max(0.3, 1.0 - (len(unique_non_neutral) - 1) * 0.2)
    # Bonus for neutrals
    score += min(0.15, neutral_count * 0.05)
    return min(1.0, score)
