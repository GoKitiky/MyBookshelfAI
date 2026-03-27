"""Tests for server-side recommendation match scoring."""

from app.models import ReaderProfile, WeightedTag
from app.services.recommendation_scoring import (
    apply_match_scores_to_recommendation_dicts,
    match_scores_for_recommendation_dicts,
    raw_profile_overlap,
    spread_match_scores,
)


def test_raw_profile_overlap_prefers_matching_tags() -> None:
    profile = ReaderProfile(
        top_genres=[WeightedTag(name="фантастика", weight=0.8)],
        top_themes=[WeightedTag(name="этика", weight=0.6)],
        favorite_authors=["Лем"],
    )
    strong = raw_profile_overlap(
        profile,
        ["научная фантастика"],
        ["моральные дилеммы", "этика"],
        "Станислав Лем",
    )
    weak = raw_profile_overlap(
        profile,
        ["любовный роман"],
        ["быт"],
        "Джейн Остин",
    )
    assert strong > weak


def test_spread_match_scores_orders_batch() -> None:
    out = spread_match_scores([0.2, 0.8])
    assert out[0] < out[1]
    tied = spread_match_scores([0.5, 0.5, 0.5])
    assert len(tied) == 3
    assert tied[0] > tied[1] > tied[2]


def test_match_scores_for_dicts_and_apply() -> None:
    profile = ReaderProfile(
        top_genres=[WeightedTag(name="фантастика", weight=0.9)],
        top_themes=[WeightedTag(name="дружба", weight=0.5)],
        favorite_authors=[],
    )
    items = [
        {
            "title": "A",
            "author": "X",
            "genres": ["фантастика"],
            "themes": ["дружба", "космос"],
        },
        {
            "title": "B",
            "author": "Y",
            "genres": ["детектив"],
            "themes": ["убийство"],
        },
    ]
    scores = match_scores_for_recommendation_dicts(profile, items)
    assert scores[0] > scores[1]

    raw = [{"title": "A", "author": "X", "genres": ["фантастика"], "themes": []}]
    fixed = apply_match_scores_to_recommendation_dicts(raw, profile)
    assert fixed[0]["match_score"] > 0

    # Weaker match first in input → sorted to descending match_score
    weak_first = [
        {
            "title": "B",
            "author": "Y",
            "genres": ["детектив"],
            "themes": ["убийство"],
        },
        {
            "title": "A",
            "author": "X",
            "genres": ["фантастика"],
            "themes": ["дружба", "космос"],
        },
    ]
    ordered = apply_match_scores_to_recommendation_dicts(weak_first, profile)
    assert ordered[0]["title"] == "A"
    assert ordered[0]["match_score"] >= ordered[1]["match_score"]
