import numpy as np
import pandas as pd

from src.utils import compute_running_average, compute_running_average_ranking


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
            2021: {"club_a": 1, "club_b": 2},
        }
    )
    pd.testing.assert_frame_equal(result, expected)
