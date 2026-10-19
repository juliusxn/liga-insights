import numpy as np
import pandas as pd

from src.utils import (
    compute_average_points_by_season_rank,
    compute_running_average,
    compute_running_average_ranking,
    plot_average_points_by_season_rank,
)


def _unique_object_pairs(pairs):
    clubs = {}
    for key, value in pairs:
        if key in clubs:
            raise AssertionError(f"Duplicate club ID: {key}")
        clubs[key] = value
    return clubs


def test_compute_running_average_uses_selected_years():
    rank_df = pd.DataFrame(
        {
            2019: {"club_a": 1, "club_b": 2},
            2020: {"club_a": np.nan, "club_b": 1},
            2021: {"club_a": 3, "club_b": np.nan},
        }
    )

    result = compute_running_average(rank_df, [2021, 2020])

    expected = pd.DataFrame(
        {
            2021: {"club_a": 3.0, "club_b": 4.0},
            2020: {"club_a": 2.5, "club_b": 2.5},
        }
    )
    pd.testing.assert_frame_equal(result, expected)


def test_compute_running_average_ranking_uses_selected_years():
    rank_df = pd.DataFrame(
        {
            2019: {"club_a": 1, "club_b": 2},
            2020: {"club_a": np.nan, "club_b": 1},
            2021: {"club_a": 3, "club_b": np.nan},
        }
    )

    result = compute_running_average_ranking(rank_df, [2020, 2021])

    expected = pd.DataFrame(
        {
            2020: {"club_a": 2, "club_b": 1},
            2021: {"club_a": 1, "club_b": 1},
        }
    )
    pd.testing.assert_frame_equal(result, expected)


def test_compute_average_points_by_season_rank_aggregates_points_and_event_std(tmp_path):
    data_dir = tmp_path / "data"
    result_file = data_dir / "league_1" / "2020" / "season.json"
    result_file.parent.mkdir(parents=True)
    result_file.write_text(
        '{"club_a": {"events": [1, 3], "season": 1}, ' '"club_b": {"events": [2, 4], "season": 2}}',
        encoding="utf-8",
    )
    manifest = {"competition": {"league_1": {"seasons": [{"year": 2020, "ranking_file": "league_1/2020/season.json"}]}}}

    result = compute_average_points_by_season_rank(data_dir, manifest)["league_1"]

    expected = pd.DataFrame(
        {
            "average_points": [2.0, 3.0],
            "std_event_results": [1.0, 1.0],
            "seasons": [1, 1],
        },
        index=pd.MultiIndex.from_tuples(
            [(2020, 1), (2020, 2)],
            names=["year", "season_rank"],
        ),
    )
    pd.testing.assert_frame_equal(result, expected)
